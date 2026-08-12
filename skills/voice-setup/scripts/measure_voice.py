#!/usr/bin/env python3
"""
measure_voice.py - turn a pile of writing samples into a profile starting point.

The sample workflow in SKILL.md is the fastest way into a voice profile, and it
was described as a manual procedure: run scan.py on each sample, read five
numbers off each report, average them in your head, notice if any sample is
contaminated, and write the result into the profile. That is a script, and
asking a person to do it by hand is how the numbers end up approximate and the
contamination check ends up skipped.

    python3 measure_voice.py sample1.md sample2.md sample3.md
    python3 measure_voice.py samples/*.md --json

What comes out:

  a per-sample table, so an outlier is visible rather than averaged away
  the aggregate, with a spread, because how *consistent* a writer is across
    pieces is itself a fact about them
  the `Measured from samples` block from voices/TEMPLATE.md, ready to paste
  a starter `mechanics` object, ready to paste

Everything in that last block is a **suggestion from three or four documents**,
and it is printed as one. A person who never used a semicolon in four blog posts
may still use them in email, and a profile that bans them because a script
counted zero is a profile that will be wrong in a way its owner did not choose.
Confirm each line with them. The script's job is to make the question specific.

Contamination is checked, not assumed away. A sample carrying a P0 fingerprint
is AI-assisted writing until the author says otherwise, and a tell that gets into
a profile is then reproduced on purpose, forever. Any P0 in any sample exits 1
so this cannot pass unnoticed in a pipeline.

Exit codes: 0 clean, 1 a sample carries a P0 fingerprint, 2 no readable sample.
Stdlib only, 3.9+.
"""

import argparse
import importlib.util
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# scripts -> voice-setup -> skills. Walked rather than spelled out, so a skill
# directory can be renamed without editing the scripts inside it.
SKILLS = os.path.dirname(os.path.dirname(HERE))
SCAN_PATH = os.path.join(SKILLS, "rabbit-writes", "scripts", "scan.py")
# rwlib lives beside scan.py, resolved from it so the two cannot end up pointing
# at different checkouts.
RWLIB_PARENT = os.path.dirname(SCAN_PATH)
if RWLIB_PARENT not in sys.path:
    sys.path.insert(0, RWLIB_PARENT)

# Contractions are in the template's block and are not one of scan.py's stats,
# so they are counted here. Apostrophe either way: a sample pasted out of Word
# or Google Docs has curly ones, and a rate that silently reads zero on half the
# samples is worse than not reporting it.
CONTRACTION_RX = re.compile(
    r"(?i)\b\w+['’](?:t|s|re|ve|ll|d|m)\b|\b(?:can['’]t|won['’]t)\b")

# What the report and the pasteable block quote, in order. Second element is the
# name the template's block uses, which is not always scan.py's key.
MEASURES = (
    ("avg_sentence_words", "avg_sentence_words"),
    ("sentence_sd", "sentence_length_sd"),
    ("burstiness", "burstiness"),
    ("mattr", "mattr"),
    ("em_dashes_per_1k", "em_dashes_per_1000w"),
    ("contraction_rate", "contraction_rate"),
)

# Below this many words a sample's stylometry is noise. scan.py says so in its
# own report; said here too, because a person handing over four short emails
# deserves to be told the numbers are thin before they build a profile on them.
THIN_SAMPLE_WORDS = 250


