#!/usr/bin/env python3
"""
Opt-in inflection on a ban list.

The shipped profile lists `synergy` and `synergies`, `thought leader` and
`thought leaders`, `bad actor` and `bad actors`, `circle back` and `circling
back`. Every pair is a line somebody had to remember, and forgetting one leaves
a ban that reads as enforced and is not. `"inflect": true` covers the regular
cases.

Opt-in is the load-bearing half. A profile that says nothing behaves exactly as
it did, and a narrow ban written on purpose stays narrow, which is why the
default-off tests below matter as much as the expansion ones.

Stdlib only, 3.9+.
"""

from helpers import scan_with_rules, voice_ids

from rwlib import inflect, voices

FILLER = ("The build reads a manifest and writes a report. It runs from a "
          "checkout with nothing installed. Paths resolve against the file "
          "that holds them, so a directory can move.\n\n")


def banned(text, entries, key="banned_words"):
    rules = {"voice": "t", "default_priority": "P0", key: entries}
    result, _ = scan_with_rules(FILLER + text + "\n\n" + FILLER, rules)
    return voice_ids(result)


# --------------------------------------------------------------------------
# the suffix rules
# --------------------------------------------------------------------------

def test_the_regular_suffixes():
    assert inflect.forms("synergy") == ["synergy", "synergies", "synergied",
                                        "synergying"]
    assert inflect.plural("box") == "boxes"
    assert inflect.plural("church") == "churches"
    assert inflect.plural("actor") == "actors"
    assert inflect.past("leverage") == "leveraged"
    assert inflect.gerund("leverage") == "leveraging"
    assert inflect.gerund("agree") == "agreeing"


def test_y_after_a_vowel_is_not_a_consonant_y():
    """`day` takes an s. `synergy` takes ies. Getting this backwards produces
    `daies`, a pattern that matches nothing and reads as a rule that fired."""
    assert inflect.plural("day") == "days"
    assert inflect.plural("synergy") == "synergies"


def test_a_phrase_varies_one_word_at_a_time():
    """Both ends, because the head of the phrase is at the front in `circle
    back` and at the back in `thought leader`, and no rule here knows which."""
    out = inflect.forms("thought leader")
    assert "thought leaders" in out, out
    assert "circling back" in inflect.forms("circle back")
    # One at a time, not the cross product: nobody writes `circling backing`.
    assert "circling backing" not in inflect.forms("circle back")


def test_expansion_is_off_unless_asked_for():
    assert inflect.expand(["synergy"]) == ["synergy"]
    assert inflect.expand([{"word": "synergy"}]) == ["synergy"]
    assert "synergies" in inflect.expand([{"word": "synergy", "inflect": True}])


def test_an_entry_naming_no_term_is_dropped_rather_than_crashing():
    """One malformed line in a hand-edited profile costs that line. The same
    bargain compiled_patterns makes for the catalogue."""
    assert inflect.expand(["ok", {}, {"inflect": True}, 7, None]) == ["ok"]


# --------------------------------------------------------------------------
# through the scanner
# --------------------------------------------------------------------------

def test_a_plain_string_entry_still_bans_exactly_itself():
    """The default has not moved. This is the assertion that lets the feature
    ship: an existing profile scans the way it always did."""
    assert "voice-banned-word" in banned("We need more synergy here.", ["synergy"])
    assert "voice-banned-word" not in banned("We need more synergies here.",
                                             ["synergy"])


def test_an_inflected_entry_catches_the_plural():
    hits = banned("We need more synergies here.",
                  [{"word": "synergy", "inflect": True}])
    assert "voice-banned-word" in hits, hits


def test_an_inflected_phrase_catches_the_plural():
    hits = banned("The thought leaders will convene.",
                  [{"phrase": "thought leader", "inflect": True}],
                  key="banned_phrases")
    assert "voice-banned-phrase" in hits, hits


def test_a_narrow_ban_stays_narrow():
    """`lowly` is banned in the shipped profile and `lowlying` is a different
    word. An author who wrote one word meant one word."""
    assert "voice-banned-word" not in banned(
        "The low lying cable runs under the floor here.", ["lowly"])


# --------------------------------------------------------------------------
# inheritance
# --------------------------------------------------------------------------

def test_a_ban_list_merges_on_the_term_not_the_entry():
    """A dict is unhashable, so the old union raised TypeError the first time a
    child inherited from a parent using the object form. Keying on the term also
    lets a child restate a word in order to add `inflect` to it, rather than
    ending up with the word listed twice."""
    parent = {"banned_words": ["synergy", "piggyback"]}
    child = {"banned_words": [{"word": "synergy", "inflect": True}]}
    merged = voices.merge(parent, child)
    assert len(merged["banned_words"]) == 2, merged["banned_words"]
    assert "synergies" in inflect.expand(merged["banned_words"])
    assert "piggyback" in inflect.expand(merged["banned_words"])
