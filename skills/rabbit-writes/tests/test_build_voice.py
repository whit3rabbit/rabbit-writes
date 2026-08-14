#!/usr/bin/env python3
"""
build_voice.py and rwlib/voice_check.py: scaffolding a profile, and proving it.

The script lives in voice-setup and is tested from this suite for the reason
test_measure_voice.py is: everything it decides comes out of this engine. It
strips the template using this engine's idea of what the template's residue is,
it validates against this engine's mechanic vocabulary and register list, and
its live-fire pass is scan.py run on a document it generated.

The assertions worth having are the negative ones. A checker that passes
everything is indistinguishable from no checker, and every case below is a
profile that reads as enforced and is not.

Stdlib only, 3.9+.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

from helpers import ROOT, VOICES, load_module

BUILD = os.path.join(os.path.dirname(ROOT), "voice-setup", "scripts",
                     "build_voice.py")
TEMPLATE_RULES = os.path.join(VOICES, "TEMPLATE.rules.json")
TEMPLATE_MD = os.path.join(VOICES, "TEMPLATE.md")

# A filled-in markdown half, so a test about the rules file is not also a test
# about the guidance prompts. Short on purpose: check_markdown looks for the
# template's shapes, not for completeness.
FILLED_MD = ("# Voice: dana\n\n"
             "## The three essentials\n\n"
             "1. Lead with the conclusion.\n"
             "2. Name the tradeoff.\n"
             "3. Say what you did not check.\n")


def build_module():
    return load_module("rw_build_voice_test", BUILD)


def check_module():
    # Imported as part of the package rather than loaded by path, because it
    # imports three siblings and a by-path load has no parent package to find
    # them through. helpers puts scripts/ on sys.path for exactly this.
    from rwlib import voice_check
    return voice_check


def run(*args):
    out = subprocess.run([sys.executable, BUILD, *args],
                         capture_output=True, text=True)
    return out.stdout + out.stderr, out.returncode


def profile(tmp, rules, markdown=FILLED_MD, name="dana"):
    """Write a profile pair into tmp and return the rules path."""
    rules_path = os.path.join(tmp, name + ".rules.json")
    with open(rules_path, "w", encoding="utf-8") as fh:
        json.dump(rules, fh)
    if markdown is not None:
        with open(os.path.join(tmp, name + ".md"), "w", encoding="utf-8") as fh:
            fh.write(markdown)
    return rules_path


def messages(rules_path, **kwargs):
    voice_check = check_module()
    return [f["message"] for f in voice_check.check_profile(rules_path, **kwargs)
            if f["level"] == voice_check.FAIL]


# --------------------------------------------------------------------------
# scaffolding
# --------------------------------------------------------------------------

def test_scaffold_writes_a_pair_with_the_template_taken_out_of_it():
    tmp = tempfile.mkdtemp()
    try:
        out, code = run("--scaffold", "--name", "dana", "--out", tmp)
        assert code == 0, out
        rules_path = os.path.join(tmp, "dana.rules.json")
        md_path = os.path.join(tmp, "dana.md")
        assert os.path.exists(rules_path) and os.path.exists(md_path), out

        with open(rules_path, encoding="utf-8") as fh:
            rules = json.load(fh)
        assert rules["voice"] == "dana"
        assert not [k for k in rules if k.startswith("_")], rules
        assert not [k for k in rules["mechanics"] if k.startswith("_")]
        # The entry that compiles, enforces a phrase nobody chose, and is
        # invisible to every other check in the repository.
        assert rules["banned_regex"] == []

        with open(md_path, encoding="utf-8") as fh:
            markdown = fh.read()
        assert markdown.startswith("# Voice: dana")
        assert "<name>" not in markdown          # including the Hard nos line
        assert "Copy this file to" not in markdown
    finally:
        shutil.rmtree(tmp)


def test_a_scaffold_is_unfinished_and_check_says_so():
    """The guidance prompts stay, because they are the form. A scaffold that
    deleted them would look finished and describe nobody."""
    tmp = tempfile.mkdtemp()
    try:
        run("--scaffold", "--name", "dana", "--out", tmp)
        out, code = run("--check", os.path.join(tmp, "dana.rules.json"))
        assert code == 1, out
        assert "unfilled guidance prompt" in out, out
    finally:
        shutil.rmtree(tmp)


def test_scaffold_refuses_to_overwrite_somebody_else_work():
    tmp = tempfile.mkdtemp()
    try:
        run("--scaffold", "--name", "dana", "--out", tmp)
        with open(os.path.join(tmp, "dana.md"), "w", encoding="utf-8") as fh:
            fh.write("# Voice: dana\n\nhand written\n")
        out, code = run("--scaffold", "--name", "dana", "--out", tmp)
        assert code == 2, out
        assert "--force" in out
        with open(os.path.join(tmp, "dana.md"), encoding="utf-8") as fh:
            assert "hand written" in fh.read()

        out, code = run("--scaffold", "--name", "dana", "--out", tmp, "--force")
        assert code == 0, out
        with open(os.path.join(tmp, "dana.md"), encoding="utf-8") as fh:
            assert "hand written" not in fh.read()
    finally:
        shutil.rmtree(tmp)


def test_a_destination_outside_voices_says_what_it_costs():
    """`.rabbit-voice` and ACTIVE both resolve a name inside voices/ and
    nowhere else, so a profile written elsewhere is reachable by path only. The
    person choosing the directory is the one who has to know that."""
    tmp = tempfile.mkdtemp()
    try:
        out, code = run("--scaffold", "--name", "dana", "--out", tmp)
        assert code == 0, out
        assert "--voice-rules" in out, out
        assert ".rabbit-voice" in out, out
    finally:
        shutil.rmtree(tmp)


def test_scaffold_will_not_name_a_profile_TEMPLATE():
    tmp = tempfile.mkdtemp()
    try:
        out, code = run("--scaffold", "--name", "TEMPLATE", "--out", tmp)
        assert code == 2, out
    finally:
        shutil.rmtree(tmp)


# --------------------------------------------------------------------------
# structure
# --------------------------------------------------------------------------

def test_check_catches_every_shape_of_dead_rule():
    """Table-driven, and every row is a real authoring mistake rather than an
    invented one: each reads as an enforced rule and enforces nothing."""
    cases = [
        ("a guidance key left in",
         {"voice": "dana", "_how_to_use": ["delete me"]},
         "guidance keys"),
        ("the template's example rule",
         {"voice": "dana",
          "banned_regex": [{"id": "example-rule", "label": "Example",
                            "rx": "(?i)nope"}]},
         "example-rule"),
        ("the template's voice name",
         {"voice": "<name>"}, "still the template"),
        ("a voice field that is not the filename",
         {"voice": "someone-else"}, "but the filename says"),
        ("a mechanic this engine does not read",
         {"voice": "dana", "mechanics": {"semicolons": "forbid"}},
         "not a mechanic"),
        ("a mechanic value that is not in the vocabulary",
         {"voice": "dana", "mechanics": {"semicolon": "forbidden"}},
         "not one of"),
        ("a register that does not exist",
         {"voice": "dana", "mechanics_by_register": {"linkdin": {}}},
         "which is not a register"),
        ("a rule scoped to a register that does not exist",
         {"voice": "dana",
          "banned_regex": [{"id": "r", "label": "r", "rx": "x",
                            "applies_to_registers": ["emial"]}]},
         "applies nowhere at all"),
        ("a regex that does not compile",
         {"voice": "dana",
          "banned_regex": [{"id": "r", "label": "r", "rx": "(unclosed"}]},
         "does not compile"),
        ("a regex that does not match its own example",
         {"voice": "dana",
          "banned_regex": [{"id": "r", "label": "r", "rx": "(?i)war room",
                            "example": "they met in a conference room"}]},
         "does not match its own example"),
        ("a ban entry naming no term",
         {"voice": "dana", "banned_words": [{"term": "synergy"}]},
         "matches nothing"),
        ("a ban entry padded with whitespace",
         {"voice": "dana", "banned_phrases": [" circle back "]},
         "padded with whitespace"),
        ("a priority that is not a priority",
         {"voice": "dana", "default_priority": "P3"}, "default_priority"),
        ("a presence check that fires on everything",
         {"voice": "dana", "required_when": [{"id": "closer", "label": "c"}]},
         "no any_of_rx"),
        ("a gate example the gate never opens on",
         {"voice": "dana",
          "required_when": [{"id": "closer", "label": "c",
                             "any_of_rx": ["(?im)^thanks,"],
                             "when_rx": "(?im)^hi ",
                             "when_example": "Dear Dana,"}]},
         "does not match its own when_rx"),
        ("a gate example that already carries the closer",
         {"voice": "dana",
          "required_when": [{"id": "closer", "label": "c",
                             "any_of_rx": ["(?im)^thanks,"],
                             "when_rx": "(?im)^hi ",
                             "when_example": "Hi Dana,\n\nThanks,"}]},
         "already satisfies"),
    ]
    tmp = tempfile.mkdtemp()
    try:
        for label, rules, expected in cases:
            found = messages(profile(tmp, rules))
            assert any(expected in m for m in found), (label, expected, found)
    finally:
        shutil.rmtree(tmp)


def test_a_rules_file_with_no_markdown_beside_it_is_a_failure():
    """It enforces punctuation and describes nobody, and the markdown is the
    half the model actually reads."""
    tmp = tempfile.mkdtemp()
    try:
        found = messages(profile(tmp, {"voice": "dana"}, markdown=None))
        assert any("no dana.md beside it" in m for m in found), found
    finally:
        shutil.rmtree(tmp)


def test_a_clean_profile_reports_nothing():
    tmp = tempfile.mkdtemp()
    try:
        rules = {"voice": "dana", "mechanics": {"semicolon": "forbid"},
                 "banned_words": ["synergy"]}
        assert messages(profile(tmp, rules)) == []
    finally:
        shutil.rmtree(tmp)


def test_the_shipped_profile_and_the_template_both_hold():
    """The repository's own voice is the one profile a stranger reads as an
    example, and TEMPLATE is exempt from exactly the checks that are about
    being a profile rather than a form."""
    voice_check = check_module()
    assert messages(os.path.join(VOICES, "whit3rabbit.rules.json")) == []
    template = voice_check.check_rules(TEMPLATE_RULES)
    assert [f["message"] for f in template
            if f["level"] == voice_check.FAIL], \
        "TEMPLATE is supposed to fail these checks: it is the form"


def test_the_template_options_block_matches_the_engine_vocabulary():
    """The template documents the vocabulary a third time, after voices.py and
    scan.py. A test rather than a comment, because a value added to one and not
    the others is a mechanic somebody writes and nothing runs."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from rwlib import voices as voices_mod

    with open(TEMPLATE_RULES, encoding="utf-8") as fh:
        options = json.load(fh)["mechanics"]["_options"]
    for key, documented in options.items():
        if key in voices_mod.NUMERIC_MECHANICS:
            continue
        allowed = voices_mod.MECHANIC_VALUES.get(key)
        assert allowed is not None, "%s is documented and not implemented" % key
        for value in allowed:
            assert value in documented, (key, value, documented)
    for key in voices_mod.MECHANIC_VALUES:
        assert key in options, "%s is implemented and not documented" % key


