#!/usr/bin/env python3
"""
Repo validator. Checks the things that break an install silently.

    python3 scripts/validate.py

Exit 0 clean, 1 on any failure. Stdlib only.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
VOICES = os.path.join(SKILLS, "rabbit-writes", "voices")

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
        text = open(path, encoding="utf-8").read()
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
    for required in ("rabbit-writes", "human-writing", "voice-setup"):
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
        active = open(active_path, encoding="utf-8").read().strip()
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
            data = json.loads(open(os.path.join(VOICES, fn), encoding="utf-8").read())
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
    lex = os.path.join(SKILLS, "human-writing", "scripts", "lexicon.json")
    if not os.path.exists(lex):
        fail("human-writing/scripts/lexicon.json is missing")
        return
    try:
        data = json.loads(open(lex, encoding="utf-8").read())
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
        if not os.path.exists(os.path.join(SKILLS, "human-writing", "references", ref)):
            fail("human-writing/references/%s is missing" % ref)


def check_cross_references():
    """A ${CLAUDE_PLUGIN_ROOT} path that points nowhere fails silently at runtime."""
    rx = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")
    for skill in sorted(os.listdir(SKILLS)):
        path = os.path.join(SKILLS, skill, "SKILL.md")
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        for rel in set(rx.findall(text)):
            if "<" in rel or rel.endswith("/"):
                continue
            if not os.path.exists(os.path.join(ROOT, rel)):
                fail("skills/%s references a missing path: %s" % (skill, rel))


check_manifests()
check_skills()
check_voices()
check_engine()
check_cross_references()

for note in notes:
    print("  %s" % note)

if problems:
    print("\n%d problem(s):" % len(problems))
    for p in problems:
        print("  FAIL  %s" % p)
    sys.exit(1)

print("\nrepo valid")
