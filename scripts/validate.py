#!/usr/bin/env python3
"""
Repo validator. Checks the things that break an install silently.

    python3 scripts/validate.py

Exit 0 clean, 1 on any failure. Stdlib only.
"""

import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
VOICES = os.path.join(SKILLS, "rabbit-writes", "voices")
ENGINE = os.path.join(SKILLS, "rabbit-writes", "scripts")
SCAN = os.path.join(ENGINE, "scan.py")
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

# Findings the engine raises itself rather than from a lexicon pattern. Imported
# rather than restated: this list existed in three files, and a new synthetic
# finding added to two of them made the third reject a register that named it.
from rwlib import inflect                       # noqa: E402
from rwlib import registers as registers_mod    # noqa: E402
from rwlib import stylometry as stylometry_mod  # noqa: E402
from rwlib import voice_check                   # noqa: E402
from rwlib.lexicon import SYNTHETIC_FINDING_IDS  # noqa: E402

problems = []
notes = []


def fail(msg):
    problems.append(msg)


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


# The two schemastore URLs, pinned as literals. Nothing else in the repo checks
# them: `claude plugin validate` ignores `$schema`, so a fat-fingered URL costs
# you editor validation and reports nothing. The marketplace one shipped wrong
# (`claude-code-marketplace-manifest.json`, a 404) and nobody noticed. Both were
# fetched by hand and returned 200 at the values below. They stay literals rather
# than a request because CI is stdlib-only and offline-safe, and the failure worth
# catching is a typo here rather than an outage at schemastore.
SCHEMA_URLS = {
    os.path.join(".claude-plugin", "plugin.json"):
        "https://json.schemastore.org/claude-code-plugin-manifest.json",
    os.path.join(".claude-plugin", "marketplace.json"):
        "https://json.schemastore.org/claude-code-marketplace.json",
}


def check_manifests():
    for rel, required in (
        (os.path.join(".claude-plugin", "plugin.json"),
         ("name", "description", "version", "license")),
        (os.path.join(".claude-plugin", "marketplace.json"),
         ("name", "owner", "plugins")),
    ):
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail("missing %s" % rel)
            continue
        try:
            data = json.loads(read(rel))
        except ValueError as exc:
            fail("%s does not parse: %s" % (rel, exc))
            continue
        for key in required:
            if not data.get(key):
                fail("%s missing key: %s" % (rel, key))
        want = SCHEMA_URLS[rel]
        if data.get("$schema") != want:
            fail("%s $schema is %r, expected %r. A wrong one is a 404 that only "
                 "an editor notices." % (rel, data.get("$schema"), want))
        notes.append("%s ok" % rel)

    try:
        plugin = json.loads(read(".claude-plugin", "plugin.json"))
        market = json.loads(read(".claude-plugin", "marketplace.json"))
    except (OSError, ValueError):
        return
    names = [p.get("name") for p in market.get("plugins", [])]
    if plugin.get("name") not in names:
        fail("plugin.json name %r is not listed in marketplace.json plugins %r"
             % (plugin.get("name"), names))
    for entry in market.get("plugins", []):
        src = entry.get("source", "./")
        if not os.path.isdir(os.path.join(ROOT, src)):
            fail("marketplace plugin %r points at missing source %r"
                 % (entry.get("name"), src))
        # The schema allows `version` on a marketplace entry as well as in
        # plugin.json, and this repo deliberately carries it only in plugin.json:
        # a second copy is the drift one-home-per-fact exists to prevent, and the
        # marketplace catalog reads the plugin manifest anyway. Anyone who adds one
        # back has to keep the two in step, which is what this says out loud.
        if entry.get("version") and entry["version"] != plugin.get("version"):
            fail("marketplace entry %r pins version %r while plugin.json says %r"
                 % (entry.get("name"), entry["version"], plugin.get("version")))


