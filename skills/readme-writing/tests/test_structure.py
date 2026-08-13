#!/usr/bin/env python3
"""
Calibration and structure: a README that follows the measured convention comes
back quiet, one that violates it comes back loud, and the ordering rules fire on
the shapes the corpus says they should.
"""

import shutil
import tempfile

from helpers import (bad_result, check_module, good_result, ids, run,
                     run_code, sample, total, written)


def test_the_good_sample_raises_no_p0_and_no_p1():
    good = good_result()
    assert good["counts"]["P0"] == 0, "got %s" % ids(good, "P0")
    assert good["counts"]["P1"] == 0, "got %s" % ids(good, "P1")


def test_the_bad_sample_raises_a_p0():
    assert bad_result()["counts"]["P0"] >= 1, "got %s" % ids(bad_result(), "P0")


def test_the_two_samples_are_separated_by_5x():
    good, bad = total(good_result()), total(bad_result())
    assert bad > 5 * good, "%s vs %s" % (bad_result()["counts"], good_result()["counts"])


def test_a_buried_pitch_is_found():
    assert "pitch-buried" in ids(bad_result())


def test_a_sponsor_block_above_the_pitch_is_found():
    assert "promo-before-pitch" in ids(bad_result())


def test_install_after_the_community_sections_is_found():
    assert "install-late" in ids(bad_result())


def test_a_license_that_is_not_last_is_found():
    assert "license-not-last" in ids(bad_result())


def test_restated_license_terms_are_found():
    assert "license-long" in ids(bad_result())


def test_a_badge_wall_is_found():
    assert "badge-wall" in ids(bad_result())


def test_a_toc_on_a_short_readme_is_found():
    assert "toc-unneeded" in ids(bad_result())


def test_an_html_header_is_not_read_as_a_buried_pitch():
    """76% of the corpus centers its header, and a centered header puts the
    tagline inside HTML. Treating markup as decoration would report a buried
    pitch on most of the good READMEs in the study."""
    assert "pitch-buried" not in ids(good_result())


def test_a_long_paragraph_is_reported_at_its_real_line():
    """Fences, headings, and tables are blanked rather than stripped, so a
    finding's line still points at the file. Deleting them shifts every line
    below, which is worse than no line number at all."""
    with open(sample("good-readme.md"), encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    expected = next(i + 1 for i, line in enumerate(lines)
                    if line.startswith("Bug reports and patches"))
    hits = [f for f in good_result()["findings"] if f["id"] == "long-paragraph"]
    assert len(hits) == 1 and hits[0]["line"] == expected, "expected L%d, got %s" % (
        expected, [f["line"] for f in hits])


def test_check_exits_zero_with_no_p0():
    result, code = run_code(sample("good-readme.md"), "--no-voice", "--check")
    assert code == 0 and result["counts"]["P0"] == 0, "code %d, %s" % (code, result["counts"])


def test_check_exits_one_on_a_p0():
    result, code = run_code(sample("bad-readme.md"), "--no-voice", "--check")
    assert code == 1 and result["counts"]["P0"] >= 1, "code %d, %s" % (code, result["counts"])


def test_without_check_a_p0_still_exits_zero():
    _, code = run_code(sample("bad-readme.md"), "--no-voice")
    assert code == 0, "code %d" % code


# --------------------------------------------------------------------------
# shapes no fixture used to exercise
#
# Every bug in this block survived two review passes because nothing in the
# suite had the shape that triggers it. The fixtures are the fix.
# --------------------------------------------------------------------------

BADGE_README = """# Widget

[![PyPI](https://img.shields.io/pypi/v/widget.svg)](https://pypi.org/project/widget/)
[![Build](https://github.com/o/widget/actions/workflows/ci.yml/badge.svg)](https://github.com/o/widget/actions)

Widget converts one file format into another without a build step.

## Install

```bash
pip install widget
```

## License

MIT.
"""


def test_a_badge_wrapped_link_counts_once():
    """`[![alt](badge)](target)`. LINK_RX's outer bracket stops at the `]`
    closing the alt text, so without images blanked first it captured `![alt` as
    the link text and the badge image URL as the destination: a link that is not
    in the file, counted and averaged."""
    scratch = tempfile.mkdtemp()
    try:
        result = run(written(scratch, "BADGE.md", BADGE_README), "--no-voice")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert result["stats"]["inline_links"] == 2, "got %d" % result["stats"]["inline_links"]
    # Badge alt text ("PyPI", "Build") is what used to be averaged in here.
    assert result["stats"]["avg_link_text_words"] == 0, "got %s" % result["stats"]["avg_link_text_words"]
    assert result["stats"]["badge_count"] == 2, "got %d" % result["stats"]["badge_count"]
    assert result["stats"]["bare_urls"] == 0, "got %d" % result["stats"]["bare_urls"]


API_README = """# Widget

Widget converts one file format into another without a build step.

## Install

```bash
pip install widget
```

## API

`convert(src, dst)` does the work.

## License

MIT.
"""


def test_a_bare_api_heading_classifies_as_api():
    """The keyword was written " api" so it could not match a word at the start
    of the string, and the single most obvious API heading in the corpus
    classified as "other"."""
    scratch = tempfile.mkdtemp()
    try:
        result = run(written(scratch, "API.md", API_README), "--no-voice")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert "api" in result["stats"]["sections"], str(result["stats"]["sections"])


UNCLOSED_README = """<h1 align="center">Widget</h1>

<table>
<tr><td><img src="https://acme.example/logo.png" width="120"></td></tr>

## About

Widget converts one file format into another without a build step.

## Install

```bash
pip install widget
```

## License

MIT.
"""


def test_an_unclosed_table_does_not_swallow_the_pitch():
    """GitHub renders it anyway. The depth counter has no way to know, so it
    stayed positive to the end of the file, every line after it skipped, and a
    README that describes itself in its second paragraph reported no-pitch: a
    P0, and a CI failure under --check."""
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "UNCLOSED.md", UNCLOSED_README)
        result = run(path, "--no-voice")
        code = run_code(path, "--no-voice", "--check")[1]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert "no-pitch" not in ids(result), str(ids(result))
    assert result["stats"]["pitch_line"] == 8, "got %s" % result["stats"]["pitch_line"]
    assert code == 0, "code %d" % code


