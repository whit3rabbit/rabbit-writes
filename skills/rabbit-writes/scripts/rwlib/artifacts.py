#!/usr/bin/env python3
"""
Paste artifacts: what survives a copy out of a chat window.

These are facts about how a file was produced rather than about what it says,
which is why three different scripts need the same table. scan.py reports them,
fixes.py removes the ones it is allowed to remove, and verify.py grants the
removal a carve-out so a rewrite that strips one still passes preservation.

Written as escapes, never as the characters themselves. As literals these keys
are invisible: two that look identical in an editor merge into one and a check
disappears without a word, and any tool that normalizes whitespace can turn the
U+00A0 key into a plain space, at which point the counter reads every space in
every document as a paste artifact. The test suite pins the exact codepoints, so
a normalizing save fails the build instead of the scan.

Stdlib only, 3.9+.
"""

import re

HIDDEN_UNICODE = {
    "\u200b": "zero-width space",
    "\u200c": "zero-width non-joiner",
    "\u200d": "zero-width joiner",
    "\u2060": "word joiner",
    "\ufeff": "byte-order mark",
    "\u00ad": "soft hyphen",
    "\u00a0": "non-breaking space",
    "\u202f": "narrow no-break space",
}

# The invisible characters above have no honest use in prose, so one occurrence
# is a paste artifact and a P0. The two space-like ones are different: a
# non-breaking space is correct French typography, correct in front of a unit,
# and correct in a name that must not wrap. Calling those a credibility killer
# fails documents that were typeset properly, so they report at P2 and only once
# there are enough of them to look mechanical.
SPACE_LIKE_UNICODE = frozenset({"\u00a0", "\u202f"})
SPACE_LIKE_TOLERANCE = 3

# Everything safe to delete outright, because it carries no meaning at all.
ZERO_WIDTH = {ch: name for ch, name in HIDDEN_UNICODE.items()
              if ch not in SPACE_LIKE_UNICODE}

# One exception to "no honest use". A zero-width joiner between two pictographs
# is the emoji: U+1F468 ZWJ U+1F4BB is the man-technologist glyph, and family
# and profession emoji are all built this way. Deleting it does not clean the
# document, it silently replaces one emoji with two, and reporting it calls an
# ordinary README a paste artifact. One of the trending READMEs in the corpus
# tripped this. Written as an escape, like every key above, and for the same
# reason: as a literal it is invisible and a normalizing save deletes the check.
ZWJ = "\u200d"


def _pictographic(ch):
    # No unicodedata category covers "emoji", so this is the ranges that matter:
    # the pictograph blocks, the miscellaneous symbols, and the variation
    # selector and skin-tone modifiers that attach to them.
    point = ord(ch)
    return (0x1F000 <= point <= 0x1FAFF or 0x2600 <= point <= 0x27BF
            or 0xFE0E <= point <= 0xFE0F or 0x1F3FB <= point <= 0x1F3FF
            or point in (0x2640, 0x2642, 0x00A9, 0x00AE, 0x2122))


def load_bearing_zwj(text, index):
    """True when the character at `index` is a joiner inside an emoji sequence.

    Deliberately narrow: both neighbours have to be pictographic. A joiner
    between two letters is still the paste artifact it has always been, which is
    the case this table exists for.
    """
    if text[index] != ZWJ:
        return False
    if index == 0 or index + 1 >= len(text):
        return False
    return _pictographic(text[index - 1]) and _pictographic(text[index + 1])


def occurrences(text, ch):
    """Offsets of every `ch` that counts as a paste artifact.

    The one shared definition of "how many are in here". scan.py reports off it
    and fixes.py thresholds off it, because the two used to count differently:
    the scan saw the whole file and the fixer saw only the spans it was allowed
    to edit, so a document could be reported and then neither fixed nor
    explained. Emoji joiners are excluded here rather than at either caller.
    """
    if ch not in text:
        return []
    out, index = [], text.find(ch)
    while index != -1:
        if not load_bearing_zwj(text, index):
            out.append(index)
        index = text.find(ch, index + 1)
    return out

# Tracking parameters an AI tool appends to a link it hands out. Anchored, so
# only a whole query parameter matches and a URL that happens to contain the
# substring elsewhere is left alone.
AI_PARAM_RX = re.compile(
    r"(utm_source=(chatgpt|openai|copilot|claude|perplexity|gemini)[a-z.]*"
    r"|referrer=grok\.com)\Z", re.I)


def norm_url(url):
    """The URL with AI tracking parameters dropped and the query rebuilt.

    Shared by the fixer, which produces this string, and the verifier, which has
    to accept it. One function, so a fixed URL cannot fail the verification the
    fixer runs on its own output.
    """
    if "?" not in url:
        return url
    base, _, rest = url.partition("?")
    query, hash_sep, fragment = rest.partition("#")
    kept = [p for p in query.split("&") if p and not AI_PARAM_RX.match(p)]
    out = base + ("?" + "&".join(kept) if kept else "")
    # A bare trailing "#" is kept. Dropping it makes a URL that ends in an empty
    # fragment compare unequal to the identical URL on the other side, which is
    # a violation nobody caused.
    return out + hash_sep + fragment
