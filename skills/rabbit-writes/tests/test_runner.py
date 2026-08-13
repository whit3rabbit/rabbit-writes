#!/usr/bin/env python3
"""
The stdlib runner's empty-selection contract, pinned.

A `-k` keyword that matches no test used to exit 0, which is this suite's own
empty-is-loud rule unapplied to its runner: a typo'd filter looked like a green
run. `-k` as the last argument used to raise IndexError. Both are exit 2 now,
and this holds the line for both near-identical runners so a refactor of one
does not silently reintroduce the vacuous pass in the other.

Subprocess, on purpose. The runner discovers `test_*.py` in its own directory,
so a test that imports the runner and calls `main` in-process would be
collected and re-entered. A separate process with a keyword that matches
nothing runs no test functions and stays bounded.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RUNNERS = [
    os.path.join(HERE, "run.py"),
    os.path.join(REPO_ROOT, "skills", "readme-writing", "tests", "run.py"),
]


def _run(runner, *args):
    return subprocess.run([sys.executable, runner, *args],
                          capture_output=True, text=True)


def test_a_keyword_that_matches_nothing_is_loud_not_silent():
    for runner in RUNNERS:
        bare = _run(runner, "-k")
        assert bare.returncode == 2, "%s -k exited %d\n%s" % (
            runner, bare.returncode, bare.stderr)
        missed = _run(runner, "-k", "ZZZNOMATCHZZ")
        assert (missed.returncode == 2
                and "no tests matched" in missed.stderr), (
            "%s -k ZZZNOMATCHZZ exited %d\n%s"
            % (runner, missed.returncode, missed.stderr))
