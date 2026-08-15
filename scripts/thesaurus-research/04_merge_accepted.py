#!/usr/bin/env python3
"""
Merge accepted candidates into the shipped thesaurus.json.

    python3 scripts/thesaurus-research/04_merge_accepted.py --dry-run
    python3 scripts/thesaurus-research/04_merge_accepted.py

The only writer of skills/voice-setup/scripts/thesaurus.json besides a human.
It takes families marked `accepted` (with at least one `accepted` term),
appends them after the hand-written families, validates the merged object
with the same `thesaurus_check.problems` the repo validator runs, and bumps
`version` only when the families actually changed. A merge that fails
validation touches nothing and exits 1.

Two refusals worth knowing about. Zero accepted families is an error rather
than a no-op write, because "I merged and nothing happened" usually means the
review marked terms and not their families, and a silent no-op hides that.
And candidates that never went through 03_corpus_evidence.py are refused
unless --allow-uncalibrated is passed, because the corpus count is the one
piece of evidence guarding the destructive-rewrite failure mode.

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
VOICE_SETUP = os.path.join(REPO_ROOT, "skills", "voice-setup", "scripts")
for path in (HERE, ENGINE, VOICE_SETUP):
    if path not in sys.path:
        sys.path.insert(0, path)

import thesaurus_io  # noqa: E402
import thesaurus_check  # noqa: E402
from rwlib import cli_error  # noqa: E402


def accepted_families(candidates):
    """[(reach, [terms])] a human signed off on, in a deterministic order.

    A family counts only when the family itself is `accepted` and at least
    one term under it is. A term accepted under a family that is not is a
    half-finished review, and the caller reports it rather than guessing.
    """
    out, half = [], []
    for family in candidates.get("families", []):
        terms = [t["term"] for t in family.get("overreach", [])
                 if t.get("status") == "accepted"]
        if family.get("status") == "accepted" and terms:
            out.append((family["reach"], terms))
        elif terms:
            half.append(family["reach"])
    return sorted(out), sorted(half)


def merge(thesaurus, accepted):
    """(merged, changed). Hand-written families keep their content and order.

    A new reach word appends a family after the existing ones, alphabetical.
    An accepted term whose reach already has a family appends to that
    family's overreach list, deduplicated. Nothing is ever removed here:
    retiring a family is a hand edit to the shipped file, reviewed like one.
    """
    merged = {"version": thesaurus["version"],
              "families": [dict(f, overreach=list(f["overreach"]))
                           for f in thesaurus["families"]]}
    by_reach = {f["reach"]: f for f in merged["families"]}
    changed = False
    for reach, terms in accepted:
        family = by_reach.get(reach)
        if family is None:
            family = {"reach": reach, "overreach": []}
            merged["families"].append(family)
            by_reach[reach] = family
        for term in terms:
            if term not in family["overreach"]:
                family["overreach"].append(term)
                changed = True
    if changed:
        merged["version"] = thesaurus["version"] + 1
    return merged, changed


def uncalibrated(candidates):
    """Accepted terms that carry no corpus block: evidence never gathered."""
    out = []
    for family in candidates.get("families", []):
        for term in family.get("overreach", []):
            if term.get("status") == "accepted" and "corpus" not in term:
                out.append("%s -> %s" % (term["term"], family["reach"]))
    return out


def main():
    examples = [
        "python3 scripts/thesaurus-research/04_merge_accepted.py --dry-run",
        "python3 scripts/thesaurus-research/04_merge_accepted.py",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would merge, write nothing")
    ap.add_argument("--allow-uncalibrated", action="store_true",
                    help="merge terms that never went through "
                         "03_corpus_evidence.py. The corpus count is the "
                         "evidence guarding destructive rewrites, so this "
                         "is for synthetic tests, not for shipping")
    ap.add_argument("--candidates", default=thesaurus_io.CANDIDATES_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--thesaurus", default=thesaurus_io.THESAURUS_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.candidates):
        ap.error("no candidates at %s. Run 02 and 03 first" % args.candidates)
    candidates = thesaurus_io.load_json(args.candidates)
    problems = thesaurus_io.candidate_problems(candidates)
    if problems:
        ap.error("candidates fail their schema:\n  " + "\n  ".join(problems))

    accepted, half = accepted_families(candidates)
    if half:
        print("note: %d family(ies) have accepted terms under a family that "
              "is not itself accepted, and were skipped: %s"
              % (len(half), ", ".join(half)), file=sys.stderr)
    if not accepted:
        ap.error("no accepted families in %s. A merge with nothing to merge "
                 "is usually a review that marked terms and not their "
                 "families, so this is an error rather than a no-op"
                 % args.candidates)
    missing_evidence = uncalibrated(candidates)
    if missing_evidence and not args.allow_uncalibrated:
        ap.error("%d accepted term(s) carry no corpus block, so their "
                 "calibration evidence was never gathered: %s. Run "
                 "03_corpus_evidence.py, or pass --allow-uncalibrated if "
                 "this is a synthetic run"
                 % (len(missing_evidence), ", ".join(missing_evidence[:6])))

    thesaurus = thesaurus_io.load_json(args.thesaurus)
    merged, changed = merge(thesaurus, accepted)
    merge_problems = thesaurus_check.problems(merged)
    if merge_problems:
        # The file on disk is untouched: validation happens on the object.
        ap.error("the merge would produce an invalid thesaurus, nothing was "
                 "written:\n  " + "\n  ".join(merge_problems))

    n_new = sum(len(terms) for _reach, terms in accepted)
    if args.dry_run:
        print("dry run: %d accepted family(ies), %d term(s), version %d -> %d. "
              "Nothing written."
              % (len(accepted), n_new, thesaurus["version"],
                 merged["version"]))
        for reach, terms in accepted:
            print("  %s <- %s" % (reach, ", ".join(terms)))
        return 0

    thesaurus_io.write_json(args.thesaurus, merged)
    if args.json:
        print(json.dumps({"families": len(accepted), "terms": n_new,
                          "version": merged["version"],
                          "changed": changed}, indent=2))
    else:
        print("merged %d family(ies), %d term(s) into %s, version %d"
              % (len(accepted), n_new, args.thesaurus, merged["version"]))
        if not changed:
            print("No family changed, so the version did not move and the "
                  "write was byte-identical.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
