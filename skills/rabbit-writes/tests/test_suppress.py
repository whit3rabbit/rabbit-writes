#!/usr/bin/env python3
"""
Inline suppressions.

The mechanism exists so a repository with a known and accepted finding has
something to reach for other than `files:` on the hook, or `--no-verify`, which
turns off every other check at the same time. `references/patterns.md` in this
repository is the case: it quotes five chat citation markers in order to warn
about them, and so a document doing exactly what the plugin asks for fails the
plugin.

Two properties carry the whole design, and both are asserted here rather than
promised in the module docstring.

**The reason is mandatory.** A suppression without one does not apply. The value
of the mechanism is that somebody had to write down why, and an optional reason
is a reason nobody writes.

**Nothing disappears.** A suppressed finding is still printed, still in --json,
and still carries its own reason and the line that allowed it. Only the exit
code moves. A fingerprint P0 is evidence about how a file was produced, and a
mechanism that made evidence vanish quietly would be worse than the scoping it
replaces.

Stdlib only, 3.9+.
"""

from helpers import WHIT3RABBIT_RULES, scan_text

from rwlib import suppress

# A citation marker in backticks. `citation-leak` carries `scan_raw`, so the
# quoted-example exemption does not reach it, which is exactly why a document
# that writes about the markers needs a way to say so.
LEAK = "The marker looks like `citeturn0search0` and you must never ship one.\n"
BODY = ("Widget resizes images in bulk. It reads a directory and writes a "
        "thumbnail beside each original, and that is the whole of it.\n\n")


def allow(ids, reason):
    return "<!-- rabbit-allow: %s (%s) -->\n\n" % (ids, reason)


def find(result, fid):
    return [f for f in result["findings"] if f["id"] == fid]


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

def test_a_comment_with_a_reason_parses():
    allowances, problems = suppress.parse(allow("citation-leak", "we catalogue them"))
    assert not problems, problems
    assert allowances[0]["ids"] == ["citation-leak"]
    assert allowances[0]["reason"] == "we catalogue them"


def test_several_ids_in_one_comment():
    allowances, _ = suppress.parse(allow("citation-leak, curly-quote", "both quoted"))
    assert allowances[0]["ids"] == ["citation-leak", "curly-quote"]


def test_a_reason_may_contain_parentheses():
    allowances, problems = suppress.parse(
        allow("citation-leak", "see patterns.md (section 46) for why"))
    assert not problems, problems
    assert "section 46" in allowances[0]["reason"]


def test_a_comment_inside_a_code_fence_is_an_example_and_not_a_suppression():
    """This module's own documentation contains the syntax. Honouring it would
    let a document about suppressions suppress its own findings."""
    fenced = "```\n" + allow("citation-leak", "shown as an example") + "```\n"
    allowances, problems = suppress.parse(fenced)
    assert not allowances and not problems, (allowances, problems)


# --------------------------------------------------------------------------
# the reason is mandatory
# --------------------------------------------------------------------------

def test_a_suppression_with_no_reason_does_not_apply():
    doc = BODY + "<!-- rabbit-allow: citation-leak -->\n\n" + LEAK + BODY
    result, code = scan_text(doc, "--check")
    leaks = find(result, "citation-leak")
    assert leaks and "suppressed" not in leaks[0], leaks
    assert code == 1, result["counts"]


def test_a_suppression_with_no_reason_is_itself_a_finding():
    doc = BODY + "<!-- rabbit-allow: citation-leak -->\n\n" + LEAK + BODY
    result, _ = scan_text(doc)
    invalid = find(result, "suppression-invalid")
    assert invalid and invalid[0]["priority"] == "P1", result["findings"]


def test_an_empty_reason_is_the_same_as_none():
    _, problems = suppress.parse("<!-- rabbit-allow: citation-leak () -->")
    assert problems, problems


# --------------------------------------------------------------------------
# nothing disappears
# --------------------------------------------------------------------------

