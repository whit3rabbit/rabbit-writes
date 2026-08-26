#!/usr/bin/env python3
"""
Tests for recent improvements:
- Centered header layout with banner, tagline, badges, and inline dot-separated TOC
- HTML badge alt text participating in inconsistent-number check
- Bare URL check ignoring URLs in HTML comments
- Singular/plural normalization for invariant nouns and -es endings
- HTML anchor navigation TOC detection
"""

import os
import shutil
import tempfile

from helpers import Repo, check_module, ids, run, sample, written


def repo_root():
    path = tempfile.mkdtemp()
    os.mkdir(os.path.join(path, ".git"))
    with open(os.path.join(path, "LICENSE"), "w", encoding="utf-8") as fh:
        fh.write("MIT License\n\nCopyright (c) 2026\n")
    return path


CENTERED_BANNER_README = """<div align="center">

<img src="assets/banner.png" alt="widget logo" width="600">

# widget

Convert images in bulk without configuration.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/widget.svg)](https://pypi.org/project/widget/)

[Install](#install) • [Usage](#usage) • [License](#license)

</div>

widget is an automated batch image processor.

## Install

```bash
pip install widget
```

## Usage

```bash
widget input/ output/
```

## License

MIT.
"""


def test_centered_banner_and_inline_toc_are_clean():
    """A centered header with a banner image, title, tagline, badge row, and
    inline dot-separated navigation TOC should parse cleanly with no P0/P1."""
    scratch = repo_root()
    try:
        path = written(scratch, "README.md", CENTERED_BANNER_README)
        result = run(path, "--no-voice")
        assert result["counts"]["P0"] == 0, ids(result, "P0")
        assert result["counts"]["P1"] == 0, ids(result, "P1")
        assert result["stats"]["badge_count"] == 2
        assert result["stats"]["has_toc"] is True
        assert result["stats"]["pitch_line"] == 7  # "Convert images in bulk..."
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


HTML_BADGE_INCONSISTENCY_README = """# widget

<div align="center">
<img src="https://img.shields.io/badge/styles-84_styles-green" alt="84 Styles">
</div>

Widget formats stylesheets in bulk without configuration.

## Install

```bash
pip install widget
```

## 67 Styles available

Here are the details.

## License

MIT.
"""


def test_html_badge_alt_text_participates_in_inconsistent_number_check():
    """HTML <img alt="..."> badges in centered headers must be inspected for
    number inconsistencies with headings."""
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "README.md", HTML_BADGE_INCONSISTENCY_README)
        result = run(path, "--no-voice")
        assert "inconsistent-number" in ids(result), ids(result)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


COMMENTED_URL_README = """# widget

Widget formats stylesheets without overhead.

<!-- Internal reference: https://internal.company.dev/specs/widget -->
<!-- See https://example.com/notes for maintainer docs -->

## Install

```bash
pip install widget
```

## License

MIT.
"""


def test_urls_in_html_comments_do_not_trigger_bare_url():
    """URLs inside HTML comments are maintainer notes, not public reader links."""
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "README.md", COMMENTED_URL_README)
        result = run(path, "--no-voice")
        assert "bare-url" not in ids(result), ids(result)
        assert result["stats"]["bare_urls"] == 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_singular_preserves_invariant_nouns_and_collides_es_plurals():
    """Nouns ending in s should not have their s stripped, and plurals with -es
    should collide with their base."""
    singular = check_module()._singular
    assert singular("status") == "status"
    assert singular("statuses") == "status"
    assert singular("alias") == "alias"
    assert singular("aliases") == "alias"
    assert singular("bus") == "bus"
    assert singular("buses") == "bus"
    assert singular("canvas") == "canvas"
    assert singular("canvases") == "canvas"
    assert singular("lens") == "lens"
    assert singular("lenses") == "lens"
    assert singular("basis") == "basis"
    assert singular("series") == "series"
    assert singular("species") == "species"
    assert singular("release") == "release"
    assert singular("releases") == "release"


