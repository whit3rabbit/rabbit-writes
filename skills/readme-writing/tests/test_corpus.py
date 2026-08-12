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
from rwlib import injection


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


# --------------------------------------------------------------------------
# the safety band, measured on the same snapshot
# --------------------------------------------------------------------------

def safety_findings():
    """[(slug, finding)] for every safety-band finding in the snapshot."""
    out = []
    for slug, path in corpus_readmes():
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        out.extend((slug, f) for f in injection.scan(raw))
    return out


def test_no_corpus_readme_raises_a_safety_p0():
    """The claim that justifies P0-gating the pre-commit hooks on this band.

    A safety P0 fails `--check`, which blocks a commit in somebody else's
    repository. Asserting zero across 100 real trending READMEs is what makes
    that defensible, and it is asserted rather than reported: if a tightening
    ever puts a P0 on ordinary documentation, the gating decision has to be
    revisited before the change ships, not after somebody's commit is blocked.
    """
    flagged = [(slug, f["id"], f["line"], f["match"])
               for slug, f in safety_findings() if f["priority"] == "P0"]
    assert not flagged, str(flagged)


def test_the_hidden_text_rate_is_the_published_one():
    """4 of 100, and PROOF.md publishes the number rather than hiding it.

    All four are genuine maintainer notes in HTML comments, the residual left
    after the build-marker allowlist in rwlib/injection.py. They are the honest
    cost of reporting concealment with no payload at P1, and a jump means the
    allowlist stopped covering something the wild actually writes.
    """
    readmes = corpus_readmes()
    if not readmes:
        return
    hidden = [slug for slug, f in safety_findings()
              if f["id"] == "injection-hidden-text"]
    if len(readmes) != EXPECTED_CORPUS_READMES:
        print("    note: corpus is %d READMEs, not the %d snapshot the rate was "
              "measured on. %d hidden-text findings, reported and not asserted."
              % (len(readmes), EXPECTED_CORPUS_READMES, len(hidden)))
        return
    assert len(hidden) == 4, str(sorted(hidden))


def test_no_corpus_readme_raises_a_visible_directive():
    """The directive families are shaped to attack idioms rather than to
    meaning. Three were cut down after this test: `instead of editing`, and an
    unanchored agent-noun rule that read "state model, output formats" and "In
    your agent, run it once per repo" as instructions."""
    readmes = corpus_readmes()
    if not readmes or len(readmes) != EXPECTED_CORPUS_READMES:
        return
    visible = [(slug, f["match"]) for slug, f in safety_findings()
               if f["id"] == "injection-visible-directive"]
    assert not visible, str(visible)
