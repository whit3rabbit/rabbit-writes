#!/usr/bin/env python3
"""
The engine's own machinery: what it detects, what it measures as prose, the
invisible-character tables, and the false positives reviewers found.
"""

import os
import shutil
import tempfile

# Invisible characters are written as escapes here, never as literals, for
# exactly the reason scan.py's HIDDEN_UNICODE says: as literals they are
# invisible, and any tool that normalizes whitespace silently turns them into
# plain spaces. That happened to this file once already, and the fixture that
# was meant to hold five non-breaking spaces held five ordinary ones instead.

from helpers import (ai_result, ids, lexicon, sample, scan_json, scan_module,
                     scan_text, tier1_table_terms, written)


def test_fingerprints_are_detected():
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "tricky.md",
                       "A line with a zero\u200bwidth space.\n\n"
                       "See https://example.com/x?utm_source=chatgpt.com for more.\n\n"
                       "Contact [Your Name] before 2025-XX-XX.\n\n"
                       "As of my last training update, this was true. citeturn0search0\n")
        found = set(ids(scan_json(path)))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    for pattern_id in ("hidden-unicode", "ai-utm", "placeholder",
                       "cutoff-disclaimer", "citation-leak"):
        assert pattern_id in found, "%s missing from %s" % (pattern_id, found)


# --------------------------------------------------------------------------
# the lexicon and patterns.md agree
#
# Drift here is silent and one-directional: the table says replace on sight, the
# engine never flags it, and nobody notices until somebody compares the two by
# hand.
# --------------------------------------------------------------------------

def test_every_section_12_word_resolves_in_tier1():
    lex = lexicon()
    known = ({w.lower() for w in lex["tier1"]}
             | {p.lower() for p in lex["tier1_phrases"]})
    missing = sorted(t for t in tier1_table_terms() if t not in known)
    assert not missing, str(missing)


def test_section_12_is_not_empty():
    """Vacuous if the table parser silently returns nothing, which it has."""
    terms = tier1_table_terms()
    assert len(terms) > 30, "got %d" % len(terms)


def test_the_tiers_do_not_overlap():
    lex = lexicon()
    for a, b in (("tier1", "tier2"), ("tier1", "tier3"), ("tier2", "tier3")):
        overlap = sorted({w.lower() for w in lex[a]} & {w.lower() for w in lex[b]})
        assert not overlap, "%s and %s share %s" % (a, b, overlap)


def test_key_is_not_a_tier3_word():
    assert "key" not in {w.lower() for w in lexicon()["tier3"]}


def test_the_lexicon_declares_a_version():
    """PROOF.md pins its numbers to a catalogue version. Without this key the
    pin is to nothing and the table becomes archaeology."""
    assert lexicon().get("version") is not None


# --------------------------------------------------------------------------
# what counts as prose for the statistics
# --------------------------------------------------------------------------

def test_heading_text_is_not_measured_as_part_of_the_sentence_below_it():
    """A heading is a label and carries no terminal punctuation. With only the
    hashes stripped, the splitter glued the heading onto the first sentence
    below it and every section opener measured two or three words too long."""
    heads, _ = scan_text("## Background and context\n\nThe cluster was retired.\n\n"
                         "## Findings from the work\n\nThe latency improved twice.\n")
    assert heads["stats"]["avg_sentence_words"] == 4.0, heads["stats"]["avg_sentence_words"]
    assert heads["stats"]["sentence_count"] == 2, heads["stats"]["sentence_count"]


def test_heading_words_are_not_counted_as_prose_words():
    heads, _ = scan_text("## Background and context\n\nThe cluster was retired.\n\n"
                         "## Findings from the work\n\nThe latency improved twice.\n")
    assert heads["stats"]["word_count"] == 8, "got %d" % heads["stats"]["word_count"]


def test_a_block_quote_is_exempt_from_the_statistics():
    """Not just from flagging. A half-quotation document used to report the
    rhythm of whoever it was quoting as its own."""
    quoted, _ = scan_text("The cluster was retired.\n\n"
                          "> It was a long and winding road that led us here, "
                          "and we would not walk it again for anything.\n")
    assert quoted["stats"]["word_count"] == 4, "got %d" % quoted["stats"]["word_count"]


# --------------------------------------------------------------------------
# the invisible-character tables
#
# The one place in this engine where a save that normalizes whitespace, or an
# editor that drops a variation selector, changes behaviour without changing
# anything a reader can see. Worst case the U+00A0 key becomes a plain space and
# every space in every document reports as a paste artifact. Assert the
# codepoints, not the keys.
# --------------------------------------------------------------------------

