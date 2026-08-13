#!/usr/bin/env python3
"""
The preservation validator.

SKILL.md promises the editor will not touch code blocks, frontmatter, tables,
block quotes, inline code, URLs, file paths, or heading structure, and will not
add em dashes or leave a draft with more tells than it started with. Edit mode
writes to files, so a broken promise there is silent and destructive. These are
the checks on the checks.
"""

import sys

from helpers import SCRIPTS, run_verify, scan_module, verify_module

sys.path.insert(0, SCRIPTS)
from rwlib import corpus, fixes                                    # noqa: E402

ORIGINAL = ("# Heading One\n\n"
            "Some prose that delves into the tapestry.\n\n"
            "```python\nx = 1  # delve\n```\n\n"
            "| a | b |\n| - | - |\n\n"
            "See https://example.com/p?utm_source=chatgpt.com&page=2\n")

CLEAN_REWRITE = ("# Heading one\n\n"
                 "Some prose that explores the subject.\n\n"
                 "```python\nx = 1  # delve\n```\n\n"
                 "| a | b |\n| - | - |\n\n"
                 "See https://example.com/p?page=2\n")

DESTRUCTIVE = ("# Heading One Rewritten\n\n"
               "Some prose that explores the subject, seamlessly.\n\n"
               "```python\nx = 2  # explore\n```\n\n"
               "| a | c |\n| - | - |\n\n"
               "See https://example.com/other\n")

RESTRUCTURED = ("# Heading one, rewritten to lead with the point\n\n"
                "Some prose that explores the subject.\n\n"
                "```python\nx = 1  # delve\n```\n\n"
                "| a | b |\n| - | - |\n\n"
                "## A section the conversion added\n\n"
                "See https://example.com/p?page=2\n")


def test_a_clean_rewrite_passes():
    result, code = run_verify(ORIGINAL, CLEAN_REWRITE)
    assert result["ok"] and code == 0, str(result.get("violations"))


def test_a_title_case_heading_fix_is_carved_out():
    result, _ = run_verify(ORIGINAL, CLEAN_REWRITE)
    assert not any("heading" in v["kind"] for v in result["violations"])


def test_stripping_an_ai_utm_parameter_is_carved_out():
    result, _ = run_verify(ORIGINAL, CLEAN_REWRITE)
    assert not any("URL" in v["kind"] for v in result["violations"])


def test_a_destructive_rewrite_fails():
    broken, code = run_verify(ORIGINAL, DESTRUCTIVE)
    assert not broken["ok"] and code == 1
    kinds = {v["kind"] for v in broken["violations"]}
    assert any("code block" in k for k in kinds), str(kinds)
    assert any("table" in k for k in kinds), str(kinds)
    assert any("heading" in k for k in kinds), str(kinds)


def test_an_added_em_dash_is_caught():
    result, _ = run_verify("Plain sentence here.", "Plain sentence — here.")
    assert any("em dashes added" in v["kind"] for v in result["violations"])


# --------------------------------------------------------------------------
# --allow-structure, for voice conversions
#
# A conversion reorders sections and rewrites headings because the profile told
# it to. The flag has to scope to headings and nothing else, or it becomes a way
# to wave through a rewrite that ate a code block.
# --------------------------------------------------------------------------

def test_a_reordered_rewrite_fails_without_the_flag():
    strict, code = run_verify(ORIGINAL, RESTRUCTURED)
    assert not strict["ok"] and code == 1, str(strict.get("violations"))


def test_the_same_rewrite_passes_with_allow_structure():
    loose, code = run_verify(ORIGINAL, RESTRUCTURED, "--allow-structure")
    assert loose["ok"] and code == 0, str(loose.get("violations"))
    assert len(loose["structure_changes"]) >= 2, str(loose.get("structure_changes"))


