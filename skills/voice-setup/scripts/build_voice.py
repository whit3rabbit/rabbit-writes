#!/usr/bin/env python3
"""
Scaffold a voice profile, and check that the one you wrote actually works.

    python3 build_voice.py --scaffold --name dana
    python3 build_voice.py --scaffold --name dana --out ~/writing/voices
    python3 build_voice.py --check dana
    python3 build_voice.py --check ~/writing/voices/dana.rules.json

Two jobs, and the second is the one that matters.

`--scaffold` copies voices/TEMPLATE.md and voices/TEMPLATE.rules.json into a
pair named for one person, with the template's own residue already gone: every
underscore-prefixed guidance key, and the `banned_regex` entry whose label reads
"Example, delete this". That entry compiles, so a copy that keeps it enforces a
rule nobody chose, at this profile's priority, against this person's name, and
nothing downstream notices. The guidance prompts in the markdown stay, because
they are the form: a scaffolded profile is deliberately unfinished and `--check`
says so until somebody fills it in.

`--check` answers two different questions.

  Structurally, is this a profile? rwlib/voice_check.py, shared with
  scripts/validate.py so the two cannot drift.

  Do the rules fire? Every banned word, banned phrase and forbidden mechanic is
  put into a probe document and run through scan.py, and anything that produces
  no finding is reported. A rule that does not fire is worse than no rule,
  because it reads as coverage. This half is here rather than in validate.py
  because it needs the engine, and because this is the script that runs on the
  machine where somebody is writing a profile: validate.py lives at the
  repository root and a plugin install does not have one.

A `banned_regex` cannot be probed from its pattern, so an entry may carry an
optional `example` string and be proven the same way. One without an example is
reported as unproven rather than passed over quietly.

Stdlib only, 3.9+.
"""

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# scripts -> voice-setup -> skills. Walked rather than spelled out, so a skill
# directory can be renamed without editing the scripts inside it.
SKILLS = os.path.dirname(os.path.dirname(HERE))
SCAN_PATH = os.path.join(SKILLS, "rabbit-writes", "scripts", "scan.py")
# rwlib lives beside scan.py, resolved from it so the two cannot end up pointing
# at different checkouts.
RWLIB_PARENT = os.path.dirname(SCAN_PATH)
if RWLIB_PARENT not in sys.path:
    sys.path.insert(0, RWLIB_PARENT)
from rwlib import cli_error, inflect, voice_check, voices as voices_mod   # noqa: E402

TEMPLATE_MD = os.path.join(voices_mod.VOICES_DIR, "TEMPLATE.md")
TEMPLATE_RULES = os.path.join(voices_mod.VOICES_DIR, "TEMPLATE.rules.json")

# The template's opening instructions, which are addressed to whoever is doing
# the copying. Removed by name rather than by counting lines, and left in place
# when either marker moves, because a scaffold that silently ate half a file is
# worse than one that left a paragraph behind: --check reports the leftover.
COPY_BLOCK_START = "> Copy this file to"
COPY_BLOCK_END = "> **Only put things here"

# One trigger per mechanic this engine can be made to forbid, and the finding it
# has to produce. Written as escapes rather than literals: the whole point of
# these three lines is the exact character, and any tool that normalizes
# whitespace or quotes turns a literal into something that no longer tests
# anything while the source still looks right.
MECHANIC_PROBES = {
    ("em_dash", "forbid"):
        ("voice-em-dash", "The plan is simple \u2014 ship it and see."),
    ("semicolon", "forbid"):
        ("voice-semicolon", "It works; it is not fast."),
    ("emoji", "forbid"):
        ("voice-emoji", "We shipped it \U0001F680 this morning."),
    ("curly_quotes", "forbid"):
        ("voice-curly-quote", "She called the release \u201cdone\u201d."),
    ("one_word_sentence", "forbid"):
        ("voice-one-word-sentence", "Right. That is the whole argument."),
    ("oxford_comma", "require"):
        ("voice-oxford-comma", "We ship docs, tests and code."),
    ("oxford_comma", "forbid"):
        ("voice-oxford-comma", "We ship docs, tests, and code."),
    ("date_format", "dmy"):
        ("voice-date-format", "It landed on September 12, 2025."),
    ("date_format", "iso"):
        ("voice-date-format", "It landed on September 12, 2025."),
    ("date_format", "mdy"):
        ("voice-date-format", "It landed on 12 September 2025."),
}


