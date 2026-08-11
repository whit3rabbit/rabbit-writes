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
SCAN = os.path.join(SKILLS, "rabbit-writes", "scripts", "scan.py")

# Findings scan.py raises itself rather than from a lexicon pattern. A register
# may name any of these in PROFILE_SKIP or PROFILE_RELAX, so the id check below
# has to know them.
SYNTHETIC_FINDING_IDS = {
    "hidden-unicode", "tier1", "clarity", "tier2-cluster", "tier3-density",
    "uniformity", "low-diversity", "trigram-repetition", "uniform-paragraphs",
    "em-dash-rate",
}

problems = []
notes = []


def fail(msg):
    problems.append(msg)


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


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

        if not fn.endswith(".rules.json"):
            continue

        vname = fn[:-11]
        try:
            with open(os.path.join(VOICES, fn), encoding="utf-8") as fh:
                data = json.load(fh)
        except ValueError as exc:
            fail("voices/%s does not parse: %s" % (fn, exc))
            continue

        if "voice" in data and data["voice"] != vname and vname != "TEMPLATE":
            fail("voices/%s: 'voice' field %r does not match filename %r"
                 % (fn, data["voice"], vname))

        for entry in data.get("banned_regex", []):
            if "id" not in entry or "rx" not in entry:
                fail("voices/%s: banned_regex entry needs id and rx" % fn)
                continue
            try:
                re.compile(entry["rx"])
            except re.error as exc:
                fail("voices/%s: regex %s does not compile: %s"
                     % (fn, entry["id"], exc))
        for entry in data.get("required_when", []):
            for rx in entry.get("any_of_rx", []):
                try:
                    re.compile(rx)
                except re.error as exc:
                    fail("voices/%s: required_when regex does not compile: %s"
                         % (fn, exc))
        for key in ("banned_words", "banned_phrases"):
            if key in data and not isinstance(data[key], list):
                fail("voices/%s: %s must be a list" % (fn, key))
        notes.append("voices/%s ok (%d words, %d phrases, %d regex)"
                     % (fn, len(data.get("banned_words", [])),
                        len(data.get("banned_phrases", [])),
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
                "voice.md", "craft.md", "checklist.md"):
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
    """A typo'd id in a register's skip or relax set silently un-skips the rule.

    Nothing fails, nothing warns: the register just quietly stops honouring a
    tolerance it claims in references/context.md, and the only symptom is a
    finding somebody eventually learns to ignore."""
    lex_path = os.path.join(SKILLS, "rabbit-writes", "scripts", "lexicon.json")
    if not (os.path.exists(SCAN) and os.path.exists(lex_path)):
        return
    try:
        spec = importlib.util.spec_from_file_location("rw_scan_validate", SCAN)
        scan = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scan)
        with open(lex_path, encoding="utf-8") as fh:
            lex = json.load(fh)
    except (OSError, ValueError, SyntaxError) as exc:
        fail("could not load scan.py to check the register profiles: %s" % exc)
        return

    known = {p.get("id") for p in lex.get("patterns", [])} | SYNTHETIC_FINDING_IDS
    for name, table in (("PROFILE_SKIP", scan.PROFILE_SKIP),
                        ("PROFILE_RELAX", scan.PROFILE_RELAX)):
        for profile, entries in table.items():
            for pid in sorted(entries):
                if pid not in known:
                    fail("scan.py %s[%r] names %r, which is not a lexicon "
                         "pattern id or a built-in finding id" % (name, profile, pid))
    overlap = {p: sorted(set(scan.PROFILE_SKIP.get(p, ())) & set(relaxed))
               for p, relaxed in scan.PROFILE_RELAX.items()}
    for profile, ids in overlap.items():
        if ids:
            fail("scan.py profile %r both skips and relaxes %s; skip wins, so the "
                 "allowance never applies" % (profile, ", ".join(ids)))
    notes.append("register profiles: %d skip sets, %d relax sets, all ids known"
                 % (len(scan.PROFILE_SKIP), len(scan.PROFILE_RELAX)))


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
                "readme-writing/scripts/readme_check.py"):
        path = os.path.join(SKILLS, rel)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                ast.parse(fh.read(), filename=path)
        except SyntaxError as exc:
            fail("%s does not parse: %s" % (rel, exc))
    notes.append("bundled scripts compile")


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
check_no_stale_skill_name()
check_mode_contract()
check_scripts_compile()
check_cross_references()

for note in notes:
    print("  %s" % note)

if problems:
    print("\n%d problem(s):" % len(problems))
    for p in problems:
        print("  FAIL  %s" % p)
    sys.exit(1)

print("\nrepo valid")
