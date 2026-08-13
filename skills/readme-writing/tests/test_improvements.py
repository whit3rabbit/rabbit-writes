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

from helpers import check_module, ids, run, written


def repo_root():
    """A throwaway directory that looks like a checkout: a `.git` marker so the
    license walk stops here, and a LICENSE for it to find.

    Only the tests that assert a clean result need it. Without the marker the
    walk runs to the filesystem root and the answer depends on whoever ran the
    suite, and without the file `license-file-missing` fires on a README that
    has nothing wrong with it. Same reasoning as `Repo` in test_license_file.py,
    which is where this pattern already lives for the tests that are about the
    license check itself.
    """
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