def load_scan():
    if not os.path.exists(SCAN_PATH):
        raise SystemExit("build_voice: cannot find %s. This script has to run "
                         "from inside an installed plugin." % SCAN_PATH)
    spec = importlib.util.spec_from_file_location("rw_scan", SCAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# scaffold
# --------------------------------------------------------------------------

def scaffold_rules(name, priority, template_path=TEMPLATE_RULES):
    """The template's rules file with the template taken out of it."""
    with open(template_path, encoding="utf-8") as fh:
        data = json.load(fh)

    out = {}
    for key, value in data.items():
        if key.startswith("_"):
            continue
        if key == "mechanics":
            value = {k: v for k, v in value.items() if not k.startswith("_")}
        if key == "banned_regex":
            value = [e for e in value
                     if e.get("id") != voice_check.EXAMPLE_RULE_ID]
        out[key] = value
    out["voice"] = name
    out["default_priority"] = priority
    if isinstance(out.get("description"), str):
        out["description"] = out["description"].replace(
            voice_check.TEMPLATE_VOICE_NAME, name)
    return out


def scaffold_markdown(name, template_path=TEMPLATE_MD):
    """The template's markdown, titled for one person, with the copying
    instructions gone and every guidance prompt still in it.

    The prompts are the form. Deleting them here would produce a file that looks
    finished and says nothing, and `--check` would pass it.
    """
    with open(template_path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    start = end = None
    for i, line in enumerate(lines):
        if start is None and line.startswith(COPY_BLOCK_START):
            start = i
        elif start is not None and line.startswith(COPY_BLOCK_END):
            end = i
            break
    if start is not None and end is not None:
        lines = lines[:start] + lines[end:]

    # Everywhere, not just the title. The template names the rules file as
    # `<name>.rules.json` down in Hard nos, and a copy that substituted only
    # the heading left a profile pointing at a file nobody has.
    return "\n".join(lines).replace(voice_check.TEMPLATE_VOICE_NAME, name)


BUILD_EXAMPLES = [
    "python3 build_voice.py --scaffold --name dana",
    "python3 build_voice.py --scaffold --name dana --out ~/writing/voices",
    "python3 build_voice.py --check dana",
    "python3 build_voice.py --check ~/writing/voices/dana.rules.json"
]


def do_scaffold(args):
    out_dir = os.path.abspath(args.out)
    md_path = os.path.join(out_dir, args.name + ".md")
    rules_path = os.path.join(out_dir, args.name + voices_mod.RULES_SUFFIX)

    existing = [p for p in (md_path, rules_path) if os.path.exists(p)]
    if existing and not args.force:
        print(cli_error.format_file_error(
            "build_voice.py", ", ".join(os.path.basename(p) for p in existing), "target files",
            expected_type="non-existent file paths (or pass --force to overwrite)",
            details="Target profile files already exist: %s" % ", ".join(existing),
            examples=BUILD_EXAMPLES), file=sys.stderr)
        return 2
    if not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir)
        except OSError as exc:
            print(cli_error.format_file_error(
                "build_voice.py", out_dir, "--out", expected_type="writable directory path",
                details=str(exc), examples=BUILD_EXAMPLES), file=sys.stderr)
            return 2

    rules = scaffold_rules(args.name, args.priority)
    markdown = scaffold_markdown(args.name)
    try:
        with open(rules_path, "w", encoding="utf-8") as fh:
            json.dump(rules, fh, indent=2)
            fh.write("\n")
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(markdown)
    except OSError as exc:
        print(cli_error.format_file_error(
            "build_voice.py", out_dir, "output directory", expected_type="writable directory path",
            details=str(exc), examples=BUILD_EXAMPLES), file=sys.stderr)
        return 2

    print("wrote %s" % md_path)
    print("       the profile a model reads. Every <angle bracket> in it is a "
          "prompt waiting")
    print("       for this person's answer, in their words.")
    print("wrote %s" % rules_path)
    print("       the subset a regex can decide, at %s. Empty, and valid "
          "empty." % args.priority)
    print("")
    print(destination_note(out_dir, args.name))
    print("")
    print("Next: fill the markdown, move what a regex can decide into the JSON, "
          "then")
    print("  python3 %s --check %s"
          % (os.path.relpath(os.path.abspath(__file__)), args.name
             if in_voices_dir(out_dir) else rules_path))
    return 0


def in_voices_dir(out_dir):
    return os.path.abspath(out_dir) == os.path.abspath(voices_mod.VOICES_DIR)


def destination_note(out_dir, name):
    """What this destination costs, said once, at the moment it is chosen."""
    if in_voices_dir(out_dir):
        return ("These are inside the installed plugin, which is where "
                "voices/ACTIVE and a\nrepo's .rabbit-voice can find them by "
                "name. A plugin update overwrites this\ndirectory: keep a copy "
                "somewhere the update cannot reach.")
    return ("This is outside the plugin's voices/ directory, so it survives a "
            "plugin update\nand nothing resolves it by name. voices/ACTIVE and "
            ".rabbit-voice both look up\n%s only, so reach this one with the "
            "path:\n  scan.py draft.md --voice-rules %s"
            % (voices_mod.VOICES_DIR,
               os.path.join(out_dir, name + voices_mod.RULES_SUFFIX)))


# --------------------------------------------------------------------------
# live fire
# --------------------------------------------------------------------------

def _probe_registers(rules):
    """Every register a rule in this profile is scoped to, plus the default.

    A rule scoped to `casual` does not fire in a scan of a blog post, so a probe
    run in one register only would report the author's own scoping as a rule
    that does not work.
    """
    found = set(rules.get("mechanics_by_register", {}))
    for key in ("banned_regex", "required_when"):
        for entry in rules.get(key, []):
            found.update(entry.get("applies_to_registers", []))
    return found


def bans_probe(rules, mech):
    """(text, expectations) covering everything a single document can carry."""
    lines, expect = [], []

    # The finding id is part of the expectation, not just the matched text. The
    # two lists compile to two different patterns, and a multi-word string in
    # `banned_words` never matches: `word_regex` does not cross a space. Without
    # the id, a profile that also banned that string as a phrase credited the
    # dead word entry with the live phrase's finding, and the commonest
    # authoring mistake in a rules file passed the check written to catch it.
    for entry in rules.get("banned_words", []):
        term = inflect.term_of(entry)
        lines.append("The report used %s once." % term)
        expect.append({"what": "banned word %r" % term, "kind": "match",
                       "value": term, "id": "voice-banned-word"})
    for entry in rules.get("banned_phrases", []):
        term = inflect.term_of(entry)
        lines.append("Somebody wrote %s in the draft." % term)
        expect.append({"what": "banned phrase %r" % term, "kind": "match",
                       "value": term, "id": "voice-banned-phrase"})
    for (key, value), (finding_id, text) in sorted(MECHANIC_PROBES.items()):
        if mech.get(key) == value:
            lines.append(text)
            expect.append({"what": "mechanics.%s = %s" % (key, value),
                           "kind": "id", "value": finding_id})

    # One sentence per line, and a blank line between each, so a paragraph cap
    # somewhere else in the profile does not fire here and read as this probe's
    # result.
    return "\n\n".join(lines), expect


def cap_probes(mech):
    """[(what, text, expectation)] for the rules that are about a whole
    document rather than a span."""
    out = []
    cap = mech.get("max_paragraph_sentences")
    if cap:
        n = int(float(cap)) + 1
        text = " ".join("The %d thing here is plain prose." % i
                        for i in range(1, n + 1))
        out.append(("mechanics.max_paragraph_sentences = %s" % cap, text,
                    {"kind": "id", "value": "voice-paragraph-length"}))
    cap = mech.get("max_avg_sentence_words")
    if cap:
        n = int(float(cap)) + 6
        text = ("This sentence " + " ".join(["runs"] * n) + " long.")
        out.append(("mechanics.max_avg_sentence_words = %s" % cap, text,
                    {"kind": "id", "value": "voice-sentence-length"}))
    if mech.get("em_dash") == "limit":
        cap = float(mech.get("max_em_dashes_per_1000w", 2))
        # Enough dashes that the rate clears the cap whatever the cap is. Each
        # line is 8 words and one dash, so the rate is 125 per 1000; a profile
        # capping higher than that gets proportionally more lines.
        n = max(3, int(cap / 100.0) + 3)
        text = "\n\n".join(["A short line here \u2014 and a dash."] * n)
        out.append(("mechanics.em_dash = limit (%.1f per 1000 words)" % cap,
                    text, {"kind": "id", "value": "voice-em-dash-rate"}))
    return out


def _fired(findings, expectation):
    if expectation["kind"] == "id":
        return any(f["id"] == expectation["value"] for f in findings)
    wanted = expectation["value"].lower()
    return any(f["id"] == expectation["id"]
               and wanted in str(f.get("match", "")).lower() for f in findings)


def live_fire(rules, scan):
    """[(ok, what, why)] for every rule this profile claims to enforce.

    `ok` is True for a rule that fired, False for one that did not, and None for
    one nothing here can settle. The third is a real answer and is reported as
    one: a check that quietly counted the unprovable as passing would be the
    coverage-shaped lie this whole function exists to catch.
    """
    unproven = []
    registers = sorted(_probe_registers(rules) | {scan.DEFAULT_REGISTER})

    def run(text, register):
        findings, _ = scan.scan(text, register, True, rules)
        return [f for f in findings if f["band"] == "voice"]

    # Once per register, and a rule counts as proven if it fired in any of
    # them, because that is exactly what its author scoped it to.
    proven = {}

    def record(what, ok):
        proven[what] = proven.get(what, False) or ok

    for register in registers:
        mech = scan.voice_mechanics(rules, register)
        text, expect = bans_probe(rules, mech)
        if text:
            voice_findings = run(text, register)
            for expectation in expect:
                record(expectation["what"], _fired(voice_findings, expectation))
        for what, cap_text, cap_expect in cap_probes(mech):
            record(what, _fired(run(cap_text, register), cap_expect))

    # A regex example gets a document of its own. In the combined probe above,
    # a pattern about document shape rather than about a phrase would match the
    # probe's own shape: `motivational-cadence` looks for three short paragraphs
    # in a row, and the probe is a stack of short paragraphs. It passed on text
    # its author never wrote, which is the same lie as a rule that never fires.
    for entry in rules.get("banned_regex", []):
        eid = entry.get("id")
        what = "banned_regex %s" % eid
        if "example" not in entry:
            unproven.append((None, what,
                             "no `example` key, so nothing here can prove it "
                             "fires. Add one: \"example\": \"a line this "
                             "should catch\""))
            continue
        scoped = entry.get("applies_to_registers") or [scan.DEFAULT_REGISTER]
        for register in scoped:
            record(what, _fired(run(entry["example"], register),
                                {"kind": "id", "value": eid}))

    for entry in rules.get("required_when", []):
        unproven.append((None, "required_when %s" % entry.get("id", "?"),
                         "presence checks fire on absence and are not probed "
                         "here. Read it against a real document."))

    results = [(ok, what,
                "" if ok else "put through scan.py and nothing was reported")
               for what, ok in sorted(proven.items())]
    return results + unproven


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------

def resolve_target(target, voices_dir):
    """A profile name, or a path to its rules file."""
    if os.path.sep in target or target.endswith(".json"):
        path = os.path.abspath(target)
        if not path.endswith(voices_mod.RULES_SUFFIX):
            path = voices_mod.strip_rules_suffix(path) + voices_mod.RULES_SUFFIX
        return path
    return os.path.join(voices_dir, target + voices_mod.RULES_SUFFIX)


def do_check(args):
    rules_path = resolve_target(args.check, args.voices_dir)
    if not os.path.exists(rules_path):
        print(cli_error.format_file_error(
            "build_voice.py", rules_path, "--check",
            expected_type="voice rules file path (.rules.json)",
            details="No rules file found at %s" % rules_path,
            examples=BUILD_EXAMPLES), file=sys.stderr)
        return 2

    name = voices_mod.strip_rules_suffix(os.path.basename(rules_path))
    print("checking %s" % rules_path)
    print("")

    results = voice_check.check_profile(rules_path, args.voices_dir)
    fails = voice_check.failures(results)
    for entry in results:
        print("  %-5s %s" % ("FAIL" if entry["level"] == voice_check.FAIL
                             else "note", entry["message"]))
    if not results:
        print("  note  structure clean")
    print("")

    unproven = []
    if not fails:
        scan = load_scan()
        rules = voices_mod.load(rules_path, args.voices_dir)
        print("live fire: every rule below was put through scan.py")
        fired = live_fire(rules, scan)
        if not fired:
            print("  note  nothing mechanically enforced, nothing to fire")
        for ok, what, why in fired:
            if ok is True:
                print("  fires %s" % what)
            elif ok is None:
                print("  ?     %s: %s" % (what, why))
                unproven.append(what)
            else:
                print("  DEAD  %s: %s" % (what, why))
                fails.append({"level": voice_check.FAIL,
                              "message": "%s never fires" % what})
        print("")
    else:
        print("live fire skipped: fix the structure first, or the probes "
              "measure a file nobody can load.")
        print("")

    if fails:
        print("%d problem(s). A rule that does not fire is worse than no rule, "
              "because it reads as coverage." % len(fails))
        return 1
    if unproven:
        print("%s is valid, with %d rule(s) nothing here can prove. Scan one of "
              "this person's real samples next: if their own writing trips "
              "their own rules, one of the two is wrong."
              % (name, len(unproven)))
    else:
        print("%s is valid and every rule in it fires. Scan one of this "
              "person's real samples next: if their own writing trips their "
              "own rules, one of the two is wrong." % name)
    return 0


def do_activate(name, voices_dir):
    """ACTIVE names a profile in voices/, so it cannot point anywhere else."""
    rules_path = os.path.join(voices_dir, name + voices_mod.RULES_SUFFIX)
    if not os.path.exists(rules_path):
        print(cli_error.format_file_error(
            "build_voice.py", rules_path, "--activate",
            expected_type="voice profile name in voices/",
            details="voices/ACTIVE holds a name and resolves inside %s, and there is no %s.rules.json there. Pass --voice-rules <path> at scan time instead."
                    % (voices_dir, name),
            examples=BUILD_EXAMPLES), file=sys.stderr)
        return 2
    active = os.path.join(voices_dir, "ACTIVE")
    previous = ""
    if os.path.exists(active):
        with open(active, encoding="utf-8") as fh:
            previous = fh.read().strip()
    try:
        with open(active, "w", encoding="utf-8") as fh:
            fh.write(name + "\n")
    except OSError as exc:
        print(cli_error.format_file_error(
            "build_voice.py", active, "ACTIVE file",
            expected_type="writable file path",
            details=str(exc), examples=BUILD_EXAMPLES), file=sys.stderr)
        return 2
    print("active voice is now %s%s"
          % (name, ", replacing %s" % previous if previous else ""))
    return 0


def main():
    examples = BUILD_EXAMPLES
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples
    )
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--scaffold", action="store_true",
                      help="write a new profile pair from the templates")
    mode.add_argument("--check", metavar="VOICE",
                      help="validate one profile, by name or by path to its "
                           "rules file")
    ap.add_argument("--name", metavar="VOICE",
                    help="the profile's name, which is also both filenames")
    ap.add_argument("--out", metavar="DIR", default=voices_mod.VOICES_DIR,
                    help="where the pair goes. Defaults to the plugin's "
                         "voices/, which is the only place ACTIVE and "
                         ".rabbit-voice resolve names")
    ap.add_argument("--priority", default="P0", choices=list(voices_mod.PRIORITY_ORDER),
                    help="default_priority for the rules file. P0 means a hit "
                         "is a defect on the same tier as a chatbot artifact")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing profile")
    ap.add_argument("--activate", action="store_true",
                    help="point voices/ACTIVE at this profile, after it checks "
                         "out")
    ap.add_argument("--voices-dir", default=voices_mod.VOICES_DIR,
                    help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.scaffold and not args.name:
        print(cli_error.format_llm_error(
            "build_voice.py", "--scaffold requires --name <voice> to set the profile name",
            parser=ap, examples=examples
        ), file=sys.stderr)
        return 2
    if args.scaffold and args.name.startswith("TEMPLATE"):
        print(cli_error.format_llm_error(
            "build_voice.py", "--name TEMPLATE is invalid: TEMPLATE is the form name, not a person's profile name",
            parser=ap, examples=examples
        ), file=sys.stderr)
        return 2

    if args.scaffold:
        code = do_scaffold(args)
        if code == 0 and args.activate:
            print("")
            print("not activating yet: a scaffold has no answers in it. Run "
                  "--check --activate once it is filled in.")
        return code

    code = do_check(args)
    if code == 0 and args.activate:
        name = voices_mod.strip_rules_suffix(
            os.path.basename(resolve_target(args.check, args.voices_dir)))
        print("")
        return do_activate(name, args.voices_dir)
    if code != 0 and args.activate:
        print("")
        print(cli_error.format_llm_error(
            "build_voice.py", "Refused activation: the profile did not check out.",
            parser=ap, examples=examples), file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