def check_skills():
    if not os.path.isdir(SKILLS):
        fail("no skills/ directory")
        return
    found = []
    for name in sorted(os.listdir(SKILLS)):
        skill_dir = os.path.join(SKILLS, name)
        if not os.path.isdir(skill_dir):
            continue
        path = os.path.join(skill_dir, "SKILL.md")
        if not os.path.exists(path):
            fail("skills/%s has no SKILL.md" % name)
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
        if not m:
            fail("skills/%s/SKILL.md has no YAML frontmatter" % name)
            continue
        fm = m.group(1)
        declared = re.search(r"(?m)^name:\s*(\S+)", fm)
        desc = re.search(r"(?m)^description:\s*(.+)", fm)
        if not declared:
            fail("skills/%s: frontmatter has no name" % name)
        elif declared.group(1) != name:
            fail("skills/%s: frontmatter name %r does not match the directory"
                 % (name, declared.group(1)))
        if not desc:
            fail("skills/%s: frontmatter has no description" % name)
        elif len(desc.group(1)) < 60:
            fail("skills/%s: description is too short to trigger reliably" % name)
        found.append(name)
    for required in ("rabbit-writes", "voice-setup", "readme-writing"):
        if required not in found:
            fail("expected skill missing: %s" % required)
    notes.append("skills: %s" % ", ".join(found))


def _expanded(entries, expanded):
    """"9" or "9 -> 14", so a profile leaning on `inflect` reports both."""
    return ("%d" % len(entries) if len(expanded) == len(entries)
            else "%d -> %d" % (len(entries), len(expanded)))


def check_voices():
    if not os.path.isdir(VOICES):
        fail("no voices/ directory")
        return

    active_path = os.path.join(VOICES, "ACTIVE")
    if not os.path.exists(active_path):
        fail("voices/ACTIVE is missing; nothing tells the skill whose voice to use")
    else:
        with open(active_path, encoding="utf-8") as fh:
            active = fh.read().strip()
        if not active:
            fail("voices/ACTIVE is empty")
        elif not os.path.exists(os.path.join(VOICES, active + ".md")):
            fail("voices/ACTIVE names %r but voices/%s.md does not exist"
                 % (active, active))
        else:
            notes.append("active voice: %s" % active)
            if not os.path.exists(os.path.join(VOICES, active + ".rules.json")):
                notes.append("note: %s has no .rules.json, so nothing is "
                             "mechanically enforced for that voice" % active)

    for fn in sorted(os.listdir(VOICES)):
        if fn.endswith(".md") and not fn.startswith("TEMPLATE"):
            vname = fn[:-3]
            json_path = os.path.join(VOICES, vname + ".rules.json")
            if not os.path.exists(json_path):
                notes.append("note: voices/%s.md has no matching %s.rules.json"
                             % (vname, vname))

        # A fingerprint is read by scan.py only through its profile's rules
        # path, so one without a rules file beside it is never loaded: no
        # error, no distance, nothing to notice. Checked here for the same
        # reason a register named in a rules file is checked, which is that a
        # silent no-op reads exactly like a rule somebody is honouring.
        if fn.endswith(stylometry_mod.FINGERPRINT_SUFFIX):
            # Only the orphan check lives here. Whether a fingerprint is
            # readable and current is voice_check's, reached from the rules
            # file, and an orphan is exactly the case that reaches nothing:
            # scan.py finds a fingerprint only through its profile's rules path,
            # so one with no rules file beside it is never loaded at all. No
            # error, no distance, nothing to notice.
            vname = fn[:-len(stylometry_mod.FINGERPRINT_SUFFIX)]
            if not os.path.exists(os.path.join(VOICES, vname + ".rules.json")):
                fail("voices/%s has no %s.rules.json, so scan.py never finds it "
                     "and no distance is ever measured" % (fn, vname))
            continue

        if not fn.endswith(".rules.json"):
            continue

        vname = fn[:-11]
        try:
            with open(os.path.join(VOICES, fn), encoding="utf-8") as fh:
                data = json.load(fh)
        except ValueError as exc:
            fail("voices/%s does not parse: %s" % (fn, exc))
            continue

        # Everything structural is voice_check's, so this validator and the one
        # a person runs on their own machine cannot disagree about what a valid
        # profile is. `voice-setup/scripts/build_voice.py --check` is the other
        # caller, and it adds the half that needs the engine: whether the rules
        # actually fire.
        #
        # TEMPLATE is the form rather than a profile, so it is exempt from the
        # checks that are about being one: its `voice` field is "<name>", its
        # underscore keys are its documentation, and its example-rule entry is
        # the shape it exists to show.
        if vname != "TEMPLATE":
            for entry in voice_check.check_profile(os.path.join(VOICES, fn),
                                                   VOICES):
                if entry["level"] == voice_check.FAIL:
                    fail("voices/%s: %s" % (fn, entry["message"]))

        words = inflect.expand(data.get("banned_words", []))
        phrases = inflect.expand(data.get("banned_phrases", []))
        # Counted after expansion, and both numbers shown when they differ, so a
        # profile that leans on `inflect` says how many terms it actually bans
        # rather than how many lines it happens to be written on.
        notes.append("voices/%s ok (%s words, %s phrases, %d regex)"
                     % (fn,
                        _expanded(data.get("banned_words", []), words),
                        _expanded(data.get("banned_phrases", []), phrases),
                        len(data.get("banned_regex", []))))

    for required in ("TEMPLATE.md", "TEMPLATE.rules.json"):
        if not os.path.exists(os.path.join(VOICES, required)):
            fail("voices/%s is missing; nobody can add their own voice without it"
                 % required)


