#!/usr/bin/env python3
"""
--apply-safe: the edits with exactly one correct answer.

The line this draws is the same fingerprint-versus-judgment line the rest of the
plugin draws, and the interesting tests are the ones proving the line holds:
that a fix does not reach into a code fence, that the substitution rule reads a
`preferred_substitutions` value as a replacement only when it is one, and that
nothing it writes fails verify.py.

test_invariants.py checks those properties over generated documents. These are
the named cases.
"""

import os
import shutil
import subprocess
import sys
import tempfile

from helpers import SCAN, WHIT3RABBIT_RULES, written

from rwlib import fixes

# Invisible characters are written as escapes here, never as literals, for
# exactly the reason scan.py's HIDDEN_UNICODE says: as literals they are
# invisible, and any tool that normalizes whitespace silently turns them into
# plain spaces. That happened to this file once already, and the fixture that
# was meant to hold five non-breaking spaces held five ordinary ones instead.

VOICE = {"voice": "t",
         "mechanics": {"em_dash": "allow"},
         "preferred_substitutions": {"leverage": "use",
                                     "at the end of the day": "cut it",
                                     "synergy": "name the combined effect",
                                     "circle back": "follow up"}}


def test_a_zero_width_space_in_prose_is_deleted():
    fixed, applied, _ = fixes.apply("A line with a zero\u200bwidth space.\n")
    assert "\u200b" not in fixed
    assert [a["id"] for a in applied] == ["hidden-unicode"]


def test_a_zero_width_space_inside_a_fence_is_reported_and_left_alone():
    """The promise is worth more than the fix. A fenced span is something
    verify.py compares verbatim, and the report says where the character is."""
    text = "Prose.\n\n```\nx = 1\u200b\n```\n"
    fixed, applied, skipped = fixes.apply(text)
    assert fixed == text
    assert not applied
    assert [s["id"] for s in skipped] == ["hidden-unicode"]
    assert "promises not to touch" in skipped[0]["note"]


def test_an_ai_tracking_parameter_is_dropped():
    fixed, applied, _ = fixes.apply(
        "See https://x.dev/p?utm_source=chatgpt.com&page=2 now.\n")
    assert "utm_source" not in fixed
    assert "page=2" in fixed
    assert [a["id"] for a in applied] == ["ai-utm"]


def test_a_tracking_parameter_inside_a_fence_is_left_alone():
    """Somebody is meant to paste that line exactly as written. Found by the
    property tests, on a document where two stray fences paired up around a
    link."""
    text = "Prose.\n\n```bash\ncurl https://x.dev/p?utm_source=chatgpt.com\n```\n"
    fixed, applied, skipped = fixes.apply(text)
    assert fixed == text
    assert not applied
    assert [s["id"] for s in skipped] == ["ai-utm"]


def test_a_preferred_substitution_that_is_a_replacement_is_applied():
    fixed, applied, _ = fixes.apply("We should leverage the platform.\n", VOICE)
    assert fixed == "We should use the platform.\n"
    assert [a["id"] for a in applied] == ["voice-substitution"]


def test_a_preferred_substitution_that_is_an_instruction_is_not():
    """`at the end of the day` maps to `cut it`, which is a note to the writer.
    Applying it literally would put the words "cut it" into the sentence."""
    text = "At the end of the day the build was green.\n"
    fixed, applied, _ = fixes.apply(text, VOICE)
    assert fixed == text
    assert not applied


def test_a_substitution_with_a_comma_or_a_parenthetical_is_not_applied():
    text = "We had real synergy on that release.\n"
    fixed, _, _ = fixes.apply(text, VOICE)
    assert fixed == text


def test_substitution_keeps_a_leading_capital():
    fixed, _, _ = fixes.apply("Leverage the platform.\n", VOICE)
    assert fixed == "Use the platform.\n"


def test_a_substitution_does_not_reach_into_code_or_a_url():
    text = ("Run `leverage --help` first.\n\n"
            "See https://x.dev/leverage/docs for more.\n\n"
            "```\nleverage build\n```\n")
    fixed, applied, _ = fixes.apply(text, VOICE)
    assert fixed == text
    assert not applied


def test_a_substitution_does_not_reach_into_a_heading():
    """verify.py holds heading text inviolable by default, so a fix that edits a
    heading fails the gate --apply-safe runs on its own output. The whole run
    was discarded and the user was told to report a bug in the fixer."""
    text = "# Leverage the API\n\nYou can leverage it from a script.\n"
    fixed, applied, _ = fixes.apply(text, VOICE)
    assert fixed.startswith("# Leverage the API\n")
    assert [a["line"] for a in applied] == [3]


def test_a_hidden_character_in_a_heading_is_left_for_a_person():
    text = "# Release\u200b notes\n\nProse under it.\n"
    fixed, applied, skipped = fixes.apply(text)
    assert fixed == text
    assert not applied
    assert {s["id"] for s in skipped} == {"hidden-unicode"}


def test_a_typed_em_dash_is_reported_and_never_fixed():
    """This started life as a fix. verify.py forbids adding an em dash under any
    circumstances, so every fix failed the plugin's own gate."""
    text = "The plan -- such as it is -- has three parts.\n"
    fixed, applied, skipped = fixes.apply(text, VOICE)
    assert fixed == text
    assert not applied
    assert {s["id"] for s in skipped} == {"double-hyphen-dash"}
    assert "never adds an em dash" in skipped[0]["note"]