def test_allow_structure_still_fails_on_an_altered_code_block():
    scoped, code = run_verify(ORIGINAL, DESTRUCTIVE, "--allow-structure")
    assert not scoped["ok"] and code == 1, str({v["kind"] for v in scoped["violations"]})


def test_allow_structure_still_fails_on_an_added_em_dash():
    result, _ = run_verify("Plain sentence here.", "Plain sentence — here.",
                           "--allow-structure")
    assert not result["ok"]


# --------------------------------------------------------------------------
# structure is read out of prose, not out of code
# --------------------------------------------------------------------------

def test_a_shell_comment_in_a_fence_is_not_a_heading():
    fenced = ("# Title\n\nSome prose here.\n\n"
              "```bash\n# install it\n| --flag | what it does |\nmake\n```\n")
    moved = ("# Title\n\nDifferent prose entirely.\n\n"
             "```bash\n# install it\n| --flag | what it does |\nmake\n```\n")
    result, code = run_verify(fenced, moved)
    assert result["ok"] and code == 0, str(result["violations"])


def test_a_path_inside_a_table_row_is_reported_once():
    """One edit, one violation. The table row is already compared verbatim, so
    reporting the path inside it as well shows a reader two broken promises where
    there is one. Same argument as the URL and inline-code carve-outs above,
    one span type over."""
    table = ("| file | what it does |\n| - | - |\n"
             "| docs/setup.md | how to install it |\n")
    edited = table.replace("docs/setup.md", "docs/install.md")
    result, _ = run_verify(table, edited)
    kinds = [v["kind"] for v in result["violations"]]
    assert any("table" in k for k in kinds), str(kinds)
    assert not any("path" in k for k in kinds), str(kinds)


def test_the_same_path_on_a_prose_line_is_still_reported():
    """The other half. Blanking the spans that carry their own promise must not
    turn the path check off everywhere else."""
    prose = "The installer reads docs/setup.md before it does anything.\n"
    result, _ = run_verify(prose, prose.replace("docs/setup.md",
                                                "docs/install.md"))
    assert any("path" in v["kind"] for v in result["violations"]), str(
        result["violations"])


def test_a_path_inside_a_url_is_not_reported_as_a_path():
    urly = "See https://raw.githubusercontent.com/user/repo/main/README.md now.\n"
    result, _ = run_verify(urly, urly.replace("now", "here"))
    assert not any("path" in v["kind"] for v in result["violations"]), str(
        result["violations"])


def test_a_url_ending_in_a_bare_fragment_survives_normalization():
    hashed = "See https://x.dev/p?utm_source=chatgpt.com# for the writeup.\n"
    result, code = run_verify(hashed, "See https://x.dev/p# for the writeup.\n")
    assert result["ok"] and code == 0, str(result["violations"])


def test_tells_come_from_the_lexicon_and_not_a_frozen_copy():
    result, _ = run_verify("Plain sentence about locking.\n",
                           "A holistic sentence about locking.\n")
    assert any("more tells" in v["kind"] for v in result["violations"]), str(
        result["violations"])


def test_auto_curled_typography_is_not_counted_as_a_tell():
    """An editor that curls quotes is not a tell generator. Building the counter
    from every fingerprint pattern swept curly-quote in with the real ones and
    hard-failed a correct rewrite for something Word did."""
    result, code = run_verify('He said "the lock is a directory" and moved on.\n',
                              'He said “the lock is a directory” and left it there.\n')
    assert result["ok"] and code == 0, str(result["violations"])
    assert result["tells_before"] == result["tells_after"], "%d -> %d" % (
        result["tells_before"], result["tells_after"])


def test_an_en_dash_in_a_numeric_range_is_not_an_added_em_dash():
    result, code = run_verify("The study ran from 2010 to 2023 across four sites.\n",
                              "The study ran 2010–2023 across four sites.\n")
    assert result["ok"] and code == 0, str(result["violations"])