def check_engine():
    lex = os.path.join(SKILLS, "rabbit-writes", "scripts", "lexicon.json")
    if not os.path.exists(lex):
        fail("rabbit-writes/scripts/lexicon.json is missing")
        return
    try:
        with open(lex, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as exc:
        fail("lexicon.json does not parse: %s" % exc)
        return
    bad = 0
    for p in data.get("patterns", []):
        try:
            re.compile(p["rx"])
        except (re.error, KeyError) as exc:
            fail("lexicon pattern %s: %s" % (p.get("id"), exc))
            bad += 1
    notes.append("lexicon: %d patterns, %d tier-1 words, %d bad regex"
                 % (len(data.get("patterns", [])), len(data.get("tier1", [])), bad))

    for ref in ("patterns.md", "false-positives.md", "context.md",
                "voice.md", "craft.md", "checklist.md", "injection.md"):
        if not os.path.exists(os.path.join(SKILLS, "rabbit-writes", "references", ref)):
            fail("rabbit-writes/references/%s is missing" % ref)

    for ref in ("patterns.md", "checklist.md"):
        if not os.path.exists(os.path.join(SKILLS, "readme-writing", "references", ref)):
            fail("readme-writing/references/%s is missing" % ref)

    check_path = os.path.join(SKILLS, "readme-writing", "scripts", "readme_check.py")
    if not os.path.exists(check_path):
        fail("readme-writing/scripts/readme_check.py is missing")
    else:
        # readme_check imports scan.py by path. A rename on either side breaks it
        # at runtime, inside a subagent, where nobody sees the traceback.
        with open(check_path, encoding="utf-8") as fh:
            text = fh.read()
        if 'os.path.join(PLUGIN_ROOT, "skills", "rabbit-writes", "scripts", "scan.py")' not in text:
            notes.append("note: readme_check.py no longer resolves scan.py the documented "
                         "way; check the engine hand-off still works")
        elif not os.path.exists(os.path.join(SKILLS, "rabbit-writes", "scripts", "scan.py")):
            fail("readme_check.py expects rabbit-writes/scripts/scan.py, which is missing")


def check_profile_ids():
    """The tolerance matrix, checked against the ids the engine can actually raise.

    A typo'd id in a register's skip or relax set silently un-skips the rule.
    Nothing fails, nothing warns: the register just quietly stops honouring a
    tolerance it claims, and the only symptom is a finding somebody eventually
    learns to ignore. rwlib.registers.problems knows the rest of the failure
    modes, including a cell that claims a tolerance nothing implements.
    """
    lex_path = os.path.join(ENGINE, "lexicon.json")
    if not (os.path.exists(SCAN) and os.path.exists(lex_path)):
        return
    try:
        from rwlib import registers
        with open(lex_path, encoding="utf-8") as fh:
            lex = json.load(fh)
    except (OSError, ValueError, ImportError) as exc:
        fail("could not load the engine to check the register profiles: %s" % exc)
        return

    known = {p.get("id") for p in lex.get("patterns", [])} | set(SYNTHETIC_FINDING_IDS)
    for problem in registers.problems(known):
        fail("registers.json: %s" % problem)
    notes.append("register profiles: %d registers, %d skip sets, %d relax sets, "
                 "%d rules with no mechanical form"
                 % (len(registers.registers()), len(registers.skip_table()),
                    len(registers.relax_table()),
                    len(registers.unimplemented_rules())))


def check_matrix_doc():
    """references/context.md's table is rendered from registers.json.

    Editing the markdown by hand is the drift this replaced: a documented
    tolerance the engine never had. The renderer is the only writer, and the
    failure message says which command puts it back.
    """
    try:
        from rwlib import registers
    except ImportError as exc:
        fail("could not import rwlib.registers: %s" % exc)
        return
    try:
        if registers.doc_table() != registers.render_table():
            fail("references/context.md's tolerance matrix no longer matches "
                 "registers.json. Run: python3 skills/rabbit-writes/scripts/"
                 "rwlib/registers.py --write")
            return
    except ValueError as exc:
        fail("could not read the tolerance matrix out of context.md: %s" % exc)
        return
    notes.append("tolerance matrix in context.md matches registers.json")


def check_corpus_summary():
    """The committed corpus extract against the research aggregate.

    readme_check.py used to carry these numbers as a literal with a comment
    promising they mirrored the aggregate, and nothing checked the promise. A
    corpus regeneration could orphan every threshold in the checker without a
    word. Skipped, with a note, when the research data is not present: an
    installed skill has no aggregate to compare against.
    """
    try:
        from rwlib import corpus
    except ImportError as exc:
        fail("could not import rwlib.corpus: %s" % exc)
        return
    if not os.path.exists(corpus.SUMMARY_PATH):
        fail("skills/readme-writing/scripts/corpus_summary.json is missing, so "
             "readme_check.py has nothing to compare a README against")
        return
    if not os.path.exists(corpus.AGGREGATE_PATH):
        notes.append("corpus summary present; no research aggregate here to "
                     "check it against")
        return
    differences = corpus.drift()
    for key, shipped, fresh in differences:
        fail("corpus_summary.json %s is %r, the aggregate says %r. Run: "
             "python3 scripts/readme-research/05_export_corpus_summary.py"
             % (key, shipped, fresh))
    if not differences:
        notes.append("corpus summary matches the aggregate (%d repos)"
                     % corpus.load()["n_repos"])


def check_finding_schema():
    """Both checkers emit the same finding shape.

    They did not: readme_check.py used a `detail` key that scan.py never
    emitted, so its own reporter had to branch on the band to find its text and
    no consumer could parse both with one reader. Run over the two sample
    documents in the test fixtures, because a schema that only holds on an empty
    finding list holds trivially.
    """
    try:
        from rwlib import findings as findings_mod
        import scan as scan_mod
    except ImportError as exc:
        fail("could not import the engine to check the finding schema: %s" % exc)
        return
    sample = os.path.join(SKILLS, "rabbit-writes", "tests", "samples", "ai-sample.md")
    if not os.path.exists(sample):
        return
    with open(sample, encoding="utf-8") as fh:
        found, _ = scan_mod.scan(fh.read())
    if not found:
        fail("the AI calibration sample raises no findings, so the schema check "
             "below proves nothing")
        return
    for index, problem in findings_mod.validate(found):
        fail("scan.py finding %d does not match the schema: %s" % (index, problem))

    check_path = os.path.join(SKILLS, "readme-writing", "scripts", "readme_check.py")
    bad_readme = os.path.join(SKILLS, "readme-writing", "tests", "samples", "bad-readme.md")
    if not (os.path.exists(check_path) and os.path.exists(bad_readme)):
        return
    spec = importlib.util.spec_from_file_location("rc_validate", check_path)
    rc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rc)
    with open(bad_readme, encoding="utf-8") as fh:
        rfound = rc.check_readme(fh.read(), bad_readme, use_voice=False)[0]
    if not rfound:
        fail("the bad README fixture raises no findings, so the schema check "
             "below proves nothing")
        return
    for index, problem in findings_mod.validate(rfound):
        fail("readme_check.py finding %d does not match the schema: %s"
             % (index, problem))
    notes.append("finding schema v%d holds for both checkers"
                 % findings_mod.SCHEMA_VERSION)


