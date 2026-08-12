#!/usr/bin/env python3
"""
HTML character references, from both directions.

An entity is the character it renders as. `&mdash;` is an em dash to every
reader, so it has to be one to the counter, the voice ban, and verify.py's "no
em dashes added" gate. Left alone, a find-and-replace over a document was enough
to pass all three while the rendered page was unchanged.

The mirror image costs more than it looks. Every entity ends in a semicolon,
and a profile that forbids semicolons reported one finding per `&amp;`,
`&nbsp;`, and `&#39;` in a README header. That is markup the writer never typed
punctuation into, and a checker that reports it is one people stop reading.

Both halves are decided in rwlib.markdown, which is why this file exists rather
than half a fix in test_voice.py and half in test_verify.py.

Stdlib only, 3.9+.
"""

from helpers import run_verify, scan_text, scan_with_rules, voice_ids

from rwlib import markdown as md

# A profile that forbids both, so the two directions can be asserted from one
# scan. Nothing else is set: the point is the mechanic, not the vocabulary.
STRICT = {
    "voice": "entity-test",
    "default_priority": "P0",
    "mechanics": {"em_dash": "forbid", "semicolon": "forbid"},
}

# Long enough to clear the reliability floor without saying anything the
# lexicon cares about, so the only findings are the ones under test.
FILLER = ("The build reads a manifest and writes a report. It runs from a "
          "checkout with nothing installed. Paths resolve against the file "
          "that holds them, so a directory can move.\n\n")


def body(line):
    return FILLER + line + "\n\n" + FILLER


# --------------------------------------------------------------------------
# the evasion direction: an entity dash is a dash
# --------------------------------------------------------------------------

def test_the_pattern_matches_every_spelling_of_an_em_dash():
    for spelling in ("—", "&mdash;", "&#8212;", "&#x2014;", "&#X2014;"):
        assert md.PROSE_DASH_RX.search("a %s b" % spelling), spelling


def test_an_entity_em_dash_is_counted_in_the_statistics():
    result, _ = scan_text(body("The report is written &mdash; and then read."))
    assert result["stats"]["em_dashes"] == 1, result["stats"]
    assert result["stats"]["em_dashes_per_1k"] > 0


def test_an_entity_em_dash_trips_a_voice_that_forbids_em_dashes():
    result, _ = scan_with_rules(
        body("The report is written &mdash; and then read."), STRICT)
    assert "voice-em-dash" in voice_ids(result), result["findings"]


def test_verify_catches_an_em_dash_added_as_an_entity():
    """The gate that a rewrite never adds an em dash. A rewrite that spells it
    `&mdash;` renders the same page, so it has to fail the same way."""
    before = body("The report is written, and then it is read.")
    after = body("The report is written &mdash; and then read.")
    result, code = run_verify(before, after)
    assert code != 0, result
    assert any(v["kind"] == "em dashes added" for v in result["violations"]), \
        result["violations"]


def test_an_entity_numeric_range_is_not_a_dash():
    """`2010&ndash;2023` is correct typography, the same as `2010–2023`. The two
    spellings have to agree or the entity form is stricter than the character."""
    assert not md.PROSE_DASH_RX.search("covering 2010&ndash;2023 in full")
    assert not md.PROSE_DASH_RX.search("covering 2010–2023 in full")


def test_a_spaced_entity_en_dash_is_still_a_dash():
    """A spaced en dash stands in for an em dash whichever way it is spelled."""
    assert md.PROSE_DASH_RX.search("the report &ndash; and then the read")


# --------------------------------------------------------------------------
# the false-positive direction: an entity's semicolon is markup
# --------------------------------------------------------------------------

def test_entities_do_not_trip_a_voice_that_forbids_semicolons():
    line = ("Sponsors &amp; partners, spaced&nbsp;out, with &#39;quotes&#39; "
            "and &#x2019;curls&#x2019; around them.")
    result, _ = scan_with_rules(body(line), STRICT)
    assert "voice-semicolon" not in voice_ids(result), result["findings"]


def test_a_real_semicolon_beside_an_entity_still_reports():
    """The guard above must not have turned the rule off. One entity and one
    genuine splice on the same line, and exactly the splice is reported."""
    line = "Sponsors &amp; partners are listed; the rest are not."
    result, _ = scan_with_rules(body(line), STRICT)
    reported = [f for f in result["findings"] if f["id"] == "voice-semicolon"]
    assert len(reported) == 1, reported


def test_a_bare_ampersand_does_not_swallow_a_later_semicolon():
    """`&` in prose is ordinary, and the pattern is bounded so that a stray one
    does not read as an entity running to the next semicolon half a line away."""
    line = "Ship it & be done with it; that is the whole rule."
    result, _ = scan_with_rules(body(line), STRICT)
    assert len([f for f in result["findings"]
                if f["id"] == "voice-semicolon"]) == 1, result["findings"]


def test_blank_entities_leaves_the_dash_entities_visible_to_the_counter():
    """Deliberately not folded into apply_exemptions: the semicolon check wants
    `&mdash;` gone and the dash check wants it there, and only one of them gets
    to blank it."""
    text = "written &mdash; and read &amp; filed"
    blanked = md.blank_entities(text)
    assert "&mdash;" not in blanked
    assert md.PROSE_DASH_RX.search(text)
