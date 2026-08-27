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


def test_both_harnesses_are_swept_and_overlap_is_flagged():
    # 200+ characters of shared substantial content, so the overlap ratio
    # clears DUAL_HARNESS_OVERLAP rather than one borrowed sentence.
    shared_lines = "\n".join(
        "- Shared standing rule number %d about how this repository works." % i
        for i in range(6))
    tree = Tree({
        "CLAUDE.md": "# root\n\nWhat this is.\n\n%s\n" % shared_lines,
        "AGENTS.md": "# agents\n\nWhat this is.\n\n%s\n" % shared_lines,
    })
    try:
        result = run(tree.path, "--no-voice")
        files = sorted(e["file"] for e in result["files"])
        assert files == ["AGENTS.md", "CLAUDE.md"], (
            "both harnesses have real content and both must be audited", files)

        by_file = {e["file"]: e for e in result["files"]}
        dups = [f for f in by_file["CLAUDE.md"]["findings"]
                if f["id"] == "claudemd-duplicate"]
        assert dups, "CLAUDE.md should find duplicates in AGENTS.md"

        for name in ("CLAUDE.md", "AGENTS.md"):
            dual = [f for f in by_file[name]["findings"]
                    if f["id"] == "claudemd-dual-harness"]
            assert dual, "%s: heavy overlap should suggest a symlink" % name
    finally:
        tree.close()


def test_symlinked_pair_never_raises_dual_harness():
    tree = Tree({"AGENTS.md": "# t\n\nWhat this is, in one line.\n"})
    os.symlink("AGENTS.md", os.path.join(tree.path, "CLAUDE.md"))
    try:
        result = run(tree.path, "--no-voice")
        found = [f for e in result["files"] for f in e["findings"]
                 if f["id"] == "claudemd-dual-harness"]
        assert found == [], "a symlinked pair is one file, not two to merge"
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



def test_symlinked_pair_is_noted_and_not_a_duplicate():
    shared = ("- The deploy pipeline reads its channel list from the "
              "release manifest file.")
    tree = Tree({"AGENTS.md": "# t\n\n%s\n" % shared})
    os.symlink("AGENTS.md", os.path.join(tree.path, "CLAUDE.md"))
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        entry = result["files"][0]
        assert any("symlink to AGENTS.md" in n for n in entry["notes"]), (
            entry["notes"])
        dups = [f for f in entry["findings"]
                if f["id"] == "claudemd-duplicate"]
        assert dups == [], ("one file with two names is not a duplication",
                            dups)
    finally:
        tree.close()
