#!/usr/bin/env python3
"""
Sentence and word segmentation.

English only, and deliberately so. The abbreviation list, the capital-letter
initial rule, the syllable heuristic, and the word pattern are all calibrated on
English orthography. rwlib.language.looks_like_english exists so a caller can
say that out loud instead of silently reporting nonsense.

Stdlib only, 3.8+.
"""

import re

# Stands in for a period that must not end a sentence, for the length of one
# split. A NUL cannot occur in a document a person edits, which is the whole
# requirement: the last step of split_sentences turns every sentinel back into a
# period, so a sentinel that a writer could legitimately have typed would be a
# silent rewrite of the copy being measured. It used to be U+2024 ONE DOT
# LEADER, which is a real character with real uses.
SENTENCE_SENTINEL = "\x00"

ABBREV_RX = re.compile(
    r"\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|etc|vs|approx|dept|est|vol|Inc|Ltd|Fig|No)\.",
    re.I,
)

WORD_RX = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def split_sentences(text):
    """Sentences, with the periods that are not sentence ends held back."""
    text = text.replace(SENTENCE_SENTINEL, "")
    protected = ABBREV_RX.sub(
        lambda m: m.group(0).replace(".", SENTENCE_SENTINEL), text)
    protected = re.sub(r"\b([A-Z])\.", r"\1" + SENTENCE_SENTINEL, protected)
    protected = re.sub(r"(?m)^\s*(\d+)\.", r"\1" + SENTENCE_SENTINEL, protected)
    parts = re.split(r"(?<=[.!?])[\s\n]+", protected)
    return [p.replace(SENTENCE_SENTINEL, ".").strip() for p in parts if p.strip()]


def tokenize(text):
    return WORD_RX.findall(text.lower())


def syllables(word):
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    groups = re.findall(r"[aeiouy]+", word)
    n = len(groups)
    if word.endswith("e") and n > 1 and not word.endswith(("le", "ee", "ye")):
        n -= 1
    return max(n, 1)