def test_a_prose_em_dash_is_still_caught_and_named():
    result, _ = run_verify("Plain sentence here.\n", "Plain sentence — here.\n")
    dashes = [v for v in result["violations"] if v["kind"] == "em dashes added"]
    assert dashes, str(result["violations"])
    assert any("Plain sentence" in v["detail"] for v in dashes), str(dashes)


def test_a_tell_inside_a_quoted_example_does_not_move_the_gate():
    before = "Notes on the draft.\n\n```\nplain\n```\n"
    after = (before + '\nCut "a word like delve" wherever it turns up.\n')
    result, code = run_verify(before, after)
    assert result["ok"] and code == 0, str(result["violations"])


def test_the_same_tell_in_running_prose_still_fails_and_names_it():
    before = "Notes on the draft.\n\n```\nplain\n```\n"
    result, _ = run_verify(before, before + "\nWe delve into it.\n")
    assert any("more tells" in v["kind"] for v in result["violations"]), str(
        result["violations"])
    assert any("delve" in v["detail"] for v in result["violations"]), str(
        result["violations"])


def test_a_dropped_duplicate_heading_is_caught():
    """Membership alone hid this: drop one of two identical headings, add a
    different one, and both the membership test and the count test stay happy
    while a section disappears."""
    before = "## Notes\n\nFirst body.\n\n## Notes\n\nSecond body.\n"
    after = "## Notes\n\nFirst body.\n\n## Other\n\nSecond body.\n"
    result, code = run_verify(before, after)
    assert not result["ok"] and code == 1
    assert any("heading" in v["kind"] for v in result["violations"]), str(
        result["violations"])


def test_two_identical_headings_that_both_survive_still_pass():
    before = "## Notes\n\nFirst body.\n\n## Notes\n\nSecond body.\n"
    result, code = run_verify(before, before)
    assert result["ok"] and code == 0, str(result["violations"])


# --------------------------------------------------------------------------
# one definition, shared
#
# This used to read verify.py's source and compare regex literals, because there
# were two of them and the only thing keeping them equal was a comment. There is
# one now, in rwlib.markdown, so the assertion is identity: two modules that
# import the same object cannot drift, and an edit that gives either its own
# copy back fails here.
# --------------------------------------------------------------------------

def test_scan_and_verify_share_one_prose_dash_definition():
    scan, verify = scan_module(), verify_module()
    assert scan.PROSE_DASH_RX is verify.PROSE_DASH_RX, "%r vs %r" % (
        scan.PROSE_DASH_RX.pattern, verify.PROSE_DASH_RX.pattern)


def test_scan_and_verify_share_one_quoted_example_definition():
    assert scan_module().QUOTED_RX is verify_module().QUOTED_RX


def test_scan_and_verify_share_one_exemption_function():
    assert scan_module().apply_exemptions is verify_module().apply_exemptions


# --------------------------------------------------------------------------
# images
# --------------------------------------------------------------------------
#
# Sources are checked and alt text is not, and both halves are measured over the
# 100-README corpus rather than argued. See verify.py's docstring for the
# numbers. These pin the behaviour those numbers bought.

IMG_DOC = ("# Title\n\nSome prose about the project that runs on for a bit.\n\n"
           "![architecture](assets/diagram)\n\nMore prose after the image.\n")


def test_a_relative_extensionless_image_source_is_protected():
    """The gap: neither URL_RX nor PATH_RX matches `assets/diagram`, so an edit
    could retarget the image with nothing reported."""
    moved = IMG_DOC.replace("assets/diagram", "assets/other")
    result, code = run_verify(IMG_DOC, moved)
    assert code != 0, result
    assert any(v["kind"] == "image source altered or removed"
               for v in result["violations"]), result["violations"]


def test_an_html_image_source_is_protected_too():
    doc = ('# Title\n\nProse about the project.\n\n'
           '<img src="assets/logo" alt="logo">\n\nMore prose here.\n')
    moved = doc.replace('src="assets/logo"', 'src="assets/wordmark"')
    result, code = run_verify(doc, moved)
    assert code != 0, result