# --------------------------------------------------------------------------
# live fire
# --------------------------------------------------------------------------

def fired(rules):
    """{what: ok} from one live-fire pass over an inline rules dict."""
    build = build_module()
    return {what: ok for ok, what, _ in build.live_fire(rules, build.load_scan())}


def test_every_mechanic_and_ban_is_proven_by_firing_it():
    rules = {
        "voice": "dana", "default_priority": "P0",
        "mechanics": {"em_dash": "forbid", "semicolon": "forbid",
                      "emoji": "forbid", "curly_quotes": "forbid",
                      "one_word_sentence": "forbid", "oxford_comma": "require",
                      "date_format": "dmy", "max_paragraph_sentences": 3,
                      "max_avg_sentence_words": 20},
        "banned_words": ["synergy"],
        "banned_phrases": ["circle back"],
        "banned_regex": [{"id": "war-metaphor", "label": "war",
                          "rx": "(?i)war ?room",
                          "example": "They ran a war room for a week."}],
    }
    results = fired(rules)
    assert results, results
    dead = [what for what, ok in results.items() if ok is not True]
    assert not dead, dead


def test_a_word_ban_is_not_credited_to_a_phrase_finding():
    """The two lists compile to two patterns, and the expectation names the
    finding id for that reason. Without it, a profile that banned the same
    string in both lists proved the dead entry with the live one's finding."""
    rules = {"voice": "dana",
             "banned_words": ["circle back"],
             "banned_phrases": ["circle back"]}
    build = build_module()
    scan = build.load_scan()
    text, expect = build.bans_probe(rules, {})
    findings, _ = scan.scan(text, None, True, rules)
    voice_findings = [f for f in findings if f["band"] == "voice"]
    for expectation in expect:
        assert expectation.get("id"), expectation
        assert build._fired(voice_findings, expectation), expectation