def check_versions():
    """A published measurement is only reproducible if it says what produced it."""
    try:
        from rwlib import lexicon, registers
    except ImportError as exc:
        fail("could not import rwlib: %s" % exc)
        return
    if lexicon.version() is None:
        fail("lexicon.json has no \"version\" key, so PROOF.md's numbers cannot "
             "be tied to the catalogue that produced them")
    if registers.version() is None:
        fail("registers.json has no \"version\" key")
    proof = os.path.join(SKILLS, "rabbit-writes", "PROOF.md")
    if os.path.exists(proof) and lexicon.version() is not None:
        with open(proof, encoding="utf-8") as fh:
            text = fh.read()
        stamp = "lexicon %s" % lexicon.version()
        if stamp not in text:
            fail("PROOF.md does not say %r, so its measurements are pinned to "
                 "nothing. Regenerate it after changing the lexicon." % stamp)
    notes.append("lexicon %s, registers %s"
                 % (lexicon.version(), registers.version()))


def check_single_definition():
    """One home per rule.

    The portability test was written out in full in three files, and by the time
    anybody compared them they disagreed about whether "country" was on the list
    of things a filler sentence could move to. Every restatement is a future
    drift site, so the definition lives in references/patterns.md and everything
    else points at it.

    Matched on the clause that makes it a definition rather than a reference, so
    a file may name the rule, summarize it, and link to it, and may not spell it
    out a second time. `patterns.md` exempts itself by being the home.
    """
    definitions = {
        "the portability test": (
            re.compile(r"(?i)could move unchanged to another|"
                       r"move unchanged to another (person|company)"),
            os.path.join("skills", "rabbit-writes", "references", "patterns.md"),
        ),
    }
    skip_dirs = {".git", "docs", "_to_delete", "__pycache__", "node_modules"}
    for rule, (rx, home) in definitions.items():
        home_path = os.path.join(ROOT, home)
        if os.path.exists(home_path):
            with open(home_path, encoding="utf-8") as fh:
                if not rx.search(fh.read()):
                    fail("%s is supposed to define %s and no longer does"
                         % (home, rule))
        strays = []
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fn in files:
                if not fn.endswith(".md") or fn in ("CHANGELOG.md", "PROOF.md"):
                    continue
                path = os.path.join(base, fn)
                if os.path.abspath(path) == os.path.abspath(home_path):
                    continue
                try:
                    with open(path, encoding="utf-8") as fh:
                        text = fh.read()
                except (OSError, UnicodeDecodeError):
                    continue
                if rx.search(text):
                    strays.append(os.path.relpath(path, ROOT))
        for stray in strays:
            fail("%s spells out %s, which is defined in %s. Summarize and point "
                 "at the definition instead: two copies of a rule drift, and "
                 "this one already had" % (stray, rule, home))
    notes.append("one definition each for %d cross-cutting rule(s)"
                 % len(definitions))


