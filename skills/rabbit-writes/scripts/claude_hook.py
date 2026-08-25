#!/usr/bin/env python3
"""
claude_hook.py - the Claude Code hook runner, for two events.

A skill enforces a voice when somebody invokes it, and the pre-commit hooks
enforce one at commit. Between those two moments the model writes in its own
register and nothing says so. These are the two host events that close that
gap:

  SessionStart    resolve the voice and say which profile is in force, or that
                  none is and which command claims one. A note printed by a
                  scanner nobody ran is a note nobody reads, and `voices/ACTIVE`
                  being empty is the shipped state, so the moment a session
                  starts is the one place that fact reaches anybody.

  PostToolUse     on Write and Edit, scan the file that was just written and
                  hand the findings back. Same check the `rabbit-scan`
                  pre-commit hook runs, one layer earlier: at commit it is a
                  blocked commit, and here it is still the turn that wrote the
                  prose.

Three rules govern everything below, and each of them is the difference between
a hook people keep and a hook people delete.

**Exit 0, always, and speak through JSON.** `PostToolUse` is a non-blocking
event, so exit 2 only prints stderr as a notice beside the tool result. The
channel that actually reaches the model is
`hookSpecificOutput.additionalContext`, which is where a finding has to land for
anything to be done about it in the same turn.

**Never fail the turn.** Unparseable stdin, a missing file, a scanner that
raises, a Python that cannot import json: every one of them exits 0 with an
empty stdout. A prose linter that breaks a coding session is uninstalled the
same day, and there is nothing this hook could report that is worth that.

**Say nothing when there is nothing to say.** Prose extensions only, silence on
a clean scan, silence on a file outside the working tree. A hook that speaks on
every file write teaches people to ignore it, which costs the P0s as well.

The scan runs `scan.py --json` in a subprocess rather than importing it. The
hook is a separate process either way, `scan.py`'s own `main()` already owns
voice resolution, register detection, and the suppression pass, and a second
in-process path through the engine is a second thing that can disagree with
what the scanner actually reports. It costs about 0.1 seconds.

Stdlib only, 3.9+.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN_PATH = os.path.join(HERE, "scan.py")

# Prose only. A voice profile has nothing to say about a .py file, and the
# engine's stylometric bands are calibrated on English prose, so a scan of
# source code is noise wearing a finding's clothes.
PROSE_EXTENSIONS = (".md", ".markdown", ".txt", ".rst")

# What is worth interrupting for. A P2 is polish and an advisory, and the
# pre-commit hooks gate on P0 for the same reason: a hook that speaks about
# polish is one people learn to ignore.
REPORT_PRIORITIES = ("P0", "P1")

# Past this many, the hook names the count and the worst few rather than
# pasting a report into the context window.
MAX_REPORTED = 8

# The scanner takes about 0.1 seconds on a small document. This is a backstop
# against a pathological input, not a budget.
SCAN_TIMEOUT = 25


def _emit(event, context=None, system_message=None):
    """The one way this script speaks. Exits 0 by every path."""
    payload = {}
    if context:
        payload["hookSpecificOutput"] = {
            "hookEventName": event,
            "additionalContext": context,
        }
    if system_message:
        payload["systemMessage"] = system_message
    if payload:
        sys.stdout.write(json.dumps(payload))
    sys.exit(0)


def _voice_note():
    """(voice_name, note) through the engine's own resolver.

    Imported rather than shelled out to, because this is the one question with
    an answer and no document: `resolve` reads a `.rabbit-voice` beside the
    working directory and then `voices/ACTIVE`, and returns the note saying
    which decided.
    """
    sys.path.insert(0, HERE)
    from rwlib import voices as voices_mod
    return voices_mod.resolve()


def on_session_start(payload):
    rules, name, note = _voice_note()
    if rules and name:
        _emit("SessionStart",
              context=("rabbit-writes: the active writing voice is %s. Prose "
                       "written for the user to send or publish follows that "
                       "profile. Run the rabbit-writes skill to load it in "
                       "full." % name),
              system_message="rabbit-writes: voice %s is active." % name)
    # No voice. The note already names the installed profiles and the command
    # that claims one, and it is the only thing here worth a line.
    if note:
        _emit("SessionStart",
              context="rabbit-writes: no writing voice is active. %s" % note,
              system_message="rabbit-writes: no voice active.")
    _emit("SessionStart")


def _target_path(payload):
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(path, str) or not path.strip():
        return None
    if not path.lower().endswith(PROSE_EXTENSIONS):
        return None
    if not os.path.isfile(path):
        return None
    return path


def _scan(path):
    """The scanner's --json document, or None if anything at all went wrong."""
    argv = [sys.executable, SCAN_PATH, path, "--json", "--voice", "auto",
            "--profile", "auto"]
    try:
        proc = subprocess.run(argv, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, timeout=SCAN_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    # A nonzero exit is the norm here rather than an error: scan.py --check
    # exits on findings, and --json still wrote the document. An unparseable
    # stdout is the actual failure and it is silent on purpose.
    try:
        return json.loads(proc.stdout.decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return None


def _format(path, doc):
    findings = [f for f in doc.get("findings", [])
                if isinstance(f, dict)
                and f.get("priority") in REPORT_PRIORITIES
                and "suppressed" not in f]
    if not findings:
        return None

    # Worst first, and the safety band ahead of everything at the same
    # priority: a concealed instruction in a file the model just wrote is not
    # a style note.
    order = {"P0": 0, "P1": 1, "P2": 2}
    findings.sort(key=lambda f: (order.get(f.get("priority"), 9),
                                 0 if f.get("band") == "safety" else 1,
                                 f.get("line") or 0))

    shown = findings[:MAX_REPORTED]
    lines = ["rabbit-writes scanned %s and found %d issue%s."
             % (os.path.basename(path), len(findings),
                "" if len(findings) == 1 else "s")]
    voice = doc.get("voice")
    if voice:
        lines.append("Active voice: %s." % voice)
    lines.append("")
    for f in shown:
        match = str(f.get("match", "")).strip()
        lines.append("- %s line %s: %s%s"
                     % (f.get("priority"), f.get("line"), f.get("label"),
                        (' ("%s")' % match) if match else ""))
    cut = len(findings) - len(shown)
    if cut > 0:
        lines.append("- and %d more." % cut)
    lines.append("")
    lines.append("Fix these if the file is prose the user will send or "
                 "publish. Ignore them if it is a fixture, a quoted example, "
                 "or a document that trips a rule on purpose, and say which. "
                 "Full report: python3 %s %s --voice auto"
                 % (SCAN_PATH, path))
    return "\n".join(lines)


def on_post_tool_use(payload):
    path = _target_path(payload)
    if not path:
        _emit("PostToolUse")
    doc = _scan(path)
    if not doc:
        _emit("PostToolUse")
    _emit("PostToolUse", context=_format(path, doc))


HANDLERS = {
    "SessionStart": on_session_start,
    "PostToolUse": on_post_tool_use,
}


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0
    handler = HANDLERS.get(payload.get("hook_event_name"))
    if handler is None:
        return 0
    handler(payload)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        # The whole point. Whatever went wrong here, it is not worth the
        # user's turn, and stderr on a non-blocking event only adds a notice
        # nobody asked for.
        sys.exit(0)
