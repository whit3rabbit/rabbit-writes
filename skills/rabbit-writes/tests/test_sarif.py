#!/usr/bin/env python3
"""
SARIF output: the uri-drop warning.

GitHub silently drops SARIF results whose artifactLocation.uri it cannot resolve
to a file in the checkout, and "silently" is the operative word: the upload
succeeds and nothing appears. warn_if_uri_drops says so on stderr for the uris
the two checkers default to (the raw --file, which may be absolute, and the
"stdin" placeholder) so the silent drop is surfaced rather than discovered when
a PR posts no annotations.
"""

import io

from rwlib import sarif


def test_an_absolute_or_stdin_uri_is_warned_about():
    # "/abs/..." is absolute on POSIX and on Windows (a root component), so the
    # assertion holds across the CI matrix without a drive-letter special case.
    for bad in ("/abs/path.md", "stdin", ""):
        buf = io.StringIO()
        sarif.warn_if_uri_drops(bad, out=buf)
        assert buf.getvalue(), "expected a drop warning for %r" % bad


def test_a_relative_uri_is_not_warned_about():
    buf = io.StringIO()
    sarif.warn_if_uri_drops("docs/README.md", out=buf)
    assert buf.getvalue() == "", buf.getvalue()