def check_no_stale_skill_name():
    """The `human-writing` skill merged into `rabbit-writes` in 2.0.0. A leftover
    path points at a directory that no longer exists, and fails at runtime inside
    a subagent where nobody sees the traceback. CHANGELOG is exempt: it documents
    the rename and rewriting history is worse than a stale name."""
    skip_dirs = {".git", "docs", "_to_delete", "__pycache__", "node_modules"}
    hits = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fn in files:
            if not fn.endswith((".md", ".py", ".json")) or fn == "CHANGELOG.md":
                continue
            path = os.path.join(base, fn)
            if os.path.abspath(path) == os.path.abspath(__file__):
                continue  # this file has to name the string in order to search for it
            try:
                with open(path, encoding="utf-8") as fh:
                    stale = "human-writing" in fh.read()
                if stale:
                    hits.append(os.path.relpath(path, ROOT))
            except (OSError, UnicodeDecodeError):
                continue
    for h in hits:
        fail("%s still references the removed `human-writing` skill" % h)
    if not hits:
        notes.append("no stale human-writing references")


def check_mode_contract():
    """The wording that fixes the shallow-edit bug is load-bearing and easy to
    undo by accident. These four assertions pin it. They are deliberately
    annoying to anyone rewording SKILL.md, which is the point."""
    path = os.path.join(SKILLS, "rabbit-writes", "SKILL.md")
    if not os.path.exists(path):
        fail("rabbit-writes/SKILL.md is missing")
        return
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    for mode in ("detect", "deslop", "voice", "draft"):
        if not re.search(r"(?m)^\|\s*\*\*%s\*\*" % mode, text):
            fail("rabbit-writes/SKILL.md: mode %r is not a row in the mode table" % mode)

    guardrails = text.split("## Modes")[0]
    if "minimum effective edit" in guardrails:
        fail("rabbit-writes/SKILL.md: 'minimum effective edit' is back in the guardrails. "
             "It belongs to deslop only; as a guardrail it outranks the voice profile "
             "and caps every conversion at a word swap")
    if "A file path tells you where the text lives" not in text:
        fail("rabbit-writes/SKILL.md: the rule that a file path is not a mode is gone. "
             "Without it, file-pointed requests route to the most conservative mode")
    voice_row = [ln for ln in text.split("\n") if ln.startswith("| **voice**")]
    if voice_row and "order" not in voice_row[0]:
        fail("rabbit-writes/SKILL.md: the voice row no longer says it may change order")
    notes.append("mode contract intact")


