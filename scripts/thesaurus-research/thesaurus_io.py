#!/usr/bin/env python3
"""
The one home for the thesaurus research pipeline's shared facts.

The dataset manifest (URL, SHA-256, license), the generation thresholds, the
paths, the candidates-file schema check, and the parsers for both raw formats
live here, and the numbered stages import them. A threshold restated in two
stages is two thresholds the moment somebody edits one.

Dataset choice is a decision, so it is recorded where the data is named.
Princeton WordNet 3.1 supplies synonym grouping (synsets), sense order, per
part-of-speech polysemy counts, and glosses for reviewer evidence. Norvig's
count_1w.txt, derived from the public Google ngram release, supplies the
frequency that decides direction: reach is the common word, overreach the rare
one. Moby Thesaurus II was considered and dropped: its associations are loose
to the point of noise (the "get" line runs to hundreds of barely related
words), so every Moby family would need the heavier human filtering this
pipeline exists to reduce. Do not re-add it without reading that sentence.

Stdlib only, 3.9+.
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

# Raw downloads live outside git: thesaurus.json ships and candidates.json is
# committed evidence, but a 16MB third-party tarball is neither. The manifest
# below commits each URL, hash, and license, and 01_fetch_datasets.py refetches
# and verifies, which is the same bargain the detector corpus makes.
RAW_DIR = os.path.join(REPO_ROOT, "docs", "thesaurus-research", "raw")
CANDIDATES_PATH = os.path.join(REPO_ROOT, "docs", "thesaurus-research",
                               "candidates.json")
THESAURUS_PATH = os.path.join(REPO_ROOT, "skills", "voice-setup", "scripts",
                              "thesaurus.json")
CORPUS_DIR = os.path.join(REPO_ROOT, "docs", "readme-analysis", "repos")

# Each entry: filename in RAW_DIR, source URL, SHA-256 of the download, byte
# size at pinning time, and the license that makes shipping derived words
# defensible. The hashes were computed from a fetch on 2026-08-14, and a
# mismatch on refetch means the source moved, not that this file is wrong.
DATASETS = {
    "wordnet": {
        "filename": "wn3.1.dict.tar.gz",
        "url": "https://wordnetcode.princeton.edu/wn3.1.dict.tar.gz",
        "sha256": "3f7d8be8ef6ecc7167d39b10d66954ec734280b5bdcd57f7d9eafe429d11c22a",
        "bytes": 16358468,
        "license": "WordNet 3.0 license (permissive, redistribution allowed)",
        # The tarball unpacks to dict/, and the parsers read these members.
        "extract_dir": "dict",
    },
    "count_1w": {
        "filename": "count_1w.txt",
        "url": "https://norvig.com/ngrams/count_1w.txt",
        "sha256": "51df159fd3de12b20e403c108f526e96dbd723d9cabdd5f17955cdc16059e690",
        "bytes": 4956241,
        "license": "derived from the public Google Web Trillion Word Corpus release",
    },
}

# The whole calibration of 02_generate_candidates.py, echoed into the
# candidates file's `generated` block as a record of what produced it.
#
# REACH_MAX_RANK: a seed must sit inside the top 5000 words. Every reach word
#   in the hand-written families does, and past 5000 a word is no longer "the
#   plain word a person actually writes".
# RATIO_MIN: count(reach) / count(term), on counts rather than ranks because
#   ranks distort in the Zipf tail. Below it the term is excluded, not
#   flagged: a near-tie like big/large is a choice, not overreach.
# SEED_SENSES_MAX: only a seed's first senses per part of speech. WordNet
#   orders a lemma's senses by tagged frequency, so this keeps "get = obtain"
#   and drops "get = beget", whose synonyms pass every frequency filter while
#   being synonyms of a sense the writer never means.
# POLYSEMY_MAX: a term with more synsets than this is flagged, because
#   fixes.py applies substitutions with no part-of-speech awareness and a
#   many-sense term is a rewrite of senses nobody vetted.
# CORPUS_FLAG_DOCS: a term appearing in this many of the 100 corpus READMEs
#   is ordinary technical vocabulary ("require", "state", "execute") and is
#   flagged rather than left pending.
# FAMILY_LIMIT: cap on emitted families, reviewable in one sitting.
REACH_MAX_RANK = 5000
RATIO_MIN = 3.0
SEED_SENSES_MAX = 3
POLYSEMY_MAX = 4
CORPUS_FLAG_DOCS = 5
FAMILY_LIMIT = 150

SCHEMA_VERSION = 1
STATUSES = ("pending", "flagged", "accepted", "rejected")
THRESHOLD_KEYS = ("reach_max_rank", "ratio_min", "seed_senses_max",
                  "polysemy_max", "corpus_flag_docs", "family_limit")

# WordNet's four database files, and the part-of-speech letter each carries.
# data.adj holds both `a` and `s` (satellite) synsets and the two are folded
# into one adjective part of speech everywhere here, because the split is a
# graph-structure fact and not a vocabulary one.
WN_FILES = {"noun": "n", "verb": "v", "adj": "a", "adv": "r"}

WORD_RX = re.compile(r"^[a-z]+$")


def thresholds():
    """The generation constants, keyed the way the candidates file records them."""
    return {
        "reach_max_rank": REACH_MAX_RANK,
        "ratio_min": RATIO_MIN,
        "seed_senses_max": SEED_SENSES_MAX,
        "polysemy_max": POLYSEMY_MAX,
        "corpus_flag_docs": CORPUS_FLAG_DOCS,
        "family_limit": FAMILY_LIMIT,
    }


def load_counts(path):
    """(counts, ranks) from a count_1w-format file: `word<TAB>count` per line,
    ordered by count descending, so rank is the line number from 1."""
    counts, ranks = {}, {}
    with open(path, encoding="utf-8") as fh:
        for rank, line in enumerate(fh, 1):
            parts = line.split()
            if len(parts) != 2:
                continue
            word, count = parts[0].lower(), parts[1]
            if word in counts or not count.isdigit():
                continue
            counts[word] = int(count)
            ranks[word] = rank
    return counts, ranks


def _clean_lemma(raw):
    """A data-file word field, lowercased, with the adjective syntactic marker
    (`beautiful(ip)`) stripped. Underscores stay: the caller decides what a
    multi-word lemma means."""
    return raw.split("(")[0].lower()


class WordNet:
    """The four WordNet database files, parsed once and queried.

    index.<pos> supplies each lemma's synset offsets in sense order (tagged
    frequency, most common sense first) and its synset count, which is the
    polysemy number. data.<pos> supplies each synset's member lemmas and its
    gloss. Nothing else in the database is read.
    """

    def __init__(self, dict_dir):
        # (pos_letter, lemma) -> offsets in sense order
        self.senses = {}
        # pos_letter -> lemma -> synset count
        self.polysemy = {letter: {} for letter in WN_FILES.values()}
        # (pos_letter, offset) -> (lemmas, gloss)
        self.synsets = {}
        for name, letter in WN_FILES.items():
            self._read_index(os.path.join(dict_dir, "index." + name), letter)
            self._read_data(os.path.join(dict_dir, "data." + name), letter)

    def _read_index(self, path, letter):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith(" "):
                    continue  # license header
                parts = line.split()
                if len(parts) < 6:
                    continue
                lemma = parts[0].lower()
                synset_cnt = int(parts[2])
                p_cnt = int(parts[3])
                offsets = parts[4 + p_cnt + 2:]
                self.senses[(letter, lemma)] = offsets
                self.polysemy[letter][lemma] = synset_cnt

    def _read_data(self, path, letter):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith(" "):
                    continue
                head, _, gloss = line.partition("|")
                parts = head.split()
                if len(parts) < 5:
                    continue
                offset = parts[0]
                # parts[2] is ss_type: `s` folds into `a` by keying on the
                # file's letter rather than the synset's own type.
                w_cnt = int(parts[3], 16)
                lemmas = [_clean_lemma(parts[4 + i * 2])
                          for i in range(w_cnt)]
                self.synsets[(letter, offset)] = (lemmas, gloss.strip())

    def lemma_pos(self, lemma):
        """The part-of-speech letters this lemma exists under."""
        return sorted(letter for letter in WN_FILES.values()
                      if lemma in self.polysemy[letter])

    def polysemy_of(self, lemma):
        """Per-pos synset counts, zero-filled, for the evidence block."""
        return {letter: self.polysemy[letter].get(lemma, 0)
                for letter in sorted(WN_FILES.values())}

    def top_synsets(self, lemma, letter, limit):
        """The lemma's first `limit` synsets under one part of speech, in
        sense order, as (offset, lemmas, gloss)."""
        out = []
        for offset in self.senses.get((letter, lemma), [])[:limit]:
            lemmas, gloss = self.synsets.get((letter, offset), ([], ""))
            out.append((offset, lemmas, gloss))
        return out


def candidate_problems(data):
    """Everything wrong with a candidates object, as prose. Empty means valid.

    Called by 02 before writing, 03 before annotating, 04 before merging, and
    the harness, so a hand-edit that breaks the shape is caught by whichever
    stage touches the file next rather than by a reviewer's confusion.
    """
    out = []
    if not isinstance(data, dict):
        return ["candidates data is %s, not an object" % type(data).__name__]
    if data.get("schema_version") != SCHEMA_VERSION:
        out.append("schema_version is %r, this code reads %d"
                   % (data.get("schema_version"), SCHEMA_VERSION))
    generated = data.get("generated")
    if not isinstance(generated, dict):
        out.append("no `generated` block recording what produced the file")
    else:
        held = generated.get("thresholds", {})
        for key in THRESHOLD_KEYS:
            if key not in held:
                out.append("generated.thresholds is missing %r" % key)
    families = data.get("families")
    if not isinstance(families, list):
        return out + ["no families list"]
    seen = set()
    for i, family in enumerate(families):
        if not isinstance(family, dict):
            out.append("family %d is not an object" % i)
            continue
        reach = family.get("reach")
        label = "family %d (reach %r)" % (i, reach)
        if not isinstance(reach, str) or not reach:
            out.append("family %d has no reach word" % i)
            continue
        if reach in seen:
            out.append("%s appears twice" % label)
        seen.add(reach)
        if not isinstance(family.get("reach_rank"), int):
            out.append("%s has no integer reach_rank" % label)
        if family.get("status") not in STATUSES:
            out.append("%s has status %r, not one of %s"
                       % (label, family.get("status"), "/".join(STATUSES)))
        terms = family.get("overreach")
        if not isinstance(terms, list) or not terms:
            out.append("%s has no overreach list" % label)
            continue
        for term in terms:
            if not isinstance(term, dict) or not term.get("term"):
                out.append("%s has a term entry with no term" % label)
                continue
            tlabel = "%s term %r" % (label, term["term"])
            if term.get("status") not in STATUSES:
                out.append("%s has status %r" % (tlabel, term.get("status")))
            for key in ("gloss", "polysemy", "cross_pos", "flags"):
                if key not in term:
                    out.append("%s is missing evidence field %r"
                               % (tlabel, key))
    return out


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, data):
    """indent=2 with a trailing newline, matching thesaurus.json, so a
    regeneration with no changes is a byte-identical no-op."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
