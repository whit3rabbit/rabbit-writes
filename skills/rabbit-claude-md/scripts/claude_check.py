#!/usr/bin/env python3
"""
claude_check.py - the mechanical layer of the rabbit-claude-md skill.

Audits CLAUDE.md and AGENTS.md files: the memory files agent harnesses (Claude
Code, Codex, etc.) load at the start of every session. A root memory file is a
quick "where am I" plus rules, and the failure modes this script can measure are
the ones where it stops being that: the file grows past what a session should
carry, bullets run long, emphasis is spent on every other line, fenced commands
point at paths that are gone, `@path` imports never resolve, and the same fact
lives in two files at once. Unless told otherwise it also runs the active
voice's rules over the prose, through the rabbit-writes engine at register
`docs`.

Everything here is something a regex or a counter can decide. Whether a line
is derivable from the code, whether it sits at the wrong altitude, whether it
survives the removal test ("would deleting this cause Claude or Codex to make
mistakes?"), and where a changelog-drift line should move are judgment calls
and stay in SKILL.md. The `claudemd-changelog-drift` findings are evidence
for that judgment, never the verdict.

There is no CLAUDE.md / AGENTS.md corpus to calibrate against, so every number
in LIMITS is pinned by the fixture tests beside this script rather than
measured the way the README thresholds were. Move a limit and the tests move
with it.

Usage:
    python3 claude_check.py CLAUDE.md
    python3 claude_check.py AGENTS.md
    python3 claude_check.py .                    # sweep a tree
    python3 claude_check.py CLAUDE.md --json
    python3 claude_check.py CLAUDE.md --check    # exit 1 on any P0
    python3 claude_check.py CLAUDE.md --no-voice

Discovery covers CLAUDE.md, CLAUDE.local.md, .claude.md, .claude.local.md,
AGENTS.md, AGENTS.override.md, .agents.md, and .agents.override.md.
When sweeping a directory, CLAUDE.md spellings are prioritized; if none are
found, AGENTS.md spellings are discovered. ~/.claude/CLAUDE.md and
~/.codex/AGENTS.md are never discovered implicitly: pass them as the file
argument if you want them read.

Exit codes: 0, or 1 with --check when a live P0 is present, or 2 when the
input cannot be read or --voice-rules names a profile that cannot be read.
A voice that cannot be *resolved* is a note and still exits 0. No claudemd-*
finding is ever P0: blocking stays reserved for the engine's safety band.
Stdlib only, 3.9+.
"""

import argparse
import importlib.util
import json
import os
import re
import sys

from _bootstrap import SCAN_PATH, cli_error  # noqa: F401

from rwlib import findings as findings_mod   # noqa: E402
from rwlib import suppress                   # noqa: E402
from rwlib import voices as voices_mod       # noqa: E402
from rwlib.markdown import (FENCE_PARTS_RX, FENCE_RX, INLINE_CODE_RX,  # noqa: E402
                            LIST_ITEM_RX, blank, line_of, word_count)

VOICES_DIR = voices_mod.VOICES_DIR

# The four spellings Claude Code reads. CLAUDE.local.md is the documented
# local-override name and .claude.md/.claude.local.md are the older ones the
# claude-md-management plugin still discovers, so a sweep covers all four.
CLAUDE_NAMES = ("CLAUDE.md", "CLAUDE.local.md", ".claude.md", ".claude.local.md")

# AGENTS.md standard spellings (OpenAI Codex / multi-agent harness conventions).
AGENT_NAMES = ("AGENTS.md", "AGENTS.override.md", ".agents.md", ".agents.override.md")

ALL_MEMORY_NAMES = CLAUDE_NAMES + AGENT_NAMES

PRUNE_DIRS = {".git", "node_modules", "dist", "build", "scratch",
              "__pycache__", ".venv", "venv", "target"}

# One home for every threshold. SKILL.md points here rather than restating
# numbers, and tests/test_thresholds.py builds its boundary fixtures from
# these constants so a moved limit moves the tests with it.
LIMITS = {
    "bullet_words": 40,        # words in one list item before claudemd-bullet-length
    "emphasis_lines_abs": 8,   # emphasized lines allowed outright...
    "emphasis_lines_pct": 0.10,  # ...or this share of prose lines, whichever is larger
    "size_lines_p2": 300,      # non-blank lines before claudemd-oversize notes it
    "size_lines_p1": 600,      # ...and before it becomes a P1
    "duplicate_min_chars": 40,  # normalized line length before it can count as a duplicate
}

