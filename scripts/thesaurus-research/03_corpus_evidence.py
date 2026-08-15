#!/usr/bin/env python3
"""
Annotate the candidates with counts over the 100-README corpus.

    python3 scripts/thesaurus-research/03_corpus_evidence.py
    python3 scripts/thesaurus-research/03_corpus_evidence.py --json

This is the calibration step the repo's own convention demands: a detector-ish
list is measured against docs/readme-analysis/repos/*/README.md before it is
wired to anything, because an accepted overreach term becomes a rewrite
`--apply-safe` performs in a stranger's document. A term that shows up across
the corpus is ordinary technical vocabulary ("require", "state", "execute"),
and this stage flags it `technical-vocabulary` and demotes it to `flagged` so
the merge cannot pick it up without a human overriding.

Counting uses `measure_voice.term_rx`, imported rather than copied, so the
evidence counts exactly what the shipped tool will count, inflections
included. A copy that drifted would calibrate a different detector than the
one shipping.

Idempotent: recomputes and overwrites only the `corpus` blocks, the way
`03_analyze_readme.py --batch` overwrites its stats file.

Exit 0 on an annotated file, 1 when the candidates or the corpus are missing.
Stdlib only, 3.9+.
"""

import argparse
import glob
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
VOICE_SETUP = os.path.join(REPO_ROOT, "skills", "voice-setup", "scripts")
for path in (HERE, ENGINE, VOICE_SETUP):
    if path not in sys.path:
        sys.path.insert(0, path)

import thesaurus_io  # noqa: E402
from rwlib import cli_error  # noqa: E402


def load_measure_voice():
    """measure_voice.py, for term_rx. Loaded by path because the module also
    loads thesaurus.json at import time, which is fine: the counting regex is
    the only thing read from it."""
    spec = importlib.util.spec_from_file_location(
        "measure_voice", os.path.join(VOICE_SETUP, "measure_voice.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corpus_texts(corpus_dir):
    """[(name, text)] for every README in the corpus, sorted for determinism."""
    out = []
    for path in sorted(glob.glob(os.path.join(corpus_dir, "*", "README.md"))):
        with open(path, encoding="utf-8", errors="replace") as fh:
            out.append((os.path.basename(os.path.dirname(path)), fh.read()))
    return out


def counts_for(term, texts, term_rx):
    """{"readmes": docs containing the term, "hits": total matches}."""
    rx = term_rx(term)
    readmes = hits = 0
    for _name, text in texts:
        n = len(rx.findall(text))
        if n:
            readmes += 1
            hits += n
    return {"readmes": readmes, "hits": hits}


def annotate(data, texts, term_rx):
    """Write corpus blocks into every family, flagging corpus-common terms."""
    demoted = 0
    for family in data["families"]:
        reach_corpus = counts_for(family["reach"], texts, term_rx)
        for term in family["overreach"]:
            term["corpus"] = counts_for(term["term"], texts, term_rx)
            term["reach_corpus"] = reach_corpus
            common = (term["corpus"]["readmes"]
                      >= thesaurus_io.CORPUS_FLAG_DOCS)
            flagged = "technical-vocabulary" in term["flags"]
            if common and not flagged:
                term["flags"].append("technical-vocabulary")
            elif not common and flagged:
                # Idempotence includes the flag: a rerun over a changed
                # corpus retracts what it asserted, or the evidence lies.
                term["flags"].remove("technical-vocabulary")
            if term["flags"] and term["status"] == "pending":
                term["status"] = "flagged"
                demoted += 1
            elif not term["flags"] and term["status"] == "flagged":
                # `flagged` is machine-set and `accepted`/`rejected` are
                # human-set, so an evidence retraction only ever lifts the
                # machine's own demotion.
                term["status"] = "pending"
    return demoted


def main():
    examples = [
        "python3 scripts/thesaurus-research/03_corpus_evidence.py",
        "python3 scripts/thesaurus-research/03_corpus_evidence.py --json",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--candidates", default=thesaurus_io.CANDIDATES_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--corpus-dir", default=thesaurus_io.CORPUS_DIR,
                    help=argparse.SUPPRESS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.candidates):
        ap.error("no candidates at %s. Run 02_generate_candidates.py first"
                 % args.candidates)
    data = thesaurus_io.load_json(args.candidates)
    problems = thesaurus_io.candidate_problems(data)
    if problems:
        ap.error("candidates fail their schema, fix before annotating:\n  "
                 + "\n  ".join(problems))
    texts = corpus_texts(args.corpus_dir)
    if not texts:
        ap.error("no READMEs under %s. The corpus is the calibration, so "
                 "annotating against nothing would stamp evidence that was "
                 "never gathered" % args.corpus_dir)

    term_rx = load_measure_voice().term_rx
    demoted = annotate(data, texts, term_rx)
    thesaurus_io.write_json(args.candidates, data)

    n_terms = sum(len(f["overreach"]) for f in data["families"])
    if args.json:
        print(json.dumps({"readmes": len(texts), "terms": n_terms,
                          "demoted": demoted}, indent=2))
    else:
        print("annotated %d terms against %d READMEs, %d newly flagged as "
              "technical vocabulary" % (n_terms, len(texts), demoted))
    return 0


if __name__ == "__main__":
    sys.exit(main())
