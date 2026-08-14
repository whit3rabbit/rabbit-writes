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
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

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
_CACHE_LOCK = threading.Lock()

# Every checker run happens from here rather than from wherever the suite was
# invoked. `resolve_voice` probes the working directory for a `.rabbit-voice`
# right after the README's own directory, so a repository that pins its own
# house voice would silently decide the result of every test below, and the
# failure would read as a bug in the checker. The samples directory has no pin
# and is not going to grow one.
NEUTRAL_CWD = SAMPLES


class Repo(object):
    """A throwaway directory with a `.git` in it, so the walk finds a root.

    Without the marker the walk runs to the filesystem root and the answer
    depends on whoever ran the suite.
    """

    def __init__(self, readme, license_name=None):
        self.path = tempfile.mkdtemp(prefix="rabbit-license-")
        os.mkdir(os.path.join(self.path, ".git"))
        self.readme = os.path.join(self.path, "README.md")
        with open(self.readme, "w", encoding="utf-8") as fh:
            fh.write(readme)
        if license_name:
            with open(os.path.join(self.path, license_name), "w",
                      encoding="utf-8") as fh:
                fh.write("MIT License\n\nCopyright (c) 2026\n")

    def sub(self, name, readme):
        """A README one directory down, the `docs/README.md` case."""
        directory = os.path.join(self.path, name)
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "README.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(readme)
        return path

    def close(self):
        shutil.rmtree(self.path, ignore_errors=True)


def run(path, *extra):
    """Parsed --json output. Raises on any exit code other than 0 or --check's 1."""
    key = ("run", path) + extra
    with _CACHE_LOCK:
        if key in _CACHE:
            return _CACHE[key]
    out = subprocess.run([sys.executable, CHECK, os.path.abspath(path),
                          "--json", *extra],
                         capture_output=True, text=True, cwd=NEUTRAL_CWD)
    if out.returncode not in (0, 1):
        raise RuntimeError("readme_check failed on %s:\n%s" % (path, out.stderr))
    res = json.loads(out.stdout)
    with _CACHE_LOCK:
        _CACHE[key] = res
    return res


def run_code(path, *extra):
    """(parsed, exit code), for the documented --check contract."""
    out = subprocess.run([sys.executable, CHECK, os.path.abspath(path),
                          "--json", *extra],
                         capture_output=True, text=True, cwd=NEUTRAL_CWD)
    return json.loads(out.stdout), out.returncode


def check_module():
    with _CACHE_LOCK:
        if "module" in _CACHE:
            return _CACHE["module"]
    spec = importlib.util.spec_from_file_location("rc_test", CHECK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with _CACHE_LOCK:
        _CACHE["module"] = module
    return module


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
    with _CACHE_LOCK:
        if "corpus" in _CACHE:
            return _CACHE["corpus"]
    try:
        from rwlib import corpus as corpus_mod
        res = corpus_mod.readme_paths()
    except ImportError:
        res = []
    with _CACHE_LOCK:
        _CACHE["corpus"] = res
    return res


def corpus_p0_slugs():
    with _CACHE_LOCK:
        if "corpus_p0" in _CACHE:
            return _CACHE["corpus_p0"]
    readmes = corpus_readmes()
    workers = min(32, (os.cpu_count() or 2) * 4)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda item: (item[0], run(item[1], "--no-voice")["counts"]["P0"]), readmes))
    res = [slug for slug, count in results if count]
    with _CACHE_LOCK:
        _CACHE["corpus_p0"] = res
    return res