def check_scripts_compile():
    """A syntax error in a bundled script only surfaces when a skill runs it."""
    import ast
    for rel in ("rabbit-writes/scripts/scan.py", "rabbit-writes/scripts/verify.py",
                "readme-writing/scripts/readme_check.py",
                "voice-setup/scripts/measure_voice.py",
                "voice-setup/scripts/build_voice.py"):
        path = os.path.join(SKILLS, rel)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                ast.parse(fh.read(), filename=path)
        except SyntaxError as exc:
            fail("%s does not parse: %s" % (rel, exc))
    notes.append("bundled scripts compile")


# A README that a stranger might plausibly commit. It carries a semicolon and an
# em dash on purpose: both are P0 under this repository's own voice profile and
# neither is a defect in anybody else's prose, so a hook that blocks on them is
# the bug this check exists to catch. No P0 structure or fingerprint problems,
# because those a hook is supposed to block on.
CONSUMER_README = """# widget

widget is a command-line tool that resizes images in bulk; it reads a directory
and writes thumbnails next to each original — nothing else.

## Install

```sh
npm install -g widget
```

## Usage

```sh
widget ./photos --size 240
```

## License

MIT.
"""


def parse_hooks(text):
    """[(id, entry, args)] out of .pre-commit-hooks.yaml.

    Hand-rolled because this file is stdlib-only and PyYAML is not a dependency
    worth adding to a validator. The shape it parses is the shape the file is
    written in, and check_precommit_hooks fails loudly if it comes back empty.

    Both YAML list spellings for `args`, flow and block. Flow-only, rewriting
    `args: [--voice-rules, path]` into the block form that YAML documents prefer
    dropped the arguments on the floor: the hook still ran, still passed, and
    the `--voice-rules` regression this whole check exists for stopped being
    covered without a word.
    """
    out = []
    for block in text.split("\n- id: ")[1:]:
        lines = block.splitlines()
        hook_id = lines[0].strip()
        entry, args, in_args = "", [], False
        for line in lines[1:]:
            stripped = line.strip()
            if in_args and stripped.startswith("- "):
                args.append(stripped[2:].strip().strip("'\""))
                continue
            in_args = False
            if line.startswith("  entry:"):
                entry = line.split(":", 1)[1].strip()
            elif line.startswith("  args:"):
                raw = line.split(":", 1)[1].strip().strip("[]")
                args = [a.strip().strip("'\"") for a in raw.split(",") if a.strip()]
                in_args = not args
        out.append((hook_id, entry, args))
    return out


