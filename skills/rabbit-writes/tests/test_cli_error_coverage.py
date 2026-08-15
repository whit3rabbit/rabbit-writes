"""
test_cli_error_coverage.py - Integration tests ensuring CLI entry points emit structured LLM error guidance on invalid arguments.
"""

import os
import subprocess
import sys

from helpers import ROOT

REPO_ROOT = os.path.dirname(os.path.dirname(ROOT))
SKILLS = os.path.join(REPO_ROOT, "skills")



def run_cmd(*args):
    proc = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def test_precommit_cli_error():
    script = os.path.join(REPO_ROOT, "scripts", "precommit.py")
    code, stdout, stderr = run_cmd(script)
    assert code == 2
    assert "CLI ERROR:" in stderr
    assert "precommit.py" in stderr
    assert "VALID USAGE EXAMPLES:" in stderr


def test_build_voice_cli_error():
    script = os.path.join(SKILLS, "voice-setup", "scripts", "build_voice.py")
    code, stdout, stderr = run_cmd(script, "--scaffold")
    assert code == 2
    assert "CLI ERROR:" in stderr
    assert "build_voice.py" in stderr
    assert "VALID USAGE EXAMPLES:" in stderr


def test_add_sample_cli_error():
    script = os.path.join(REPO_ROOT, "scripts", "detector-corpus", "add_sample.py")
    code, stdout, stderr = run_cmd(script)
    assert code == 2
    assert "CLI ERROR:" in stderr
    assert "add_sample.py" in stderr


def test_score_cli_error():
    script = os.path.join(REPO_ROOT, "scripts", "detector-corpus", "score.py")
    code, stdout, stderr = run_cmd(script, "--band", "INVALID")
    assert code == 2
    assert "CLI ERROR:" in stderr
    assert "score.py" in stderr


def test_fetch_samples_cli_error():
    script = os.path.join(REPO_ROOT, "scripts", "detector-corpus", "fetch_samples.py")
    code, stdout, stderr = run_cmd(script, "--id", "nonexistent_sample_xyz")
    assert code == 1
    assert "CLI ERROR:" in stderr
    assert "fetch_samples.py" in stderr


def test_reconstruct_cli_error():
    script = os.path.join(REPO_ROOT, "scripts", "voice-eval", "reconstruct.py")
    code, stdout, stderr = run_cmd(script, "--manifest", "nonexistent_manifest.json")
    assert code == 2
    assert "FILE / I/O ERROR:" in stderr
    assert "reconstruct.py" in stderr