# Shouting, not formatting. A bold lead-in on a definition bullet is layout,
# and an ALL-CAPS clause would count every JSON and YAML in a technical doc,
# so the budget counts only the marker words that mean "obey this line".
EMPHASIS_RX = re.compile(r"\b(?:IMPORTANT|CRITICAL|NEVER|ALWAYS|WARNING|"
                         r"MUST(?: NOT)?|DO NOT)\b")

# Evidence of a session log rather than a standing fact. Case-insensitive on
# purpose: "We fixed" and "we fixed" are the same tell.
DRIFT_RX = re.compile(r"(?i)\b(?:we (?:fixed|added|removed|renamed)"
                      r"|used to\b|no longer\b|previously\b"
                      r"|has been (?:moved|renamed|refactored)"
                      r"|as of (?:commit|version)"
                      r"|recently (?:added|changed|moved))")
COMMIT_HASH_RX = re.compile(r"\b[0-9a-f]{7,40}\b")
COMMIT_WORD_RX = re.compile(r"(?i)\b(?:commit|fix(?:ed|es)?)\b")

# A token inside a fenced command that reads as a repository path: only path
# characters, at least one slash. Requiring the slash drops bare filenames on
# purpose, because a `cd somewhere && python3 script.py` line makes a bare
# name unresolvable from the root without tracking the cd.
PATHISH_RX = re.compile(r"^(?:\.{1,2}/)?[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+/?$")
FENCE_LANGS = {"bash", "sh", "zsh", "shell", "console", "python", "py"}
# `gh repo clone owner/repo` and `npm install scope/pkg` name remote things
# that are path-shaped and never on disk.
REMOTE_VERBS = {"clone", "install", "pull", "add", "from"}

# An @path memory import. Narrowed to tokens whose last segment carries a dot
# or that start ./, ../, or ~/: a bare `@README` import is legal but the same
# shape as an @mention, and `@scope/package` in prose names an npm package,
# not a file.
IMPORT_RX = re.compile(r"(?:^|(?<=[\s(]))@((?:~/|\.{1,2}/)?"
                       r"[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)*)", re.M)

MAX_PER_ID = 10


def finding(fid, label, priority, line, detail, match=""):
    """A structure finding, in the schema every other checker here uses."""
    return findings_mod.make(fid, label, "structure", priority, line,
                             match=match, excerpt=detail)


def prose_copy(raw):
    """Fences and code spans blanked, offsets stable."""
    out = FENCE_RX.sub(blank, raw)
    return INLINE_CODE_RX.sub(blank, out)


# ---------------------------------------------------------------------------
# per-file mechanical checks
# ---------------------------------------------------------------------------

def check_size(raw, findings, stats):
    nonblank = len([l for l in raw.splitlines() if l.strip()])
    stats["nonblank_lines"] = nonblank
    if nonblank > LIMITS["size_lines_p1"]:
        findings.append(finding(
            "claudemd-oversize", "%d non-blank lines" % nonblank, "P1", 1,
            "Past %d lines this is a manual, not a map, and it is loaded into "
            "every session whether the session needs it or not. Restructure: "
            "deep context to .claude/docs/, module facts to a CLAUDE.md in "
            "that module." % LIMITS["size_lines_p1"]))
    elif nonblank > LIMITS["size_lines_p2"]:
        findings.append(finding(
            "claudemd-oversize", "%d non-blank lines" % nonblank, "P2", 1,
            "Past %d lines, start asking each line the removal test: would "
            "deleting it cause Claude to make mistakes? A bloated file "
            "buries the rules that matter." % LIMITS["size_lines_p2"]))


def check_bullets(raw, findings, stats):
    scored = FENCE_RX.sub(blank, raw)
    lines = scored.splitlines()
    items = 0
    i = 0
    while i < len(lines):
        if LIST_ITEM_RX.match(lines[i]):
            items += 1
            body = [lines[i]]
            j = i + 1
            # Continuation lines: indented, non-blank, not a new item.
            while (j < len(lines) and lines[j].strip()
                   and not LIST_ITEM_RX.match(lines[j])
                   and lines[j][:1] in (" ", "\t")):
                body.append(lines[j])
                j += 1
            words = word_count(" ".join(body))
            if words > LIMITS["bullet_words"]:
                findings.append(finding(
                    "claudemd-bullet-length",
                    "List item of %d words" % words, "P2", i + 1,
                    "The cap in force is %d. A bullet this long is a "
                    "paragraph wearing a dash: split it, cut it, or move the "
                    "depth to .claude/docs/." % LIMITS["bullet_words"]))
            i = j
        else:
            i += 1
    stats["list_items"] = items


