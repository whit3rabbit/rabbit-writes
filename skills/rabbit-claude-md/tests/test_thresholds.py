"""LIMITS is the one home for every threshold.

Boundary fixtures are built *from* the constants, so moving a limit moves
these tests with it: each check is quiet exactly at its cap and fires one
past it.
"""

from helpers import Tree, check_module, run


def _size(mod, nonblank):
    raw = "\n".join("line %d" % i for i in range(nonblank)) + "\n"
    findings, stats = [], {}
    mod.check_size(raw, findings, stats)
    assert stats["nonblank_lines"] == nonblank
    return findings


def test_oversize_reports_at_both_bands():
    mod = check_module()
    p2, p1 = mod.LIMITS["size_lines_p2"], mod.LIMITS["size_lines_p1"]
    assert _size(mod, p2) == []
    at_p2 = _size(mod, p2 + 1)
    assert [f["priority"] for f in at_p2] == ["P2"], at_p2
    at_p1 = _size(mod, p1 + 1)
    assert [f["priority"] for f in at_p1] == ["P1"], at_p1
    assert str(p1) in at_p1[0]["excerpt"] or str(p1) in at_p1[0]["label"]


def test_char_budget_reports_at_both_bands_independent_of_line_count():
    mod = check_module()
    p2, p1 = mod.LIMITS["char_budget_p2"], mod.LIMITS["char_budget_p1"]

    def _chars(n):
        # One long line: proves the character check fires on its own axis,
        # not as a side effect of the line-count bands.
        findings, stats = [], {}
        mod.check_char_budget("x" * n, findings, stats)
        assert stats["char_count"] == n
        return findings

    assert _chars(p2) == []
    at_p2 = _chars(p2 + 1)
    assert [f["priority"] for f in at_p2] == ["P2"], at_p2
    at_p1 = _chars(p1 + 1)
    assert [f["priority"] for f in at_p1] == ["P1"], at_p1


def test_bullet_cap_is_exact():
    mod = check_module()
    cap = mod.LIMITS["bullet_words"]
    for words, want in ((cap, 0), (cap + 1, 1)):
        raw = "# t\n\n- " + " ".join("w%d" % i for i in range(words)) + "\n"
        findings, stats = [], {}
        mod.check_bullets(raw, findings, stats)
        assert len(findings) == want, (words, findings)
    # A continuation line folds into its item rather than escaping the cap.
    half = cap // 2 + 1
    raw = ("# t\n\n- " + " ".join("a%d" % i for i in range(half)) + "\n  "
           + " ".join("b%d" % i for i in range(half)) + "\n")
    findings, stats = [], {}
    mod.check_bullets(raw, findings, stats)
    assert len(findings) == 1, findings


def test_emphasis_budget_is_exact():
    mod = check_module()
    allowed = mod.LIMITS["emphasis_lines_abs"]
    for markers, want in ((allowed, 0), (allowed + 1, 1)):
        lines = ["# t", ""] + ["IMPORTANT: rule %d." % i for i in range(markers)]
        findings, stats = [], {}
        mod.check_emphasis("\n".join(lines) + "\n", findings, stats)
        assert len(findings) == want, (markers, findings)
        assert stats["emphasis_lines"] == markers


def test_emphasis_budget_scales_with_file_size():
    mod = check_module()
    abs_cap = mod.LIMITS["emphasis_lines_abs"]
    pct = mod.LIMITS["emphasis_lines_pct"]
    # Enough prose lines that the percentage side of max() wins.
    prose = int((abs_cap + 5) / pct)
    allowed = max(abs_cap, int(pct * (prose + abs_cap + 5)))
    assert allowed > abs_cap
    lines = ["plain line %d" % i for i in range(prose)]
    lines += ["NEVER do thing %d." % i for i in range(abs_cap + 5)]
    findings, stats = [], {}
    mod.check_emphasis("\n".join(lines) + "\n", findings, stats)
    assert findings == [], ("under the scaled budget", stats, findings)


def test_duplicate_min_chars_is_exact():
    mod = check_module()
    floor = mod.LIMITS["duplicate_min_chars"]
    at = "x" * floor
    under = "y" * (floor - 1)
    tree = Tree({
        "CLAUDE.md": "# root\n\n%s\n%s\n" % (at, under),
        "pkg/CLAUDE.md": "# pkg\n\n%s\n%s\n" % (at, under),
    })
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        dups = [f for e in result["files"] for f in e["findings"]
                if f["id"] == "claudemd-duplicate"]
        assert len(dups) == 1, dups
        assert dups[0]["match"].startswith("x"), dups[0]
    finally:
        tree.close()


def test_json_reports_the_limits_in_force():
    mod = check_module()
    from helpers import sample
    result = run(sample("clean-claude.md"), "--no-voice")
    assert result["limits"] == mod.LIMITS