def test_a_ban_that_cannot_match_is_reported_dead():
    """A term pasted in with its markdown still on it. The quoted-example
    exemption blanks an inline code span before any ban is applied, so the
    entry parses, merges, reads as a ban, and never fires."""
    rules = {"voice": "dana", "banned_words": ["`synergy`"]}
    results = fired(rules)
    assert results and all(ok is not True for ok in results.values()), results


def test_a_regex_without_an_example_is_unproven_rather_than_passed():
    rules = {"voice": "dana",
             "banned_regex": [{"id": "r", "label": "r", "rx": "(?i)war room"}]}
    build = build_module()
    results = build.live_fire(rules, build.load_scan())
    assert [r for r in results if r[0] is None], results
    assert not [r for r in results if r[0] is True], results


def test_a_rule_scoped_to_a_register_is_probed_in_that_register():
    """A rule that only applies to `chat` does not fire in a blog scan, and
    reporting the author's own scoping as a broken rule would teach them to
    delete the scoping."""
    rules = {"voice": "dana",
             "banned_regex": [{"id": "r", "label": "r", "rx": "(?i)war room",
                               "applies_to_registers": ["chat"],
                               "example": "They ran a war room for a week."}]}
    assert fired(rules) == {"banned_regex r": True}


def test_live_fire_gives_each_regex_example_its_own_document():
    """`motivational-cadence` matches three short paragraphs in a row, which is
    the shape of the combined probe itself. Run together, it passed on text its
    author never wrote."""
    rules = {"voice": "dana",
             "banned_words": ["synergy", "piggyback", "furthermore"],
             "banned_regex": [
                 {"id": "cadence", "label": "cadence",
                  "rx": "(?m)^[A-Z][^.!?\\n]{4,60}[.!?]\\s*\\n\\s*\\n"
                        "[A-Z][^.!?\\n]{4,60}[.!?]\\s*\\n\\s*\\n"
                        "[A-Z][^.!?\\n]{4,60}[.!?]\\s*$",
                  "example": "Not three paragraphs."}]}
    assert fired(rules)["banned_regex cadence"] is False


