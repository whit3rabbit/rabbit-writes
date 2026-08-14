#!/usr/bin/env python3
"""
Shared test helpers for voice-setup.
"""

import json
import os
import subprocess
import sys
import tempfile

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")

BUILD_VOICE = os.path.join(SCRIPTS_DIR, "build_voice.py")
MEASURE_VOICE = os.path.join(SCRIPTS_DIR, "measure_voice.py")
LEARN_EDITS = os.path.join(SCRIPTS_DIR, "learn_edits.py")

RW_VOICES_DIR = os.path.abspath(os.path.join(SKILL_DIR, "..", "rabbit-writes", "voices"))

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def run_cmd(cmd, *args):
    """Run a CLI command and return (stdout, stderr, returncode)."""
    res = subprocess.run([sys.executable, cmd, *args],
                         capture_output=True, text=True)
    return res.stdout, res.stderr, res.returncode


def create_temp_file(content, suffix=".md"):
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as fh:
        fh.write(content)
        return fh.name
