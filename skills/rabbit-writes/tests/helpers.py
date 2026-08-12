#!/usr/bin/env python3
"""
Shared fixtures and subprocess helpers for the engine tests.

Everything expensive is memoized here rather than recomputed per test. Scanning
the calibration samples costs a subprocess each, and the old single-function
suite got that for free by running in one pass; splitting the file would have
made it slower without this.

Test functions take no arguments and call these directly, instead of declaring
pytest fixture parameters. That is a deliberate trade. Fixture injection is
nicer to read and it only works under pytest, and `run.py` exists so this suite
runs on a checkout with nothing installed, which is the same promise the scripts
themselves make. Memoized module functions are the one shape that behaves
identically in both.

Stdlib only, 3.9+.
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
SCAN = os.path.join(SCRIPTS, "scan.py")
VERIFY = os.path.join(SCRIPTS, "verify.py")
LEXICON = os.path.join(SCRIPTS, "lexicon.json")
PATTERNS_MD = os.path.join(ROOT, "references", "patterns.md")
CONTEXT_MD = os.path.join(ROOT, "references", "context.md")
SAMPLES = os.path.join(ROOT, "tests", "samples")
VOICES = os.path.join(ROOT, "voices")
WHIT3RABBIT_RULES = os.path.join(VOICES, "whit3rabbit.rules.json")

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

_CACHE = {}


def load_module(name, path):
    """Import a bundled script by path, the way the plugin host does."""
    key = ("module", name, path)
    if key not in _CACHE:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CACHE[key] = module
    return _CACHE[key]


def scan_module():
    return load_module("rw_scan_test", SCAN)


def verify_module():
    return load_module("rw_verify_test", VERIFY)


def lexicon():
    if "lexicon" not in _CACHE:
        with open(LEXICON, encoding="utf-8") as fh:
            _CACHE["lexicon"] = json.load(fh)
    return _CACHE["lexicon"]


# --------------------------------------------------------------------------
# running the CLI
# --------------------------------------------------------------------------

def scan_json(path, *extra):
    """Parsed --json output. Raises on a non-zero exit that is not --check's 1."""
    key = ("scan_json", path) + extra
    if key not in _CACHE:
        out = subprocess.run([sys.executable, SCAN, path, "--json", *extra],
                             capture_output=True, text=True, check=True)
        _CACHE[key] = json.loads(out.stdout)
    return _CACHE[key]


def scan_text(text, *extra):
    """Scan a string. Returns (parsed, exit code), so the documented --check
    contract can be asserted rather than assumed."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(text)
        path = fh.name
    try:
        out = subprocess.run([sys.executable, SCAN, path, "--json", *extra],
                             capture_output=True, text=True)
        return json.loads(out.stdout), out.returncode
    finally:
        os.unlink(path)


def scan_with_rules(text, rules, *extra):
    """Scan a string against an inline rules dict.

    Every mechanic in apply_voice_rules is reachable from a user-authored rules
    file, and the profiles this repo ships exercise one setting each. This lets
    the other branches be tested without inventing a voice to hold them.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".rules.json", delete=False,
                                     encoding="utf-8") as fh:
        json.dump(rules, fh)
        rules_path = fh.name
    try:
        return scan_text(text, "--voice-rules", rules_path, *extra)
    finally:
        os.unlink(rules_path)


def run_verify(original, rewritten, *extra):
    """(parsed, exit code) from verify.py over two strings."""
    paths = []
    try:
        for body in (original, rewritten):
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                             encoding="utf-8") as fh:
                fh.write(body)
                paths.append(fh.name)
        result = subprocess.run([sys.executable, VERIFY, paths[0], paths[1],
                                 "--json", *extra],
                                capture_output=True, text=True)
        return json.loads(result.stdout), result.returncode
    finally:
        for path in paths:
            os.unlink(path)


def written(directory, name, body):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


# --------------------------------------------------------------------------
# the calibration samples, scanned once
# --------------------------------------------------------------------------

def sample(name):
    return os.path.join(SAMPLES, name)


def ai_result():
    return scan_json(sample("ai-sample.md"))


def human_result():
    return scan_json(sample("human-sample.md"))


def metronomic_result():
    return scan_json(sample("metronomic-sample.md"))


def voice_ids(result):
    return [f["id"] for f in result["findings"] if f["band"] == "voice"]


def ids(result, priority=None):
    return [f["id"] for f in result["findings"]
            if priority is None or f["priority"] == priority]


def total(result):
    return sum(result["counts"][k] for k in ("P0", "P1", "P2"))


# --------------------------------------------------------------------------
# reading the reference documents
# --------------------------------------------------------------------------

def tier1_table_terms():
    """Every word in the section 12 replace-on-sight table of patterns.md."""
    with open(PATTERNS_MD, encoding="utf-8") as fh:
        md = fh.read()
    section = md.split("## 12. Tier-1 vocabulary")[1].split("\n## 13.")[0]
    terms = []
    for line in section.splitlines():
        if not line.startswith("|") or line.startswith("|---") or "| Replace |" in line:
            continue
        cell = re.sub(r"\*\([^)]*\)\*", "", line.split("|")[1])
        terms += [t.strip().strip("`").lower() for t in re.split(r"[/,]", cell) if t.strip()]
    return terms
