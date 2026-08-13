#!/usr/bin/env python3
"""
Voice rules: the mechanics the shipped profiles exercise, the ones they do not,
and inheritance.

Every mechanic in apply_voice_rules is reachable from a user-authored rules
file, and the profile this repo ships sets one value each. The branches nobody
here uses are the ones that ship broken, which is what the inline-rules helper
is for.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

from helpers import (SAMPLES, SCAN, VOICES, WHIT3RABBIT_RULES, scan_json,
                     scan_module as load_scan, scan_text, scan_with_rules,
                     voice_ids, written)

from rwlib import voices

BAD_LETTER = (
    "Good morning,\n\n"
    "We need to circle back on the synergy here — the wild west "
    "of AI driven tooling is a real risk 🚀. I'm so excited "
    "to announce our 100% secure platform, live September 12, 2025.\n\n"
    "Attached is the report; it covers everything.\n\n"
    "No.\n\n"
    "Thanks,\n-whit3rabbit\n")


def bad_letter_result():
    return scan_text(BAD_LETTER, "--voice-rules", WHIT3RABBIT_RULES)[0]


def test_the_shipped_profile_catches_its_own_mechanics():
    found = set(voice_ids(bad_letter_result()))
    for pattern_id in ("voice-em-dash", "voice-semicolon", "voice-emoji",
                       "voice-one-word-sentence", "voice-date-format",
                       "voice-banned-word", "voice-banned-phrase",
                       "absolute-claim", "manufactured-enthusiasm"):
        assert pattern_id in found, "%s missing from %s" % (pattern_id, sorted(found))


def test_every_voice_finding_reports_the_priority_its_rule_declares():
    """Read out of the rules file rather than a list written here. The previous
    version asserted P0 for everything with two ids excused by name, which held
    only because this fixture happens to miss hedge-softener, numeric-date, and
    efficiency-overuse."""
    with open(WHIT3RABBIT_RULES, encoding="utf-8") as fh:
        rules = json.load(fh)
    default = rules.get("default_priority", "P0")
    # scan.py hard-codes P2 for these two whatever the voice default is: no
    # regex settles a serial comma, and an editor curls quotes on its own.
    declared = {"voice-curly-quote": "P2", "voice-oxford-comma": "P2"}
    for entry in rules.get("banned_regex", []):
        declared[entry["id"]] = entry.get("priority", default)
    for entry in rules.get("required_when", []):
        declared[entry["id"]] = entry.get("priority", "P2")

    mismatched = [(f["id"], f["priority"], declared.get(f["id"], default))
                  for f in bad_letter_result()["findings"]
                  if f["band"] == "voice"
                  and f["priority"] != declared.get(f["id"], default)]
    assert not mismatched, str(mismatched)


def test_the_voice_band_is_reported_separately():
    assert bad_letter_result()["counts"]["voice"] >= 9, str(bad_letter_result()["counts"])


def test_a_register_never_relaxes_a_voice_rule():
    """Lowercase and loose punctuation are fine off the clock. A banned phrase
    is not."""
    strict = set(voice_ids(bad_letter_result()))
    relaxed, _ = scan_text(BAD_LETTER, "--voice-rules", WHIT3RABBIT_RULES,
                           "--profile", "chat")
    assert strict == set(voice_ids(relaxed)), "lost: %s" % (
        strict - set(voice_ids(relaxed)))


def test_no_voice_rules_means_no_voice_band():
    plain, _ = scan_text(BAD_LETTER)
    assert plain["counts"].get("voice", 0) == 0


def test_the_writers_own_register_passes_the_writers_own_rules():
    good = (
        "Good morning,\n\n"
        "Attached is the Q3 incident review. Short version: the outage "
        "came from an expired certificate on the internal proxy, not from "
        "the deploy. We caught it in 22 minutes.\n\n"
        "I really appreciate the time your team spent on the rollback "
        "plan. I know it wasn't easy on a Friday.\n\n"
        "The evidence is in section 3, with the raw logs linked at the "
        "bottom. I believe the fix holds, and I want to re-check the "
        "renewal alerting before we close it out on 12 September 2025.\n\n"
        "Thanks,\n-whit3rabbit\n")
    result, _ = scan_text(good, "--voice-rules", WHIT3RABBIT_RULES)
    assert result["counts"]["voice"] == 0, str(
        [f["label"] for f in result["findings"] if f["band"] == "voice"])


def test_the_template_profile_is_inert():
    template = os.path.join(VOICES, "TEMPLATE.rules.json")
    if not os.path.exists(template):
        return
    result = scan_json(os.path.join(SAMPLES, "human-sample.md"),
                       "--voice-rules", template)
    found = {f["id"] for f in result["findings"] if f["band"] == "voice"}
    assert found <= {"example-rule"}, str(found)


# --------------------------------------------------------------------------
# the serial comma, the advisory mechanic
#
# Advisory means reported, never enforced: it lands at P2 and it has to stay off
# the shapes it cannot decide. No regex tells a three-item list from a compound
# sentence.
# --------------------------------------------------------------------------

def test_a_three_item_list_without_the_serial_comma_is_reported():
    result, _ = scan_text(
        "We shipped the parser, the linter and the formatter this week.\n\n"
        "Read the catalog with more examples, and the checklist at the end "
        "of any draft or edit.\n\n"
        "She left the room, and he stayed behind to finish it.\n",
        "--voice-rules", WHIT3RABBIT_RULES)
    hits = [f for f in result["findings"] if f["id"] == "voice-oxford-comma"]
    assert len(hits) == 1, str([(f["line"], f["match"]) for f in hits])
    assert all(f["priority"] == "P2" for f in hits), str(hits)
    assert all(f["line"] == 1 for f in hits), str([f["line"] for f in hits])


FORBID_OXFORD = {"voice": "t", "default_priority": "P0",
                 "mechanics": {"oxford_comma": "forbid"}}


def test_a_serial_comma_is_reported_when_the_voice_omits_it():
    """The forbid side had no guard at all: a bare `,\\s+(?:and|or)` matches every
    compound sentence in the language, and nothing exercised the branch, so an
    entire mechanic shipped reporting on correct punctuation."""
    result, _ = scan_with_rules(
        "We shipped the parser, the linter, and the formatter this week.\n\n"
        "She left the room, and he stayed behind to finish it.\n\n"
        "Read the catalog with more examples, and the checklist at the end.\n",
        FORBID_OXFORD)
    hits = [f for f in result["findings"] if f["id"] == "voice-oxford-comma"]
    assert len(hits) == 1, str([(f["line"], f["match"]) for f in hits])
    assert all(f["line"] == 1 for f in hits), str([f["line"] for f in hits])
    assert all(f["priority"] == "P2" for f in hits), str(hits)


def test_prose_with_no_serial_comma_is_silent_under_forbid():
    result, _ = scan_with_rules(
        "We shipped the parser, the linter and the formatter this week.\n\n"
        "She left the room, and he stayed behind to finish it.\n", FORBID_OXFORD)
    assert not [f for f in result["findings"] if f["id"] == "voice-oxford-comma"], (
        str(voice_ids(result)))


# --------------------------------------------------------------------------
# mechanics the shipped profiles do not exercise
# --------------------------------------------------------------------------

LIMIT_DASH = {"voice": "t", "default_priority": "P0",
              "mechanics": {"em_dash": "limit", "max_em_dashes_per_1000w": 2}}


def test_em_dash_limit_fires_above_the_cap():
    over, _ = scan_with_rules(
        "The plan — such as it is — has three parts — and a deadline.\n", LIMIT_DASH)
    assert "voice-em-dash-rate" in voice_ids(over), str(voice_ids(over))
    assert "voice-em-dash" not in voice_ids(over), str(voice_ids(over))


def test_em_dash_limit_stays_quiet_under_the_cap():
    under, _ = scan_with_rules(
        "The plan has three parts and a deadline, and nobody argued.\n", LIMIT_DASH)
    assert not voice_ids(under), str(voice_ids(under))


FORBID_DASH = {"voice": "t", "default_priority": "P0",
               "mechanics": {"em_dash": "forbid"}}


def test_a_numeric_en_dash_range_is_not_a_forbidden_em_dash():
    """The same carve-out verify.py grants, on this side of the plugin. Without
    it a rewrite that correctly writes a date range as 2010–2023 passes
    verification and fails the scan, and one file gets two opposite answers from
    one plugin."""
    ranged, _ = scan_with_rules(
        "The study ran 2010–2023 across four sites, pp. 14–18.\n", FORBID_DASH)
    assert "voice-em-dash" not in voice_ids(ranged), str(voice_ids(ranged))
    assert ranged["stats"]["em_dashes"] == 0, "got %d" % ranged["stats"]["em_dashes"]


def test_a_spaced_en_dash_standing_in_for_an_em_dash_is_still_caught():
    spliced, _ = scan_with_rules(
        "The study ran for years – nobody counted them.\n", FORBID_DASH)
    assert "voice-em-dash" in voice_ids(spliced), str(voice_ids(spliced))
    real, _ = scan_with_rules(
        "The study ran for years — nobody counted them.\n", FORBID_DASH)
    assert "voice-em-dash" in voice_ids(real), str(voice_ids(real))


def test_date_format_mdy():
    rules = {"voice": "t", "default_priority": "P0",
             "mechanics": {"date_format": "mdy"}}
    flagged, _ = scan_with_rules("The review closed on 12 September 2025.\n", rules)
    assert "voice-date-format" in voice_ids(flagged), str(voice_ids(flagged))
    clean, _ = scan_with_rules("The review closed on September 12, 2025.\n", rules)
    assert not voice_ids(clean), str(voice_ids(clean))


def test_date_format_iso():
    rules = {"voice": "t", "default_priority": "P0",
             "mechanics": {"date_format": "iso"}}
    us, _ = scan_with_rules("The review closed on September 12, 2025.\n", rules)
    dmy, _ = scan_with_rules("The review closed on 12 September 2025.\n", rules)
    iso, _ = scan_with_rules("The review closed on 2025-09-12.\n", rules)
    assert "voice-date-format" in voice_ids(us), str(voice_ids(us))
    assert "voice-date-format" in voice_ids(dmy), str(voice_ids(dmy))
    assert not voice_ids(iso), str(voice_ids(iso))


CURLY = {"voice": "t", "default_priority": "P0",
         "mechanics": {"curly_quotes": "forbid"}}


def test_curly_quotes_forbid_finds_both_marks():
    """The quote sits inside a quoted span on purpose: that span is blanked in
    the scored copy, so building the excerpt from it reported a line of spaces
    and the writer could not see what was being flagged."""
    result, _ = scan_with_rules(
        "He said “the build is green” and closed the ticket.\n", CURLY)
    hits = [f for f in result["findings"] if f["id"] == "voice-curly-quote"]
    assert len(hits) == 2, str(hits)
    assert all(f["priority"] == "P2" for f in hits), str(hits)
    assert all("build is green" in f["excerpt"] for f in hits), str(
        [f["excerpt"] for f in hits])


def test_straight_quotes_are_left_alone():
    result, _ = scan_with_rules(
        "He said \"the build is green\" and closed the ticket.\n", CURLY)
    assert not voice_ids(result), str(voice_ids(result))


# --------------------------------------------------------------------------
# required_when, both directions
#
# The suite proved a letter with a closer passes. Nothing proved the check fires
# without one, so the gate could have been stuck shut.
# --------------------------------------------------------------------------

LETTER_BODY = ("Attached is the Q3 incident review. The outage came from an "
               "expired certificate on the internal proxy, not from the deploy.\n")


def test_correspondence_with_no_closer_fires():
    result, _ = scan_text("Good morning,\n\n" + LETTER_BODY,
                          "--voice-rules", WHIT3RABBIT_RULES)
    assert "missing-closer" in voice_ids(result), str(voice_ids(result))


def test_the_same_letter_with_a_closer_does_not():
    result, _ = scan_text("Good morning,\n\n" + LETTER_BODY + "\nThanks,\n-whit3rabbit\n",
                          "--voice-rules", WHIT3RABBIT_RULES)
    assert "missing-closer" not in voice_ids(result), str(voice_ids(result))


def test_the_gate_keeps_it_off_a_document_that_is_not_a_letter():
    result, _ = scan_text(
        "The certificate expired on the internal proxy at 02:14. We caught "
        "it in 22 minutes and rotated the key.\n",
        "--voice-rules", WHIT3RABBIT_RULES)
    assert "missing-closer" not in voice_ids(result), str(voice_ids(result))


# --------------------------------------------------------------------------
# conversion-depth fixtures
#
# These do not prove the model chose a deep rewrite: mode choice is prompt
# behaviour and no script can assert it. They prove the measurements the
# conversion offer is built from fire on a document that needs one, and stay
# quiet on a document that does not.
# --------------------------------------------------------------------------

def test_a_structurally_wrong_document_reports_a_conversions_worth_of_findings():
    needs = scan_json(os.path.join(SAMPLES, "needs-conversion.md"),
                      "--voice-rules", WHIT3RABBIT_RULES)
    found = [f["id"] for f in needs["findings"]]
    assert found.count("voice-paragraph-length") >= 4, "got %d" % found.count(
        "voice-paragraph-length")
    assert "uniformity" in found, str(set(found))
    assert needs["counts"]["voice"] >= 5, str(needs["counts"])
    assert needs["reliability"] == "high", needs["reliability"]


def test_a_document_already_in_the_voice_raises_nothing():
    clean = scan_json(os.path.join(SAMPLES, "already-in-voice.md"),
                      "--voice-rules", WHIT3RABBIT_RULES)
    assert sum(clean["counts"][k] for k in ("P0", "P1", "P2")) == 0, str(
        [f["id"] for f in clean["findings"]])


# --------------------------------------------------------------------------
# inheritance
# --------------------------------------------------------------------------

def test_a_child_profile_unions_bans_and_wins_on_mechanics():
    scratch = tempfile.mkdtemp()
    try:
        child = written(scratch, "child.rules.json", json.dumps({
            "voice": "child",
            "extends": "whit3rabbit",
            "banned_words": ["synergy", "flywheel"],
            "mechanics": {"em_dash": "allow", "oxford_comma": "forbid"},
        }))
        merged = voices.load(child, voices_dir=VOICES)
        parent = voices.load(WHIT3RABBIT_RULES, voices_dir=VOICES)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    assert merged["voice"] == "child"
    assert merged["mechanics"]["em_dash"] == "allow"
    assert merged["mechanics"]["oxford_comma"] == "forbid"
    # A key the child never mentions survives from the parent.
    assert merged["mechanics"]["semicolon"] == parent["mechanics"]["semicolon"]
    # Bans union: the child adds and cannot quietly drop one.
    lowered = {w.lower() for w in merged["banned_words"]}
    assert "flywheel" in lowered
    assert {w.lower() for w in parent["banned_words"]} <= lowered
    assert merged["preferred_substitutions"] == parent["preferred_substitutions"]


def test_a_child_can_soften_an_inherited_regex_by_id():
    """The supported escape hatch. Bans union, so the only way to loosen an
    inherited rule is to redefine it, and entries merge by id."""
    scratch = tempfile.mkdtemp()
    try:
        child = written(scratch, "child.rules.json", json.dumps({
            "voice": "child", "extends": "whit3rabbit",
            "banned_regex": [{"id": "absolute-claim", "rx": "\\b100% secure\\b",
                              "priority": "P2", "label": "softened"}],
        }))
        merged = voices.load(child, voices_dir=VOICES)
        parent = voices.load(WHIT3RABBIT_RULES, voices_dir=VOICES)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    entries = [e for e in merged["banned_regex"] if e["id"] == "absolute-claim"]
    assert len(entries) == 1, str(entries)
    assert entries[0]["priority"] == "P2"
    assert len(merged["banned_regex"]) == len(parent["banned_regex"])


def test_inheritance_cycles_are_caught():
    scratch = tempfile.mkdtemp()
    try:
        written(scratch, "a.rules.json", '{"voice": "a", "extends": "b"}')
        written(scratch, "b.rules.json", '{"voice": "b", "extends": "a"}')
        try:
            voices.load(os.path.join(scratch, "a.rules.json"), voices_dir=scratch)
        except voices.VoiceError as exc:
            assert "loops" in str(exc), str(exc)
        else:
            raise AssertionError("a cycle was not caught")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_a_missing_parent_is_an_error_and_not_a_silent_fallback():
    """A profile that inherits from nothing enforces nothing, and reporting a
    clean voice band on a document nobody checked is the failure this whole
    mechanism exists to avoid."""
    scratch = tempfile.mkdtemp()
    try:
        child = written(scratch, "c.rules.json", '{"voice": "c", "extends": "nope"}')
        try:
            voices.load(child, voices_dir=scratch)
        except voices.VoiceError as exc:
            assert "nope" in str(exc), str(exc)
        else:
            raise AssertionError("a missing parent was not caught")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_the_lineage_is_reported():
    scratch = tempfile.mkdtemp()
    try:
        child = written(scratch, "child.rules.json",
                        '{"voice": "child", "extends": "whit3rabbit"}')
        assert voices.lineage(child, voices_dir=VOICES) == ["child", "whit3rabbit"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# --------------------------------------------------------------------------
# resolution: which profile applies when nobody spelled out a path
# --------------------------------------------------------------------------
#
# The order used to live in readme_check.py alone, so the two checkers in this
# one plugin could disagree about whose rules were in force. It is in
# rwlib.voices now and scan.py reaches it through `--voice auto`. The
# readme-writing suite tests the same function through its own caller; these
# test the engine's half, and the flag handling around it.


def scratch_voices(*names):
    """A temporary voices/ directory holding one rules file per name."""
    scratch = tempfile.mkdtemp()
    for who in names:
        written(scratch, who + ".rules.json",
                json.dumps({"voice": who, "mechanics": {"semicolon": "forbid"}}))
    return scratch


def test_a_repo_pin_outranks_active():
    scratch = scratch_voices("ada", "grace")
    try:
        written(scratch, "ACTIVE", "ada\n")
        doc = os.path.join(scratch, "draft.md")
        written(scratch, "draft.md", "text\n")
        written(scratch, ".rabbit-voice", "grace\n")
        rules, name, note = voices.resolve(doc, voices_dir=scratch)
        assert name == "grace", name
        assert "pinned" in (note or ""), note
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_resolve_with_no_document_still_answers():
    """scan.py reads stdin as happily as a path, so there is not always a file
    to look beside. ACTIVE still decides.

    Runs from the scratch directory rather than from wherever the suite was
    invoked. With no document, `resolve` probes the working directory for a
    `.rabbit-voice`, so a repository that pins its own house voice (this one
    does) would otherwise decide the result and the failure would read as a bug
    in the resolution order. The readme-writing suite draws the same line in its
    NEUTRAL_CWD.
    """
    scratch = scratch_voices("ada")
    original = os.getcwd()
    try:
        written(scratch, "ACTIVE", "ada\n")
        os.chdir(scratch)
        rules, name, note = voices.resolve(None, voices_dir=scratch)
        assert name == "ada" and note is None, "%s %s" % (name, note)
    finally:
        os.chdir(original)
        shutil.rmtree(scratch, ignore_errors=True)


def test_installed_leaves_the_template_out():
    """TEMPLATE.rules.json is a form to fill in, not somebody's voice. Counted,
    it turns the single-profile fallback into an ambiguity on a fresh install."""
    assert "TEMPLATE" not in voices.installed(VOICES)
    assert "whit3rabbit" in voices.installed(VOICES)


def test_voice_auto_applies_a_pinned_profile():
    """The flag exists so a writer does not have to spell out a path that moves
    when the plugin is installed somewhere else.

    The pin is written here rather than borrowed from the checkout. This used to
    lean on whatever `voices/ACTIVE` said, which shipped naming this
    repository's author and no longer names anybody: a test that passes because
    the developer's tree happens to have a voice active is asserting a fact
    about the tree.
    """
    scratch = tempfile.mkdtemp()
    try:
        written(scratch, ".rabbit-voice", "whit3rabbit\n")
        path = written(scratch, "letter.md", BAD_LETTER)
        out = subprocess.run(
            [sys.executable, SCAN, path, "--json", "--voice", "auto"],
            capture_output=True, text=True, cwd=scratch)
        result = json.loads(out.stdout)
        assert result["voice"] == "whit3rabbit", result.get("notes")
        assert "voice-em-dash" in voice_ids(result), result["findings"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_no_voice_flag_means_no_voice_band():
    """The default stays silent about style. This is what the `rabbit-scan`
    hook runs in somebody else's repository, and a stranger's em dash is not a
    defect in a stranger's README."""
    result, _ = scan_text(BAD_LETTER)
    assert not voice_ids(result), result["findings"]