def check_emphasis(raw, findings, stats):
    scored = prose_copy(raw)
    lines = scored.splitlines()
    nonblank = len([l for l in lines if l.strip()])
    hits = [i + 1 for i, l in enumerate(lines) if EMPHASIS_RX.search(l)]
    stats["emphasis_lines"] = len(hits)
    allowed = max(LIMITS["emphasis_lines_abs"],
                  int(LIMITS["emphasis_lines_pct"] * nonblank))
    if len(hits) > allowed:
        findings.append(finding(
            "claudemd-emphasis-budget",
            "%d emphasized lines, budget is %d" % (len(hits), allowed),
            "P2", hits[0],
            "When this many lines carry IMPORTANT-class markers, none of "
            "them stands out. Keep emphasis for the one or two rules that "
            "get skipped without it."))


def check_fenced_paths(raw, repo_root, file_dir, findings, stats):
    checked, reported = 0, set()
    for m in FENCE_PARTS_RX.finditer(raw):
        if m.group(1).lower() not in FENCE_LANGS:
            continue
        body_start = m.start(2)
        for rel_off, line in enumerate(m.group(2).splitlines()):
            if line.lstrip().startswith("#"):
                continue
            tokens = line.split()
            for k, token in enumerate(tokens):
                token = token.strip("'\"`").rstrip(".,;:)")
                if ("://" in token or "path/to" in token
                        or any(c in token for c in "<>{}$*[]")):
                    continue
                if k:
                    prev = tokens[k - 1].strip("'\"`").lower()
                    # A remote name, or an output the command will create.
                    if (prev in REMOTE_VERBS or prev in {"-o", ">", ">>"}
                            or prev.startswith("--out")):
                        continue
                if token.startswith("~"):
                    continue
                if token.startswith("/"):
                    if not (repo_root and token.startswith(repo_root)):
                        continue
                    candidates = [token]
                elif PATHISH_RX.match(token):
                    candidates = [os.path.join(repo_root, token),
                                  os.path.join(file_dir, token)]
                else:
                    continue
                checked += 1
                if token in reported:
                    continue
                if not any(os.path.exists(c) for c in candidates):
                    reported.add(token)
                    if len(reported) > MAX_PER_ID:
                        continue
                    lineno = line_of(raw, body_start) + rel_off
                    findings.append(finding(
                        "claudemd-dead-path",
                        "Fenced command names a missing path", "P1", lineno,
                        "`%s` resolves from neither the repository root nor "
                        "this file's directory. A command that fails on "
                        "paste is worse than no command: the reader stops "
                        "trusting the rest of the file." % token,
                        match=token))
    stats["fenced_paths_checked"] = checked


def check_imports(raw, file_dir, findings, stats):
    scored = prose_copy(raw)
    found, missing = 0, 0
    for m in IMPORT_RX.finditer(scored):
        # A sentence-final dot belongs to the sentence, not the path.
        token = m.group(1).rstrip(".")
        last = token.rsplit("/", 1)[-1]
        if "." not in last and not token.startswith(("./", "../", "~/")):
            continue
        found += 1
        target = os.path.expanduser(token)
        if not os.path.isabs(target):
            target = os.path.join(file_dir, target)
        if not os.path.exists(target):
            missing += 1
            findings.append(finding(
                "claudemd-import-unresolved",
                "@%s does not resolve" % token, "P1",
                line_of(scored, m.start()),
                "An @import that points at nothing loads nothing, silently. "
                "Fix the path or drop the import.", match="@" + token))
    stats["imports"] = found
    stats["imports_missing"] = missing


def check_changelog_tells(raw, findings, stats):
    scored = prose_copy(raw)
    hits = 0
    for m in DRIFT_RX.finditer(scored):
        hits += 1
        if hits > MAX_PER_ID:
            continue
        findings.append(finding(
            "claudemd-changelog-drift", "Session-log phrasing", "P2",
            line_of(scored, m.start()),
            "%r narrates a change instead of stating what is true now. "
            "Evidence, not a verdict: rewrite it as the standing fact, or "
            "delete it if the history is the only content." % m.group(0),
            match=m.group(0)))
    for i, line in enumerate(scored.splitlines(), start=1):
        if COMMIT_WORD_RX.search(line) and COMMIT_HASH_RX.search(line):
            hits += 1
            if hits > MAX_PER_ID:
                continue
            findings.append(finding(
                "claudemd-changelog-drift", "Commit reference in prose", "P2",
                i,
                "A commit hash in a memory file is a log entry. Git already "
                "remembers it: state the standing rule instead.",
                match=COMMIT_HASH_RX.search(line).group(0)))
    stats["changelog_tells"] = hits


