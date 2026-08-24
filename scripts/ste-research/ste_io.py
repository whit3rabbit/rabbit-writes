#!/usr/bin/env python3
"""
The one home for the STE-vocabulary research pipeline's shared facts.

Paths, the corpus-flag threshold, and the candidates-file schema check live
here, the same split thesaurus_io.py uses for the sibling pipeline, so a
threshold restated in two stages does not become two thresholds the moment
somebody edits one.

Unlike the thesaurus pipeline, there is no fetch stage: the raw material is
already a committed file, skills/rabbit-writes/scripts/ste_dictionary_full.json,
itself the output of a one-time PDF parse documented in
skills/rabbit-writes/scripts/SOURCING.md. This pipeline starts from that file,
not from a network download.

Stdlib only, 3.9+.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

DICTIONARY_PATH = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts",
                               "ste_dictionary_full.json")
CANDIDATES_PATH = os.path.join(REPO_ROOT, "docs", "ste-research",
                               "candidates.json")
STE_LEXICON_PATH = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts",
                                "ste_lexicon.json")
CORPUS_DIR = os.path.join(REPO_ROOT, "docs", "readme-analysis", "repos")

# A candidate appearing in this many of the 100 corpus READMEs is ordinary
# technical vocabulary in software documentation, not evidence of an STE
# violation worth flagging: ASD-STE100 is an aerospace-maintenance standard,
# and words it bans for that register ("ability", "any", "run") are exactly
# the connective tissue of a README. Same value thesaurus_io.py uses, for the
# same reason: it is the number that came out of measuring the sibling
# pipeline's own overreach terms against this corpus, not a fresh guess.
CORPUS_FLAG_DOCS = 5

REQUIRED_KEYS = ("word", "source_pos", "alternative", "alt_pos", "status",
                 "flags")
VALID_STATUSES = ("candidate", "flagged", "accepted", "rejected")


def candidate_problems(data):
    """[] when `data["candidates"]` is well-formed, else what is wrong."""
    out = []
    if not isinstance(data, dict) or "candidates" not in data:
        return ["missing a top-level \"candidates\" list"]
    for i, entry in enumerate(data["candidates"]):
        missing = [k for k in REQUIRED_KEYS if k not in entry]
        if missing:
            out.append("candidate %d (%r): missing %s"
                      % (i, entry.get("word"), ", ".join(missing)))
            continue
        if entry["status"] not in VALID_STATUSES:
            out.append("candidate %d (%r): status %r not one of %s"
                      % (i, entry["word"], entry["status"], VALID_STATUSES))
    return out


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