def load_scan():
    if not os.path.exists(SCAN_PATH):
        raise SystemExit("measure_voice: cannot find %s. This script has to run "
                         "from inside an installed plugin." % SCAN_PATH)
    spec = importlib.util.spec_from_file_location("rw_scan", SCAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mean(values):
    return sum(values) / len(values) if values else None


def sd(values):
    """Sample standard deviation, or 0.0 for a single value.

    Across samples, not within one. It answers "how consistent is this person
    from piece to piece", which is the number that tells you whether one profile
    can describe them at all or whether they have two registers you are about to
    average into a third that is nobody.
    """
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def contraction_rate(scan, text):
    """Contractions per 100 words of prose.

    Measured over the same stripped copy scan.py measures its own stats on, so
    `don't` inside a code fence is not counted as how this person talks.
    """
    prose = scan.strip_for_stats(text)
    words = scan.tokenize(prose)
    if not words:
        return None
    return 100.0 * len(CONTRACTION_RX.findall(prose)) / len(words)


def measure_one(scan, path):
    """Everything one sample contributes, or None when it cannot be read."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print("measure_voice: %s" % exc, file=sys.stderr)
        return None

    findings, stats = scan.scan(text)
    stats["contraction_rate"] = contraction_rate(scan, text)
    p0 = [f for f in findings if f["priority"] == "P0"]
    scored = scan.apply_exemptions(text)

    return {
        "path": path,
        "words": stats.get("word_count", 0),
        "reliability": scan.reliability(stats.get("word_count", 0)),
        "stats": stats,
        "p0": [{"id": f["id"], "label": f["label"], "line": f["line"]} for f in p0],
        "marks": count_marks(scan, text, scored, stats),
    }


def count_marks(scan, raw_text, scored, stats):
    """The raw counts behind every mechanics suggestion.

    Reported alongside the suggestion rather than folded into it. "semicolon:
    forbid" is a claim about a person; "0 semicolons in 4,100 words" is what the
    samples actually said, and only the second is something they can check.
    """
    return {
        "em_dashes": stats.get("em_dashes", 0),
        "em_dashes_per_1k": stats.get("em_dashes_per_1k", 0.0),
        # Entities blanked first, the same as the voice check does: the `;`
        # closing `&nbsp;` is markup, and counting it would report semicolon
        # habits this writer does not have and then suggest allowing them.
        "semicolons": len(re.findall(r";", scan.blank_entities(scored))),
        "emoji": len(scan.EMOJI_RX.findall(scored)),
        "curly_quotes": len(scan.CURLY_QUOTE_RX.findall(raw_text)),
        "one_word_sentences": len([
            m for m in scan.ONE_WORD_SENTENCE_RX.finditer(scored)
            if not scan.ONE_WORD_ABBREV_RX.fullmatch(m.group(0))]),
        "oxford_missing": len(scan.OXFORD_MISSING_RX.findall(scored)),
        "oxford_present": len(scan.OXFORD_PRESENT_RX.findall(scored)),
        "date_us": len(scan.US_DATE_RX.findall(scored)),
        "date_dmy": len(scan.DMY_DATE_RX.findall(scored)),
        "date_iso": len(scan.ISO_DATE_RX.findall(scored)),
    }


def totals(samples, key):
    return sum(s["marks"].get(key, 0) or 0 for s in samples)


def suggest_mechanics(samples):
    """A starter `mechanics` object, with the count behind each line.

    Silence in the samples is read as a ban only where a ban is the cheap
    direction. A writer who used no emoji in four pieces very likely does not use
    them, and being wrong costs one line they delete. A writer with no semicolons
    is a weaker signal, and it is still offered, because the alternative is
    offering nothing and the person then never being asked the question.

    Every value here is returned with its evidence so the caller can print both.
    Nothing in this function decides anything. It proposes, with the count.
    """
    words = sum(s["words"] for s in samples) or 1
    out = []

    def add(key, value, why):
        out.append((key, value, why))

    em = totals(samples, "em_dashes")
    rate = 1000.0 * em / words
    if em == 0:
        add("em_dash", "forbid", "0 in %d words" % words)
    elif rate <= 2.0:
        # Capped a little above what they actually do, not at it. A cap set to
        # the observed rate fails the next piece for being one dash busier than
        # the average of the last four, which is noise rather than a defect.
        cap = max(1.0, round(rate + 0.5, 1))
        add("em_dash", "limit", "%d in %d words (%.1f/1k), cap suggested %.1f"
            % (em, words, rate, cap))
        add("max_em_dashes_per_1000w", cap, "")
    else:
        add("em_dash", "allow", "%d in %d words (%.1f/1k): this writer uses them"
            % (em, words, rate))

    for key, mark, noun in (("semicolon", "semicolons", "semicolons"),
                            ("emoji", "emoji", "emoji"),
                            ("curly_quotes", "curly_quotes", "curly quotes"),
                            ("one_word_sentence", "one_word_sentences",
                             "one-word sentences")):
        n = totals(samples, mark)
        add(key, "forbid" if n == 0 else "allow",
            "%d %s in %d words" % (n, noun, words))

    missing, present = totals(samples, "oxford_missing"), totals(samples, "oxford_present")
    if present > missing * 2:
        add("oxford_comma", "require", "%d serial commas present, %d missing"
            % (present, missing))
    elif missing > present * 2:
        add("oxford_comma", "forbid", "%d serial commas missing, %d present"
            % (missing, present))
    else:
        add("oxford_comma", "allow", "%d present, %d missing: no clear habit"
            % (present, missing))

    dates = {"mdy": totals(samples, "date_us"),
             "dmy": totals(samples, "date_dmy"),
             "iso": totals(samples, "date_iso")}
    top = max(dates, key=lambda k: dates[k])
    if dates[top] == 0:
        # "0 dates" rather than "no dates", so every line in this block carries a
        # count. A suggestion whose evidence is a sentence reads as a judgement,
        # and the point of the column is that the reader can check it.
        add("date_format", "any", "0 dates in %d words" % words)
    else:
        add("date_format", top, "%s" % ", ".join("%d %s" % (v, k)
                                                 for k, v in sorted(dates.items()) if v))
    return out


def aggregate(samples):
    """{measure: {"mean": x, "sd": y, "n": k}} across the samples."""
    out = {}
    for key, _ in MEASURES:
        values = [s["stats"][key] for s in samples
                  if s["stats"].get(key) is not None]
        if values:
            out[key] = {"mean": round(mean(values), 2),
                        "sd": round(sd(values), 2),
                        "n": len(values)}
    return out


def measured_block(agg):
    """The `Measured from samples` block out of voices/TEMPLATE.md, filled in."""
    lines = ["```"]
    for key, label in MEASURES:
        entry = agg.get(key)
        lines.append("%-22s %s" % (label + ":",
                                   "" if entry is None else entry["mean"]))
    lines.append("```")
    return "\n".join(lines)


def mechanics_block(suggestions):
    body = {key: value for key, value, _ in suggestions}
    return json.dumps({"mechanics": body}, indent=2)


def report(samples, agg, suggestions, contaminated):
    out = ["voice measurement: %d sample(s)" % len(samples), ""]

    out.append("  %-34s %7s  %-12s %s" % ("sample", "words", "reliability", "P0"))
    for s in samples:
        name = os.path.basename(s["path"])
        if len(name) > 34:
            name = name[:31] + "..."
        out.append("  %-34s %7d  %-12s %s"
                   % (name, s["words"], s["reliability"],
                      "-" if not s["p0"] else
                      ", ".join(sorted({f["id"] for f in s["p0"]}))))
    out.append("")

    out.append("aggregate (mean across samples, spread between them)")
    for key, label in MEASURES:
        entry = agg.get(key)
        if entry is None:
            out.append("  %-24s %-8s %s" % (label, "-", "not measurable here"))
            continue
        note = ""
        if entry["n"] < len(samples):
            note = "from %d of %d samples" % (entry["n"], len(samples))
        out.append("  %-24s %-8s +/- %-6s %s"
                   % (label, entry["mean"], entry["sd"], note))
    out.append("")

    out.append("paste into the profile, under `## Measured from samples`")
    out.append(measured_block(agg))
    out.append("")

    out.append("a starting point for `mechanics`, one question each")
    for key, value, why in suggestions:
        if why:
            out.append("  %-28s %-10s %s" % (key, json.dumps(value), why))
    out.append("")
    out.append(mechanics_block(suggestions))
    out.append("")

    thin = [s for s in samples if s["words"] < THIN_SAMPLE_WORDS]
    if thin:
        out.append("note: %d sample(s) under %d words. Stylometry on a short "
                   "piece is noise, and a profile built on it will describe the "
                   "piece rather than the person: %s"
                   % (len(thin), THIN_SAMPLE_WORDS,
                      ", ".join(os.path.basename(s["path"]) for s in thin)))

    if len(samples) < 3:
        out.append("note: %d sample(s). The spread column above is what tells "
                   "you whether one profile can describe this writer at all, "
                   "and it means little under three." % len(samples))

    if contaminated:
        out.append("")
        out.append("STOP. %d sample(s) carry a P0 fingerprint, which is evidence "
                   "of AI-assisted writing:" % len(contaminated))
        for s in contaminated:
            for f in s["p0"]:
                out.append("  %s:%s  %s" % (os.path.basename(s["path"]),
                                            f["line"], f["label"]))
        out.append("")
        out.append("Ask the author before going further. A tell that reaches a "
                   "profile is reproduced on purpose, forever. If they confirm a "
                   "sample was assisted, drop it, rerun this, and record what "
                   "you dropped under `## Known contamination`.")

    out.append("")
    out.append("Every suggestion above comes from these documents and nothing "
               "else. Read the samples yourself for what no counter sees: "
               "paragraph openings, how they transition, where they hedge, how "
               "they sign off, and what they refuse to write.")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("samples", nargs="+", help="files this person wrote")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    scan = load_scan()
    samples = [s for s in (measure_one(scan, p) for p in args.samples) if s]
    if not samples:
        print("measure_voice: no readable samples", file=sys.stderr)
        return 2

    agg = aggregate(samples)
    suggestions = suggest_mechanics(samples)
    contaminated = [s for s in samples if s["p0"]]

    if args.json:
        print(json.dumps({
            "samples": [{"path": s["path"], "words": s["words"],
                         "reliability": s["reliability"], "p0": s["p0"],
                         "marks": s["marks"]} for s in samples],
            "aggregate": agg,
            "measured_block": measured_block(agg),
            "mechanics": {k: v for k, v, _ in suggestions},
            "mechanics_evidence": {k: w for k, _, w in suggestions if w},
            "contaminated": [s["path"] for s in contaminated],
        }, indent=2))
    else:
        print(report(samples, agg, suggestions, contaminated))

    return 1 if contaminated else 0


if __name__ == "__main__":
    sys.exit(main())