def test_an_allowed_p0_stops_failing_the_run():
    doc = BODY + allow("citation-leak", "this file catalogues the markers") + LEAK + BODY
    result, code = scan_text(doc, "--check")
    assert code == 0, result["findings"]


def test_an_allowed_p0_is_still_reported_with_its_reason():
    """The half that makes this safe to ship. A scoped hook says nothing at all;
    a suppression says here is a P0, here is who allowed it, and here is why."""
    doc = BODY + allow("citation-leak", "this file catalogues the markers") + LEAK + BODY
    result, _ = scan_text(doc)
    leaks = find(result, "citation-leak")
    assert leaks, result["findings"]
    assert leaks[0]["suppressed"] == "this file catalogues the markers", leaks[0]
    assert leaks[0]["suppressed_at"] > 0, leaks[0]


def test_an_allowed_finding_comes_out_of_the_priority_counts():
    """It has to, or the finding fails the build it was allowed for."""
    doc = BODY + allow("citation-leak", "catalogued on purpose") + LEAK + BODY
    result, _ = scan_text(doc)
    assert result["counts"]["P0"] == 0, result["counts"]
    assert result["counts"]["suppressed"] >= 1, result["counts"]


def test_a_suppression_survives_alongside_a_voice_profile():
    """The two layers are independent. A voice band running does not change
    which findings an allowance covers, or whether it is reported."""
    doc = BODY + allow("citation-leak", "catalogued on purpose") + LEAK + BODY
    result, _ = scan_text(doc, "--voice-rules", WHIT3RABBIT_RULES)
    assert any(f.get("suppressed") for f in result["findings"]), result["findings"]


# --------------------------------------------------------------------------
# stale suppressions
# --------------------------------------------------------------------------

def test_a_suppression_covering_nothing_is_reported():
    """They accumulate otherwise: an id gets allowed, the prose that tripped it
    is rewritten a year later, and the comment sits there covering a rule
    nobody is breaking."""
    doc = BODY + allow("citation-leak", "there is no marker in here") + BODY
    result, _ = scan_text(doc)
    unused = find(result, "suppression-unused")
    assert unused and unused[0]["priority"] == "P2", result["findings"]


def test_a_typo_in_an_id_looks_the_same_and_is_reported_the_same():
    doc = BODY + allow("citation-leek", "typo on purpose") + LEAK + BODY
    result, code = scan_text(doc, "--check")
    assert find(result, "suppression-unused"), result["findings"]
    # And the finding it was meant to allow is still failing, loudly.
    assert code == 1, result["counts"]


def test_a_live_suppression_is_not_reported_as_stale():
    doc = BODY + allow("citation-leak", "catalogued on purpose") + LEAK + BODY
    result, _ = scan_text(doc)
    assert not find(result, "suppression-unused"), result["findings"]


# --------------------------------------------------------------------------
# scope
# --------------------------------------------------------------------------

def test_the_scope_is_the_whole_file_not_the_next_line():
    """Line-scoped suppressions are a maintenance trap: the line moves, the
    suppression does not, and it silently starts covering something else."""
    doc = (BODY + allow("citation-leak", "catalogued on purpose")
           + LEAK + BODY + LEAK + BODY)
    result, code = scan_text(doc, "--check")
    leaks = find(result, "citation-leak")
    assert len(leaks) >= 2, leaks
    assert all("suppressed" in f for f in leaks), leaks
    assert code == 0, result["counts"]


def test_an_unrelated_finding_is_untouched():
    doc = (BODY + allow("citation-leak", "catalogued on purpose")
           + LEAK + "As of my last training update, that was true.\n\n" + BODY)
    result, code = scan_text(doc, "--check")
    cutoff = find(result, "cutoff-disclaimer")
    assert cutoff and "suppressed" not in cutoff[0], cutoff
    assert code == 1, result["counts"]
