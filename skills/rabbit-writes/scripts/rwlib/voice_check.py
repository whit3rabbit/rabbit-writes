#!/usr/bin/env python3
"""
Is this voice profile a voice profile, or is it a copy of the template?

Two callers, one answer. `voice-setup/scripts/build_voice.py --check` runs this
on one profile, in an install where the repository's validate.py was never
copied in, and `scripts/validate.py` runs it on every profile in voices/. They
used to be one checker and no checker: validate.py compiled the regexes and
matched the filename, and nothing at all ran on the machine where somebody
actually writes a profile. Splitting the logic across the two would have
repeated the drift `rwlib.voices.resolve` exists to end, where two halves of one
plugin disagreed about whose rules were in force.

What it looks for, in the order it matters:

  template residue    an underscore-prefixed key, the `example-rule` entry, or
                      `"voice": "<name>"`. Every one of these is enforced,
                      silently, against the name of a person who did not write
                      it. `example-rule` compiles cleanly, which is why nothing
                      caught it before.
  rules that cannot   a regex that does not compile, a mechanic this engine
  run                 does not read, a register that does not exist. All three
                      fail the same way at runtime, which is by doing nothing.
  a missing half      a rules file with no markdown beside it enforces
                      punctuation and describes nobody.
  an unfilled form    guidance prompts still in the markdown.

Everything here is structural. Whether a rule *fires* is a separate question and
a harder one, and it lives in build_voice.py, which has scan.py to answer it
with.

Stdlib only, 3.9+.
"""

import json
import os
import re

try:
    from . import inflect as inflect_mod
    from . import registers as registers_mod
    from . import stylometry as stylometry_mod
    from . import voices as voices_mod
except ImportError:                     # run as a script: rwlib/ is on sys.path
    import inflect as inflect_mod
    import registers as registers_mod
    import stylometry as stylometry_mod
    import voices as voices_mod

FAIL = "fail"
NOTE = "note"

# The template's own markers. Each one is a thing its guidance tells the copier
# to delete, and each one survived a real copy at least once.
TEMPLATE_VOICE_NAME = "<name>"
EXAMPLE_RULE_ID = "example-rule"
COPY_INSTRUCTION_RX = re.compile(r"(?m)^>\s*Copy this file to")
# A guidance prompt, as the template writes them: an angle-bracket span holding
# a sentence. Narrow on purpose. An HTML tag has no spaces in it and `<name>` is
# caught by its own check above, so the length-and-a-space test is what
# separates "the author has not filled this in" from markup somebody meant.
GUIDANCE_RX = re.compile(r"<[A-Za-z][^<>]{18,}>", re.S)
MEASURED_HEADING = "## Measured from samples"

MD_SUFFIX = ".md"


def _finding(level, message):
    return {"level": level, "message": message}


def _name_of(rules_path):
    return voices_mod.strip_rules_suffix(os.path.basename(rules_path))


