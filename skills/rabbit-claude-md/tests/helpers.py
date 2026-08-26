#!/usr/bin/env python3
"""
Shared fixtures and subprocess helpers for the CLAUDE.md checker tests.

Same shape and same reasoning as the rabbit-readme-improver suite: the
expensive runs are memoized, and test functions take no arguments so
`run.py` can drive them without pytest installed.

Stdlib only, 3.9+.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
CHECK = os.path.join(SCRIPTS, "claude_check.py")
SAMPLES = os.path.join(ROOT, "tests", "samples")
PLUGIN_ROOT = os.path.dirname(os.path.dirname(ROOT))
ENGINE = os.path.join(PLUGIN_ROOT, "skills", "rabbit-writes", "scripts")

for entry in (SCRIPTS, ENGINE):
    if entry not in sys.path:
        sys.path.insert(0, entry)

_CACHE = {}
_CACHE_LOCK = threading.Lock()

# Every checker run happens from here rather than from wherever the suite was
# invoked, so a repository pinning its own `.rabbit-voice` cannot decide the
# result of a test. The samples directory has no pin and is not growing one.
NEUTRAL_CWD = SAMPLES


class Tree(object):
    """A throwaway directory tree with an optional `.git` marker.

    The dead-path, duplicate, and discovery checks all depend on what exists
    on disk around the file, so their fixtures are built here rather than
    committed as samples whose truth would depend on this repository's own
    layout.
    """

    def __init__(self, files, git=True):
        self.path = tempfile.mkdtemp(prefix="rabbit-claude-md-")
        if git:
            os.mkdir(os.path.join(self.path, ".git"))
        for rel, body in files.items():
            full = os.path.join(self.path, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(body)

    def file(self, rel):
        return os.path.join(self.path, rel)

    def close(self):
        shutil.rmtree(self.path, ignore_errors=True)


def run_raw(path, *extra, cwd=None):
    """(stdout, stderr, exit code), no parsing and no cache."""
    out = subprocess.run([sys.executable, CHECK, path, *extra],
                         capture_output=True, text=True,
                         cwd=cwd or NEUTRAL_CWD)
    return out.stdout, out.stderr, out.returncode


def run(path, *extra):
    """Parsed --json output. Raises on any exit code other than 0 or --check's 1."""
    key = ("run", path) + extra
    with _CACHE_LOCK:
        if key in _CACHE:
            return _CACHE[key]
    stdout, stderr, code = run_raw(os.path.abspath(path), "--json", *extra)
    if code not in (0, 1):
        raise RuntimeError("claude_check failed on %s:\n%s" % (path, stderr))
    res = json.loads(stdout)
    with _CACHE_LOCK:
        _CACHE[key] = res
    return res


def run_code(path, *extra):
    """(parsed, exit code), for the documented --check contract."""
    stdout, stderr, code = run_raw(os.path.abspath(path), "--json", *extra)
    return json.loads(stdout) if stdout.strip() else None, code


def check_module():
    with _CACHE_LOCK:
        if "module" in _CACHE:
            return _CACHE["module"]
    spec = importlib.util.spec_from_file_location("cc_test", CHECK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with _CACHE_LOCK:
        _CACHE["module"] = module
    return module


def sample(name):
    return os.path.join(SAMPLES, name)


def all_findings(result):
    """Every finding across every file in a --json payload."""
    return [f for entry in result["files"] for f in entry["findings"]]


def ids(result, prefix=None):
    out = [f["id"] for f in all_findings(result)]
    if prefix:
        out = [i for i in out if i.startswith(prefix)]
    return out


def structure_ids(result):
    return ids(result, prefix="claudemd-")
