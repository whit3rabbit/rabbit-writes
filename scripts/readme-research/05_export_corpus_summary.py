#!/usr/bin/env python3
"""
Step 5: export the figures readme_check.py compares a README against.

Steps 03 and 04 leave a full aggregate under docs/readme-analysis/. That file is
research output and does not ship with the skill. This writes the small extract
that does: skills/readme-writing/scripts/corpus_summary.json.

The extraction itself lives in rwlib.corpus.derive, so this script and the
drift check in scripts/validate.py run the same code over the same input. Two
implementations of "the same numbers" is exactly the problem the extract exists
to solve.

    python3 05_export_corpus_summary.py            # write it
    python3 05_export_corpus_summary.py --check    # exit 1 if it has drifted
"""

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RWLIB_PARENT = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
if RWLIB_PARENT not in sys.path:
    sys.path.insert(0, RWLIB_PARENT)

from rwlib import corpus  # noqa: E402


def main(argv):
    aggregate = corpus.load_aggregate()
    if aggregate is None:
        print("no %s; run 03_analyze_readme.py --batch and 04_aggregate.py first"
              % os.path.relpath(corpus.AGGREGATE_PATH, REPO_ROOT), file=sys.stderr)
        return 2

    derived = corpus.derive(aggregate)
    if "--check" in argv:
        # Checked here rather than left to drift(), which returns "no drift" for
        # a summary that is not there at all. That is right for drift's other
        # caller, an installed skill with no aggregate to compare against, and
        # wrong here: this printed "matches the aggregate" about a file that did
        # not exist, while readme_check.py raised FileNotFoundError on import.
        if not os.path.exists(corpus.SUMMARY_PATH):
            print("%s does not exist. Run this script without --check to write it."
                  % os.path.relpath(corpus.SUMMARY_PATH, REPO_ROOT),
                  file=sys.stderr)
            return 1
        differences = corpus.drift()
        if not differences:
            print("corpus_summary.json matches the aggregate (%d repos)"
                  % derived["n_repos"])
            return 0
        for key, shipped, fresh in differences:
            print("  %-32s shipped %r, aggregate %r" % (key, shipped, fresh))
        print("\nRun: python3 scripts/readme-research/05_export_corpus_summary.py",
              file=sys.stderr)
        return 1

    with open(corpus.SUMMARY_PATH, "w", encoding="utf-8") as fh:
        json.dump(derived, fh, indent=2)
        fh.write("\n")
    print("wrote %s from %d repos"
          % (os.path.relpath(corpus.SUMMARY_PATH, REPO_ROOT), derived["n_repos"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