def test_a_profile_named_by_hand_that_does_not_exist_is_an_error():
    """Exit 2, the same as --voice-rules with a typo in it. A clean voice band
    on a profile nobody read is a false pass."""
    result = subprocess.run(
        [sys.executable, SCAN, os.path.join(SAMPLES, "human-sample.md"),
         "--json", "--voice", "nobody-by-that-name"],
        capture_output=True, text=True)
    assert result.returncode == 2, result.stdout
    assert "nobody-by-that-name" in result.stderr, result.stderr


def test_voice_and_voice_rules_cannot_both_be_given():
    """Silently preferring one produces a report about a profile nobody asked
    for, which is the failure the whole band exists to avoid."""
    result = subprocess.run(
        [sys.executable, SCAN, os.path.join(SAMPLES, "human-sample.md"),
         "--voice", "auto", "--voice-rules", WHIT3RABBIT_RULES],
        capture_output=True, text=True)
    assert result.returncode == 2, result.stdout


# --------------------------------------------------------------------------
# per-register voice rules
# --------------------------------------------------------------------------
#
# The profile markdown has always distinguished on the clock from off it, and
# until now the rules file could say so only for `required_when`. A writer can
# now scope a mechanic or a banned_regex the same way.
#
# This is not the register relaxing a voice rule, which stays forbidden and is
# pinned above. It is the writer saying which of their own rules applied where.
# The direction matters: `--profile chat` still cannot soften anything on its
# own, it can only select among rules the author already wrote.

