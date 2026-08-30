#!/usr/bin/env python3
"""
Merge accepted candidates into the shipped lexicon.json.

    python3 scripts/claude-vocab-research/04_merge_accepted.py --dry-run
    python3 scripts/claude-vocab-research/04_merge_accepted.py

The only writer of skills/rabbit-writes/scripts/lexicon.json from this
pipeline. It takes families marked `accepted`, appends every form to the
family's proposed tier (deduplicated), refuses anything that would double-flag
or double-list, and bumps `version` only when the content actually changed.

Refusals worth knowing about. Zero accepted families is an error rather than
a no-op write, because "I merged and nothing happened" usually means the
review edited nothing and reran the wrong stage. Candidates that never went
through 03_corpus_evidence.py are refused unless --allow-uncalibrated is
passed, because the corpus count is the one piece of evidence this pipeline
adds over the dataset's own lift. A form may not land in tier1 (that is a
hand edit gated by the patterns.md section 12 table), may not already sit in
any lexicon list, and may not be covered by an existing catalogue pattern, or
the same word would fire twice per occurrence.

A changed merge bumps lexicon.json's version, and scripts/validate.py then
fails the build until PROOF.md's heading is regenerated to quote the new
number. That is deliberate: a version nobody re-measured against is a claim
with no evidence behind it.

Exit 0 on a clean merge or dry run, 1 on refusal.
Stdlib only, 3.9+.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
for path in (HERE, ENGINE):
    if path not in sys.path:
        sys.path.insert(0, path)

import claude_vocab_io  # noqa: E402
from rwlib import cli_error  # noqa: E402


def accepted_families(candidates):
    """[(tier, stem, forms)] a human signed off on, in a deterministic order."""
    out = []
    for family in candidates.get("families", []):
        if family.get("status") == "accepted":
            out.append((family.get("proposed_tier"), family["stem"],
                        family["forms"]))
    return sorted(out)


def uncalibrated(candidates):
    """Accepted families that carry no corpus block: evidence never gathered."""
    return [family["stem"] for family in candidates.get("families", [])
            if family.get("status") == "accepted" and "corpus" not in family]


def merge(lexicon, accepted):
    """(merged, problems, changed). Lists keep their order, new words append.

    Nothing is ever removed here: retiring a word is a hand edit to the
    shipped file, reviewed like one.
    """
    merged = {key: (list(value) if isinstance(value, list) else value)
              for key, value in lexicon.items()}
    owned = {}
    for key in ("tier1", "tier1_phrases", "tier2", "tier3", "clarity",
                "clarity_phrases", "technical_exempt", "academic_exempt"):
        for word in merged.get(key, []):
            owned.setdefault(word.lower(), []).append(key)

    problems, changed = [], False
    for tier, stem, forms in accepted:
        if tier not in claude_vocab_io.TIERS:
            problems.append("%s proposes tier %r, and only %s are merge "
                            "targets. tier1 is a hand edit gated by the "
                            "patterns.md section 12 table"
                            % (stem, tier, "/".join(claude_vocab_io.TIERS)))
            continue
        for form in forms:
            holders = owned.get(form.lower(), [])
            if tier in holders:
                # Already merged into this tier: a rerun of 04 over the same
                # review is the normal idempotence case, not a collision.
                continue
            if holders:
                problems.append("%s (%s) is already in %s"
                                % (form, stem, "/".join(holders)))
                continue
            merged[tier].append(form)
            owned.setdefault(form.lower(), []).append(tier)
            changed = True
    return merged, problems, changed


def main():
    examples = [
        "python3 scripts/claude-vocab-research/04_merge_accepted.py --dry-run",
        "python3 scripts/claude-vocab-research/04_merge_accepted.py",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would merge, write nothing")
    ap.add_argument("--allow-uncalibrated", action="store_true",
                    help="merge families that never went through "
                         "03_corpus_evidence.py. The corpus count is the "
                         "evidence this pipeline adds over the dataset's "
                         "lift, so this is for synthetic tests, not shipping")
    ap.add_argument("--candidates", default=claude_vocab_io.CANDIDATES_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--lexicon", default=claude_vocab_io.LEXICON_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.candidates):
        ap.error("no candidates at %s. Run 02 and 03 first" % args.candidates)
    candidates = claude_vocab_io.load_json(args.candidates)
    problems = claude_vocab_io.candidate_problems(candidates)
    if problems:
        ap.error("candidates fail their schema:\n  " + "\n  ".join(problems))

    accepted = accepted_families(candidates)
    if not accepted:
        ap.error("no accepted families in %s. A merge with nothing to merge "
                 "is usually a review that never happened, so this is an "
                 "error rather than a no-op" % args.candidates)
    missing_evidence = uncalibrated(candidates)
    if missing_evidence and not args.allow_uncalibrated:
        ap.error("%d accepted family(ies) carry no corpus block, so their "
                 "calibration evidence was never gathered: %s. Run "
                 "03_corpus_evidence.py, or pass --allow-uncalibrated if "
                 "this is a synthetic run"
                 % (len(missing_evidence), ", ".join(missing_evidence[:6])))

    lexicon = claude_vocab_io.load_json(args.lexicon)
    # The pattern check runs against the shipped file as it is, before any
    # merge, so a refusal names the pre-existing collision rather than one
    # this run introduced.
    for _tier, stem, forms in accepted:
        for form in forms:
            pattern = claude_vocab_io.covered_by_catalogue(form, args.lexicon)
            if pattern:
                ap.error("%s (%s) is already flagged by the catalogue "
                         "pattern %r. A tier entry beside it would fire twice "
                         "per occurrence" % (form, stem, pattern))

    merged, merge_problems, changed = merge(lexicon, accepted)
    if merge_problems:
        # The file on disk is untouched: validation happens on the object.
        ap.error("the merge would double-list a word, nothing was written:\n  "
                 + "\n  ".join(merge_problems))

    n_forms = sum(len(forms) for _tier, _stem, forms in accepted)
    if changed:
        merged["version"] = lexicon.get("version", 0) + 1
    if args.dry_run:
        print("dry run: %d accepted family(ies), %d form(s), version %s -> %s. "
              "Nothing written."
              % (len(accepted), n_forms, lexicon.get("version"),
                 merged.get("version")))
        for tier, stem, forms in accepted:
            print("  %s <- %s (%s)" % (tier, ", ".join(forms), stem))
        return 0

    claude_vocab_io.write_json(args.lexicon, merged)
    if args.json:
        print(json.dumps({"families": len(accepted), "forms": n_forms,
                          "version": merged.get("version"),
                          "changed": changed}, indent=2))
    else:
        print("merged %d family(ies), %d form(s) into %s, version %s"
              % (len(accepted), n_forms, args.lexicon,
                 merged.get("version")))
        if not changed:
            print("Nothing changed, so the version did not move and the "
                  "write was byte-identical.")
        else:
            print("The lexicon version moved: regenerate PROOF.md's self-scan "
                  "tables and its heading before running validate.py, which "
                  "fails the build until the heading quotes this version.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