def check_precommit_hooks():
    """Run every shipped hook the way pre-commit runs it: from somebody else's
    repository, on somebody else's README.

    Two shipped hooks were broken on arrival and both suites were blind to it,
    because everything else in the tree runs from this repository root with this
    repository's files. `readme-check` blocked a stranger's commit over this
    author's semicolon, and `rabbit-scan-voice` passed a plugin-relative
    `--voice-rules` path straight through to a working directory where it does
    not exist, so scan.py exited 2 and precommit.py called that a P0 finding.
    """
    import shutil
    import subprocess
    import tempfile

    hooks_path = os.path.join(ROOT, ".pre-commit-hooks.yaml")
    if not os.path.exists(hooks_path):
        fail(".pre-commit-hooks.yaml is missing, so the hooks ship unusable")
        return
    with open(hooks_path, encoding="utf-8") as fh:
        hooks_text = fh.read()
    hooks = parse_hooks(hooks_text)
    if not hooks:
        fail("no hooks parsed out of .pre-commit-hooks.yaml, so this check is "
             "passing on an empty list. Did the file's shape change?")
        return
    # The same guard one level down. An empty hook list is loud; a hook whose
    # `args` silently parsed to nothing is not, and the shipped voice flag is the
    # single argument this whole check was written to cover. Written against
    # `args:` rather than against a flag name, because the flag has changed once
    # already: the invariant is that parse_hooks read the arguments, not which
    # arguments they happen to be this release.
    if "\n  args:" in hooks_text and not any(args for _, _, args in hooks):
        fail(".pre-commit-hooks.yaml has an `args:` line but parse_hooks found "
             "arguments on no hook, so the flags the hooks ship with are no "
             "longer covered. Did the `args` shape change?")

    precommit = os.path.join(ROOT, "scripts", "precommit.py")
    if not os.access(precommit, os.X_OK):
        fail("scripts/precommit.py is not executable, and `language: script` "
             "runs the entry directly rather than through python3")

    tmp = tempfile.mkdtemp(prefix="rabbit-hook-")
    try:
        readme = os.path.join(tmp, "README.md")
        with open(readme, "w", encoding="utf-8") as fh:
            fh.write(CONSUMER_README)
        for hook_id, entry, args in hooks:
            words = entry.split()
            if not words or not words[0].endswith("precommit.py"):
                fail("hook %r does not go through scripts/precommit.py, so the "
                     "batching and the flag split are bypassed" % hook_id)
                continue
            # Whether this hook applies somebody's style rules, read off its own
            # configuration rather than off its name. A substring test on the id
            # turns the strongest assertion here off silently the day a hook is
            # renamed, and it is the assertion that catches a default hook
            # blocking a stranger's commit over this author's punctuation.
            checker = words[1] if len(words) > 1 else ""
            # `--voice` covers `--voice-rules` too, which is the point: a hook
            # that names a profile any way at all is one that applies somebody's
            # style rules, and this must not go stale the next time the flag
            # spelling changes.
            applies_voice = ("--no-voice" not in words
                             and (checker == "readme"
                                  or any(a.startswith("--voice") for a in args)))
            # cwd is the temp directory, which is the whole point: pre-commit
            # runs hooks from the consuming repository, and every relative path
            # in `args` resolves there.
            result = subprocess.run(
                [sys.executable, precommit] + words[1:] + args + ["--", "README.md"],
                cwd=tmp, capture_output=True, text=True)
            if result.returncode == 2 or "could not check" in result.stderr:
                fail("hook %r cannot run from a consuming repository: exit %d. %s"
                     % (hook_id, result.returncode,
                        result.stderr.strip().splitlines()[0] if result.stderr.strip()
                        else "no stderr"))
            elif not applies_voice and result.returncode:
                fail("hook %r blocks an ordinary third-party README (exit %d). "
                     "The default hooks may only fail on evidence, not on this "
                     "repository's own style rules." % (hook_id, result.returncode))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # The regression the VALUE_FLAGS set exists to prevent, pinned rather than
    # left to the comment asking the next person to remember.
    spec = importlib.util.spec_from_file_location("rw_precommit", precommit)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:                              # noqa: BLE001
        fail("could not import scripts/precommit.py: %s" % exc)
        return
    flags, files = module.split_args(
        ["--check", "--voice-rules", "voices/dana.rules.json", "a.md", "b.md"])
    if files != ["a.md", "b.md"]:
        fail("precommit.split_args treats a value-taking flag's value as a file: "
             "got %r. Add the option to VALUE_FLAGS." % files)
    if "voices/dana.rules.json" not in flags:
        fail("precommit.split_args dropped the --voice-rules value: %r" % flags)
    notes.append("%d pre-commit hook(s) run from a foreign working directory"
                 % len(hooks))


