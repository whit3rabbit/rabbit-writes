#!/usr/bin/env python3
"""
Shared fixtures and subprocess helpers for the README checker tests.

Same shape and same reasoning as the rabbit-writes suite: the expensive runs are
memoized, and test functions take no arguments so `run.py` can drive them
without pytest installed. See that file's helpers.py for why.

Stdlib only, 3.9+.
"""

import glob
import importlib.util
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "scripts", "readme_check.py")
SAMPLES = os.path.join(ROOT, "tests", "samples")
PLUGIN_ROOT = os.path.dirname(os.path.dirname(ROOT))
CORPUS_DIR = os.path.join(PLUGIN_ROOT, "docs", "readme-analysis", "repos")
ENGINE = os.path.join(PLUGIN_ROOT, "skills", "rabbit-writes", "scripts")

if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

# The corpus under docs/readme-analysis/repos is a snapshot committed with the
# study, so the band in test_corpus.py is a regression guard rather than a live
# measurement. Refetching it invalidates the band, which is why the count is
# asserted before the band is.
EXPECTED_CORPUS_READMES = 100

_CACHE = {}

# Every checker run happens from here rather than from wherever the suite was
# invoked. `resolve_voice` probes the working directory for a `.rabbit-voice`
# right after the README's own directory, so a repository that pins its own
# house voice would silently decide the result of every test below, and the
# failure would read as a bug in the checker. The samples directory has no pin
# and is not going to grow one.
NEUTRAL_CWD = SAMPLES


def run(path, *extra):
    """Parsed --json output. Raises on any exit code other than 0 or --check's 1."""
    key = ("run", path) + extra
    if key not in _CACHE:
        out = subprocess.run([sys.executable, CHECK, os.path.abspath(path),
                              "--json", *extra],
                             capture_output=True, text=True, cwd=NEUTRAL_CWD)
        if out.returncode not in (0, 1):
            raise SystemExit("readme_check failed on %s:\n%s" % (path, out.stderr))
        _CACHE[key] = json.loads(out.stdout)
    return _CACHE[key]


def run_code(path, *extra):
    """(parsed, exit code), for the documented --check contract."""
    out = subprocess.run([sys.executable, CHECK, os.path.abspath(path),
                          "--json", *extra],
                         capture_output=True, text=True, cwd=NEUTRAL_CWD)
    return json.loads(out.stdout), out.returncode


def check_module():
    if "module" not in _CACHE:
        spec = importlib.util.spec_from_file_location("rc_test", CHECK)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CACHE["module"] = module
    return _CACHE["module"]


def sample(name):
    return os.path.join(SAMPLES, name)


def good_result():
    return run(sample("good-readme.md"), "--no-voice")


def bad_result():
    return run(sample("bad-readme.md"), "--no-voice")


def ids(result, priority=None):
    return [f["id"] for f in result["findings"]
            if priority is None or f["priority"] == priority]


def total(result):
    return sum(result["counts"][k] for k in ("P0", "P1", "P2"))


def written(directory, name, body):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


def corpus_readmes():
    """[(slug, path)] for the committed snapshot, or [] when it is not here.

    The glob itself lives in rwlib.corpus, because the engine suite needs the
    same list now: CLAUDE.md requires every new detector to be calibrated
    against these 100 real third-party documents, and two copies of the locator
    is how two halves of one plugin end up disagreeing about what the corpus is.
    """
    if "corpus" not in _CACHE:
        from rwlib import corpus as corpus_mod
        _CACHE["corpus"] = corpus_mod.readme_paths()
    return _CACHE["corpus"]


def corpus_p0_slugs():
    if "corpus_p0" not in _CACHE:
        _CACHE["corpus_p0"] = [slug for slug, path in corpus_readmes()
                               if run(path, "--no-voice")["counts"]["P0"]]
    return _CACHE["corpus_p0"]