SHOUTY = "This is fine. No. It really is fine, and the build stays green.\n"


def test_a_mechanic_can_be_scoped_to_a_register():
    rules = {"voice": "t", "default_priority": "P0",
             "mechanics": {"one_word_sentence": "forbid"},
             "mechanics_by_register": {"chat": {"one_word_sentence": "allow"}}}
    strict, _ = scan_with_rules(SHOUTY, rules)
    relaxed, _ = scan_with_rules(SHOUTY, rules, "--profile", "chat")
    assert "voice-one-word-sentence" in voice_ids(strict), strict["findings"]
    assert "voice-one-word-sentence" not in voice_ids(relaxed), relaxed["findings"]


def test_a_one_word_sentence_after_two_spaces_is_still_caught():
    """The lookbehind is fixed-width, so the one-space form let anybody who
    types two spaces after a period out of this rule entirely."""
    rules = {"voice": "t", "default_priority": "P0",
             "mechanics": {"one_word_sentence": "forbid"}}
    wide = "This is fine.  No.  It really is fine, and the build stays green.\n"
    result, _ = scan_with_rules(wide, rules)
    assert "voice-one-word-sentence" in voice_ids(result), result["findings"]


def test_an_unscoped_mechanic_still_applies_everywhere():
    """The default has not moved. Every profile written before this key existed
    behaves exactly as it did, in every register."""
    rules = {"voice": "t", "default_priority": "P0",
             "mechanics": {"one_word_sentence": "forbid"}}
    for profile in ("blog", "chat", "docs", "linkedin"):
        result, _ = scan_with_rules(SHOUTY, rules, "--profile", profile)
        assert "voice-one-word-sentence" in voice_ids(result), profile