def test_one_non_breaking_space_is_left_alone():
    """Correct French typography. Only a count that looks mechanical is touched,
    which is the same threshold scan.py reports at."""
    text = "Une phrase\u00a0: le texte suit.\n"
    fixed, applied, _ = fixes.apply(text)
    assert fixed == text
    assert not applied


def test_non_breaking_spaces_in_quantity_become_plain_spaces():
    text = "a\u00a0b\u00a0c\u00a0d\u00a0e\u00a0f words to make a sentence.\n"
    assert text.count("\u00a0") == 5, "the fixture stopped holding five of them"
    fixed, applied, _ = fixes.apply(text)
    assert "\u00a0" not in fixed
    assert len(applied) == 5


def test_nothing_to_fix_leaves_the_document_alone():
    text = "The certificate expired on the internal proxy at 02:14.\n"
    fixed, applied, skipped = fixes.apply(text, VOICE)
    assert (fixed, applied, skipped) == (text, [], [])


# --------------------------------------------------------------------------
# the CLI
# --------------------------------------------------------------------------

def run_scan(args):
    return subprocess.run([sys.executable, SCAN] + args,
                          capture_output=True, text=True)


def test_apply_safe_is_a_dry_run_by_default():
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "draft.md",
                       "We should leverage it. See https://x.dev/p?utm_source=chatgpt.com\n")
        before = open(path, encoding="utf-8").read()
        result = run_scan([path, "--apply-safe", "--voice-rules", WHIT3RABBIT_RULES])
        assert result.returncode == 0, result.stderr
        assert "Dry run" in result.stdout, result.stdout
        assert open(path, encoding="utf-8").read() == before
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_apply_safe_write_writes_and_reports_verification():
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "draft.md",
                       "We should leverage it. See https://x.dev/p?utm_source=chatgpt.com\n")
        result = run_scan([path, "--apply-safe", "--write",
                           "--voice-rules", WHIT3RABBIT_RULES])
        assert result.returncode == 0, result.stderr
        assert "verified:" in result.stdout, result.stdout
        after = open(path, encoding="utf-8").read()
        assert "utm_source" not in after
        assert "leverage" not in after
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_apply_safe_stdout_prints_the_document():
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "draft.md", "See https://x.dev/p?utm_source=chatgpt.com\n")
        result = run_scan([path, "--apply-safe", "--stdout"])
        assert result.returncode == 0, result.stderr
        assert result.stdout == "See https://x.dev/p\n", repr(result.stdout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_apply_safe_stdout_runs_the_same_gate_as_the_report():
    """--stdout used to skip verification entirely, which is the path most likely
    to be redirected into a file. A fix the gate would reject has to reach neither
    the file nor the pipe."""
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "draft.md", "Prose.\n")
        result = run_scan([path, "--apply-safe", "--stdout"])
        assert result.returncode == 0, result.stderr
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    module = __import__("rwlib.fixes", fromlist=["fixes"])
    verify = __import__("verify")
    text = "# Leverage the API\n\nWe should leverage it here.\n"
    voice = {"voice": "t", "preferred_substitutions": {"leverage": "use"}}
    assert verify.validate(text, module.apply(text, voice)[0])["ok"]


def test_write_keeps_the_line_endings_the_file_arrived_with():
    """Rewriting every line of a CRLF document is not an edit with exactly one
    correct answer, and verify.py cannot see it: both sides are read through
    universal newlines, so the comparison normalizes the difference away."""
    scratch = tempfile.mkdtemp()
    try:
        path = os.path.join(scratch, "draft.md")
        with open(path, "wb") as fh:
            fh.write(b"Intro line here.\r\n\r\nWe should leverage it now.\r\n")
        result = run_scan([path, "--apply-safe", "--write",
                           "--voice-rules", WHIT3RABBIT_RULES])
        assert result.returncode == 0, result.stderr
        raw = open(path, "rb").read()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert b"use it now" in raw, raw
    assert raw.count(b"\r\n") == 3, raw
    assert raw.count(b"\n") == raw.count(b"\r\n"), raw


def test_sarif_output_is_shaped_like_sarif():
    import json
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "draft.md",
                       "As of my last training update, this was true.\n")
        result = run_scan([path, "--sarif", "--sarif-uri", "docs/draft.md"])
        assert result.returncode == 0, result.stderr
        log = json.loads(result.stdout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    assert log["version"] == "2.1.0"
    run = log["runs"][0]
    assert run["tool"]["driver"]["name"] == "rabbit-writes/scan"
    assert run["results"], "no results"
    first = run["results"][0]
    assert first["level"] in ("error", "warning", "note")
    location = first["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "docs/draft.md"
    assert location["region"]["startLine"] >= 1
    # Every result's ruleId resolves against the driver's rule table, which is
    # what GitHub needs to render the annotation rather than dropping it.
    rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
    assert all(r["ruleId"] in rule_ids for r in run["results"])
    assert all(run["tool"]["driver"]["rules"][r["ruleIndex"]]["id"] == r["ruleId"]
               for r in run["results"])


def test_a_p0_maps_to_the_sarif_error_level():
    import json
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "draft.md",
                       "As of my last training update, this was true.\n")
        log = json.loads(run_scan([path, "--sarif"]).stdout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    levels = {r["properties"]["priority"]: r["level"] for r in log["runs"][0]["results"]}
    assert levels.get("P0") == "error", str(levels)
