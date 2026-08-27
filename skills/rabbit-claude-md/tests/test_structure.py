"""The claudemd-* structure checks, one fire-test per id.

Every fire-test also asserts the clean sample stays quiet on that id, because
a check that fires everywhere and one that never fires read the same from a
single assertion.
"""

from helpers import Tree, check_module, run, sample, structure_ids


def test_clean_sample_raises_no_structure_findings():
    assert structure_ids(run(sample("clean-claude.md"), "--no-voice")) == []


def test_bullet_length_fires_past_the_cap():
    got = structure_ids(run(sample("bullets-long.md"), "--no-voice"))
    assert got.count("claudemd-bullet-length") == 1, got
    clean = structure_ids(run(sample("clean-claude.md"), "--no-voice"))
    assert "claudemd-bullet-length" not in clean


def test_emphasis_budget_fires_when_most_lines_shout():
    got = structure_ids(run(sample("emphasis-heavy.md"), "--no-voice"))
    assert got.count("claudemd-emphasis-budget") == 1, got
    clean = structure_ids(run(sample("clean-claude.md"), "--no-voice"))
    assert "claudemd-emphasis-budget" not in clean


def test_changelog_tells_are_reported_as_evidence():
    result = run(sample("changelog-drift.md"), "--no-voice")
    drift = [f for e in result["files"] for f in e["findings"]
             if f["id"] == "claudemd-changelog-drift"]
    # Four phrase tells plus one commit-hash line. The `used to` inside a
    # code span on line 3 must not be a sixth.
    assert len(drift) == 5, [(f["line"], f["match"]) for f in drift]
    assert all(f["priority"] == "P2" for f in drift), (
        "drift is evidence for the judgment pass, never a defect on its own")


def test_no_structure_finding_is_ever_p0():
    mod = check_module()
    for name in ("bullets-long.md", "emphasis-heavy.md", "changelog-drift.md"):
        for entry in run(sample(name), "--no-voice")["files"]:
            for f in entry["findings"]:
                if f["id"].startswith("claudemd-"):
                    assert f["priority"] != "P0", f
    # And the module agrees about where blocking lives: nothing in the
    # checker constructs a structure finding at P0.
    import inspect
    src = inspect.getsource(mod)
    for line in src.splitlines():
        if "finding(" in line and '"P0"' in line:
            raise AssertionError("a claudemd finding is built at P0: %r" % line)


def test_dead_path_fires_only_inside_fences():
    tree = Tree({
        "scripts/real.py": "print('here')\n",
        "CLAUDE.md": (
            "# t\n\nProse mention of scripts/gone.py never fires.\n\n"
            "```bash\npython3 scripts/gone.py\n"
            "python3 scripts/real.py\n"
            "python3 <placeholder>/thing.py\n"
            "python3 $HOME/thing.py\n"
            "python3 path/to/thing.py\n"
            "gh repo clone owner/repo\n"
            "python3 x.py --out scratch/output.txt\n"
            "```\n"),
    })
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        dead = [f for e in result["files"] for f in e["findings"]
                if f["id"] == "claudemd-dead-path"]
        assert [f["match"] for f in dead] == ["scripts/gone.py"], dead
    finally:
        tree.close()


def test_import_unresolved_fires_and_resolving_import_is_quiet():
    tree = Tree({
        "docs/real.md": "# here\n",
        "CLAUDE.md": ("# t\n\nLoad @docs/real.md always.\n"
                      "Also @docs/missing.md and a bare @mention.\n"
                      "An npm package @scope/pkg is not an import.\n"),
    })
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        imports = [f for e in result["files"] for f in e["findings"]
                   if f["id"] == "claudemd-import-unresolved"]
        assert [f["match"] for f in imports] == ["@docs/missing.md"], imports
    finally:
        tree.close()


def test_duplicate_requires_two_files_and_min_length():
    mod = check_module()
    long_line = "- The fixture regenerator rewrites every golden file under tests/golden on demand."
    assert len(long_line) >= mod.LIMITS["duplicate_min_chars"]
    short = "- Shared short line."
    tree = Tree({
        "CLAUDE.md": "# root\n\n%s\n%s\n" % (long_line, short),
        "pkg/CLAUDE.md": "# pkg\n\n%s\n%s\n" % (long_line, short),
    })
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        dups = [f for e in result["files"] for f in e["findings"]
                if f["id"] == "claudemd-duplicate"]
        assert len(dups) == 1, dups
        assert "pkg/CLAUDE.md" in dups[0]["excerpt"], dups[0]
    finally:
        tree.close()


def test_docs_ignored_fires_only_when_gitignore_hides_claude():
    body = "# t\n\nDeep dive: [packaging](.claude/docs/packaging.md)\n"
    for ignore, want in (("scratch/\n.claude/\n", 1), ("scratch/\n", 0)):
        tree = Tree({"CLAUDE.md": body, ".gitignore": ignore,
                     ".claude/docs/packaging.md": "# packaging\n"})
        try:
            result = run(tree.file("CLAUDE.md"), "--no-voice")
            got = [f for e in result["files"] for f in e["findings"]
                   if f["id"] == "claudemd-docs-ignored"]
            assert len(got) == want, (ignore, got)
        finally:
            tree.close()