# A presence check gated by `when_rx`. scan.py skips the entry until the gate
# matches, so all three of these are about the probe rather than about the rule.
GATED = {"id": "closer", "label": "c",
         "any_of_rx": ["(?im)^\\s*thanks,"], "when_rx": "(?im)^\\s*hi "}


def test_a_gated_presence_check_without_an_example_is_unproven_rather_than_dead():
    """No text this script invents is known to match somebody else's gate
    regex, and calling a working rule dead teaches its author to delete it.
    This is the case that reported the shipped profile's `missing-closer` as
    dead: the probe was a plain sentence and the gate wanted correspondence."""
    build = build_module()
    results = build.live_fire({"voice": "dana", "required_when": [dict(GATED)]},
                              build.load_scan())
    assert [r for r in results if r[0] is None], results
    assert not [r for r in results if r[0] is False], results


def test_a_gated_presence_check_fires_on_its_when_example():
    entry = dict(GATED,
                 when_example="Hi Dana,\n\nThe deploy finished and it held.")
    assert fired({"voice": "dana", "required_when": [entry]}) == \
        {"required_when closer": True}


def test_a_when_example_that_already_closes_proves_nothing():
    """A presence check fires on absence, so a probe carrying the thing it is
    meant to be missing leaves the rule correctly silent. Reporting that as
    dead is the same false accusation from the other direction."""
    entry = dict(GATED, when_example="Hi Dana,\n\nThanks,")
    build = build_module()
    results = build.live_fire({"voice": "dana", "required_when": [entry]},
                              build.load_scan())
    assert [r for r in results if r[0] is None], results
    assert not [r for r in results if r[0] is False], results