def test_a_banned_regex_can_be_scoped_to_a_register():
    rules = {"voice": "t", "default_priority": "P0",
             "banned_regex": [{"id": "no-lowercase-opener",
                               "label": "Lowercase opener",
                               "rx": "(?m)^[a-z]",
                               "applies_to_registers": ["blog", "docs"]}]}
    text = "hey, the build is green and the report is attached.\n"
    strict, _ = scan_with_rules(text, rules, "--profile", "blog")
    off, _ = scan_with_rules(text, rules, "--profile", "chat")
    assert "no-lowercase-opener" in voice_ids(strict), strict["findings"]
    assert "no-lowercase-opener" not in voice_ids(off), off["findings"]


def test_scoped_mechanics_merge_two_levels_deep_under_extends():
    """A child overriding one mechanic in `chat` must not drop the others the
    parent scoped there. A shallow update silently unbans them, which is the
    failure the whole merge section of voices.py is written against."""
    parent = {"mechanics_by_register": {"chat": {"emoji": "allow",
                                                   "one_word_sentence": "allow"}}}
    child = {"mechanics_by_register": {"chat": {"emoji": "forbid"}}}
    merged = voices.merge(parent, child)["mechanics_by_register"]["chat"]
    assert merged == {"emoji": "forbid", "one_word_sentence": "allow"}, merged


