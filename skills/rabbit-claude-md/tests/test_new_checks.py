"""The dogfooding-round additions: forward-state tells, over-verification,
the missing-intro check, effective-size accounting through @imports, dead
slash-command references, and the three root-file notes (map coverage,
harness inventory, git currency).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

from helpers import Tree, check_module, run, sample


def test_no_intro_fires_on_a_bare_title_and_clean_sample_is_quiet():
    tree = Tree({"CLAUDE.md": "# t\n\n## Commands\n\n- do the thing\n"})
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        ids = [f["id"] for e in result["files"] for f in e["findings"]]
        assert "claudemd-no-intro" in ids, ids
    finally:
        tree.close()

    tree2 = Tree({"CLAUDE.md": "# t\n\nA short sentence saying what this is.\n"})
    try:
        result2 = run(tree2.file("CLAUDE.md"), "--no-voice")
        ids2 = [f["id"] for e in result2["files"] for f in e["findings"]]
        assert "claudemd-no-intro" not in ids2, ids2
    finally:
        tree2.close()


def test_todo_marker_and_session_state_fire_as_evidence():
    body = ("# t\n\nWhat this is, in one line.\n\n"
            "## Notes\n\n"
            "- TODO: wire up the retry path.\n"
            "- Roadmap: support Windows next quarter.\n"
            "- FIXME later.\n")
    tree = Tree({"CLAUDE.md": body})
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        findings = [f for e in result["files"] for f in e["findings"]]
        todo = [f for f in findings if f["id"] == "claudemd-todo-marker"]
        state = [f for f in findings if f["id"] == "claudemd-session-state"]
        assert len(todo) == 2, todo   # TODO and FIXME
        assert len(state) == 1, state  # "Roadmap:"
        assert all(f["priority"] == "P2" for f in todo + state)
    finally:
        tree.close()


def test_over_verification_tells_fire_and_clean_sample_is_quiet():
    body = ("# t\n\nWhat this is, in one line.\n\n"
            "## Rules\n\n"
            "- Always double-check your output before finishing.\n"
            "- Be extremely careful with destructive commands.\n")
    tree = Tree({"CLAUDE.md": body})
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        ids = [f["id"] for e in result["files"] for f in e["findings"]]
        assert ids.count("claudemd-over-verify") == 2, ids
    finally:
        tree.close()

    clean = run(sample("clean-claude.md"), "--no-voice")
    clean_ids = [f["id"] for e in clean["files"] for f in e["findings"]]
    assert "claudemd-over-verify" not in clean_ids


def test_import_cost_fires_only_when_own_size_passes_but_effective_fails():
    mod = check_module()
    p2 = mod.LIMITS["size_lines_p2"]
    small_body = "# t\n\nWhat this is.\n\n@docs/big.md\n"
    big_body = "\n".join("line %d of imported depth" % i for i in range(p2 + 50))
    tree = Tree({"CLAUDE.md": small_body, "docs/big.md": big_body})
    try:
        own_only = len([l for l in small_body.splitlines() if l.strip()])
        assert own_only <= p2, "the fixture's own size must stay under the cap"
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        findings = [f for e in result["files"] for f in e["findings"]]
        cost = [f for f in findings if f["id"] == "claudemd-import-cost"]
        assert cost, findings
        oversize = [f for f in findings if f["id"] == "claudemd-oversize"]
        assert oversize == [], (
            "claudemd-oversize reads the file's own size and must stay "
            "quiet here, or the two checks would be reporting the same "
            "thing twice", oversize)
    finally:
        tree.close()


def test_import_cost_is_quiet_when_nothing_is_imported_or_own_size_already_fails():
    mod = check_module()
    p1 = mod.LIMITS["size_lines_p1"]
    tree = Tree({"CLAUDE.md": "# t\n\nWhat this is.\n"})
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        findings = [f for e in result["files"] for f in e["findings"]]
        assert not any(f["id"] == "claudemd-import-cost" for f in findings)
    finally:
        tree.close()

    oversize_body = "\n".join("line %d" % i for i in range(p1 + 10))
    tree2 = Tree({"CLAUDE.md": oversize_body})
    try:
        result2 = run(tree2.file("CLAUDE.md"), "--no-voice")
        findings2 = [f for e in result2["files"] for f in e["findings"]]
        assert not any(f["id"] == "claudemd-import-cost" for f in findings2), (
            "a file already oversized on its own has nothing new to say "
            "about import cost", findings2)
        assert any(f["id"] == "claudemd-oversize" for f in findings2)
    finally:
        tree2.close()


def test_import_cost_respects_the_hop_limit_and_does_not_loop_on_a_cycle():
    mod = check_module()
    # Two files importing each other: a naive recursion never returns.
    tree = Tree({
        "CLAUDE.md": "# t\n\nWhat this is.\n\n@docs/b.md\n",
        "docs/b.md": "@../CLAUDE.md\nsome content\n",
    })
    try:
        with open(tree.file("CLAUDE.md"), encoding="utf-8") as fh:
            raw = fh.read()
        own, total = mod.effective_size(raw, tree.path)
        assert total >= own  # returns at all, rather than hanging
    finally:
        tree.close()


def test_char_budget_can_fire_independent_of_line_count():
    mod = check_module()
    p1 = mod.LIMITS["char_budget_p1"]
    # Few lines, each very long: clears size_lines_p2 by a wide margin, but
    # the raw character count crosses the budget on its own.
    body = "\n".join("x" * (p1 // 3) for _ in range(4))
    tree = Tree({"CLAUDE.md": body})
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        findings = [f for e in result["files"] for f in e["findings"]]
        assert any(f["id"] == "claudemd-char-budget" for f in findings), findings
        assert not any(f["id"] == "claudemd-oversize" for f in findings), (
            "only 4 non-blank lines: the line-count band must stay quiet",
            findings)
    finally:
        tree.close()


def test_dead_command_ref_fires_only_when_commands_dir_exists():
    tree = Tree({
        "CLAUDE.md": "# t\n\nWhat this is.\n\nRun `/deploy` when ready.\n",
        ".claude/commands/other.md": "# other\n",
    })
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        findings = [f for e in result["files"] for f in e["findings"]]
        dead = [f for f in findings if f["id"] == "claudemd-dead-command"]
        assert len(dead) == 1 and dead[0]["match"] == "/deploy", dead
    finally:
        tree.close()

    tree2 = Tree({"CLAUDE.md": "# t\n\nWhat this is.\n\nRun `/deploy`.\n"})
    try:
        result2 = run(tree2.file("CLAUDE.md"), "--no-voice")
        findings2 = [f for e in result2["files"] for f in e["findings"]]
        assert not any(f["id"] == "claudemd-dead-command" for f in findings2), (
            "no .claude/commands/ means the convention is not in use here",
            findings2)
    finally:
        tree2.close()


def test_map_coverage_note_only_covers_the_root_file():
    tree = Tree({
        "CLAUDE.md": "# t\n\nWhat this is.\n",
        "pkg/lib/x.py": "",
        "pkg/CLAUDE.md": "# pkg\n\nWhat this module is.\n",
    })
    try:
        result = run(tree.path, "--no-voice")
        by_file = {e["file"]: e for e in result["files"]}
        root_notes = by_file["CLAUDE.md"]["notes"]
        assert any("pkg" in n and "top-level" in n for n in root_notes), root_notes
        module_notes = by_file[os.path.join("pkg", "CLAUDE.md")]["notes"]
        assert not any("top-level" in n for n in module_notes), (
            "a nested module file is not the root and gets no map-coverage "
            "note", module_notes)
    finally:
        tree.close()


def test_harness_inventory_note_reports_what_exists():
    tree = Tree({
        "CLAUDE.md": "# t\n\nWhat this is.\n",
        ".claude/settings.json": "{}",
        ".claude/commands/deploy.md": "# deploy\n",
        ".mcp.json": '{"mcpServers": {"a": {}, "b": {}}}',
    })
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        notes = result["files"][0]["notes"]
        joined = " ".join(notes)
        assert ".claude/settings.json" in joined, notes
        assert ".mcp.json (2 server(s))" in joined, notes
        assert ".claude/commands/ (1)" in joined, notes
    finally:
        tree.close()


def test_harness_inventory_is_silent_with_nothing_to_report():
    tree = Tree({"CLAUDE.md": "# t\n\nWhat this is.\n"})
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        notes = result["files"][0]["notes"]
        assert not any("harness config" in n for n in notes), notes
    finally:
        tree.close()


def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, check=True,
                   capture_output=True, text=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t.co",
                            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t.co"))


def test_git_currency_note_on_a_real_repo_and_silent_on_a_fake_one():
    tree = Tree({"CLAUDE.md": "# t\n\nWhat this is.\n"}, git=False)
    try:
        _git(["init", "-q"], tree.path)
        _git(["add", "CLAUDE.md"], tree.path)
        _git(["commit", "-q", "-m", "first"], tree.path)
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        notes = result["files"][0]["notes"]
        assert any("last changed" in n for n in notes), notes
    finally:
        tree.close()

    # The bare ".git" marker the other tests use is not a real repository:
    # git_currency_note fails silently rather than raising.
    fake = Tree({"CLAUDE.md": "# t\n\nWhat this is.\n"})
    try:
        result2 = run(fake.file("CLAUDE.md"), "--no-voice")
        notes2 = result2["files"][0]["notes"]
        assert not any("last changed" in n for n in notes2), notes2
    finally:
        fake.close()


def test_global_flag_folds_home_memory_into_duplicate_check():
    shared = "- Shared standing rule about how every one of my repos works."
    home = None
    try:
        home = tempfile.mkdtemp(prefix="rabbit-claude-md-home-")
        os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
        with open(os.path.join(home, ".claude", "CLAUDE.md"), "w",
                  encoding="utf-8") as fh:
            fh.write("# global\n\n%s\n" % shared)

        tree = Tree({"CLAUDE.md": "# t\n\nWhat this is.\n\n%s\n" % shared})
        try:
            real_home = os.environ.get("HOME")
            os.environ["HOME"] = home
            try:
                out = subprocess.run(
                    [sys.executable, check_module().__file__,
                     tree.file("CLAUDE.md"), "--json", "--no-voice", "--global"],
                    capture_output=True, text=True)
            finally:
                if real_home is not None:
                    os.environ["HOME"] = real_home
            payload = json.loads(out.stdout)
            findings = payload["files"][0]["findings"]
            dup = [f for f in findings if f["id"] == "claudemd-duplicate"]
            assert dup, (out.stdout, out.stderr)
            assert any("~" in f["excerpt"] for f in dup), dup
        finally:
            tree.close()
    finally:
        if home:
            shutil.rmtree(home, ignore_errors=True)


def test_without_global_flag_home_memory_is_not_compared():
    shared = "- Shared standing rule about how every one of my repos works."
    home = None
    try:
        home = tempfile.mkdtemp(prefix="rabbit-claude-md-home-")
        os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
        with open(os.path.join(home, ".claude", "CLAUDE.md"), "w",
                  encoding="utf-8") as fh:
            fh.write("# global\n\n%s\n" % shared)

        tree = Tree({"CLAUDE.md": "# t\n\nWhat this is.\n\n%s\n" % shared})
        try:
            real_home = os.environ.get("HOME")
            os.environ["HOME"] = home
            try:
                out = subprocess.run(
                    [sys.executable, check_module().__file__,
                     tree.file("CLAUDE.md"), "--json", "--no-voice"],
                    capture_output=True, text=True)
            finally:
                if real_home is not None:
                    os.environ["HOME"] = real_home
            payload = json.loads(out.stdout)
            findings = payload["files"][0]["findings"]
            assert not any(f["id"] == "claudemd-duplicate" for f in findings), findings
        finally:
            tree.close()
    finally:
        if home:
            shutil.rmtree(home, ignore_errors=True)