def test_the_shipped_profile_has_no_rule_that_does_not_fire():
    """The structural pass says a profile is well formed. This is the half that
    runs it, and the half nothing here covered: `--check whit3rabbit` reported
    a dead rule while the whole suite stayed green."""
    build = build_module()
    with open(os.path.join(VOICES, "whit3rabbit.rules.json"),
              encoding="utf-8") as fh:
        rules = json.load(fh)
    results = build.live_fire(rules, build.load_scan())
    assert results
    dead = [what for ok, what, _ in results if ok is False]
    assert not dead, dead


# --------------------------------------------------------------------------
# the CLI contract
# --------------------------------------------------------------------------

def test_check_exits_1_on_a_dead_rule_and_0_on_a_live_one():
    tmp = tempfile.mkdtemp()
    try:
        live = profile(tmp, {"voice": "dana", "banned_words": ["synergy"]})
        out, code = run("--check", live)
        assert code == 0, out
        assert "fires banned word" in out, out

        dead = profile(tmp, {"voice": "dana", "banned_words": ["`synergy`"]},
                       name="dana")
        out, code = run("--check", dead)
        assert code == 1, out
        assert "DEAD" in out, out
    finally:
        shutil.rmtree(tmp)


def test_activate_is_refused_outside_the_voices_directory():
    """ACTIVE holds a name and resolves it in voices/, so pointing it at a
    profile that lives anywhere else names a file nothing can load."""
    tmp = tempfile.mkdtemp()
    try:
        rules_path = profile(tmp, {"voice": "dana", "banned_words": ["synergy"]})
        out, code = run("--check", rules_path, "--activate")
        assert code == 2, out
        assert "--voice-rules" in out, out
        assert not os.path.exists(os.path.join(tmp, "ACTIVE"))
    finally:
        shutil.rmtree(tmp)


def test_activate_writes_active_and_names_what_it_replaced():
    tmp = tempfile.mkdtemp()
    try:
        shutil.copy(TEMPLATE_MD, os.path.join(tmp, "TEMPLATE.md"))
        profile(tmp, {"voice": "dana", "banned_words": ["synergy"]})
        with open(os.path.join(tmp, "ACTIVE"), "w", encoding="utf-8") as fh:
            fh.write("someone-else\n")
        out, code = run("--check", "dana", "--voices-dir", tmp, "--activate")
        assert code == 0, out
        assert "replacing someone-else" in out, out
        with open(os.path.join(tmp, "ACTIVE"), encoding="utf-8") as fh:
            assert fh.read().strip() == "dana"
    finally:
        shutil.rmtree(tmp)


