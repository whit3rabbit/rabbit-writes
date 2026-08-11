#!/usr/bin/env python3
"""
Calibration: known slop scores high, known human scores low, and the two are
separated by enough of a margin that a small regression does not close the gap.

These are the numbers PROOF.md publishes. They are a regression guard and not an
accuracy claim, for the reason that file states at length and
docs/detector-corpus/README.md gives the fix for: two hand-written samples
establish that a detector separates an obvious case from an obvious case.
"""

from helpers import (ai_result, human_result, metronomic_result, scan_text,
                     total)


def test_ai_sample_raises_enough_findings():
    ai = ai_result()
    assert total(ai) >= 20, "got %d" % total(ai)
    assert ai["counts"]["P0"] >= 3, "got %d" % ai["counts"]["P0"]


def test_human_sample_raises_no_p0():
    human = human_result()
    assert human["counts"]["P0"] == 0, "got %s" % [
        f["id"] for f in human["findings"] if f["priority"] == "P0"]


def test_human_sample_stays_quiet():
    human = human_result()
    assert total(human) < 6, "got %d: %s" % (
        total(human), [f["id"] for f in human["findings"]])


def test_the_two_samples_are_separated_by_more_than_4x():
    ai, human = total(ai_result()), total(human_result())
    assert ai > human * 4, "%d vs %d" % (ai, human)


def test_human_burstiness_is_in_the_human_range():
    human = human_result()
    assert human["stats"]["burstiness"] >= 0.45, "got %s" % human["stats"]["burstiness"]


def test_reliability_is_reported():
    assert human_result()["reliability"] in ("high", "medium", "low", "insufficient")


# Burstiness is an independent axis from vocabulary. A draft can pass every word
# check and still read as machine output because the rhythm is even, which is
# what the metronomic fixture is for.

def test_metronomic_sample_is_clean_on_vocabulary():
    found = {f["id"] for f in metronomic_result()["findings"]}
    assert not ({"tier1", "chatbot-artifact", "generic-conclusion"} & found), str(found)


def test_metronomic_sample_still_flags_uniformity():
    metro = metronomic_result()
    found = {f["id"] for f in metro["findings"]}
    assert "uniformity" in found or "uniform-paragraphs" in found, (
        "burstiness %s, para sd %s" % (metro["stats"]["burstiness"],
                                       metro["stats"].get("paragraph_sd")))


def test_metronomic_burstiness_is_below_the_human_floor():
    metro = metronomic_result()
    assert metro["stats"]["burstiness"] < 0.45, "got %s" % metro["stats"]["burstiness"]
    assert human_result()["stats"]["burstiness"] > metro["stats"]["burstiness"]


def test_bands_are_both_populated():
    ai = ai_result()
    assert [f for f in ai["findings"] if f["band"] == "fingerprint"]
    assert [f for f in ai["findings"] if f["band"] == "craft"]


def test_wordiness_is_craft_and_never_a_fingerprint():
    """A clarity edit must never look like authorship evidence."""
    ai = ai_result()
    assert all(f["band"] == "craft"
               for f in ai["findings"] if f["id"] == "clarity")


def test_check_exits_zero_with_no_p0():
    clean, code = scan_text("The certificate expired on the internal proxy. "
                            "We caught it in 22 minutes.\n", "--check")
    assert code == 0 and clean["counts"]["P0"] == 0, "code %d, %s" % (code, clean["counts"])


def test_check_exits_one_on_a_p0():
    dirty, code = scan_text("As of my last training update, this was true.\n", "--check")
    assert code == 1 and dirty["counts"]["P0"] >= 1, "code %d, %s" % (code, dirty["counts"])


def test_without_check_a_p0_still_exits_zero():
    _, code = scan_text("As of my last training update, this was true.\n")
    assert code == 0, "code %d" % code
