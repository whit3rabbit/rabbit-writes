#!/usr/bin/env python3
"""
Links and headline claims: the two checks that cost the most in false positives.

A bare-URL finding that fires on an HTML `href` and a caveat check that accepts
one "results vary" from an FAQ three screens away are both worse than not
checking at all, because a linter nobody trusts is a linter nobody runs.
"""

import shutil
import tempfile

from helpers import bad_result, good_result, ids, run, sample, written


def test_link_syntax_inside_backticks_is_not_counted():
    """A doc that explains `[text][ref]` is talking about it, not using it."""
    assert "reference-links" not in ids(good_result()), ids(good_result())


def test_a_bare_url_is_found():
    assert "bare-url" in ids(bad_result())


def test_vague_link_text_is_found():
    assert "vague-link-text" in ids(bad_result())


def test_an_html_href_is_not_counted_as_bare():
    assert good_result()["stats"]["bare_urls"] == 0, "got %d" % good_result()["stats"]["bare_urls"]


def test_html_badges_are_counted():
    assert good_result()["stats"]["badge_count"] == 2, "got %d" % good_result()["stats"]["badge_count"]


def test_repeated_vague_link_text_reports_distinct_lines():
    """Searching for the link text finds the first occurrence every time, so
    three "here" links used to send the writer to the same line three times."""
    lines = sorted(f["line"] for f in bad_result()["findings"]
                   if f["id"] == "vague-link-text")
    assert len(lines) >= 3, str(lines)
    assert len(set(lines)) == len(lines), str(lines)
    with open(sample("bad-readme.md"), encoding="utf-8") as fh:
        source = fh.read().split("\n")
    assert all("[here]" in source[n - 1] for n in lines), str(
        [(n, source[n - 1][:40]) for n in lines])


BRACKETS_README = """# Matrix

Matrix converts one file format into another without a build step.

## Install

```bash
pip install matrix
```

## Usage

Read matrix[i][j] for a cell and matrix[row][col] for the transposed view.
See the [Astro][] docs and the [spec][markdown-spec] for the rest.

[astro]: https://astro.build
[markdown-spec]: https://spec.commonmark.org

## License

MIT.
"""


def test_bracket_adjacent_prose_is_not_a_reference_link():
    """`matrix[i][j]` outside a code span is the common case, and the finding
    told the writer to convert a link that does not exist. A `[a][b]` match now
    has to resolve against a definition before it is reported."""
    scratch = tempfile.mkdtemp()
    try:
        result = run(written(scratch, "BRACKETS.md", BRACKETS_README), "--no-voice")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert result["stats"]["reference_links"] == 2, "got %d" % result["stats"]["reference_links"]


# --------------------------------------------------------------------------
# claims are caveated near the claim, not anywhere
# --------------------------------------------------------------------------

def test_an_uncaveated_claim_is_found():
    assert "uncaveated-claim" in ids(bad_result())


def test_a_caveated_claim_is_not_flagged():
    assert "uncaveated-claim" not in ids(good_result())


def test_the_good_sample_actually_contains_a_headline_claim():
    """Vacuous if it does not, which is how the check above passed for a while."""
    assert good_result()["stats"]["headline_claims"] >= 1, "got %s" % (
        good_result()["stats"]["headline_claims"])


FAR_CAVEAT = ("# Tool\n\nTool does one thing well and does it fast.\n\n"
              "## Install\n\n```bash\npip install tool\n```\n\n"
              "## Benchmarks\n\nIt is 40% faster than the alternative.\n\n"
              "## FAQ\n\nWhy is it slow for me? Results vary.\n\n"
              "## License\n\nMIT.\n")

NEAR_CAVEAT = ("# Tool\n\nTool does one thing well and does it fast.\n\n"
               "## Install\n\n```bash\npip install tool\n```\n\n"
               "## Benchmarks\n\nIt is 40% faster than the alternative. "
               "That is measured on one machine and results vary with disk.\n\n"
               "## License\n\nMIT.\n")


def test_a_caveat_in_a_distant_section_does_not_launder_the_claim():
    """One "results vary" buried in an FAQ used to excuse every headline number
    in the header, and a caveat the reader never reaches beside the number is
    not a caveat."""
    scratch = tempfile.mkdtemp()
    try:
        result = run(written(scratch, "README.md", FAR_CAVEAT), "--no-voice")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert "uncaveated-claim" in ids(result), str(ids(result))


def test_a_caveat_in_the_claims_own_section_counts():
    scratch = tempfile.mkdtemp()
    try:
        result = run(written(scratch, "NEAR.md", NEAR_CAVEAT), "--no-voice")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert "uncaveated-claim" not in ids(result), str(ids(result))


def test_inconsistent_number_between_badge_and_heading_fires():
    """84 UI Styles vs Available Styles (67) should fire inconsistent-number."""
    text = (
        "# Project\n\n"
        "Project does one thing well and fast.\n\n"
        "![Styles](https://img.shields.io/badge/styles-84%20UI%20Styles-blue)\n\n"
        "## Install\n\n```sh\npip install x\n```\n\n"
        "## Available Styles (67)\n\nHere are the styles.\n\n"
        "## License\n\nMIT\n"
    )
    scratch = tempfile.mkdtemp()
    try:
        result = run(written(scratch, "README.md", text), "--no-voice")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert "inconsistent-number" in ids(result), str(ids(result))


def test_bare_url_overflow_caps_displayed_findings():
    """README with >20 bare URLs shouldn't overflow, caps properly."""
    urls = "\n".join("https://example.com/item/%d" % i for i in range(25))
    text = "# Project\n\nProject does something.\n\n## Install\n\n```sh\npip install x\n```\n\n## Links\n\n" + urls + "\n\n## License\n\nMIT\n"
    scratch = tempfile.mkdtemp()
    try:
        result = run(written(scratch, "README.md", text), "--no-voice")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert result["stats"]["bare_urls"] == 25
    bare_findings = [f for f in result["findings"] if f["id"] == "bare-url"]
    assert len(bare_findings) == 21

