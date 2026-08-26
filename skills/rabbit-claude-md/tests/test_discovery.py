"""Discovery: which files a sweep finds, and what a single-file run still sees."""

import os

from helpers import Tree, run, run_raw


def test_directory_sweep_finds_all_spellings_and_skips_junk():
    tree = Tree({
        "CLAUDE.md": "# root\n",
        "CLAUDE.local.md": "# local\n",
        ".claude.md": "# dot\n",
        "pkg/CLAUDE.md": "# pkg\n",
        "pkg/.claude.local.md": "# pkg local\n",
        "node_modules/dep/CLAUDE.md": "# vendored, never audited\n",
        "docs/notes.md": "# not a memory file\n",
    })
    try:
        result = run(tree.path, "--no-voice")
        files = sorted(e["file"] for e in result["files"])
        assert files == [".claude.md", "CLAUDE.local.md", "CLAUDE.md",
                         os.path.join("pkg", ".claude.local.md"),
                         os.path.join("pkg", "CLAUDE.md")], files
    finally:
        tree.close()


def test_single_file_still_sees_siblings_for_duplicates():
    shared = "- The deploy pipeline reads its channel list from the release manifest file."
    tree = Tree({
        "CLAUDE.md": "# root\n\n%s\n" % shared,
        "pkg/CLAUDE.md": "# pkg\n\n%s\n" % shared,
    })
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        assert len(result["files"]) == 1
        dups = [f for f in result["files"][0]["findings"]
                if f["id"] == "claudemd-duplicate"]
        assert dups, "a single-file run must still read sibling memory files"
    finally:
        tree.close()


def test_no_git_root_stays_silent_on_root_dependent_checks():
    tree = Tree({
        "CLAUDE.md": ("# t\n\n```bash\npython3 scripts/gone.py\n```\n"),
    }, git=False)
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        entry = result["files"][0]
        dead = [f for f in entry["findings"] if f["id"] == "claudemd-dead-path"]
        assert dead == [], "no root means the walk cannot judge a path"
        assert any("no .git root" in n for n in entry["notes"]), entry["notes"]
    finally:
        tree.close()


def test_empty_sweep_reports_and_exits_zero():
    tree = Tree({"docs/notes.md": "# nothing here\n"})
    try:
        stdout, stderr, code = run_raw(tree.path, "--no-voice")
        assert code == 0, stderr
        assert "no CLAUDE.md or AGENTS.md files" in stdout, stdout
    finally:
        tree.close()


def test_agents_md_discovery_when_no_claude_md():
    tree = Tree({
        "AGENTS.md": "# agents root\n",
        "AGENTS.override.md": "# agents override\n",
        "pkg/.agents.md": "# pkg agents\n",
        "docs/notes.md": "# not a memory file\n",
    })
    try:
        result = run(tree.path, "--no-voice")
        files = sorted(e["file"] for e in result["files"])
        assert files == [".agents.md", "AGENTS.override.md", "AGENTS.md",
                         os.path.join("pkg", ".agents.md")] or files == ["AGENTS.md", "AGENTS.override.md", os.path.join("pkg", ".agents.md")], files
        # Each AGENTS.md without CLAUDE.md companion offers the symlink hint in notes
        root_entry = next(e for e in result["files"] if e["file"] == "AGENTS.md")
        assert any("consider symlinking" in n for n in root_entry["notes"]), root_entry["notes"]
    finally:
        tree.close()


def test_claude_md_precedence_in_sweep_and_duplicate_detection():
    shared = "- The deploy pipeline reads its channel list from the release manifest file."
    tree = Tree({
        "CLAUDE.md": "# root\n\n%s\n" % shared,
        "AGENTS.md": "# agents\n\n%s\n" % shared,
    })
    try:
        # Sweep prioritizes CLAUDE.md
        result = run(tree.path, "--no-voice")
        assert len(result["files"]) == 1
        assert result["files"][0]["file"] == "CLAUDE.md"
        # Duplicate detection across both memory files still works
        dups = [f for f in result["files"][0]["findings"]
                if f["id"] == "claudemd-duplicate"]
        assert dups, "CLAUDE.md should find duplicates in AGENTS.md"
    finally:
        tree.close()


def test_single_agents_md_companion_check():
    # Without companion
    tree1 = Tree({"AGENTS.md": "# root\n"})
    try:
        result1 = run(tree1.file("AGENTS.md"), "--no-voice")
        notes1 = result1["files"][0]["notes"]
        assert any("ln -s AGENTS.md CLAUDE.md" in n for n in notes1), notes1
    finally:
        tree1.close()

    # With companion
    tree2 = Tree({"AGENTS.md": "# root\n", "CLAUDE.md": "# companion\n"})
    try:
        result2 = run(tree2.file("AGENTS.md"), "--no-voice")
        notes2 = result2["files"][0]["notes"]
        assert not any("consider symlinking" in n for n in notes2), notes2
    finally:
        tree2.close()

