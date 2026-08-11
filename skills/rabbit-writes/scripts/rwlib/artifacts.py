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

Stdlib only, 3.8+.
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
