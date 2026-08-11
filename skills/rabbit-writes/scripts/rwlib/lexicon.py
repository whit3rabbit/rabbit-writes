#!/usr/bin/env python3
"""
The pattern catalogue, loaded once and shared.

scan.py scores against it, verify.py gates against it, and PROOF.md publishes
numbers measured against it. Those three only mean the same thing if they read
the same file, and "measured against lexicon 3" is only checkable if the file
says which version it is. `version` is that field, echoed into scan's --json
output and into PROOF.md's header.

Stdlib only, 3.8+.
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LEXICON_PATH = os.path.join(os.path.dirname(HERE), "lexicon.json")

# Findings the engine raises itself rather than from a catalogue pattern. A
# register may name any of these in its skip or relax set, so anything checking
# those ids has to know them.
SYNTHETIC_FINDING_IDS = frozenset({
    "hidden-unicode", "tier1", "clarity", "tier2-cluster", "tier3-density",
    "uniformity", "low-diversity", "trigram-repetition", "uniform-paragraphs",
    "em-dash-rate",
})

_CACHE = {}


def load(path=LEXICON_PATH):
    """The parsed lexicon. Cached by path: scan.py reads it once per document
    and the corpus regression test runs it over a hundred of them."""
    if path not in _CACHE:
        with open(path, encoding="utf-8") as fh:
            _CACHE[path] = json.load(fh)
    return _CACHE[path]


def version(path=LEXICON_PATH):
    """The lexicon's declared version, or None on a file that predates the key.

    None rather than a guess: a report that invents a version number is worse
    than one that admits it does not know, because the whole point of the field
    is to make a published measurement reproducible.
    """
    return load(path).get("version")


def word_regex(entries):
    """Whole-word alternation, longest first so `game-changer` wins over `game`.

    The boundary is `(?<![\\w-])` rather than `\\b`, because a hyphen is a word
    character to a reader and not to `re`: without it, "cutting-edge" matches
    the bare word "edge" as well.
    """
    escaped = sorted((re.escape(e) for e in entries), key=len, reverse=True)
    return re.compile(r"(?i)(?<![\w-])(" + "|".join(escaped) + r")(?![\w-])")


def phrase_regex(entries):
    """Same, for multi-word entries, with runs of whitespace made flexible so a
    phrase still matches across a line break."""
    escaped = sorted((re.escape(e).replace(r"\ ", r"\s+") for e in entries),
                     key=len, reverse=True)
    return re.compile(r"(?i)\b(" + "|".join(escaped) + r")\b")


def compiled_patterns(path=LEXICON_PATH, skip=()):
    """[(entry, compiled_rx)] for every catalogue pattern that compiles.

    A pattern that does not compile is reported to stderr and dropped rather
    than raising: one bad regex in a user-edited lexicon should cost that one
    rule, not the whole scan.
    """
    import sys
    out = []
    for p in load(path).get("patterns", []):
        if p["id"] in skip:
            continue
        try:
            out.append((p, re.compile(p["rx"])))
        except re.error as exc:
            print("lexicon: bad regex %s (%s)" % (p["id"], exc), file=sys.stderr)
    return out
