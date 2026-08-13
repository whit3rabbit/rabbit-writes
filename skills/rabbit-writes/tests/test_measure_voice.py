#!/usr/bin/env python3
"""
measure_voice.py, the voice-setup script that reads a pile of samples.

It lives in the other skill and is tested from this suite because everything it
measures comes out of this engine: it imports scan.py, reuses its mark regexes,
and its whole value is that the numbers it prints are the numbers scan.py would
print. A copy of those regexes over there would be the drift rwlib exists to
prevent, so the coupling is deliberate and this file is where it is pinned.

The assertions worth having are about restraint. The script proposes a
`mechanics` object from three or four documents, and the failure mode is not a
wrong average, it is a confident one: a ban asserted because a counter saw zero,
with nothing telling the reader how thin the evidence was.

Stdlib only, 3.9+.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

from helpers import ROOT, sample, written

# ROOT is skills/rabbit-writes, so its parent is skills/. Walked rather than
# spelled out from the repository root, the way every script here resolves a
# sibling, so a skill directory can move without editing this.
MEASURE = os.path.join(os.path.dirname(ROOT), "voice-setup", "scripts",
                       "measure_voice.py")

# Long enough to clear the reliability floor, plain enough that the only marks
# in it are the ones a test puts there.
BODY = ("The build reads a manifest and writes a report. It runs from a "
        "checkout with nothing installed, which is the whole bargain. Paths "
        "resolve against the file that holds them, so a directory can move "
        "without anybody editing the scripts inside it.\n\n"
        "We shipped the change on a Tuesday. The rollback took four minutes "
        "and nobody outside the team noticed, which is the outcome you want "
        "and never get to write about.\n\n")

# A second piece by the same imaginary person, for the tests that need two
# samples that are not the same file twice.
OTHER_BODY = ("The hook runs from somebody else's checkout, which is the only "
              "place it matters. We tested it here for a year and here is not "
              "where it fails. Two of them shipped broken because of that.\n\n"
              "So the fixture is a stranger's repository now, built in a "
              "temporary directory and thrown away after. It costs a second "
              "per run and it caught both bugs on the first pass.\n\n")


def run(*paths, **kwargs):
    extra = kwargs.pop("extra", ())
    assert not kwargs, kwargs
    out = subprocess.run([sys.executable, MEASURE, *paths, "--json", *extra],
                         capture_output=True, text=True)
    assert out.stdout, out.stderr
    return json.loads(out.stdout), out.returncode


def scratch(files):
    """(directory, [paths]) for a dict of name -> body."""
    directory = tempfile.mkdtemp(prefix="rabbit-measure-")
    return directory, [written(directory, name, body)
                       for name, body in sorted(files.items())]


def test_the_script_is_where_the_skill_says_it_is():
    assert os.path.exists(MEASURE), MEASURE


def test_it_reports_one_row_per_sample():
    directory, paths = scratch({"a.md": BODY * 2, "b.md": BODY * 2})
    try:
        result, code = run(*paths)
        assert len(result["samples"]) == 2, result["samples"]
        assert code == 0, result
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_the_measured_block_matches_the_template_field_names():
    """The block is pasted straight into a profile under `## Measured from
    samples`, so the labels have to be the template's, not scan.py's. Two of
    them differ: `sentence_sd` is `sentence_length_sd` there, and
    `em_dashes_per_1k` is `em_dashes_per_1000w`."""
    directory, paths = scratch({"a.md": BODY * 2})
    try:
        block = run(*paths)[0]["measured_block"]
        for label in ("avg_sentence_words", "sentence_length_sd", "burstiness",
                      "mattr", "em_dashes_per_1000w", "contraction_rate"):
            assert label + ":" in block, (label, block)
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_every_suggestion_carries_the_count_behind_it():
    """"semicolon: forbid" is a claim about a person. "0 semicolons in 900
    words" is what the samples said, and only the second is checkable by the
    person it is about."""
    directory, paths = scratch({"a.md": BODY * 2})
    try:
        result = run(*paths)[0]
        for key in result["mechanics"]:
            if key == "max_em_dashes_per_1000w":
                continue          # carried by the em_dash line above it
            assert result["mechanics_evidence"].get(key), key
            assert any(ch.isdigit() for ch in result["mechanics_evidence"][key]), key
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_a_writer_who_uses_em_dashes_is_not_told_to_stop():
    """The suggestion has to be able to come back `allow`. A script that always
    proposes a ban is installing the author of the script."""
    dashy = BODY.replace("on a Tuesday.", "on a Tuesday — a bad day for it.")
    directory, paths = scratch({"a.md": dashy * 4})
    try:
        result = run(*paths)[0]
        assert result["mechanics"]["em_dash"] in ("allow", "limit"), result["mechanics"]
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_an_em_dash_cap_sits_above_the_observed_rate():
    """A cap set to the average fails the next piece for being one dash busier
    than the last four, which is noise rather than a defect."""
    text = (BODY * 6).replace("on a Tuesday.", "on a Tuesday — a bad day.", 1)
    directory, paths = scratch({"a.md": text})
    try:
        result = run(*paths)[0]
        if result["mechanics"]["em_dash"] == "limit":
            marks = result["samples"][0]["marks"]
            assert result["mechanics"]["max_em_dashes_per_1000w"] > \
                marks["em_dashes_per_1k"], result["mechanics"]
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_a_contaminated_sample_stops_the_run():
    """A tell that reaches a profile is reproduced on purpose, forever. Exit 1
    so this cannot pass unnoticed in a pipeline."""
    result, code = run(sample("ai-sample.md"))
    assert code == 1, result
    assert result["contaminated"], result
    assert any(f["id"] == "chatbot-artifact"
               for f in result["samples"][0]["p0"]), result["samples"][0]["p0"]


def test_a_clean_sample_does_not():
    result, code = run(sample("human-sample.md"))
    assert code == 0, result
    assert not result["contaminated"], result


def test_the_semicolon_count_ignores_html_entities():
    """The `;` closing `&nbsp;` is markup. Counted, it reports semicolon habits
    this writer does not have and then suggests allowing them."""
    entity = BODY + "Sponsors &amp; partners, spaced&nbsp;out for the header.\n\n"
    directory, paths = scratch({"a.md": entity * 2})
    try:
        result = run(*paths)[0]
        assert result["samples"][0]["marks"]["semicolons"] == 0, \
            result["samples"][0]["marks"]
        assert result["mechanics"]["semicolon"] == "forbid"
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_no_readable_sample_is_an_error_and_not_an_empty_profile():
    out = subprocess.run([sys.executable, MEASURE, "/nonexistent/nope.md"],
                         capture_output=True, text=True)
    assert out.returncode == 2, out.stdout


# --------------------------------------------------------------------------
# the fingerprint and the distributions
# --------------------------------------------------------------------------

def test_it_builds_a_fingerprint_from_two_or_more_samples():
    """The calibration band is the output worth having. A raw distance means
    nothing on its own, and "0.9, where this writer's own samples sit under
    0.6" is a claim a person can act on.

    Two different bodies, because two copies of one file have a self-distance of
    exactly zero and would assert nothing about whether the band is measured."""
    directory, paths = scratch({"a.md": BODY * 2, "b.md": OTHER_BODY * 2})
    try:
        result = run(*paths)[0]
        fp = result["fingerprint"]
        assert fp["n_samples"] == 2, fp
        assert fp["self_distance"]["max"] > 0, fp["self_distance"]
        assert result["fingerprint_written_to"] is None, result
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_one_sample_gets_no_fingerprint_rather_than_an_uncalibrated_one():
    directory, paths = scratch({"a.md": BODY * 2})
    try:
        assert run(*paths)[0]["fingerprint"] is None
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_write_fingerprint_lands_where_scan_looks_for_it():
    directory, paths = scratch({"a.md": BODY * 2, "b.md": BODY * 2})
    try:
        result = run(*paths, extra=("--name", "tester", "--write-fingerprint",
                                    "--voices-dir", directory))[0]
        target = os.path.join(directory, "tester.fingerprint.json")
        assert result["fingerprint_written_to"] == target, result
        with open(target, encoding="utf-8") as fh:
            assert json.load(fh)["voice"] == "tester"
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_a_fingerprint_is_never_written_from_a_contaminated_sample():
    """Every other output here is a suggestion a person reads and confirms.
    This one is a file a later scan measures against without asking, so an
    assisted sample in it makes the assisted register the target."""
    directory = tempfile.mkdtemp(prefix="rabbit-measure-")
    try:
        result, code = run(sample("ai-sample.md"), sample("human-sample.md"),
                           extra=("--name", "tester", "--write-fingerprint",
                                  "--voices-dir", directory))
        assert code == 1, result
        assert result["fingerprint_written_to"] is None, result
        assert not os.path.exists(os.path.join(directory,
                                               "tester.fingerprint.json"))
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_write_fingerprint_without_a_name_is_an_error():
    """The name decides the filename and labels the fingerprint. Guessing one
    writes a profile nobody asked for into somebody's voices directory."""
    directory, paths = scratch({"a.md": BODY * 2, "b.md": BODY * 2})
    try:
        out = subprocess.run([sys.executable, MEASURE, *paths,
                              "--write-fingerprint"],
                             capture_output=True, text=True)
        assert out.returncode == 2, out.stdout
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_exemplars_are_opt_in_because_they_copy_the_writers_prose():
    directory, paths = scratch({"a.md": BODY * 2, "b.md": BODY * 2})
    try:
        assert "exemplars" not in run(*paths)[0]["fingerprint"]
        with_them = run(*paths, extra=("--with-exemplars",))[0]["fingerprint"]
        assert with_them["exemplars"], with_them
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_the_distributions_carry_what_the_means_hide():
    """Openers, connectors, contractions and the sign-off. None of these is a
    threshold: they are what a person reads before writing the markdown half of
    a profile, which is the half no counter reaches."""
    directory, paths = scratch({"a.md": BODY * 2})
    try:
        dist = run(*paths)[0]["samples"][0]["distributions"]
        for key in ("sentence_openers", "paragraph_openers", "connectors",
                    "contractions", "hedges", "closer"):
            assert key in dist, (key, sorted(dist))
        assert dist["closer"], dist
        assert "\n" not in dist["closer"], repr(dist["closer"])
    finally:
        shutil.rmtree(directory, ignore_errors=True)
