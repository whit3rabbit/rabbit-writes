#!/usr/bin/env python3
"""
Annotate the candidates with counts over the 100-README corpus.

    python3 scripts/ste-research/02_corpus_evidence.py
    python3 scripts/ste-research/02_corpus_evidence.py --json

The calibration step this repo's own convention demands before any
detector-ish list is wired to anything: ASD-STE100 is an aerospace
maintenance-manual standard, and a word it bans for that register ("ability",
"any", "run", "check") can be the ordinary connective tissue of a software
README. A candidate that shows up across the corpus gets flagged
`corpus-common` and demoted out of auto-accept, mirroring exactly what
scripts/thesaurus-research/03_corpus_evidence.py does for its own overreach
terms, at the same document-count threshold (ste_io.CORPUS_FLAG_DOCS).

Two things have to match what actually ships, or the evidence is measuring a
different detector than the one that runs:

  The regex. rwlib.ste.dictionary_vocab_regex is imported, not copied. A
  first pass here used a hand-rolled pattern with a plain \\b boundary and
  measured "cross" as rare; the shipped check uses a hyphen-aware boundary
  (word_regex's own, so "cross" does not match inside "cross-platform")
  built by that exact function, and only importing it keeps the two in sync
  the next time either changes.

  The text. scan.py never runs STE checks over a raw README: every call goes
  through apply_exemptions first (code fences, inline code, quoted examples
  blanked). A raw-text pass here counted "mask" and "circle" 97 and 95 times
  apiece, entirely from a `mask=circle` query parameter in an avatar-crop
  image URL -- markup scan.py already blanks before scan_dictionary_vocabulary
  ever sees it. Counting raw text measured a detector nobody ships.

Idempotent: recomputes and overwrites only the `corpus` and `flags` fields,
never `status` once a human has moved it to `accepted` or `rejected` --
those are read back in and left alone.

Exit 0 on an annotated file, 1 when the candidates or the corpus are missing.
Stdlib only, 3.9+.
"""

import argparse
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
for path in (HERE, ENGINE):
    if path not in sys.path:
        sys.path.insert(0, path)

import ste_io  # noqa: E402
import scan  # noqa: E402
from rwlib import cli_error  # noqa: E402
from rwlib.ste import dictionary_vocab_regex  # noqa: E402


def corpus_texts(corpus_dir):
    """[(name, exempted_text), ...] for every README in the corpus, run
    through the same apply_exemptions pass scan.py feeds every STE check,
    sorted for determinism."""
    out = []
    for path in sorted(glob.glob(os.path.join(corpus_dir, "*", "README.md"))):
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        out.append((os.path.basename(os.path.dirname(path)),
                    scan.apply_exemptions(raw)))
    return out


def count_all(words, texts):
    """{word: {"readmes": N, "hits": N}} for every word, one finditer pass
    per document rather than one compile-and-scan per word per document."""
    rx = dictionary_vocab_regex(words)
    counts = {w: {"readmes": 0, "hits": 0} for w in words}
    for _name, text in texts:
        seen_this_doc = set()
        for m in rx.finditer(text):
            w = m.group(0).lower()
            counts[w]["hits"] += 1
            seen_this_doc.add(w)
        for w in seen_this_doc:
            counts[w]["readmes"] += 1
    return counts


def annotate(data, texts):
    """Write corpus counts into every candidate, flagging corpus-common ones.
    Returns the number newly demoted."""
    demoted = 0
    words = [c["word"] for c in data["candidates"]]
    counts = count_all(words, texts)
    for c in data["candidates"]:
        c["corpus"] = counts[c["word"]]
        common = c["corpus"]["readmes"] >= ste_io.CORPUS_FLAG_DOCS
        flagged = "corpus-common" in c["flags"]
        if common and not flagged:
            c["flags"].append("corpus-common")
        elif not common and flagged:
            # Idempotence includes the flag: a rerun over a changed corpus
            # retracts what it asserted, or the evidence lies.
            c["flags"].remove("corpus-common")
        if c["flags"] and c["status"] == "candidate":
            c["status"] = "flagged"
            demoted += 1
        elif not c["flags"] and c["status"] == "flagged":
            # `flagged` is machine-set; `accepted`/`rejected` are human-set
            # and never touched here. An evidence retraction only ever lifts
            # the machine's own demotion.
            c["status"] = "candidate"
    return demoted


def main():
    examples = [
        "python3 scripts/ste-research/02_corpus_evidence.py",
        "python3 scripts/ste-research/02_corpus_evidence.py --json",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--candidates", default=ste_io.CANDIDATES_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--corpus-dir", default=ste_io.CORPUS_DIR,
                    help=argparse.SUPPRESS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.candidates):
        ap.error("no candidates at %s. Run 01_extract_candidates.py first"
                 % args.candidates)
    data = ste_io.load_json(args.candidates)
    problems = ste_io.candidate_problems(data)
    if problems:
        ap.error("candidates fail their schema, fix before annotating:\n  "
                 + "\n  ".join(problems))
    texts = corpus_texts(args.corpus_dir)
    if not texts:
        ap.error("no READMEs under %s. The corpus is the calibration, so "
                 "annotating against nothing would stamp evidence that was "
                 "never gathered" % args.corpus_dir)

    demoted = annotate(data, texts)
    ste_io.write_json(args.candidates, data)

    if args.json:
        import json
        print(json.dumps({"readmes": len(texts),
                          "candidates": len(data["candidates"]),
                          "newly_flagged": demoted}, indent=2))
    else:
        print("annotated %d candidates against %d READMEs, %d newly flagged "
              "corpus-common" % (len(data["candidates"]), len(texts), demoted))
    return 0


if __name__ == "__main__":
    sys.exit(main())