def test_a_failing_check_does_not_activate():
    tmp = tempfile.mkdtemp()
    try:
        profile(tmp, {"voice": "dana", "banned_words": ["`synergy`"]})
        out, code = run("--check", "dana", "--voices-dir", tmp, "--activate")
        assert code == 1, out
        assert not os.path.exists(os.path.join(tmp, "ACTIVE")), out
    finally:
        shutil.rmtree(tmp)


# --------------------------------------------------------------------------
# the fingerprint beside the pair
# --------------------------------------------------------------------------
#
# check_fingerprint runs on the optional third file. The assertions here are
# the negative ones for the same reason as everything above: a malformed
# measure block is not a degraded measurement, it is one an attainment check
# reads and silently answers nothing from, which reads exactly like a profile
# somebody is honouring.

GOOD_MEASURES = {
    "avg_sentence_words": {"mean": 14.0, "sd": 2.0, "min": 12.0, "max": 16.0,
                           "n": 3},
}
GOOD_SHAPE = {
    "n_sentences": 30,
    "quantiles": [4, 8, 10, 12, 13, 15, 17, 19, 21, 26, 34],
    "mean": 15.0, "sd": 7.0, "short_share": 0.2, "long_share": 0.1,
    "per_sample_median": [14, 15, 16],
}


def fingerprint_beside(tmp, name="dana", **overrides):
    """Write a v2 fingerprint next to the profile and return the rules path."""
    from rwlib import stylometry
    rules_path = profile(tmp, {"voice": name, "banned_words": ["synergy"]},
                         name=name)
    body = {"schema_version": stylometry.SCHEMA_VERSION, "voice": name,
            "n_samples": 3, "sample_words": [900, 950, 1000],
            "thin_samples": 0, "markers": {},
            "self_distance": {"per_sample": [0.5, 0.6, 0.4], "mean": 0.5,
                              "max": 0.6},
            "measures": dict(GOOD_MEASURES),
            "sentence_shape": dict(GOOD_SHAPE)}
    body.update(overrides)
    with open(os.path.join(tmp, name + ".fingerprint.json"), "w",
              encoding="utf-8") as fh:
        json.dump(body, fh)
    return rules_path


def test_a_well_formed_fingerprint_passes_and_says_what_it_holds():
    tmp = tempfile.mkdtemp()
    try:
        rules_path = fingerprint_beside(tmp)
        voice_check = check_module()
        results = voice_check.check_profile(rules_path)
        assert not voice_check.failures(results), results
        assert any("1 measures" in r["message"] and "30 sentences" in r["message"]
                   for r in results), results
    finally:
        shutil.rmtree(tmp)


def test_a_fingerprint_with_no_measure_block_fails():
    """The half a later attainment check reads. Without it the check answers
    nothing and says nothing, which is the orphan failure one file over."""
    tmp = tempfile.mkdtemp()
    try:
        rules_path = fingerprint_beside(tmp, measures={})
        assert any("no `measures` block" in m for m in messages(rules_path)), \
            messages(rules_path)
    finally:
        shutil.rmtree(tmp)


def test_a_fingerprint_with_the_numbers_in_the_wrong_slots_fails():
    """The one check worth having beyond a key-shape test. A builder that swaps
    min and max passes every other assertion here and produces an envelope
    nothing can fall outside of."""
    tmp = tempfile.mkdtemp()
    try:
        swapped = {"avg_sentence_words": {"mean": 14.0, "sd": 2.0, "min": 16.0,
                                          "max": 12.0, "n": 3}}
        rules_path = fingerprint_beside(tmp, measures=swapped)
        assert any("not an envelope" in m for m in messages(rules_path)), \
            messages(rules_path)
    finally:
        shutil.rmtree(tmp)


def test_a_measure_this_engine_does_not_know_fails():
    tmp = tempfile.mkdtemp()
    try:
        rules_path = fingerprint_beside(
            tmp, measures={"vibes": {"mean": 1.0, "sd": 0.0, "min": 1.0,
                                     "max": 1.0, "n": 3}})
        assert any("different builder" in m for m in messages(rules_path)), \
            messages(rules_path)
    finally:
        shutil.rmtree(tmp)