def check_rules(rules_path, voices_dir=None):
    """Structural checks on the rules file alone."""
    out = []
    name = _name_of(rules_path)

    try:
        with open(rules_path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except OSError as exc:
        return [_finding(FAIL, "%s cannot be read: %s"
                         % (os.path.basename(rules_path), exc))]
    except ValueError as exc:
        return [_finding(FAIL, "%s does not parse: %s"
                         % (os.path.basename(rules_path), exc))]
    if not isinstance(raw, dict):
        return [_finding(FAIL, "%s is not a rules object"
                         % os.path.basename(rules_path))]

    # Template residue, first, because everything below it reports on rules that
    # a half-deleted template makes up.
    stray = [k for k in raw if k.startswith("_")]
    if stray:
        out.append(_finding(FAIL, "%s still carries the template's guidance "
                            "keys (%s). They are inert, and they are somebody "
                            "else's documentation sitting in a file with this "
                            "author's name on it: delete them."
                            % (name, ", ".join(sorted(stray)))))
    stray_mech = [k for k in raw.get("mechanics", {}) if k.startswith("_")]
    if stray_mech:
        out.append(_finding(FAIL, "%s: mechanics still carries %s from the "
                            "template" % (name, ", ".join(sorted(stray_mech)))))
    if any(e.get("id") == EXAMPLE_RULE_ID for e in raw.get("banned_regex", [])):
        out.append(_finding(FAIL, "%s still has the template's %r entry, which "
                            "is enforced at this profile's priority against a "
                            "phrase nobody chose. It compiles, so nothing else "
                            "notices." % (name, EXAMPLE_RULE_ID)))
    if raw.get("voice") == TEMPLATE_VOICE_NAME:
        out.append(_finding(FAIL, "%s: the `voice` field is still the "
                            "template's %r" % (name, TEMPLATE_VOICE_NAME)))
    elif "voice" in raw and raw["voice"] != name:
        out.append(_finding(FAIL, "%s: `voice` field is %r but the filename "
                            "says %r, and scan.py reports the field"
                            % (name, raw["voice"], name)))

    # Inheritance. A parent that does not resolve is not a smaller profile, it
    # is no profile: see the module docstring in voices.py.
    try:
        rules = voices_mod.load(rules_path, voices_dir)
    except voices_mod.VoiceError as exc:
        out.append(_finding(FAIL, "%s: %s" % (name, exc)))
        rules = raw
    else:
        if raw.get("extends"):
            out.append(_finding(NOTE, "%s extends %s"
                                % (name, raw["extends"])))

    known_registers = set(registers_mod.registers())

    for key, message in voices_mod.mechanic_problems(rules.get("mechanics", {})):
        out.append(_finding(FAIL, "%s: mechanics.%s %s" % (name, key, message)))
    for register, overrides in rules.get("mechanics_by_register", {}).items():
        if register not in known_registers:
            out.append(_finding(FAIL, "%s: mechanics_by_register names %r, "
                                "which is not a register (%s). A typo here is "
                                "a rule that silently stops applying."
                                % (name, register,
                                   ", ".join(sorted(known_registers)))))
        for key, message in voices_mod.mechanic_problems(overrides):
            out.append(_finding(FAIL, "%s: mechanics_by_register.%s.%s %s"
                                % (name, register, key, message)))

    for key in ("banned_words", "banned_phrases"):
        out += _ban_list_problems(name, key, rules.get(key, []))

    seen_ids = set()
    for entry in rules.get("banned_regex", []):
        eid = entry.get("id")
        if not eid or "rx" not in entry:
            out.append(_finding(FAIL, "%s: a banned_regex entry needs id and "
                                "rx (%s)" % (name, json.dumps(entry)[:80])))
            continue
        if eid in seen_ids:
            out.append(_finding(FAIL, "%s: two banned_regex entries share the "
                                "id %r, and a later one wins on merge" % (name, eid)))
        seen_ids.add(eid)
        try:
            rx = re.compile(entry["rx"])
        except re.error as exc:
            out.append(_finding(FAIL, "%s: regex %s does not compile: %s"
                                % (name, eid, exc)))
            rx = None
        priority = entry.get("priority")
        if priority is not None and priority not in voices_mod.PRIORITY_ORDER:
            out.append(_finding(FAIL, "%s: %s has priority %r, not one of %s"
                                % (name, eid, priority,
                                   ", ".join(voices_mod.PRIORITY_ORDER))))
        out += _register_scope(name, eid, entry, known_registers)
        # An optional worked example, and the cheapest proof a pattern does
        # what its author thinks. build_voice.py runs it through scan.py as
        # well, which is the end-to-end half; this catches it without one.
        example = entry.get("example")
        if rx is not None and example is not None and not rx.search(example):
            out.append(_finding(FAIL, "%s: %s does not match its own example "
                                "%r, so the rule cannot fire on the text its "
                                "author wrote it for" % (name, eid, example)))

    for entry in rules.get("required_when", []):
        eid = entry.get("id", "?")
        for key in ("any_of_rx",):
            for pattern in entry.get(key, []):
                try:
                    re.compile(pattern)
                except re.error as exc:
                    out.append(_finding(FAIL, "%s: required_when %s has a "
                                        "regex that does not compile: %s"
                                        % (name, eid, exc)))
        gate = entry.get("when_rx")
        if gate:
            try:
                re.compile(gate)
            except re.error as exc:
                out.append(_finding(FAIL, "%s: required_when %s when_rx does "
                                    "not compile: %s" % (name, eid, exc)))
        if not entry.get("any_of_rx"):
            out.append(_finding(FAIL, "%s: required_when %s has no any_of_rx, "
                                "so it fires on every document" % (name, eid)))
        out += _register_scope(name, eid, entry, known_registers)

    default = rules.get("default_priority", "P0")
    if default not in voices_mod.PRIORITY_ORDER:
        out.append(_finding(FAIL, "%s: default_priority is %r, not one of %s"
                            % (name, default, ", ".join(voices_mod.PRIORITY_ORDER))))

    enforced = (len(rules.get("banned_words", []))
                + len(rules.get("banned_phrases", []))
                + len(rules.get("banned_regex", []))
                + len([k for k, v in rules.get("mechanics", {}).items()
                       if not k.startswith("_") and v not in ("allow", "any")]))
    if not enforced:
        out.append(_finding(NOTE, "%s enforces nothing mechanically. Valid, and "
                            "worth saying out loud: every rule in it is a "
                            "rule a reader applies." % name))
    return out


BAN_ENTRY_KEYS = {"word", "phrase", "inflect"}


def _ban_list_problems(name, key, entries):
    """A ban entry the engine will compile into nothing.

    `rwlib.inflect.term_of` reads the term out of `word` or `phrase` and returns
    "" for anything else, and an empty term compiles to a pattern that matches
    nothing. That is the whole failure: `{"term": "synergy"}` reads like a ban,
    parses as JSON, survives a merge, and is not enforced.
    """
    out = []
    for entry in entries:
        if isinstance(entry, dict):
            unknown = sorted(set(entry) - BAN_ENTRY_KEYS)
            if unknown:
                out.append(_finding(FAIL, "%s: a %s entry has key(s) the engine "
                                    "does not read (%s). The term comes from "
                                    "`word` or `phrase`."
                                    % (name, key, ", ".join(unknown))))
        elif not isinstance(entry, str):
            out.append(_finding(FAIL, "%s: a %s entry is %r, which is neither a "
                                "string nor an object" % (name, key, entry)))
            continue
        term = inflect_mod.term_of(entry)
        if not term.strip():
            out.append(_finding(FAIL, "%s: an empty %s entry (%s) matches "
                                "nothing" % (name, key, json.dumps(entry))))
        elif term != term.strip():
            out.append(_finding(FAIL, "%s: the %s entry %r is padded with "
                                "whitespace, which is part of the pattern and "
                                "will not match" % (name, key, term)))
        elif key == "banned_words" and re.search(r"\s", term):
            out.append(_finding(NOTE, "%s: %r is in banned_words and has a "
                                "space in it. It matches, on one line only: "
                                "banned_phrases is the list whose whitespace "
                                "flexes across a line break." % (name, term)))
    return out


def _register_scope(name, eid, entry, known_registers):
    out = []
    for register in entry.get("applies_to_registers", []):
        if register not in known_registers:
            out.append(_finding(FAIL, "%s: %s is scoped to register %r, which "
                                "does not exist, so it applies nowhere at all"
                                % (name, eid, register)))
    return out


def check_markdown(rules_path):
    """The half a regex cannot enforce, checked for being present and filled."""
    out = []
    name = _name_of(rules_path)
    md_path = voices_mod.strip_rules_suffix(rules_path) + MD_SUFFIX
    if not os.path.exists(md_path):
        out.append(_finding(FAIL, "%s has no %s.md beside it. A rules file on "
                            "its own enforces punctuation and describes "
                            "nobody, and it is the markdown the model reads."
                            % (os.path.basename(rules_path), name)))
        return out
    try:
        with open(md_path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        out.append(_finding(FAIL, "%s.md cannot be read: %s" % (name, exc)))
        return out

    if COPY_INSTRUCTION_RX.search(text):
        out.append(_finding(FAIL, "%s.md still opens with the template's copy "
                            "instructions" % name))
    prompts = GUIDANCE_RX.findall(text)
    if prompts:
        out.append(_finding(FAIL, "%s.md still carries %d unfilled guidance "
                            "prompt(s) from the template, starting at %r. Each "
                            "one is a section describing what to write rather "
                            "than what this person writes."
                            % (name, len(prompts), prompts[0][:60])))
    if TEMPLATE_VOICE_NAME in text:
        out.append(_finding(FAIL, "%s.md still says %r somewhere"
                            % (name, TEMPLATE_VOICE_NAME)))

    if MEASURED_HEADING in text:
        block = text.split(MEASURED_HEADING, 1)[1]
        numbers = re.findall(r"(?m)^\s*[a-z_0-9]+:\s*(\S+)\s*$", block[:600])
        if not numbers:
            out.append(_finding(NOTE, "%s.md has an empty `Measured from "
                                "samples` block. Fill it with measure_voice.py "
                                "or delete the section: an empty one reads as "
                                "a measurement nobody took." % name))
    return out


def check_fingerprint(rules_path):
    """The optional third file, when there is one."""
    out = []
    name = _name_of(rules_path)
    path = (voices_mod.strip_rules_suffix(rules_path)
            + stylometry_mod.FINGERPRINT_SUFFIX)
    if not os.path.exists(path):
        return out
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        out.append(_finding(FAIL, "%s%s does not parse: %s"
                            % (name, stylometry_mod.FINGERPRINT_SUFFIX, exc)))
        return out
    declared = data.get("schema_version")
    if declared != stylometry_mod.SCHEMA_VERSION:
        out.append(_finding(FAIL, "%s%s is schema %r and stylometry.py reads "
                            "%d. Regenerate it with measure_voice.py: the "
                            "marker list has moved and the stored means are "
                            "against a baseline nobody builds now."
                            % (name, stylometry_mod.FINGERPRINT_SUFFIX,
                               declared, stylometry_mod.SCHEMA_VERSION)))
    elif data.get("voice") not in (None, name):
        out.append(_finding(FAIL, "%s%s: `voice` field %r does not match the "
                            "filename" % (name, stylometry_mod.FINGERPRINT_SUFFIX,
                                          data.get("voice"))))
    else:
        band = data.get("self_distance", {})
        out.append(_finding(NOTE, "%s has a fingerprint (%s samples, band max "
                            "%s)" % (name, data.get("n_samples", "?"),
                                     band.get("max", "?"))))
    return out


def check_profile(rules_path, voices_dir=None, markdown=True):
    """Everything, for one profile. [{"level": ..., "message": ...}]."""
    out = check_rules(rules_path, voices_dir)
    if markdown:
        out += check_markdown(rules_path)
    out += check_fingerprint(rules_path)
    return out


def failures(results):
    return [r for r in results if r["level"] == FAIL]
