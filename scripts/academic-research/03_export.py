#!/usr/bin/env python3
"""
Freeze the corpus measurement into docs/academic-corpus/summary.json.

PROOF.md quotes numbers from this file, so it is the committed half of a
measurement whose inputs are not committed. The manifest says which papers,
this says what the engine found in them, and 01_fetch_corpus.py --verify ties
the two together by hash. Without this step, a rate in PROOF.md is a number
somebody remembered.

`measured_at` is the corpus's own newest publication date, not the clock, so
re-exporting an unchanged corpus does not move the stamp. That is the rule
readme-research/04_aggregate.py already follows, and it exists so a rerun is
visible as a no-op in the diff rather than as a date change hiding one.

Run 01_fetch_corpus.py first. Step 03 is not optional after a cell change:
without it PROOF.md keeps quoting the numbers from before the change.

Usage:
  python3 scripts/academic-research/03_export.py
  python3 scripts/academic-research/03_export.py --check

Exit code: 0 on success, 1 when the corpus is missing or --check finds drift.
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

import academic_io as aio                               # noqa: E402
from rwlib import cli_error, lexicon, registers         # noqa: E402

measure_mod = __import__("02_measure")


def build():
    papers, bad = measure_mod.load_corpus()
    if not papers:
        return None, bad
    manifest = aio.load_manifest()
    payload = measure_mod.report_quiet(papers, list(registers.registers()))
    payload["measured_at"] = manifest.get("latest_published", "")
    payload["lexicon_version"] = lexicon.version()
    payload["registers_version"] = registers.version()
    payload["source"] = "PLOS, CC BY 4.0, abstract and prose sections only"
    payload["journals"] = sorted({p["journal"] for p, _ in papers})
    payload["subjects"] = sorted({p["subject"] for p, _ in papers})
    return payload, bad


def main(argv):
    examples = [
        "python3 scripts/academic-research/03_export.py",
        "python3 scripts/academic-research/03_export.py --check",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the committed summary has drifted")
    args = ap.parse_args(argv)

    payload, bad = build()
    for line in bad:
        print("  note  %s" % line, file=sys.stderr)
    if payload is None:
        print("no corpus to export. Run 01_fetch_corpus.py first.",
              file=sys.stderr)
        return 1

    new = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not os.path.exists(aio.SUMMARY_PATH):
            print("no summary.json. Run this script without --check.",
                  file=sys.stderr)
            return 1
        with open(aio.SUMMARY_PATH, encoding="utf-8") as fh:
            if fh.read() == new:
                print("summary.json matches the corpus")
                return 0
        print("summary.json has drifted from the corpus. Re-run: python3 %s"
              % os.path.relpath(__file__, REPO_ROOT), file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(aio.SUMMARY_PATH), exist_ok=True)
    with open(aio.SUMMARY_PATH, "w", encoding="utf-8") as fh:
        fh.write(new)
    print("wrote %s: %d paper(s), %s words, %d register(s), measured_at %s"
          % (os.path.relpath(aio.SUMMARY_PATH, REPO_ROOT), payload["papers"],
             format(payload["words"], ","), len(payload["registers"]),
             payload["measured_at"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
