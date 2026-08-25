#!/usr/bin/env python3
"""
The host installer, against a throwaway HOME.

This is the one script in the plugin that writes outside its own tree, into a
file the user has their own settings in. So the tests that matter are not the
ones proving the install worked. They are the ones proving it did not take
anything else with it:

  - a settings file it could not parse is never rewritten
  - unrelated keys, and the user's own hooks, survive the round-trip
  - `--uninstall` restores the previous `outputStyle` rather than dropping it
  - a second `--install` is a no-op, not a duplicate hook entry
  - `--dry-run` writes nothing at all
  - a style file edited by hand blocks the uninstall

Every case runs with HOME pointed at a temporary directory, so nothing here can
reach the machine's real configuration even if the script is wrong.

Stdlib only, 3.9+. Tests take no arguments.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SKILL = os.path.dirname(HERE)
INSTALL_HOST = os.path.join(SKILL, "scripts", "install_host.py")
REPO = os.path.dirname(os.path.dirname(SKILL))

BASE_SETTINGS = {
    "model": "opus",
    "env": {"FOO": "bar"},
    "hooks": {
        "PostToolUse": [
            {"matcher": "Bash",
             "hooks": [{"type": "command", "command": "echo mine"}]}
        ]
    },
    "outputStyle": "Explanatory",
}


class home(object):
    """A temporary HOME with a settings.json in it, and the repo as cwd.

    cwd is the repository because that is where the root `.rabbit-voice`
    lives, so a voice resolves and the generated style is part of what gets
    tested. A test that ran from an empty directory would exercise the
    baseline-only path and quietly stop covering the interesting one.
    """

    def __init__(self, settings=None):
        self.settings = BASE_SETTINGS if settings is None else settings

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="rw-host-")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(self.claude)
        if self.settings is not None:
            self.write_settings(self.settings)
        return self

    def __exit__(self, *exc):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        return False

    @property
    def settings_path(self):
        return os.path.join(self.claude, "settings.json")

    def write_settings(self, data):
        with open(self.settings_path, "w", encoding="utf-8") as fh:
            if isinstance(data, str):
                fh.write(data)
            else:
                fh.write(json.dumps(data, indent=2) + "\n")

    def read_settings(self):
        with open(self.settings_path, encoding="utf-8") as fh:
            return json.load(fh)

    def files(self):
        out = []
        for root, _dirs, names in os.walk(self.claude):
            for name in names:
                out.append(os.path.relpath(os.path.join(root, name),
                                           self.claude))
        return sorted(out)

    def run(self, *args):
        env = dict(os.environ)
        env["HOME"] = self.tmp
        env.pop("USERPROFILE", None)
        proc = subprocess.run([sys.executable, INSTALL_HOST] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              cwd=REPO, env=env)
        return proc.stdout.decode("utf-8"), proc.returncode


def test_dry_run_writes_nothing():
    with home() as h:
        before = h.files()
        out, code = h.run("--install", "--dry-run")
        assert code == 0, out
        assert "nothing was written" in out, out
        assert h.files() == before, h.files()
        assert h.read_settings() == BASE_SETTINGS


def test_install_writes_exactly_what_it_announced():
    with home() as h:
        out, code = h.run("--install")
        assert code == 0, out
        announced = sorted(line.split(":", 1)[1].strip()
                           for line in out.splitlines()
                           if line.startswith("write:"))
        for path in announced:
            assert os.path.exists(path), "announced but not written: %s" % path
        assert h.files() == sorted([
            "output-styles/rabbit-whit3rabbit.md",
            "output-styles/rabbit-writes.md",
            "rabbit-writes-host.json",
            "settings.json",
            "settings.json.rabbit-bak",
        ]), h.files()


def test_unrelated_settings_survive():
    """The whole reason this is a merge and not a write."""
    with home() as h:
        out, code = h.run("--install")
        assert code == 0, out
        data = h.read_settings()
        assert data["model"] == "opus", data
        assert data["env"] == {"FOO": "bar"}, data
        bash = [g for g in data["hooks"]["PostToolUse"]
                if g.get("matcher") == "Bash"]
        assert len(bash) == 1, data["hooks"]
        assert bash[0]["hooks"][0]["command"] == "echo mine", bash


def test_a_second_install_adds_no_second_hook():
    with home() as h:
        h.run("--install")
        out, code = h.run("--install")
        assert code == 0, out
        assert "already installed" in out, out
        data = h.read_settings()
        ours = [g for g in data["hooks"]["PostToolUse"]
                if g.get("matcher") == "Write|Edit"]
        assert len(ours) == 1, data["hooks"]
        assert len(data["hooks"]["SessionStart"]) == 1, data["hooks"]


def test_a_second_install_does_not_forget_the_original_output_style():
    """The trap. Recording the style set by the first install as "what was
    there before" makes the uninstall a no-op that looks like it worked."""
    with home() as h:
        h.run("--install")
        h.run("--install")
        with open(os.path.join(h.claude, "rabbit-writes-host.json"),
                  encoding="utf-8") as fh:
            side = json.load(fh)
        assert side["previous_output_style"] == "Explanatory", side