HTML_ANCHOR_TOC_README = """# Large Project

A long documentation document.

<a href="#install">Install</a> | <a href="#usage">Usage</a> | <a href="#license">License</a>

## Install

```bash
pip install widget
```

## Usage

```bash
widget run
```

## License

MIT.
"""


def test_html_anchor_links_count_as_toc():
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "README.md", HTML_ANCHOR_TOC_README)
        result = run(path, "--no-voice")
        assert result["stats"]["has_toc"] is True
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


CODE_FIRST_PITCH_README = """# Pipeline Tool

```
+---------+     +---------+
|  Input  | --> | Output  |
+---------+     +---------+
```

Pipeline Tool processes streams of binary records in real time.

## Install

```sh
pip install pipeline
```

## License

MIT.
"""


def test_pitch_scan_skips_initial_code_block():
    """Fenced code blocks opening a README before prose description do not
    corrupt the pitch scan."""
    scratch = repo_root()
    try:
        path = written(scratch, "README.md", CODE_FIRST_PITCH_README)
        result = run(path, "--no-voice")
        assert result["stats"]["pitch_line"] == 9, result["stats"]["pitch_line"]
        assert "no-pitch" not in ids(result)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


SEMVER_AND_YEAR_README = """# Widget Project

Widget formats files in bulk safely.

## 1.2.0 Release

Improvements in 2025 Roadmap.

## 1.3.1 Release

Plans for 2026 Roadmap.

## Install

```sh
pip install widget
```

## License

MIT.
"""


def test_semver_and_years_do_not_trigger_inconsistent_number():
    """Semver segments and 4-digit year numbers do not trip inconsistent-number."""
    scratch = repo_root()
    try:
        path = written(scratch, "README.md", SEMVER_AND_YEAR_README)
        result = run(path, "--no-voice")
        assert "inconsistent-number" not in ids(result), ids(result)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


SCATTERED_ANCHORS_README = """# Small Project

Small Project processes data easily.

See details [above](#install) for prerequisites.

## Install

```sh
pip install widget
```

Check out our [examples](#usage) for more details.

## Usage

```sh
widget run
```

Refer to the [terms](#license) for rights.

## License

MIT.
"""


def test_scattered_anchors_do_not_count_as_toc():
    """Scattered anchor links throughout a file do not count as a TOC."""
    scratch = repo_root()
    try:
        path = written(scratch, "README.md", SCATTERED_ANCHORS_README)
        result = run(path, "--no-voice")
        assert result["stats"]["has_toc"] is False
        assert "toc-unneeded" not in ids(result)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


BACKTICK_CLAIM_README = """# Fast Converter

Fast Converter converts image files quickly.

Documenting the benchmark output string: `40% faster` than baseline.

## Install

```sh
pip install converter
```

## License

MIT.
"""


def test_claims_inside_inline_backticks_are_ignored():
    """Claims written inside backticks are ignored when checking headline claims."""
    scratch = repo_root()
    try:
        path = written(scratch, "README.md", BACKTICK_CLAIM_README)
        result = run(path, "--no-voice")
        assert "uncaveated-claim" not in ids(result), ids(result)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


VAGUE_LINK_PUNCTUATION_README = """# Fast Converter

Fast Converter converts image files quickly.

Want to learn more? Check out our docs [read more?](https://example.com/docs).

## Install

```sh
pip install converter
```

## License

MIT.
"""


def test_vague_link_text_strips_punctuation():
    """Vague link text with trailing question mark or ellipsis is detected."""
    scratch = repo_root()
    try:
        path = written(scratch, "README.md", VAGUE_LINK_PUNCTUATION_README)
        result = run(path, "--no-voice")
        assert "vague-link-text" in ids(result), ids(result)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)



def test_no_ste_runs_and_silences_the_readability_caps():
    """--no-ste crashed for a release: scan.scan's ste= tri-state raises on
    the None the flag used to pass, and nothing ran the flag. The half worth
    pinning is that the run completes and no ste- id survives."""
    result = run(sample("good-readme.md"), "--no-voice", "--no-ste")
    assert not any(i.startswith("ste-") for i in ids(result)), ids(result)
