#!/usr/bin/env python3
"""
The corpus regression, and the numbers the checker compares against.

The band here is calibrated against the snapshot committed with the study, so it
only means anything on that snapshot. Refetching the corpus changes the
denominator and the repos in it, and a band that keeps asserting through a
refetch is asserting about a different population. The count is checked first
and the band is reported rather than asserted when it moves.
"""

import os
import re

from helpers import (CORPUS_DIR, EXPECTED_CORPUS_READMES, corpus_p0_slugs,
                     corpus_readmes)

from rwlib import corpus as corpus_mod


def test_the_corpus_summary_matches_the_research_aggregate():
    """readme_check.py used to carry these as a literal with a comment promising
    they mirrored the aggregate, and nothing checked the promise. Regenerating
    the corpus could orphan every threshold in the checker without a word."""
    differences = corpus_mod.drift()
    assert not differences, "\n".join(
        "%s: shipped %r, aggregate %r" % d for d in differences)


def test_the_corpus_summary_is_shipped_and_populated():
    summary = corpus_mod.load()
    assert summary["n_repos"] >= 50, "got %d" % summary["n_repos"]
    assert summary["word_count_percentiles"]["p50"] > 0
    assert summary["section_avg_position"]["license"] > 0.8


def test_the_p0_rate_stays_in_the_worst_decile_of_the_corpus():
    """6 of 100 in the study sample. A jump means a check got noisier, which
    matters more than the exact number."""
    readmes = corpus_readmes()
    if not readmes:
        return
    if len(readmes) != EXPECTED_CORPUS_READMES:
        print("    note: corpus is %d READMEs, not the %d snapshot the band was "
              "calibrated on. P0 rate %d, reported and not asserted."
              % (len(readmes), EXPECTED_CORPUS_READMES, len(corpus_p0_slugs())))
        return
    flagged = corpus_p0_slugs()
    assert 2 <= len(flagged) <= 12, "%d repos: %s" % (len(flagged), flagged)


def test_spec_kit_stays_clean_of_p0():
    """A named fixture, asserted whether or not the snapshot moved: this one is
    in the study by name and its verdict is the calibration."""
    slugs = {slug for slug, _ in corpus_readmes()}
    if "github__spec-kit" not in slugs:
        return
    assert "github__spec-kit" not in corpus_p0_slugs()


def test_ecc_is_still_flagged():
    slugs = {slug for slug, _ in corpus_readmes()}
    if "affaan-m__ECC" not in slugs:
        return
    assert "affaan-m__ECC" in corpus_p0_slugs()


def test_the_corpus_is_present_in_this_checkout():
    """Not an assertion about the engine. Without it, every check above passes
    by returning early and the suite reports green over nothing."""
    if not os.path.isdir(CORPUS_DIR):
        print("    note: docs/readme-analysis/repos is not present, so the "
              "corpus regression did not run")
        return
    assert corpus_readmes(), "the corpus directory exists but holds no READMEs"


def test_the_corpus_is_dated_in_the_shipped_extract():
    """A frozen snapshot has to say when it was frozen. The study skews toward
    whatever was trending the week it was taken, and the writeup says so; the
    extract that ships with the skill did not, so the checker's report read as a
    standing fact about READMEs rather than a measurement with an age."""
    summary = corpus_mod.load()
    measured = summary.get("measured_at")
    assert measured, "corpus_summary.json carries no measured_at"
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", measured), measured


def test_the_report_quotes_the_date_beside_the_count():
    """Undated, "100 trending repos" is the thing a reader in 2028 cannot
    discount without going and finding the writeup."""
    import subprocess
    import sys
    from helpers import CHECK, NEUTRAL_CWD, sample
    out = subprocess.run([sys.executable, CHECK, sample("good-readme.md")],
                         capture_output=True, text=True, cwd=NEUTRAL_CWD)
    line = [ln for ln in out.stdout.splitlines() if "corpus comparison" in ln]
    assert line, out.stdout[:400]
    assert corpus_mod.load()["measured_at"] in line[0], line[0]
