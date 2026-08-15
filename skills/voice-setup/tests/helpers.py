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
AUDIT_VOICE = os.path.join(SCRIPTS_DIR, "audit_voice.py")

RW_SKILL_DIR = os.path.abspath(os.path.join(SKILL_DIR, "..", "rabbit-writes"))
RW_VOICES_DIR = os.path.join(RW_SKILL_DIR, "voices")
ENGINE = os.path.join(RW_SKILL_DIR, "scripts")

# The engine directory as well as this skill's own, so a test here can reach
# rwlib the same way build_voice.py does. Without it the scripts under test can
# import rwlib and the tests covering them cannot, which reads as rwlib being
# private to one skill.
for _path in (SCRIPTS_DIR, ENGINE):
    if _path not in sys.path:
        sys.path.insert(0, _path)


def run_cmd(cmd, *args):
    """Run a CLI command and return (stdout, stderr, returncode)."""
    res = subprocess.run([sys.executable, cmd, *args],
                         capture_output=True, text=True)
    return res.stdout, res.stderr, res.returncode


def create_temp_file(content, suffix=".md"):
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as fh:
        fh.write(content)
        return fh.name
