#!/usr/bin/env python3
"""
Straight quotes pair positionally, so a skipped pair poisons the rest of the line.

A straight quote closes with the same character it opens with. There is no way
to tell an opener from a closer except by counting from the left, which makes
every quotation on a paragraph depend on every quotation before it having been
matched. QUOTED_RX used to carry a `{4,400}` body, and the lower bound is what
broke that chain: `("No.")` holds three characters, fell under the floor, and
was skipped whole. Its *closing* quote then read as an opener and ran forward to
the opening quote of the next real quotation, swallowing it. What was left was
`circle back"` sitting in prose with no quotes around it.

That is a false positive in the one mechanism that exists to prevent false
positives. `apply_exemptions` promises a document quoting a banned phrase in
order to name it does not score as one, and voice-setup/SKILL.md does exactly
that: it asks the writer which cliches to ban and offers `"circle back"` as an
example. The scan raised a P0 banned phrase against it and CI went red.

`facts.quoted` paid for it in the other direction. A span running from one
quotation's close to the next one's open is not a quotation, and verify.py
compares quotations verbatim, so the fixer could be told a quotation went
missing when what actually changed was ordinary prose between two of them.

Length is a judgement about a span that matched, never about where one ends.
The callers that want a floor apply their own: facts.quoted has
QUOTED_MIN_WORDS. This file pins the separation.

Stdlib only, 3.9+.
"""

from helpers import scan_with_rules, voice_ids

from rwlib import facts
from rwlib import markdown as md

# The shape voice-setup/SKILL.md uses: name a phrase you want banned, in quotes,
# on a line that follows a short quoted example. Nothing about the profile
# matters here except that it bans the phrase being named.
NAMING = {
    "voice": "quote-pairing-test",
    "default_priority": "P0",
    "banned_phrases": ["circle back"],
}


def quoted_spans(text):
    return [m.group(0) for m in md.QUOTED_RX.finditer(text)]


def test_a_short_quotation_does_not_swallow_the_next_one():
    # Each body is under the old four-character floor, which is the whole point:
    # every one of these was skipped, and skipping inverted the parity of the
    # quotes after it.
    cases = [
        '("No.")',
        'say "hi" first',
        'the "x" flag',
        'an empty "" value',
    ]
    for short in cases:
        text = short + '\nfiller (e.g. "circle back", "thought leader")'
        spans = quoted_spans(text)
        assert '"circle back"' in spans, (short, spans)
        assert '"thought leader"' in spans, (short, spans)


def test_a_quoted_example_of_a_banned_phrase_is_exempt_after_a_short_quotation():
    text = (
        '2. Do you ban one-word period sentences ("No.")?\n'
        '3. What corporate filler (e.g. "circle back") do you refuse?\n'
    )
    # --check, because the exit code is the thing that went red. Without it
    # scan.py reports and returns 0 whatever it found, so a gate assertion
    # written against a bare --json run passes on a document that fails CI.
    result, code = scan_with_rules(text, NAMING, "--check")
    assert "voice-banned-phrase" not in voice_ids(result), result["findings"]
    assert code == 0, result["counts"]


def test_the_same_phrase_unquoted_still_reports():
    # The exemption is about quotation, not about the phrase. A profile that
    # bans "circle back" has to keep firing on prose that uses it, or the fix
    # above bought silence instead of accuracy.
    text = (
        '2. Do you ban one-word period sentences ("No.")?\n'
        '3. Let us circle back on the roadmap next quarter.\n'
    )
    result, code = scan_with_rules(text, NAMING, "--check")
    assert "voice-banned-phrase" in voice_ids(result), result["findings"]
    assert code == 1, result["counts"]


def test_no_quotation_spans_the_gap_between_two_quotations():
    text = 'He said "No." and then, much later in the line, she said "yes it is".'
    for span in quoted_spans(text):
        assert "and then" not in span, span


def test_a_short_quotation_is_still_below_the_word_floor_for_facts():
    # Pairing changed, the reported set did not. facts.quoted owns its own
    # threshold and a three-character aside is not a quotation to compare.
    assert facts.quoted('He said "No." to that.') == []


def test_each_quote_style_still_closes_with_its_own_kind():
    # The floor moved and the pairing rule did not. A straight quote must not
    # close on a curly one, which is what the comment above _QUOTE_PAIRS is for.
    spans = quoted_spans('a "straight and “curly” b')
    assert all("straight" not in s for s in spans), spans
    assert "“curly”" in spans, spans


def test_a_blank_line_still_ends_an_unclosed_quotation():
    text = 'an unclosed "quote mark here\n\nA new paragraph with no quotes.'
    assert quoted_spans(text) == []
