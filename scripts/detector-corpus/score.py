#!/usr/bin/env python3
"""
Score the engine against the labeled corpus, and say how sure the number is.

    python3 score.py                 # rates, per register, with intervals
    python3 score.py --verify        # hashes only: has any sample moved?
    python3 score.py --json
    python3 score.py --band P1       # count P1 as a flag as well as P0

What this measures, exactly, is the false-positive rate of the P0 band: the
share of documents with evidence of pre-generation authorship that the engine
nevertheless reports a P0 on. P0 is the band the README calls evidence rather
than opinion, and it is the one --check gates CI on, so it is the number that
costs somebody something when it is wrong. P1 and P2 are craft findings and a
human document *should* trip them: good prose has wordiness in it.

Three things this deliberately does not do.

It does not report an accuracy figure. Accuracy over a corpus somebody chose is
a number about the corpus. The false-positive rate per register is the claim a
reader can act on: "if you write documentation and this fires a P0, here is how
often that has been wrong."

It does not report a point estimate without an interval. Zero flags out of
twelve samples is not a 0% error rate, and a Wilson interval says so out loud.
See corpus_io.wilson for why the normal approximation is wrong here.

It does not average across registers. The tolerance matrix exists because the
registers behave differently, so a pooled rate hides the register where the
engine is worst, which is the one somebody needs to know about.

Empty is a legitimate state and it prints as one. A corpus with no samples
reports that it has no samples, rather than a rate of 0.0 over nothing.
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

import corpus_io  # noqa: E402
import scan  # noqa: E402
from rwlib import cli_error  # noqa: E402
from rwlib import lexicon as lexicon_mod  # noqa: E402
from rwlib import registers  # noqa: E402


BANDS = ("P0", "P1", "P2")


def flagged(findings, threshold):
    """True when the document trips at or above `threshold`."""
    cutoff = BANDS.index(threshold)
    return any(BANDS.index(f["priority"]) <= cutoff for f in findings)


def verify(manifest):
    """(present, missing, moved). A sample whose text no longer hashes to its
    manifest entry is not the document the published rate was measured on."""
    present, missing, moved = [], [], []
    for sample in manifest["samples"]:
        text = corpus_io.read_text(sample)
        if text is None:
            missing.append(sample)
        elif corpus_io.digest(text) != sample["sha256"]:
            moved.append(sample)
        else:
            present.append(sample)
    return present, missing, moved


def score(samples, threshold="P0"):
    """{register: {label: {n, flagged, rate, lo, hi}}} plus an "all" register."""
    buckets = {}
    for sample in samples:
        text = corpus_io.read_text(sample)
        findings, _ = scan.scan(text, sample["register"], ste="off")
        hit = flagged(findings, threshold)
        for key in (sample["register"], "all"):
            row = buckets.setdefault(key, {}).setdefault(
                sample["label"], {"n": 0, "flagged": 0, "ids": []})
            row["n"] += 1
            row["flagged"] += int(hit)
            if hit:
                row["ids"].append(sample["id"])
    for register in buckets.values():
        for row in register.values():
            rate, lo, hi = corpus_io.wilson(row["flagged"], row["n"])
            row.update(rate=rate, ci_low=lo, ci_high=hi)
    return buckets


def report(buckets, threshold, present, missing, moved):
    out = ["labeled-corpus score (lexicon %s, registers %s, threshold %s)"
           % (lexicon_mod.version(), registers.version(), threshold), ""]
    if not present:
        out.append("No scorable samples. The manifest holds %d entry(ies) and "
                   "this checkout has the text for none of them."
                   % (len(missing) + len(moved)))
        out.append("")
        out.append("This is the honest state of the evidence, not a failure. "
                   "docs/detector-corpus/README.md has the procedure for "
                   "populating it, and PROOF.md says plainly that until it is "
                   "populated the calibration rests on two hand-written "
                   "samples.")
        return "\n".join(out)

    out.append("%-16s %-10s %5s %8s %8s   %s"
               % ("register", "label", "n", "flagged", "rate", "95% interval"))
    for register in sorted(buckets, key=lambda r: (r == "all", r)):
        for label in corpus_io.LABELS:
            row = buckets[register].get(label)
            if not row:
                continue
            enough = row["n"] >= corpus_io.MIN_SAMPLES_FOR_RATE
            out.append("%-16s %-10s %5d %8d %7.1f%%   %.1f%% to %.1f%%%s"
                       % (register, label, row["n"], row["flagged"],
                          row["rate"] * 100, row["ci_low"] * 100,
                          row["ci_high"] * 100,
                          "" if enough else "   (under %d samples)"
                          % corpus_io.MIN_SAMPLES_FOR_RATE))
    out.append("")

    human = buckets.get("all", {}).get("human")
    if human:
        out.append("Read the human row as the false-positive rate: %d of %d "
                   "documents with pre-generation provenance were flagged at "
                   "%s, so the rate is somewhere between %.1f%% and %.1f%%."
                   % (human["flagged"], human["n"], threshold,
                      human["ci_low"] * 100, human["ci_high"] * 100))
        if human["ids"]:
            out.append("Flagged: %s. Read them. Every one is either a bug in a "
                       "pattern or a document that earned it."
                       % ", ".join(human["ids"][:12]))
    generated = buckets.get("all", {}).get("generated")
    if generated:
        out.append("Read the generated row the other way round: %d of %d "
                   "documents the engine has generation evidence for were "
                   "flagged at %s, which is the detection rate. A dataset "
                   "sample's evidence is the row's own attribution rather "
                   "than a recorded prompt, and vocabulary marks sit at P1, "
                   "so run --band P1 before reading a low P0 rate as a miss."
                   % (generated["flagged"], generated["n"], threshold))
    if missing:
        out.append("")
        out.append("%d sample(s) in the manifest have no text here, so they are "
                   "not in the numbers above. Refetch from the archive URLs."
                   % len(missing))
    if moved:
        out.append("")
        out.append("%d sample(s) no longer hash to their manifest entry and "
                   "were excluded: %s. Either the source changed or the local "
                   "copy did, and both invalidate the sample."
                   % (len(moved), ", ".join(s["id"] for s in moved[:6])))
    return "\n".join(out)


def main():
    examples = [
        "python3 scripts/detector-corpus/score.py",
        "python3 scripts/detector-corpus/score.py --verify",
        "python3 scripts/detector-corpus/score.py --json",
        "python3 scripts/detector-corpus/score.py --band P1"
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples
    )

    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="check hashes and stop, without scoring")
    ap.add_argument("--band", default="P0", choices=BANDS,
                    help="count a finding at this priority or worse as a flag "
                         "(default: P0, the band that is evidence)")
    args = ap.parse_args()

    manifest = corpus_io.load()
    issues = corpus_io.problems(manifest, registers.registers())
    if issues:
        for issue in issues:
            print("  %s" % issue, file=sys.stderr)
        print("\nThe manifest does not validate, so no rate is published from "
              "it. A corpus with a broken provenance record is an assertion, "
              "not evidence.", file=sys.stderr)
        return 1

    present, missing, moved = verify(manifest)
    if args.verify:
        print("%d verified, %d missing locally, %d moved"
              % (len(present), len(missing), len(moved)))
        for sample in moved:
            print("  moved: %s (%s)" % (sample["id"],
                                        sample["provenance"].get("source_url", "")))
        return 1 if moved else 0

    buckets = score(present, args.band)
    if args.json:
        print(json.dumps({
            "lexicon_version": lexicon_mod.version(),
            "registers_version": registers.version(),
            "threshold": args.band,
            "n_manifest": len(manifest["samples"]),
            "n_scored": len(present),
            "n_missing": len(missing),
            "n_moved": len(moved),
            "min_samples_for_rate": corpus_io.MIN_SAMPLES_FOR_RATE,
            "buckets": buckets,
        }, indent=2))
    else:
        print(report(buckets, args.band, present, missing, moved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