def test_voice_mechanics_resolves_the_active_register():
    scan = load_scan()
    rules = {"mechanics": {"emoji": "forbid", "semicolon": "forbid"},
             "mechanics_by_register": {"chat": {"emoji": "allow"}}}
    assert scan.voice_mechanics(rules, "blog") == {"emoji": "forbid",
                                                   "semicolon": "forbid"}
    assert scan.voice_mechanics(rules, "chat") == {"emoji": "allow",
                                                     "semicolon": "forbid"}


# --------------------------------------------------------------------------
# blending
# --------------------------------------------------------------------------
#
# voice.md specified a blend precisely enough to be code and only `extends`
# existed, so half the doc was a promise the machinery could not keep. The
# rules-file half is code now. The dimensions half is not and cannot be: those
# numbers live in the profile markdown and no threshold in this engine reads
# them, which the doc now says instead of implying.

LEFT = {"voice": "ada", "default_priority": "P0",
        "mechanics": {"em_dash": "forbid", "oxford_comma": "require",
                      "max_paragraph_sentences": 5, "date_format": "dmy"},
        "banned_words": ["synergy"],
        "banned_regex": [{"id": "shared", "rx": "a", "priority": "P0"},
                         {"id": "ada-only", "rx": "b"}]}
GRACE = {"voice": "grace", "default_priority": "P2",
         "mechanics": {"em_dash": "allow", "oxford_comma": "allow",
                       "max_paragraph_sentences": 9, "date_format": "mdy"},
         "banned_words": ["piggyback"],
         "banned_regex": [{"id": "shared", "rx": "z", "priority": "P2"},
                          {"id": "grace-only", "rx": "y"}]}