def normalize_line(line):
    s = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line.strip())
    return re.sub(r"\s+", " ", s).lower()


def duplicate_index(paths):
    """normalized line -> [(path, lineno)] over every discovered file."""
    index = {}
    for path in paths:
        try:
            with open(path, encoding="utf-8-sig") as fh:
                text = fh.read()
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            norm = normalize_line(line)
            if len(norm) < LIMITS["duplicate_min_chars"]:
                continue
            index.setdefault(norm, []).append((path, i))
    return index


def check_duplicates(path, raw, index, repo_root, findings):
    if not index:
        return
    seen = set()
    for i, line in enumerate(raw.splitlines(), start=1):
        norm = normalize_line(line)
        if len(norm) < LIMITS["duplicate_min_chars"] or norm in seen:
            continue
        entries = index.get(norm, [])
        others = [(p, ln) for p, ln in entries if os.path.abspath(p) != os.path.abspath(path)]
        if not others:
            continue
        seen.add(norm)
        if len(seen) > MAX_PER_ID:
            continue
        where = ", ".join("%s:%d" % (os.path.relpath(p, repo_root), ln)
                          for p, ln in others[:3])
        findings.append(finding(
            "claudemd-duplicate", "Same line in %d files" % (len(others) + 1),
            "P1", i,
            "Also at %s. One home per fact: keep the copy at the right "
            "altitude and link or delete the rest." % where,
            match=line.strip()[:80]))


# ---------------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------------

def find_repo_root(start, max_up=8):
    """Nearest ancestor of `start` holding .git, or None."""
    directory = os.path.abspath(start)
    for _ in range(max_up + 1):
        if os.path.isdir(os.path.join(directory, ".git")):
            return directory
        parent = os.path.dirname(directory)
        if parent == directory:
            return None
        directory = parent
    return None


def discover(root, names=CLAUDE_NAMES):
    """Every matching memory file spelling under `root`, pruned of vendored trees."""
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in PRUNE_DIRS and not d.startswith("."))
        for name in filenames:
            if name in names:
                hits.append(os.path.join(dirpath, name))
    return sorted(hits)


# ---------------------------------------------------------------------------
# the engine
# ---------------------------------------------------------------------------