def test_a_shape_with_the_wrong_number_of_boundaries_fails():
    tmp = tempfile.mkdtemp()
    try:
        short = dict(GOOD_SHAPE, quantiles=[4, 8, 12])
        rules_path = fingerprint_beside(tmp, sentence_shape=short)
        assert any("quantiles" in m for m in messages(rules_path)), \
            messages(rules_path)
    finally:
        shutil.rmtree(tmp)


def test_a_shape_that_goes_backwards_fails():
    tmp = tempfile.mkdtemp()
    try:
        backwards = dict(GOOD_SHAPE,
                         quantiles=[4, 8, 10, 12, 13, 15, 17, 19, 9, 26, 34])
        rules_path = fingerprint_beside(tmp, sentence_shape=backwards)
        assert any("non-decreasing" in m for m in messages(rules_path)), \
            messages(rules_path)
    finally:
        shutil.rmtree(tmp)


def test_a_missing_shape_is_not_a_failure():
    """The shape is a rewrite target and nothing raises a finding off it. A
    profile measured before it existed still has a usable measure block."""
    tmp = tempfile.mkdtemp()
    try:
        rules_path = fingerprint_beside(tmp, sentence_shape=None)
        assert not messages(rules_path), messages(rules_path)
    finally:
        shutil.rmtree(tmp)


# --------------------------------------------------------------------------
# the two advisory keys
# --------------------------------------------------------------------------

def test_a_signature_move_with_no_threshold_fails():
    """It compiles, it runs, it counts, and it can never report anything. That
    is the silent no-op this whole checker exists for: in the file it reads
    exactly like a rule somebody is honouring."""
    tmp = tempfile.mkdtemp()
    try:
        rules_path = profile(tmp, {"voice": "dana", "signature_moves": [
            {"id": "sig-x", "label": "X", "rx": "(?i)bottom line"}]})
        assert any("sets none of" in m for m in messages(rules_path)), \
            messages(rules_path)
    finally:
        shutil.rmtree(tmp)


def test_a_signature_move_with_a_floor_above_its_cap_fails():
    tmp = tempfile.mkdtemp()
    try:
        rules_path = profile(tmp, {"voice": "dana", "signature_moves": [
            {"id": "sig-x", "label": "X", "rx": "(?i)bottom line",
             "min_per_1000w": 4.0, "max_per_1000w": 2.0}]})
        assert any("no document can satisfy both" in m
                   for m in messages(rules_path)), messages(rules_path)
    finally:
        shutil.rmtree(tmp)


def test_a_well_formed_signature_move_passes():
    tmp = tempfile.mkdtemp()
    try:
        rules_path = profile(tmp, {"voice": "dana", "signature_moves": [
            {"id": "sig-x", "label": "X", "rx": "(?i)bottom line",
             "max_allowed": 3, "min_per_1000w": 0.5}]})
        assert not messages(rules_path), messages(rules_path)
    finally:
        shutil.rmtree(tmp)


def test_half_a_contrastive_pair_fails():
    """A pair is worth ten adjectives and half a pair is an adjective."""
    tmp = tempfile.mkdtemp()
    try:
        rules_path = profile(tmp, {"voice": "dana", "banned_words": ["synergy"],
                                   "contrastive_pairs": [
                                       {"rule": "connectors",
                                        "would": "Also, it shipped."}]})
        assert any("would_never" in m for m in messages(rules_path)), \
            messages(rules_path)
    finally:
        shutil.rmtree(tmp)


def test_a_whole_contrastive_pair_passes():
    tmp = tempfile.mkdtemp()
    try:
        rules_path = profile(tmp, {"voice": "dana", "banned_words": ["synergy"],
                                   "contrastive_pairs": [
                                       {"rule": "connectors",
                                        "would": "Also, it shipped.",
                                        "would_never": "Furthermore, it was "
                                                       "successfully shipped."}]})
        assert not messages(rules_path), messages(rules_path)
    finally:
        shutil.rmtree(tmp)
