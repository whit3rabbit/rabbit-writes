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
import tempfile

from helpers import (SAMPLES, VOICES, WHIT3RABBIT_RULES, scan_json, scan_text,
                     scan_with_rules, voice_ids, written)

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
                           "--profile", "casual")
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