def test_a_source_already_covered_is_not_reported_twice():
    """A src reported by both the URL check and the image check is one broken
    promise counted twice, and a reader tallying violations sees two problems
    where there is one."""
    doc = ("# Title\n\nProse about the project here.\n\n"
           "![logo](https://acme.example/logo.png)\n\nMore prose.\n")
    moved = doc.replace("logo.png", "wordmark.png")
    result, _ = run_verify(doc, moved)
    kinds = [v["kind"] for v in result["violations"]]
    assert "URL altered or removed" in kinds, kinds
    assert "image source altered or removed" not in kinds, kinds


def test_alt_text_stays_editable():
    """Measured, not assumed: alt text in the corpus is overwhelmingly badge
    labels, and "PyPI" becoming "PyPI version" is a fix. SKILL.md's guardrails
    never promised alt text was untouchable, and this file does not invent a
    promise the skill does not make."""
    edited = IMG_DOC.replace("![architecture]", "![architecture diagram]")
    result, code = run_verify(IMG_DOC, edited)
    assert code == 0, result["violations"]


# --------------------------------------------------------------------------
# facts: numbers, dates, quotations
# --------------------------------------------------------------------------
#
# Guardrail 1 says never invent a number, a date or a quote, and until these it
# was prose in SKILL.md with nothing behind it. Every other check here proves
# the rewrite did not touch a code fence, and none of them noticed the sentence
# that turned 3,200 into 3,000.
#
# The assertions come in pairs on purpose. A checker that never fires passes
# every carve-out test in the file, so each "this reformat is allowed" case has
# a "this corruption is caught" case beside it.

PROSE = ("The build reads a manifest and writes a report. It runs from a "
         "checkout with nothing installed, which is the whole bargain.\n\n")


def test_a_changed_number_fails_and_names_both_halves():
    """One lost and one added is the same fact moving. Printing only the loss
    makes a reader go and find the other half themselves."""
    before = PROSE + "We shipped 3,200 units in the first quarter.\n"
    after = PROSE + "We shipped 3,000 units in the first quarter.\n"
    result, code = run_verify(before, after)
    assert code == 1, result
    detail = [v["detail"] for v in result["violations"]
              if v["kind"] == "number altered or removed"]
    assert detail and "3200" in detail[0] and "3000" in detail[0], detail


def test_reformatting_a_number_is_not_a_changed_number():
    """A thousands separator, a percent spelling and a range spelling are all
    formatting. This check exists for the edit that moved the value."""
    before = PROSE + "It saved 1,200 hours, or 10-20% of the budget.\n"
    after = PROSE + "It saved 1200 hours, or 10 to 20 percent of the budget.\n"
    result, code = run_verify(before, after)
    assert code == 0, result["violations"]


def test_a_date_reformat_is_carved_out_and_a_moved_date_is_not():
    """A `date_format: dmy` profile instructs the rewrite to move a date
    between spellings, so a checker that failed that would be failing the edit
    the skill asked for."""
    before = PROSE + "We shipped on September 12, 2025 after two delays.\n"
    same, code = run_verify(before, PROSE +
                            "We shipped on 12 September 2025 after two delays.\n")
    assert code == 0, same["violations"]
    moved, code = run_verify(before, PROSE +
                             "We shipped on 12 September 2024 after two delays.\n")
    assert code == 1, moved
    assert any(v["kind"] == "date altered or removed"
               for v in moved["violations"]), moved["violations"]


def test_a_quotation_survives_reflow_and_curling_but_not_rewording():
    before = PROSE + 'She said "the rollback took four minutes" and left.\n'
    reflowed, code = run_verify(
        before, PROSE + 'She said "the rollback took   four\nminutes" and left.\n')
    assert code == 0, reflowed["violations"]
    reworded, code = run_verify(
        before, PROSE + 'She said "the rollback took several minutes" and left.\n')
    assert code == 1, reworded
    assert any(v["kind"] == "quotation altered or removed"
               for v in reworded["violations"]), reworded["violations"]