LANGUAGE_BAR_README = """<h1 align="center">Widget</h1>

<details>
<summary>Read this in another language</summary>

# Widget en Deutsch

Widget ist eine kleine Bibliothek und wandelt ein Format in ein anderes um.

</details>

Widget converts one file format into another without a build step.

## Install

```
pip install widget
```

## License

MIT.
"""


def test_a_heading_inside_a_closed_details_block_is_not_the_pitch():
    """A language bar routinely holds a heading and a translated tagline. A pass
    that let any heading close the enclosing <details> handed back the collapsed
    translation as the pitch, which moved pitch_line, the lines-above count, and
    whether pitch-buried fired. The tags balance here, so nothing is unclosed and
    nothing needs repairing."""
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "LANGBAR.md", LANGUAGE_BAR_README)
        result = run(path, "--no-voice")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert result["stats"]["pitch_line"] == 12, (
        "got %s, the German line inside <details> is at 8"
        % result["stats"]["pitch_line"])


TWO_LICENSE_README = """# Widget

Widget converts one file format into another without a build step.

## Install

```bash
pip install widget
```

## License and pricing

Free for personal use, commercial terms below.

## Contributing

Patches welcome.

## License

MIT. See LICENSE.
"""


def test_a_real_final_license_section_is_not_reported_as_out_of_place():
    """The position check read the first licence mention, so a file that ends
    with its license was told the license is not last."""
    scratch = tempfile.mkdtemp()
    try:
        result = run(written(scratch, "TWOLIC.md", TWO_LICENSE_README), "--no-voice")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert "license-not-last" not in ids(result), str(ids(result))
    assert result["stats"]["license_words"] == 3, "got %s" % result["stats"]["license_words"]


def test_singular_collides_a_plural_with_its_singular():
    """The inconsistent-number check keys on the noun so a plural and a
    singular of the same countable noun are compared. rstrip("s") split them:
    "classes" and "class" landed in different buckets and a real conflict went
    unflagged. "cases" has to stay "case" (a unit of measure), not "cas"."""
    singular = check_module()._singular
    assert singular("classes") == singular("class") == "class"
    assert singular("boxes") == "box"
    assert singular("entries") == "entry"
    assert singular("cases") == "case"
    assert singular("libraries") == "library"
    assert singular("cats") == "cat"


def test_a_singular_and_plural_with_different_numbers_is_flagged():
    """The same count reported once as a plural and once as a singular is the
    conflict the old rstrip key missed: "3 classes" and "1 class" used to land
    in different buckets. Now they collide and the inconsistency is a P2."""
    scratch = tempfile.mkdtemp()
    try:
        body = ("# proj\n\n## 3 classes of export\n\nprose here.\n\n"
                "### backed by 1 class\n\nmore prose here.\n")
        result = run(written(scratch, "README.md", body), "--no-voice")
        assert "inconsistent-number" in ids(result), str(ids(result))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