def test_bans_union_and_neither_side_can_drop_one():
    rules, _ = voices.blend(LEFT, GRACE, 0.9)
    assert set(rules["banned_words"]) == {"synergy", "piggyback"}
    assert {e["id"] for e in rules["banned_regex"]} == {"shared", "ada-only",
                                                        "grace-only"}


def test_the_stricter_mechanic_wins_whatever_the_weight_says():
    """The weight is a statement about emphasis, not permission. A blend that
    can drop a refusal is a blend nobody can rely on."""
    for weight in (0.0, 0.1, 0.5, 0.9, 1.0):
        rules, _ = voices.blend(LEFT, GRACE, weight)
        assert rules["mechanics"]["em_dash"] == "forbid", weight
        assert rules["mechanics"]["max_paragraph_sentences"] == 5, weight
        assert rules["default_priority"] == "P0", weight


def test_a_side_with_no_opinion_yields_to_the_side_with_one():
    """`allow` on the serial comma is the absence of a rule, not a competing
    one, so it does not get to cancel the profile that has a habit."""
    rules, _ = voices.blend(LEFT, GRACE, 0.1)
    assert rules["mechanics"]["oxford_comma"] == "require", rules["mechanics"]


def test_a_real_conflict_is_broken_by_weight_and_reported():
    """`dmy` and `mdy` are two conventions rather than degrees of one. Picking
    silently is the choice the person whose name goes on this has to see."""
    heavy_left, notes = voices.blend(LEFT, GRACE, 0.9)
    heavy_right, _ = voices.blend(LEFT, GRACE, 0.1)
    assert heavy_left["mechanics"]["date_format"] == "dmy"
    assert heavy_right["mechanics"]["date_format"] == "mdy"
    assert any("date_format" in n for n in notes), notes


