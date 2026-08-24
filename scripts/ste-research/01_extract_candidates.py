#!/usr/bin/env python3
"""
Pull clean word -> approved-alternative candidates out of the parsed ASD-STE100
dictionary, for words the standard does not approve.

    python3 scripts/ste-research/01_extract_candidates.py
    python3 scripts/ste-research/01_extract_candidates.py --json

ste_dictionary_full.json's `meaning_or_alternatives` field is the mangled
column text SOURCING.md documents: two PDF table columns (an all-caps STE
example and a lowercase one) got interleaved during flattening, and the field
carries both, word-for-word. Buried at the front of that mess, though, is one
reliable structure: `ALTERNATIVE (pos)`, the dictionary's own ruling, before
the interleaved example text begins. This stage extracts exactly that and
nothing past it.

Anchored on the part-of-speech tag deliberately, not on "the first run of
capital letters": a bare-phrase alternative ("NOT EASY", "AT THE SAME TIME")
has no tag and no reliable delimiter separating it from the capitalized
example text that follows, so those entries are left out rather than guessed
at. Measured over the 1,283 not-approved entries: 1,188 (92.6%) carry a
POS-tagged leading alternative and extract cleanly; the other 93 do not and
are skipped, reported at the end rather than silently dropped.

Two exclusions past that:

  Multi-sense entries only keep their first-listed alternative. "complete
  (adj)" has three approved senses (FULL, ALL, COMPLETED) and this keeps only
  the first. A P2 advisory suggesting one of three valid words is still
  useful; the other two are a data-quality gap this pipeline does not close.

  A candidate whose alternative is textually identical to the word itself
  (case and spacing aside) is dropped outright: "bank (n)" -> "BANK (v)" is a
  real ruling (the noun sense is banned, the verb sense is not), but a
  word-boundary regex has no part-of-speech to check, so shipping it would
  read as "replace bank with bank," which is not actionable advice.

Idempotent: overwrites docs/ste-research/candidates.json in full each run,
carrying forward `status` and `flags` for any word already present so a
rerun after the dictionary changes does not silently discard a human's or
02_corpus_evidence.py's prior judgement.

Exit 0 always; the skip count is reported, not treated as failure.
Stdlib only, 3.9+.
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
for path in (HERE, ENGINE):
    if path not in sys.path:
        sys.path.insert(0, path)

import ste_io  # noqa: E402
from rwlib import cli_error  # noqa: E402

POS_TAGS = ("v", "n", "adj", "adv", "conj", "prep", "pron", "art", "TN")
LEAD_RX = re.compile(
    r"^([A-Z][A-Z \-/]+?)\s*\((%s)\)" % "|".join(POS_TAGS))


def extract(entry):
    """(alternative, alt_pos) or None. `entry` is one ste_dictionary_full.json
    record with approved == False."""
    m = LEAD_RX.match(entry["meaning_or_alternatives"].strip())
    if not m:
        return None
    alt = m.group(1).strip()
    if not alt:
        return None
    if alt.lower().replace(" ", "") == entry["word"].lower().replace(" ", ""):
        return None
    return alt, m.group(2)


def build_candidates(dictionary_entries, previous):
    """[candidate, ...], one per not-approved word that extracts cleanly.
    `previous` is {word: prior candidate dict}, for carrying status/flags
    forward across a rerun."""
    seen = set()
    out, skipped = [], []
    for entry in dictionary_entries:
        if entry["approved"]:
            continue
        word = entry["word"]
        if word in seen:
            # A second POS row for a word already captured from an earlier
            # row. The first ruling wins; a word-boundary check cannot tell
            # which sense fired anyway, so a second candidate for the same
            # spelling would only ever collide with the first.
            continue
        result = extract(entry)
        if result is None:
            skipped.append(word)
            continue
        seen.add(word)
        alt, alt_pos = result
        prior = previous.get(word, {})
        out.append({
            "word": word,
            "source_pos": entry["pos"],
            "alternative": alt,
            "alt_pos": alt_pos,
            "status": prior.get("status", "candidate"),
            "flags": prior.get("flags", []),
        })
    out.sort(key=lambda c: c["word"])
    return out, sorted(skipped)


def main():
    examples = [
        "python3 scripts/ste-research/01_extract_candidates.py",
        "python3 scripts/ste-research/01_extract_candidates.py --json",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--dictionary", default=ste_io.DICTIONARY_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--out", default=ste_io.CANDIDATES_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.dictionary):
        ap.error("no dictionary at %s" % args.dictionary)
    dictionary = ste_io.load_json(args.dictionary)

    previous = {}
    if os.path.exists(args.out):
        prior_data = ste_io.load_json(args.out)
        previous = {c["word"]: c for c in prior_data.get("candidates", [])}

    candidates, skipped = build_candidates(dictionary["entries"], previous)
    ste_io.write_json(args.out, {
        "_source": ste_io.DICTIONARY_PATH,
        "_comment": "One row per ASD-STE100 word the dictionary does not "
                    "approve, with its first-listed approved alternative. "
                    "See this script's own docstring for the extraction "
                    "rule and what it leaves out.",
        "candidates": candidates,
        "skipped_words": skipped,
    })

    if args.json:
        print(json.dumps({"extracted": len(candidates),
                          "skipped": len(skipped)}, indent=2))
    else:
        print("extracted %d candidates, skipped %d entries with no "
              "cleanly-parseable alternative -> %s"
              % (len(candidates), len(skipped), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