def test_hidden_unicode_holds_exactly_the_eight_expected_codepoints():
    expected = [0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0x00A0, 0x202F]
    got = sorted(ord(c) for c in scan_module().HIDDEN_UNICODE)
    assert got == sorted(expected), str(["U+%04X" % c for c in got])


def test_every_hidden_unicode_key_is_one_character():
    keys = scan_module().HIDDEN_UNICODE
    assert all(len(c) == 1 for c in keys), str([repr(c) for c in keys if len(c) != 1])


def test_space_like_unicode_is_nbsp_and_narrow_nbsp():
    scan = scan_module()
    assert sorted(ord(c) for c in scan.SPACE_LIKE_UNICODE) == [0x00A0, 0x202F]
    assert set(scan.SPACE_LIKE_UNICODE) <= set(scan.HIDDEN_UNICODE)


def test_no_plain_space_leaked_into_the_tables():
    scan = scan_module()
    assert not (set(scan.HIDDEN_UNICODE) & set(" \t\n\r")), str(sorted(scan.HIDDEN_UNICODE))


def test_the_sentence_sentinel_is_a_character_prose_cannot_contain():
    """It used to be U+2024 ONE DOT LEADER, which a writer may legitimately have
    typed, and the swap-back turned theirs into a period inside the copy being
    measured."""
    assert scan_module().SENTENCE_SENTINEL == "\x00"


def test_a_legitimate_dot_leader_survives_the_split():
    parts = scan_module().split_sentences(
        "The dial reads 1․5 in the old style. Dr. Adeyemi signed it off.")
    assert any("1․5" in s for s in parts), str(parts)
    assert len(parts) == 2 and parts[1].startswith("Dr."), str(parts)


def test_emoji_rx_still_matches_the_presentation_selector():
    scan = scan_module()
    assert scan.EMOJI_RX.search("\ufe0f")
    assert scan.EMOJI_RX.search("\U0001F680")


# --------------------------------------------------------------------------
# false positives the reviewers found
# --------------------------------------------------------------------------

def test_a_mismatched_quote_pair_does_not_exempt_the_span():
    stray = ('The flag is " here. A comprehensive robust seamless meticulous '
             'pivotal delve into it.” Done.\n')
    result, _ = scan_text(stray)
    assert "tier1" in set(ids(result)), str(result["findings"])


def test_a_matched_quote_pair_still_exempts_the_span():
    paired = ('He said "a comprehensive robust seamless meticulous pivotal '
              'delve into it" and left.\n')
    result, _ = scan_text(paired)
    assert "tier1" not in ids(result), str([f["match"] for f in result["findings"]])


def test_one_non_breaking_space_is_not_a_p0():
    """Correct French typography, and a document typeset properly should not be
    told it has a credibility problem."""
    result, _ = scan_text("Une phrase\u00a0: le texte qui suit tient sur une ligne.\n")
    assert "hidden-unicode" not in ids(result), str(result["findings"])


def test_non_breaking_spaces_in_quantity_report_at_p2():
    result, _ = scan_text("a\u00a0b\u00a0c\u00a0d\u00a0e\u00a0f words to make a sentence.\n")
    hits = [f for f in result["findings"] if f["id"] == "hidden-unicode"]
    assert len(hits) == 1 and hits[0]["priority"] == "P2", str(hits)


def test_a_zero_width_space_is_still_a_p0():
    result, _ = scan_text("a\u200bb zero width here.\n")
    hits = [f for f in result["findings"] if f["id"] == "hidden-unicode"]
    assert len(hits) == 1 and hits[0]["priority"] == "P0", str(hits)


def test_the_exemption_suppresses_quoted_examples():
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "meta.md",
                       'A guide about AI writing.\n\n'
                       'Avoid phrases like "delve into the rich tapestry of innovation".\n\n'
                       '```\ndelve tapestry nestled showcasing\n```\n\n'
                       '> Experts believe this is a testament to progress.\n')
        with_exempt = scan_json(path)
        without = scan_json(path, "--no-exempt")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert len(with_exempt["findings"]) < len(without["findings"]), "%d vs %d" % (
        len(with_exempt["findings"]), len(without["findings"]))


# --------------------------------------------------------------------------
# the reported shape
# --------------------------------------------------------------------------

def test_json_output_carries_its_schema_and_lexicon_versions():
    """A consumer that pins the schema finds out at parse time when the shape
    moves, and a published measurement names the catalogue that produced it."""
    ai = ai_result()
    assert ai["schema_version"] >= 1
    assert ai["lexicon_version"] is not None
    assert ai["registers_version"] is not None


def test_every_finding_matches_the_schema():
    from rwlib import findings as findings_mod
    problems = findings_mod.validate(ai_result()["findings"])
    assert not problems, str(problems)