def test_uninstall_restores_the_settings_byte_for_byte():
    with home() as h:
        original = h.read_settings()
        h.run("--install")
        out, code = h.run("--uninstall")
        assert code == 0, out
        assert h.read_settings() == original, h.read_settings()
        assert h.files() == ["settings.json", "settings.json.rabbit-bak"], \
            h.files()


def test_uninstall_with_no_previous_style_drops_the_key():
    """Setting it back to a value nobody chose would be as wrong as leaving
    ours in place."""
    with home({"model": "opus"}) as h:
        h.run("--install")
        assert "outputStyle" in h.read_settings()
        h.run("--uninstall")
        assert "outputStyle" not in h.read_settings(), h.read_settings()


def test_a_hand_edited_style_blocks_the_uninstall():
    """Somebody's edits to their own style file are theirs, and --force is the
    way to say otherwise."""
    with home() as h:
        h.run("--install")
        target = os.path.join(h.claude, "output-styles", "rabbit-writes.md")
        with open(target, "a", encoding="utf-8") as fh:
            fh.write("\nmy own rule\n")
        out, code = h.run("--uninstall")
        assert code == 2, out
        assert "edited" in out, out
        assert os.path.exists(target), "refused and deleted it anyway"
        out, code = h.run("--uninstall", "--force")
        assert code == 0, out
        assert not os.path.exists(target), out


def test_an_unparseable_settings_file_is_never_rewritten():
    """Overwriting a file this script could not read discards whatever the
    user had in it, and "it was broken already" is not a defence when the
    backup is written from the same read."""
    with home("{ not json\n") as h:
        out, code = h.run("--install")
        assert code == 2, out
        with open(h.settings_path, encoding="utf-8") as fh:
            assert fh.read() == "{ not json\n"
        assert h.files() == ["settings.json"], h.files()


def test_status_reports_a_hand_edited_file():
    with home() as h:
        h.run("--install")
        target = os.path.join(h.claude, "output-styles", "rabbit-writes.md")
        with open(target, "a", encoding="utf-8") as fh:
            fh.write("x\n")
        out, code = h.run("--status")
        assert code == 0, out
        assert "edited by hand" in out, out


def test_status_on_a_clean_home_says_nothing_is_installed():
    with home() as h:
        out, code = h.run("--status")
        assert code == 0, out
        assert "installed: no" in out, out


def test_the_generated_style_is_the_active_voice():
    with home() as h:
        h.run("--install")
        path = os.path.join(h.claude, "output-styles",
                            "rabbit-whit3rabbit.md")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        assert 'name: "Rabbit: whit3rabbit"' in text, text[:200]
        assert "keep-coding-instructions: true" in text, text[:200]
        assert h.read_settings()["outputStyle"] == "Rabbit: whit3rabbit"


def test_the_hook_command_points_at_a_file_that_exists():
    """A settings entry naming a path that is not there is a hook the host
    reports as failing on every single event."""
    with home() as h:
        h.run("--install")
        data = h.read_settings()
        command = data["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        target = command.split(" ", 1)[1].strip().strip('"')
        assert os.path.isfile(target), command
