#!/usr/bin/env python3
"""
Write the candidates that cleared corpus evidence into ste_lexicon.json.

    python3 scripts/ste-research/03_merge_accepted.py
    python3 scripts/ste-research/03_merge_accepted.py --dry-run

Takes every candidate whose status is `candidate` (extracted cleanly, not
flagged corpus-common) or `accepted` (a human overrode a flag), and writes
{word: ALTERNATIVE} into a new `dictionary_vocabulary` key in
ste_lexicon.json -- the bulk ASD-STE100 word list, kept apart from the
existing hand-cited sections (banned_verbs, banned_words_software,
recurring_errors, ai_slop) rather than merged into any of them, because those
carry a rule-number citation per entry and this is 600-plus words with one
shared citation for the whole block.

A candidate already covered by one of those hand-cited sections is skipped
here on purpose: the existing entry carries a specific rule citation
(SOURCING.md's spot-check discipline), and this bulk block would either
duplicate it verbatim or, worse, disagree with it if the two were ever edited
separately. `rejected` and `flagged` candidates are excluded outright --
`flagged` means corpus-common, `rejected` means a human said no.

Idempotent and always overwrites `dictionary_vocabulary` whole, the way
`04_merge_accepted.py` overwrites the thesaurus's shipped file: rerunning
after 02_corpus_evidence.py without any status change reproduces the same
output byte for byte.

Exit 0 on a merge (or a clean no-op dry run), 1 when candidates.json is
missing or malformed.
Stdlib only, 3.9+.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
for path in (HERE, ENGINE):
    if path not in sys.path:
        sys.path.insert(0, path)

import ste_io  # noqa: E402
from rwlib import cli_error  # noqa: E402

MERGEABLE_STATUSES = ("candidate", "accepted")


def already_curated(lexicon):
    """Every word/phrase a hand-cited section of ste_lexicon.json already
    names, so the bulk block never restates one of them."""
    out = set()
    out |= set(lexicon.get("banned_verbs", []))
    out |= set(lexicon.get("banned_modals", []))
    out |= set(lexicon.get("banned_words_software", {}))
    out |= set(lexicon.get("recurring_errors", {}))
    out |= set(lexicon.get("approved_verb_replacements", {}))
    out |= set(lexicon.get("ai_slop", {}))
    return out


def build_vocabulary(candidates, curated):
    out = {}
    skipped_curated = []
    for c in candidates:
        if c["status"] not in MERGEABLE_STATUSES:
            continue
        if c["word"] in curated:
            skipped_curated.append(c["word"])
            continue
        out[c["word"]] = c["alternative"]
    return dict(sorted(out.items())), sorted(skipped_curated)


def main():
    examples = [
        "python3 scripts/ste-research/03_merge_accepted.py",
        "python3 scripts/ste-research/03_merge_accepted.py --dry-run",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--candidates", default=ste_io.CANDIDATES_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--lexicon", default=ste_io.STE_LEXICON_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--dry-run", action="store_true",
                    help="report counts, write nothing")
    args = ap.parse_args()

    if not os.path.exists(args.candidates):
        ap.error("no candidates at %s. Run 01_extract_candidates.py and "
                 "02_corpus_evidence.py first" % args.candidates)
    data = ste_io.load_json(args.candidates)
    problems = ste_io.candidate_problems(data)
    if problems:
        ap.error("candidates fail their schema, fix before merging:\n  "
                 + "\n  ".join(problems))

    lexicon = ste_io.load_json(args.lexicon)
    curated = already_curated(lexicon)
    vocabulary, skipped_curated = build_vocabulary(data["candidates"], curated)

    counts_by_status = {}
    for c in data["candidates"]:
        counts_by_status[c["status"]] = counts_by_status.get(c["status"], 0) + 1

    print("candidates by status: %s" % counts_by_status)
    print("merging %d words (%d already covered by a hand-cited section, "
          "skipped)" % (len(vocabulary), len(skipped_curated)))

    if args.dry_run:
        print("dry run: ste_lexicon.json not written")
        return 0

    # A version bump is a claim that a word, phrase, or pattern changed
    # (ste_lexicon.json's own convention). Comparing before writing, rather
    # than incrementing unconditionally, is what keeps a rerun with no new
    # evidence idempotent: two runs back to back used to bump the version
    # twice for a content change that happened once.
    changed = lexicon.get("dictionary_vocabulary") != vocabulary
    lexicon["dictionary_vocabulary"] = vocabulary
    lexicon["dictionary_vocabulary_comment"] = (
        "Bulk ASD-STE100 Issue 9 word -> approved-alternative mapping, "
        "%d entries, generated by scripts/ste-research/ from "
        "ste_dictionary_full.json and calibrated against the 100-README "
        "corpus (docs/ste-research/candidates.json carries the evidence: "
        "a word appearing in %d or more of the 100 corpus READMEs was "
        "excluded as ordinary technical vocabulary rather than an STE "
        "violation). Kept apart from banned_verbs/banned_words_software/"
        "recurring_errors/ai_slop, which carry a rule citation per entry; "
        "this block carries one citation for all of it. P2 advisory, "
        "behind --ste, same as ai_slop." % (len(vocabulary),
                                            ste_io.CORPUS_FLAG_DOCS))
    if changed:
        lexicon["version"] = lexicon.get("version", 0) + 1
    ste_io.write_json(args.lexicon, lexicon)
    print("wrote %d entries to %s (version %s -> %d)"
         % (len(vocabulary), args.lexicon,
            "bumped" if changed else "unchanged", lexicon["version"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