def check_cross_references():
    """A ${CLAUDE_PLUGIN_ROOT} path that points nowhere fails silently at runtime."""
    rx = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")
    for skill in sorted(os.listdir(SKILLS)):
        skill_dir = os.path.join(SKILLS, skill)
        if not os.path.isdir(skill_dir):
            continue
        # References and bundled scripts cite these paths too, and a dead path in
        # a reference file fails exactly as silently as one in SKILL.md.
        targets = [os.path.join(skill_dir, "SKILL.md")]
        for sub in ("references", "scripts", "voices"):
            subdir = os.path.join(skill_dir, sub)
            if os.path.isdir(subdir):
                targets += [os.path.join(subdir, f) for f in sorted(os.listdir(subdir))
                            if f.endswith((".md", ".py"))]
        for path in targets:
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            for rel in set(rx.findall(text)):
                if "<" in rel or rel.endswith("/"):
                    continue
                if not os.path.exists(os.path.join(ROOT, rel)):
                    fail("%s references a missing path: %s"
                         % (os.path.relpath(path, ROOT), rel))


check_manifests()
check_skills()
check_voices()
check_engine()
check_profile_ids()
check_matrix_doc()
check_corpus_summary()
check_finding_schema()
check_versions()
check_single_definition()
check_no_stale_skill_name()
check_mode_contract()
check_scripts_compile()
check_precommit_hooks()
check_cross_references()

for note in notes:
    print("  %s" % note)

if problems:
    print("\n%d problem(s):" % len(problems))
    for p in problems:
        print("  FAIL  %s" % p)
    sys.exit(1)

print("\nrepo valid")
