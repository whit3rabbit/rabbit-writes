#!/usr/bin/env python3
"""
Which voice governs, and what happens when the answer is unclear.

Resolution order: --voice-rules, then a `.rabbit-voice` file beside the README
or in the working directory, then voices/ACTIVE, then the single installed
profile as an announced fallback.

These run against a throwaway voices/ directory, so they assert the mechanism
rather than whichever profile this checkout happens to ship or have active.
Swapping the shipped voice must not move a single result in this file.
"""

import json
import os
import shutil
import tempfile

from helpers import CORPUS_DIR, check_module, ids, run, sample

ORIGINAL_CWD = os.getcwd()

VOICED = "voiced-readme.md"
TEST_RULES = "test-voice.rules.json"


def test_the_active_voice_resolves_without_being_named():
    result = run(sample(VOICED))
    assert result["voice"] is not None, "notes: %s" % result["notes"]


def test_the_profile_markdown_is_pointed_at_and_not_just_the_rules_file():
    """A clean scan reads like a pass, and the half that decides whether this
    sounds like anyone is in the markdown."""
    result = run(sample(VOICED))
    assert any(".md" in note for note in result["notes"]), result["notes"]


def test_voice_findings_land_in_a_readme():
    """Enforcement runs against a fixture profile, not against whichever voice
    the plugin ships. Swapping either must not move these results."""
    voiced = run(sample(VOICED), "--voice-rules", sample(TEST_RULES))
    hits = [f["id"] for f in voiced["findings"] if f["band"] == "voice"]
    for pattern_id in ("voice-em-dash", "voice-semicolon", "voice-banned-word",
                       "voice-banned-phrase"):
        assert pattern_id in hits, "%s missing from %s" % (pattern_id, hits)


def test_a_correspondence_closer_is_not_demanded_of_a_readme():
    voiced = run(sample(VOICED), "--voice-rules", sample(TEST_RULES))
    hits = [f["id"] for f in voiced["findings"] if f["band"] == "voice"]
    assert "missing-closer" not in hits, hits


def test_no_voice_suppresses_the_voice_band():
    quiet = run(sample(VOICED), "--no-voice")
    assert not [f for f in quiet["findings"] if f["band"] == "voice"]


def test_voice_findings_do_not_change_structure_findings():
    voiced = run(sample(VOICED), "--voice-rules", sample(TEST_RULES))
    quiet = run(sample(VOICED), "--no-voice")
    assert set(ids(voiced)) >= set(ids(quiet))


def scratch_voices():
    """A temporary voices/ holding two profiles and a README to resolve from.

    Also makes it the working directory. `resolve_voice` probes cwd for a
    `.rabbit-voice` right after the README's own directory, so without this a
    stray pin at the developer's repository root decides these tests and the
    failure reads as a bug in the resolution order.
    """
    tmp = tempfile.mkdtemp()
    readme = os.path.join(tmp, "README.md")
    open(readme, "w").close()
    for who in ("ada", "grace"):
        with open(os.path.join(tmp, who + ".rules.json"), "w") as fh:
            json.dump({"voice": who}, fh)
        open(os.path.join(tmp, who + ".md"), "w").close()
    os.chdir(tmp)
    return tmp, readme


def restore(rc, real_voices_dir, tmp):
    """Undo everything scratch_voices touched, cwd included."""
    rc.VOICES_DIR = real_voices_dir
    os.chdir(ORIGINAL_CWD)
    shutil.rmtree(tmp, ignore_errors=True)


def test_active_decides_which_voice_whoever_it_is():
    rc = check_module()
    tmp, readme = scratch_voices()
    real = rc.VOICES_DIR
    try:
        rc.VOICES_DIR = tmp
        with open(os.path.join(tmp, "ACTIVE"), "w") as fh:
            fh.write("grace\n")
        rules, name, note = rc.resolve_voice(readme)
        assert name == "grace", name
        assert rules.endswith("grace.rules.json"), rules
        assert note is None, note
    finally:
        restore(rc, real, tmp)


def test_no_active_with_several_profiles_asks_instead_of_guessing():
    """Writing in the wrong person's register is worse than writing in none."""
    rc = check_module()
    tmp, readme = scratch_voices()
    real = rc.VOICES_DIR
    try:
        rc.VOICES_DIR = tmp
        rules, name, note = rc.resolve_voice(readme)
        assert rules is None and "Name one" in (note or ""), note
    finally:
        restore(rc, real, tmp)


def test_no_active_with_one_profile_falls_back_and_says_so():
    rc = check_module()
    tmp, readme = scratch_voices()
    real = rc.VOICES_DIR
    try:
        rc.VOICES_DIR = tmp
        os.remove(os.path.join(tmp, "ada.rules.json"))
        rules, name, note = rc.resolve_voice(readme)
        assert name == "grace" and rules is not None, "%s %s" % (name, rules)
        assert "falling back" in (note or ""), note
    finally:
        restore(rc, real, tmp)


def test_a_repo_pin_outranks_active():
    rc = check_module()
    tmp, readme = scratch_voices()
    real = rc.VOICES_DIR
    try:
        rc.VOICES_DIR = tmp
        with open(os.path.join(tmp, ".rabbit-voice"), "w") as fh:
            fh.write("grace\n")
        with open(os.path.join(tmp, "ACTIVE"), "w") as fh:
            fh.write("nobody\n")
        rules, name, note = rc.resolve_voice(readme)
        assert name == "grace" and "pinned" in (note or ""), note
    finally:
        restore(rc, real, tmp)


def test_a_named_profile_that_cannot_be_read_is_an_error_not_a_silent_pass():
    """`--voice-rules <typo>` used to cancel the whole prose scan and exit 0:
    the fingerprint band, which has nothing to do with whose voice it is in,
    disappeared with the profile, so a README carrying a chat citation marker
    reported "No mechanical findings". scan.py exits 2 here and so does this."""
    import subprocess
    import sys

    from helpers import CHECK, NEUTRAL_CWD

    tmp = tempfile.mkdtemp()
    try:
        readme = os.path.join(tmp, "README.md")
        with open(readme, "w", encoding="utf-8") as fh:
            fh.write("# widget\n\nwidget resizes images. See "
                     "cite" + "turn0search0 for details.\n")
        out = subprocess.run(
            [sys.executable, CHECK, readme, "--json", "--check",
             "--voice-rules", os.path.join(tmp, "nobody.rules.json")],
            capture_output=True, text=True, cwd=NEUTRAL_CWD)
        assert out.returncode == 2, "%d: %s" % (out.returncode, out.stderr)

        # And with no profile asked for, the same document still fails on the
        # marker rather than passing quietly.
        out = subprocess.run(
            [sys.executable, CHECK, readme, "--json", "--check", "--no-voice"],
            capture_output=True, text=True, cwd=NEUTRAL_CWD)
        assert out.returncode == 1, "%d: %s" % (out.returncode, out.stderr)
        assert "citation-leak" in ids(json.loads(out.stdout), "P0")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
