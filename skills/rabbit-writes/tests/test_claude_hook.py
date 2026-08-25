#!/usr/bin/env python3
"""
The Claude Code hook runner, over the payloads the host actually sends.

The contract this file exists to hold is narrow and absolute: **exit 0 by every
path, and say nothing when there is nothing to say.** A prose linter that
breaks a coding session gets uninstalled the same day, and there is no finding
worth that. So the interesting tests here are the ones where the answer is
silence.

Stdlib only, 3.9+. Tests take no arguments.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import helpers  # noqa: E402

HOOK = os.path.join(helpers.SCRIPTS, "claude_hook.py")


def run(payload, cwd=None):
    """(stdout, exit_code) for one hook invocation."""
    if not isinstance(payload, (str, bytes)):
        payload = json.dumps(payload)
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    proc = subprocess.run([sys.executable, HOOK], input=payload,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          cwd=cwd or helpers.ROOT)
    return proc.stdout.decode("utf-8"), proc.returncode


def write(tmp, name, text):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def test_every_malformed_input_exits_zero_and_says_nothing():
    """The rule, stated as a table. Each of these is a real shape: a host that
    changed its payload, a tool call with no file, an event nobody handles."""
    cases = [
        ("not json at all", "unparseable stdin"),
        ("", "empty stdin"),
        ("[1, 2, 3]", "a JSON array rather than an object"),
        ('{"hook_event_name": "PreToolUse"}', "an event with no handler"),
        ('{"hook_event_name": "PostToolUse"}', "no tool_input"),
        ('{"hook_event_name": "PostToolUse", "tool_input": "nope"}',
         "tool_input that is not an object"),
        ('{"hook_event_name": "PostToolUse", "tool_input": {}}',
         "tool_input with no file_path"),
        ('{"hook_event_name": "PostToolUse", "tool_input": '
         '{"file_path": "/no/such/file.md"}}', "a file that is not there"),
    ]
    for payload, why in cases:
        out, code = run(payload)
        assert code == 0, "%s exited %d" % (why, code)
        assert out == "", "%s printed %r" % (why, out)


def test_a_source_file_is_not_scanned():
    """A voice profile has nothing to say about Python, and the stylometric
    bands are calibrated on English prose."""
    out, code = run({"hook_event_name": "PostToolUse", "tool_name": "Write",
                     "tool_input": {"file_path": HOOK}})
    assert code == 0, code
    assert out == "", out


def test_clean_prose_is_silent():
    """A hook that speaks on every write teaches people to ignore it, which
    costs the P0s as well."""
    with tempfile.TemporaryDirectory() as tmp:
        path = write(tmp, "clean.md",
                     "The migration finished overnight and the numbers held.\n")
        out, code = run({"hook_event_name": "PostToolUse",
                         "tool_input": {"file_path": path}}, cwd=tmp)
        assert code == 0, code
        assert out == "", out


def test_a_finding_comes_back_as_additional_context():
    """`PostToolUse` is non-blocking, so exit 2 only prints a notice beside the
    tool result. additionalContext is the channel that reaches the model in
    the turn that wrote the file."""
    with tempfile.TemporaryDirectory() as tmp:
        path = write(tmp, "draft.md",
                     "We need to delve into the results before shipping.\n")
        out, code = run({"hook_event_name": "PostToolUse",
                         "tool_input": {"file_path": path}}, cwd=tmp)
        assert code == 0, code
        doc = json.loads(out)
        context = doc["hookSpecificOutput"]["additionalContext"]
        assert doc["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
        assert "delve into" in context, context
        assert "draft.md" in context, context


def test_a_p2_alone_does_not_speak():
    """The pre-commit hooks gate on P0 for the same reason: a hook that
    interrupts over polish is one people learn to pass --no-verify to."""
    with tempfile.TemporaryDirectory() as tmp:
        # A curly apostrophe is a P2 in the default register and nothing else.
        # Written as an escape, never as a literal: any tool that normalizes
        # punctuation turns it into a plain quote and the fixture stops
        # exercising anything, without changing a character a reader can see.
        path = write(tmp, "polish.md",
                     "The build finished and the numbers held. "
                     "Nothing here is wrong\u2019s worth blocking a turn.\n")
        out, code = run({"hook_event_name": "PostToolUse",
                         "tool_input": {"file_path": path}}, cwd=tmp)
        assert code == 0, code
        if out:
            doc = json.loads(out)
            context = doc["hookSpecificOutput"]["additionalContext"]
            for line in context.splitlines():
                assert not line.startswith("- P2"), context


def test_session_start_names_the_active_voice():
    """The repository pins its own house voice with a root `.rabbit-voice`,
    which is the mechanism a consumer uses too."""
    out, code = run({"hook_event_name": "SessionStart"}, cwd=helpers.ROOT)
    assert code == 0, code
    doc = json.loads(out)
    assert "whit3rabbit" in doc["hookSpecificOutput"]["additionalContext"]
    assert "whit3rabbit" in doc["systemMessage"]


def test_session_start_with_no_voice_names_the_command_that_claims_one():
    """`voices/ACTIVE` being empty is the shipped state, and a note printed by
    a scanner nobody ran is a note nobody reads. This is the one moment that
    fact reaches anybody."""
    with tempfile.TemporaryDirectory() as tmp:
        out, code = run({"hook_event_name": "SessionStart"}, cwd=tmp)
        assert code == 0, code
        doc = json.loads(out)
        context = doc["hookSpecificOutput"]["additionalContext"]
        assert "no writing voice is active" in context, context
        assert "--activate" in context, context


def test_the_command_the_note_prints_is_one_that_runs():
    """It was not, for the whole life of the message.

    `resolve` told a fresh install to run `build_voice.py --activate <name>`,
    and `--activate` is a flag on a required mode group, so that invocation
    exits 2 on "one of the arguments --scaffold --check is required". It is
    the single line standing between a fresh install and an enforced voice,
    and nothing was checking that it parsed.
    """
    import re
    from rwlib import voices as voices_mod
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd()
        try:
            os.chdir(tmp)
            _rules, _name, note = voices_mod.resolve()
        finally:
            os.chdir(cwd)
    assert note and "--activate" in note, note
    m = re.search(r"build_voice\.py ([^`]+)", note)
    assert m, note
    argv = m.group(1).split()
    assert "--check" in argv or "--scaffold" in argv, (
        "the note prints `build_voice.py %s`, and build_voice.py requires one "
        "of --scaffold or --check" % " ".join(argv))


def test_the_path_the_note_prints_is_a_file_that_is_there():
    """The other half of the same fact, and it was wrong the same way.

    The note named `skills/voice-setup/scripts/build_voice.py`, which is right
    in a checkout and wrong in every packaged bundle, where this file sits at
    `<bundle>/scripts/rwlib/voices.py` and there is no `skills/` above it.
    `package_skills.py` rewrites markdown paths per layout and never touches a
    string inside Python, so nothing upstream was going to catch it.

    Run from two different working directories, because the path is printed
    relative to the one it can be printed relative to.
    """
    import re
    from rwlib import voices as voices_mod
    for cwd_name, where in (("the repository", helpers.ROOT), ("elsewhere", None)):
        with tempfile.TemporaryDirectory() as tmp:
            here = os.getcwd()
            try:
                os.chdir(where or tmp)
                command = voices_mod.build_voice_command()
            finally:
                os.chdir(here)
            m = re.search(r"python3 (\S+) --check", command)
            assert m, "%s: %r names no script" % (cwd_name, command)
            path = m.group(1)
            resolved = path if os.path.isabs(path) else os.path.join(
                where or tmp, path)
            assert os.path.isfile(resolved), (
                "%s: the note tells somebody to run %s, and there is no file "
                "there" % (cwd_name, resolved))


def test_an_unrelatable_path_falls_back_instead_of_raising():
    """`relpath` raises on Windows across drives, and `resolve` calls this on
    every `--voice auto` scan, so the note would have become a traceback for a
    plugin on C: and a document on D:."""
    from rwlib import voices as voices_mod

    real = os.path.relpath

    def explode(path, start=None):
        raise ValueError("path is on mount 'C:', start on mount 'D:'")

    os.path.relpath = explode
    try:
        command = voices_mod.build_voice_command()
    finally:
        os.path.relpath = real
    assert "build_voice.py" in command, command
    assert os.path.isabs(command.split("python3 ", 1)[1].split(" --check")[0]), \
        command


def test_the_note_names_the_skill_when_the_script_is_not_bundled():
    """Four of the five bundles vendor rwlib without build_voice.py, because
    only voice-setup builds profiles. There is no path to name there, and
    naming the skill is the right answer rather than a degraded one.

    A bare `<tmp>/scripts/rwlib` is exactly the shape of a bundle with the
    script missing, which is why this can be asserted without unpacking one.
    """
    from rwlib import voices as voices_mod
    with tempfile.TemporaryDirectory() as tmp:
        fake = os.path.join(tmp, "scripts", "rwlib")
        os.makedirs(fake)
        assert voices_mod.build_voice_path(here=fake) is None
        command = voices_mod.build_voice_command(here=fake)
    assert "voice-setup" in command, command
    assert "python3" not in command, (
        "the fallback offers a command that names no script: %r" % command)


def test_the_repository_still_prints_the_relative_path_it_always_did():
    """The message a person copy-pastes from a checkout root should not have
    become an absolute path on this machine as a side effect of fixing the
    bundles.

    The repository root, not `helpers.ROOT`, which is the skill root two levels
    below it. From the skill root `skills/voice-setup/...` is a `../` path and
    correctly prints absolute, so asserting against that would have been
    asserting the opposite of this.
    """
    from rwlib import voices as voices_mod
    repo = os.path.dirname(os.path.dirname(helpers.ROOT))
    here = os.getcwd()
    try:
        os.chdir(repo)
        command = voices_mod.build_voice_command()
    finally:
        os.chdir(here)
    assert "python3 skills/voice-setup/scripts/build_voice.py" in command, command