def load_scan():
    if not os.path.exists(SCAN_PATH):
        return None
    spec = importlib.util.spec_from_file_location("hw_scan", SCAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SCAN = None


def run_prose_scan(raw, rules_path, required=False, ste="mechanical"):
    """(findings, stats, note, rules), same contract as readme_check.py.

    A voice that cannot be loaded never cancels the scan: the fingerprint and
    safety bands have nothing to do with whose voice the file is in.
    `required` is set when --voice-rules named the file by hand, and then the
    error is raised so main() exits 2 the way scan.py does.
    """
    global _SCAN
    if _SCAN is None:
        _SCAN = load_scan()
    if _SCAN is None:
        return [], {}, "rabbit-writes/scripts/scan.py not found, prose not scanned", None
    rules, note = None, None
    if rules_path:
        try:
            rules = voices_mod.load(rules_path, voices_dir=VOICES_DIR)
        except voices_mod.VoiceError as exc:
            if required:
                raise
            note = ("%s. No voice band in this report, everything else still "
                    "ran" % exc)
    # register 'docs': a CLAUDE.md is reference documentation by shape.
    # ste stated rather than inherited, so a default change upstream cannot
    # move this report silently.
    findings, stats = _SCAN.scan(raw, profile="docs", exempt=True,
                                 voice_rules=rules, suppressions=False,
                                 ste=ste)
    return findings, stats, note, rules


# ---------------------------------------------------------------------------
# one file
# ---------------------------------------------------------------------------

def check_claude_file(raw, path, repo_root, dup_index, use_voice=True,
                      voice_rules=None, no_ste=False):
    """(findings, stats, voice_name, notes) for one CLAUDE.md / AGENTS.md."""
    findings, stats, notes = [], {}, []
    file_dir = os.path.dirname(os.path.abspath(path))
    basename = os.path.basename(path)

    if basename in AGENT_NAMES:
        claude_companion = os.path.join(file_dir, "CLAUDE.md")
        if not os.path.exists(claude_companion):
            notes.append("AGENTS.md detected without a companion CLAUDE.md. "
                         "If using the Claude Code harness, consider symlinking: "
                         "ln -s %s CLAUDE.md" % basename)

    check_size(raw, findings, stats)
    check_bullets(raw, findings, stats)
    check_emphasis(raw, findings, stats)
    check_changelog_tells(raw, findings, stats)
    check_imports(raw, file_dir, findings, stats)
    if repo_root:
        check_fenced_paths(raw, repo_root, file_dir, findings, stats)
        check_duplicates(path, raw, dup_index, repo_root, findings)
    else:
        notes.append("no .git root above this file, so the dead-path and "
                     "duplicate checks did not run")

    voice_name, rules_path = None, None
    if use_voice:
        rules_path = voice_rules
        if rules_path is None:
            rules_path, voice_name, note = voices_mod.resolve(
                path, voices_dir=VOICES_DIR)
            if note:
                notes.append(note)
        else:
            voice_name = voices_mod.strip_rules_suffix(
                os.path.basename(rules_path))

    # The engine's ste= is a tri-state and raises on anything else, None
    # included: "off" is the spelling for --no-ste.
    ste_mode = "off" if no_ste else "mechanical"
    prose_findings, prose_stats, note, rules = run_prose_scan(
        raw, rules_path, required=bool(use_voice and voice_rules),
        ste=ste_mode)
    if note:
        notes.append(note)
    findings.extend(prose_findings)
    for key in ("avg_sentence_words", "burstiness", "word_count"):
        if key in prose_stats:
            stats[key] = prose_stats[key]

    # One unified suppression pass over both halves, the readme_check shape:
    # scan ran with suppressions=False so an inline rabbit-allow can cover a
    # structure finding too, and a profile's engine_exemptions ride along.
    allowances, problems = suppress.parse(raw)
    allowances.extend(suppress.profile_allowances(rules))
    used, refused = suppress.apply(findings, allowances)
    findings.extend(suppress.audit(allowances, problems, used,
                                   findings_mod.make, refused))

    findings.sort(key=findings_mod.sort_key)
    return findings, stats, voice_name, notes


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------

PRIORITY_TITLES = {"P0": "P0  blocks: evidence of concealed or planted text",
                   "P1": "P1  clear defect in the memory file",
                   "P2": "P2  polish, and evidence for the judgment pass"}
BAND_TITLES = {"safety": "  safety (concealed text, or text aimed at an agent)",
               "structure": "  structure and format (rabbit-claude-md)",
               "voice": "  voice (this writer's own rules)",
               "fingerprint": "  fingerprints (evidence about production)",
               "craft": "  craft (bad writing regardless of author)"}


def report_file(path, findings, stats, voice_name, notes):
    out = ["%s" % path,
           "  voice: %s   non-blank lines: %d   list items: %d   "
           "emphasis lines: %d"
           % (voice_name or "none", stats.get("nonblank_lines", 0),
              stats.get("list_items", 0), stats.get("emphasis_lines", 0))]
    for note in notes:
        out.append("  note: %s" % note)

    allowed = suppress.suppressed(findings)
    live = suppress.live(findings)

    if not live:
        out.append("  No mechanical findings. The judgment pass still has to "
                   "happen: run references/criteria.md over every line.")
    for pri in ("P0", "P1", "P2"):
        group = [f for f in live if f["priority"] == pri]
        if not group:
            continue
        out.append(PRIORITY_TITLES[pri])
        for band in ("safety", "structure", "voice", "fingerprint", "craft"):
            sub = [f for f in group if f["band"] == band]
            if not sub:
                continue
            out.append(BAND_TITLES[band])
            shown = {}
            for f in sub:
                shown[f["id"]] = shown.get(f["id"], 0) + 1
                if shown[f["id"]] > 4:
                    continue
                out.append("    L%-4d %s" % (f["line"], f["label"]))
                if (band == "structure" or f["priority"] == "P0") and f["excerpt"]:
                    out.append("           %s" % f["excerpt"])
            for fid, n in shown.items():
                if n > 4:
                    out.append("    ... and %d more %s" % (n - 4, fid))

    if allowed:
        out.append("  suppressed (%d, not counted above)" % len(allowed))
        for f in allowed:
            out.append("    L%-4d %s" % (f["line"], f["label"]))
    return "\n".join(out)


def report(root, entries):
    out = ["claude check: %s" % root,
           "files found: %d" % len(entries), ""]
    for e in entries:
        out.append(report_file(e["file"], e["findings"], e["stats"],
                               e["voice"], e["notes"]))
        out.append("")
    if len(entries) > 1:
        out.append("inventory")
        for e in entries:
            c = e["counts"]
            out.append("  %-40s %5d lines   P0 %d  P1 %d  P2 %d"
                       % (e["file"], e["stats"].get("nonblank_lines", 0),
                          c["P0"], c["P1"], c["P2"]))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------

def main():
    examples = [
        "python3 claude_check.py CLAUDE.md",
        "python3 claude_check.py AGENTS.md",
        "python3 claude_check.py .",
        "python3 claude_check.py CLAUDE.md --json",
        "python3 claude_check.py CLAUDE.md --check",
        "python3 claude_check.py CLAUDE.md --no-voice",
        "python3 claude_check.py CLAUDE.md --voice-rules path/to/dana.rules.json",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples
    )
    ap.add_argument("path", help="a CLAUDE.md or AGENTS.md file, or a directory to sweep "
                                 "for memory files")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--no-voice", action="store_true",
                    help="apply no voice profile. Structure, fingerprints and "
                         "craft are still checked")
    ap.add_argument("--voice-rules", metavar="PATH",
                    help="a voice's <name>.rules.json; overrides .rabbit-voice "
                         "and ACTIVE")
    ap.add_argument("--no-ste", action="store_true",
                    help="disable STE readability rules (sentence length caps, "
                         "paragraph sentence counts, trailing conditions)")
    ap.add_argument("--repo-root", metavar="PATH",
                    help="override the repository root used for the dead-path "
                         "and duplicate checks. Default: nearest ancestor "
                         "holding .git")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any unsuppressed P0 finding is present")
    args = ap.parse_args()

    target = os.path.abspath(args.path)
    if os.path.isdir(target):
        repo_root = args.repo_root or find_repo_root(target) or target
        files = discover(target, CLAUDE_NAMES)
        if not files:
            files = discover(target, AGENT_NAMES)
        if not files:
            print("no CLAUDE.md or AGENTS.md files under %s (looked for %s)"
                  % (target, ", ".join(ALL_MEMORY_NAMES)))
            return 0
    elif os.path.isfile(target):
        repo_root = args.repo_root or find_repo_root(os.path.dirname(target))
        files = [target]
    else:
        print(cli_error.format_file_error(
            "claude_check.py", args.path, "path",
            expected_type="CLAUDE.md or AGENTS.md file or directory",
            details="path does not exist", examples=examples
        ), file=sys.stderr)
        return 2

    # The duplicate index reads the whole tree even for a single-file run, so
    # a fact that also lives in a sibling memory file is still reported.
    dup_paths = discover(repo_root, ALL_MEMORY_NAMES) if repo_root else files
    dup_index = duplicate_index(dup_paths)

    entries = []
    for path in files:
        try:
            with open(path, encoding="utf-8-sig") as fh:
                raw = fh.read()
        except OSError as exc:
            print(cli_error.format_file_error(
                "claude_check.py", path, "path", expected_type="file path",
                details=str(exc), examples=examples
            ), file=sys.stderr)
            return 2
        try:
            findings, stats, voice_name, notes = check_claude_file(
                raw, path, repo_root, dup_index,
                use_voice=not args.no_voice, voice_rules=args.voice_rules,
                no_ste=args.no_ste)
        except voices_mod.VoiceError as exc:
            print(cli_error.format_file_error(
                "claude_check.py", args.voice_rules or "voice profile",
                "--voice-rules",
                expected_type="voice rules file path (.rules.json)",
                details=str(exc), examples=examples
            ), file=sys.stderr)
            return 2
        entries.append({"file": os.path.relpath(path, repo_root)
                        if repo_root else path,
                        "voice": voice_name, "notes": notes, "stats": stats,
                        "counts": findings_mod.counts(findings),
                        "findings": findings})

    total = {"P0": 0, "P1": 0, "P2": 0, "suppressed": 0}
    for e in entries:
        for key in total:
            total[key] += e["counts"].get(key, 0)

    if args.json:
        print(json.dumps({
            "schema_version": findings_mod.SCHEMA_VERSION,
            "root": repo_root,
            "limits": LIMITS,
            "counts": total,
            "files": entries,
        }, indent=2))
    else:
        print(report(repo_root or target, entries))

    if args.check and total["P0"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
