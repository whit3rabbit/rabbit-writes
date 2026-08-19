#!/usr/bin/env python3
"""
Scan the academic corpus and report what the engine says about real papers.

This is the instrument the `academic` register is calibrated with, and it is
run twice: once before the register exists, to find out which rules fire on
prose nobody would call machine-written, and once after, to publish what the
new cells cost. A rule firing on most of the corpus is either a real finding
about how papers are written or a cell that needs a tolerance, and the matched
terms are what tells the two apart.

It scans in process rather than by subprocess. Twenty papers times seven
registers is 140 scans, which is about two minutes shelled out and a few
seconds imported, and the numbers are identical either way.

Nothing here decides anything. It prints per-register, per-finding counts and
the terms driving the vocabulary rules, and a person reads them.

Usage:
  python3 scripts/academic-research/02_measure.py
  python3 scripts/academic-research/02_measure.py --profile formal
  python3 scripts/academic-research/02_measure.py --json

Exit code: 0 when the corpus scanned, 1 when the manifest does not validate.
Stdlib only, 3.9+.
"""

import argparse
import collections
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
from rwlib import cli_error, registers                  # noqa: E402

import importlib.util                                   # noqa: E402

# scan.py is a script rather than a package member, so it is loaded by path,
# the way skills/rabbit-writes/tests/helpers.py does it.
_spec = importlib.util.spec_from_file_location(
    "rw_scan", os.path.join(ENGINE, "scan.py"))
scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan)

# The rules worth watching on academic prose. Everything else is reported too,
# but these are the ones a register argument would be about.
WATCHED = ("tier1", "tier2-cluster", "tier3-density", "transition-stack",
           "hedge-stack", "signposting", "uniform-paragraphs", "curly-quote",
           "rhetorical-question", "em-dash-rate", "confidence-calibration",
           "significance-inflation", "promotional", "generic-conclusion",
           "boilerplate-phrase", "list-label-period")


def load_corpus():
    manifest = aio.load_manifest()
    bad = aio.problems(manifest)
    if bad:
        return None, bad
    papers = []
    for paper in manifest["papers"]:
        path = aio.text_path(paper["doi"])
        if not os.path.exists(path):
            bad.append("%s: no text on disk. Run 01_fetch_corpus.py"
                       % paper["doi"])
            continue
        with open(path, encoding="utf-8") as fh:
            papers.append((paper, fh.read()))
    return papers, bad


def measure(papers, profile):
    """{finding id: {docs, hits, terms}} for one register over the corpus."""
    out = collections.defaultdict(
        lambda: {"docs": 0, "hits": 0, "terms": collections.Counter()})
    for _, text in papers:
        findings, _stats = scan.scan(text, profile=profile)
        seen = set()
        for finding in findings:
            fid = finding.get("id")
            if not fid:
                continue
            entry = out[fid]
            entry["hits"] += 1
            if fid not in seen:
                entry["docs"] += 1
                seen.add(fid)
            match = finding.get("match")
            if match:
                for term in str(match).split(", "):
                    entry["terms"][term.strip().lower()] += 1
    return out


def report(papers, profiles):
    total = len(papers)
    words = sum(aio.word_count(t) for _, t in papers)
    print("%d paper(s), %s words, %s\n"
          % (total, format(words, ","),
             ", ".join(sorted({p["journal"] for p, _ in papers}))))

    payload = {"papers": total, "words": words, "registers": {}}
    for profile in profiles:
        stats = measure(papers, profile)
        print("== %s" % profile)
        rows = sorted(stats.items(),
                      key=lambda kv: (-kv[1]["docs"], kv[0]))
        if not rows:
            print("   nothing fired\n")
        for fid, entry in rows:
            mark = " *" if fid in WATCHED else "  "
            terms = ", ".join("%s(%d)" % (t, n)
                              for t, n in entry["terms"].most_common(6))
            print("  %s %-24s %2d/%-2d docs  %3d hits  %s"
                  % (mark, fid, entry["docs"], total, entry["hits"], terms))
        print("")
        payload["registers"][profile] = {
            fid: {"docs": e["docs"], "hits": e["hits"],
                  "terms": dict(e["terms"].most_common(12))}
            for fid, e in stats.items()
        }
    return payload


def main(argv):
    examples = [
        "python3 scripts/academic-research/02_measure.py",
        "python3 scripts/academic-research/02_measure.py --profile formal",
        "python3 scripts/academic-research/02_measure.py --json",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--profile", action="append",
                    choices=list(registers.registers()),
                    help="register to scan under, repeatable. Default: all")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON instead of a table")
    args = ap.parse_args(argv)

    papers, bad = load_corpus()
    if papers is None or not papers:
        for line in bad:
            print("  FAIL  %s" % line, file=sys.stderr)
        print("no corpus to measure", file=sys.stderr)
        return 1
    for line in bad:
        print("  note  %s" % line, file=sys.stderr)

    profiles = args.profile or list(registers.registers())
    if args.json:
        payload = report_quiet(papers, profiles)
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        report(papers, profiles)
    return 0


def report_quiet(papers, profiles):
    payload = {"papers": len(papers),
               "words": sum(aio.word_count(t) for _, t in papers),
               "registers": {}}
    for profile in profiles:
        stats = measure(papers, profile)
        payload["registers"][profile] = {
            fid: {"docs": e["docs"], "hits": e["hits"],
                  "terms": dict(e["terms"].most_common(12))}
            for fid, e in stats.items()
        }
    return payload


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
