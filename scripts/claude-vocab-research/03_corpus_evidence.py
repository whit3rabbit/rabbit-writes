#!/usr/bin/env python3
"""
Annotate the candidates with counts over the 100-README corpus.

    python3 scripts/claude-vocab-research/03_corpus_evidence.py
    python3 scripts/claude-vocab-research/03_corpus_evidence.py --json

This is the calibration step the repo's own convention demands: a detector
list is measured against docs/readme-analysis/repos/*/README.md before it is
wired to anything, because an accepted word becomes a finding a stranger's
commit gate can trip. A word that shows up across the corpus is ordinary
technical vocabulary, and this stage flags it `technical-vocabulary` and
demotes it to `flagged` so the merge cannot pick it up without a human
overriding.

Counting uses `rwlib.lexicon.word_regex`, imported rather than copied, because
that is the regex the shipped scanner will match these words with: the
hyphen-aware boundary decides whether "pre-fix" hits "prefix-friendly" and
whether "seam" hits "seamless", so calibrating with any other counter would
measure a different detector than the one shipping.

The second number this stage adds is `new_tier2_clusters`: how many
tier2-cluster findings the family would create across the corpus if merged,
computed with the scanner's own rule (two or more tier-2 hits in one
blank-line paragraph). A tier-2 word costs nothing on its own, so this, not
the raw hit count, is the number a reviewer weighs against the lift.

Idempotent: recomputes and overwrites only the `corpus` blocks.

Exit 0 on an annotated file, 1 when the candidates or the corpus are missing.
Stdlib only, 3.9+.
"""

import argparse
import glob
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

import claude_vocab_io  # noqa: E402
from rwlib import cli_error  # noqa: E402
from rwlib import lexicon as lexicon_mod  # noqa: E402

# The scanner's own paragraph split (scan.py splits tier-2 counting on runs
# of whitespace with a blank line in it). Restated here rather than imported
# because scan.py is a script whose import would drag its CLI in with it.
PARAGRAPH_SPLIT = r"(\n\s*\n)"


def corpus_texts(corpus_dir):
    """[(name, text)] for every README in the corpus, sorted for determinism."""
    out = []
    for path in sorted(glob.glob(os.path.join(corpus_dir, "*", "README.md"))):
        with open(path, encoding="utf-8", errors="replace") as fh:
            out.append((os.path.basename(os.path.dirname(path)), fh.read()))
    return out


def counts_for(forms, texts):
    """{"readmes": docs containing any form, "hits": total matches}."""
    rx = lexicon_mod.word_regex(forms)
    readmes = hits = 0
    for _name, text in texts:
        n = len(rx.findall(text))
        if n:
            readmes += 1
            hits += n
    return {"readmes": readmes, "hits": hits}


def new_tier2_clusters(forms, texts, tier2_rx):
    """Paragraphs where this family tips the tier-2 rule from quiet to firing.

    The rule fires at 2 or more hits in one paragraph. A paragraph already
    carrying 2 fired before this family existed, so what is new is exactly:
    existing + family >= 2 while existing < 2.
    """
    rx = lexicon_mod.word_regex(forms)
    count = 0
    for _name, text in texts:
        for para in re.split(PARAGRAPH_SPLIT, text):
            existing = len(tier2_rx.findall(para))
            if existing >= 2:
                continue
            if existing + len(rx.findall(para)) >= 2:
                count += 1
    return count


def annotate(data, texts, tier2_rx):
    """Write corpus blocks into every family, flagging corpus-common words."""
    demoted = 0
    for family in data["families"]:
        corpus = counts_for(family["forms"], texts)
        corpus["new_tier2_clusters"] = new_tier2_clusters(
            family["forms"], texts, tier2_rx)
        family["corpus"] = corpus
        common = corpus["readmes"] >= claude_vocab_io.CORPUS_FLAG_DOCS
        flagged = "technical-vocabulary" in family["flags"]
        if common and not flagged:
            family["flags"].append("technical-vocabulary")
        elif not common and flagged:
            # Idempotence includes the flag: a rerun over a changed corpus
            # retracts what it asserted, or the evidence lies.
            family["flags"].remove("technical-vocabulary")
        if family["flags"] and family["status"] == "pending":
            family["status"] = "flagged"
            demoted += 1
        elif not family["flags"] and family["status"] == "flagged":
            # `flagged` is machine-set and `accepted`/`rejected` are
            # human-set, so an evidence retraction only ever lifts the
            # machine's own demotion.
            family["status"] = "pending"
    return demoted


def main():
    examples = [
        "python3 scripts/claude-vocab-research/03_corpus_evidence.py",
        "python3 scripts/claude-vocab-research/03_corpus_evidence.py --json",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--candidates", default=claude_vocab_io.CANDIDATES_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--corpus-dir", default=claude_vocab_io.CORPUS_DIR,
                    help=argparse.SUPPRESS)
    ap.add_argument("--lexicon", default=claude_vocab_io.LEXICON_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.candidates):
        ap.error("no candidates at %s. Run 02_generate_candidates.py first"
                 % args.candidates)
    data = claude_vocab_io.load_json(args.candidates)
    problems = claude_vocab_io.candidate_problems(data)
    if problems:
        ap.error("candidates fail their schema, fix before annotating:\n  "
                 + "\n  ".join(problems))
    texts = corpus_texts(args.corpus_dir)
    if not texts:
        ap.error("no READMEs under %s. The corpus is the calibration, so "
                 "annotating against nothing would stamp evidence that was "
                 "never gathered" % args.corpus_dir)

    # The shipped tier-2 list minus the always-on exemptions, which is what
    # scan.py counts with under the default register.
    lexicon = lexicon_mod.load(args.lexicon)
    exempt = {w.lower() for w in lexicon.get("technical_exempt", [])}
    tier2 = [w for w in lexicon["tier2"] if w.lower() not in exempt]
    tier2_rx = lexicon_mod.word_regex(tier2)

    demoted = annotate(data, texts, tier2_rx)
    claude_vocab_io.write_json(args.candidates, data)

    if args.json:
        print(json.dumps({"readmes": len(texts),
                          "families": len(data["families"]),
                          "demoted": demoted}, indent=2))
    else:
        print("annotated %d families against %d READMEs, %d newly flagged as "
              "technical vocabulary" % (len(data["families"]), len(texts),
                                        demoted))
        print("Next: review `status` by hand, then 04_merge_accepted.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