def test_a_blend_drops_template_guidance_from_both_mechanic_levels():
    """The template's underscore keys are its own documentation and it tells its
    copier to delete them. `mechanics` was filtered and `mechanics_by_register`
    was not, so the guidance could survive a blend by the back door and end up
    in a file with somebody's name on it."""
    left = dict(LEFT, mechanics_by_register={
        "_example": {"em_dash": "allow"},
        "chat": {"_note": "what this key is for", "em_dash": "allow"}})
    rules, _ = voices.blend(left, GRACE, 0.9)
    scoped = rules.get("mechanics_by_register", {})
    assert "_example" not in scoped, scoped
    assert scoped["chat"] == {"em_dash": "allow"}, scoped


def test_the_lineage_is_written_into_the_file():
    rules, _ = voices.blend(LEFT, GRACE, 0.7, name="ada-grace")
    assert rules["voice"] == "ada-grace"
    assert rules["blend"] == {"of": ["ada", "grace"], "weight": 0.7}


def test_a_blend_is_not_a_child_of_either_parent():
    """`extends` surviving would send load() off to re-merge a parent whose
    rules are already folded in, at a path relative to a file that is gone."""
    rules, _ = voices.blend(dict(LEFT, extends="somebody"), GRACE, 0.7)
    assert "extends" not in rules, rules


def test_the_notes_say_the_dimensions_were_not_blended():
    """The half a script cannot do has to be handed back explicitly, or the
    person reads a generated file as the whole answer."""
    _, notes = voices.blend(LEFT, GRACE, 0.7)
    assert any("dimensions" in n for n in notes), notes


def test_a_weight_outside_the_range_is_an_error():
    try:
        voices.blend(LEFT, GRACE, 1.5)
    except voices.VoiceError as exc:
        assert "between 0 and 1" in str(exc), str(exc)
    else:
        raise AssertionError("a weight of 1.5 was accepted")


def test_a_blended_profile_loads_and_scans():
    """The output is a rules file, not a report about one. If scan.py cannot
    enforce it, the whole exercise produced a document."""
    scratch = tempfile.mkdtemp()
    try:
        rules, _ = voices.blend(LEFT, GRACE, 0.7, name="ada-grace")
        path = written(scratch, "ada-grace.rules.json", json.dumps(rules))
        result, _ = scan_text("We need more synergy, and piggyback on it.\n" * 6,
                              "--voice-rules", path)
        found = voice_ids(result)
        assert found.count("voice-banned-word") >= 2, result["findings"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