def test_an_added_number_is_reported_and_never_fails():
    """A rewrite that turns "the last two years" into "2024 and 2025" is
    deriving a number the source carried, not inventing one. The asymmetry is a
    decision, and this is where it is pinned."""
    before = PROSE + "It happened over the last two years.\n"
    after = PROSE + "It happened over 2024 and 2025.\n"
    result, code = run_verify(before, after)
    assert code == 0, result["violations"]
    assert result["facts"]["numbers_added"], result["facts"]


def test_allow_facts_reports_instead_of_failing():
    before = PROSE + "We shipped 3,200 units.\n"
    after = PROSE + "We shipped 3,000 units.\n"
    result, code = run_verify(before, after, "--allow-facts")
    assert code == 0, result["violations"]
    assert any(c["kind"] == "number altered or removed"
               for c in result["fact_changes"]), result["fact_changes"]


def test_a_number_inside_a_code_fence_is_not_a_prose_fact():
    """The fence is compared verbatim two checks above, which is the stricter
    promise. Counting it here reports one broken promise twice."""
    before = PROSE + "```\nPORT = 8080\n```\n"
    result, _ = run_verify(before, before)
    assert result["facts"]["numbers_after"] == 0, result["facts"]


def test_an_html_character_reference_is_markup_and_not_a_number():
    """`&#8203;` is a zero-width space, and stripping it is an instructed fix.
    Read as a number, the fixer's own output failed verification with "8203 was
    removed"."""
    before = PROSE + "word&#8203;break here.\n"
    after = PROSE + "wordbreak here.\n"
    result, code = run_verify(before, after)
    assert code == 0, result["violations"]


def test_an_entity_delta_is_reported_and_never_fails():
    """Report-only forever. A capitalized-run regex cannot tell a product name
    from the first word of a sentence, and set-equality on it would fail every
    rewrite that splits a sentence at a capital."""
    before = PROSE + "The report covers Acme Corp and its Northwind division.\n"
    after = PROSE + "The report covers its Northwind division.\n"
    result, code = run_verify(before, after)
    assert code == 0, result["violations"]
    assert "Acme Corp" in result["facts"]["entities_lost"], result["facts"]


# --------------------------------------------------------------------------
# the same checks, over 100 real third-party documents
# --------------------------------------------------------------------------
#
# CLAUDE.md requires a new detector to be calibrated against these before it is
# wired to anything, and to assert the zero rather than report it: a false
# positive here is a stranger's blocked commit, and worse than that, verify.py's
# `ok` gates whether `scan.py --apply-safe --write` writes at all. A false
# positive does not produce a noisy report, it silently refuses to write and
# blames the fixer.

def test_no_corpus_readme_loses_a_fact_against_itself():
    """Identity. Any loss here is a non-idempotent canonicalizer, which is a bug
    in the extractor rather than a false positive."""
    verify = verify_module()
    bad = []
    for slug, path in corpus.readme_paths():
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        result = verify.validate(text, text)
        if not result["ok"]:
            bad.append((slug, result["violations"][:2]))
    assert not bad, bad


def test_the_mechanical_fixer_never_costs_a_corpus_readme_a_fact():
    """`scan.run_apply_safe` refuses to write when verify says not ok, so a
    false positive here is a fixer that stops working and reports itself as the
    problem. The fixer only strips hidden characters, tracking parameters and
    single-word substitutions, none of which is a number."""
    verify = verify_module()
    bad = []
    for slug, path in corpus.readme_paths():
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        fixed, applied, _ = fixes.apply(text, None)
        result = verify.validate(text, fixed)
        if not result["ok"]:
            bad.append((slug, applied, result["violations"][:2]))
    assert not bad, bad
