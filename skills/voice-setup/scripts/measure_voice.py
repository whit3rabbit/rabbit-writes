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
    python3 measure_voice.py samples/*.md --name dana --write-fingerprint

What comes out:

  a per-sample table, so an outlier is visible rather than averaged away
  the aggregate, with a spread, because how *consistent* a writer is across
    pieces is itself a fact about them
  the `Measured from samples` block from voices/TEMPLATE.md, ready to paste
  a starter `mechanics` object, ready to paste
  the distributions behind the means, because a mean hides the thing a reader
    recognizes: two writers with the same 18-word average write nothing alike
    if one opens half her sentences with "But"
  a voice fingerprint, with the band of the writer's own samples around it,
    which is what turns "does this sound like them" into a number

The fingerprint is the one output that is a file rather than a paste. It goes
beside the profile as `voices/<name>.fingerprint.json`, and `scan.py --voice`
measures a document against it and reports the distance at P2. Nothing enforces
it: see rwlib/stylometry.py on why a distance that could block a commit would be
the failure this plugin exists to avoid.

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
from collections import Counter

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
# Where a written fingerprint lands, resolved the same way and for the same
# reason. rwlib.voices owns the answer, so a moved voices/ directory moves this.
from rwlib import stylometry, voices as voices_mod   # noqa: E402

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

    # The prose, with the markup gone. Everything stylometry measures runs off
    # this copy, because scan.py's own distance check does: a fingerprint built
    # over raw markdown and compared against stripped prose would be measuring
    # two different things, and a code fence has no function words in it at all.
    prose = scan.strip_for_stats(text)

    return {
        "path": path,
        "words": stats.get("word_count", 0),
        "reliability": scan.reliability(stats.get("word_count", 0)),
        "stats": stats,
        "prose": prose,
        "distributions": stylometry.distributions(
            prose, split_sentences=scan.split_sentences),
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


def build_fingerprint(samples, name, exemplars=False):
    """The stored fingerprint, or None when there are too few samples.

    Two is the floor and it is thin: with two samples the calibration band is a
    single number, and a single number cannot say how much a person varies. The
    caller prints that rather than hiding it.
    """
    if len(samples) < 2:
        return None
    return stylometry.fingerprint([s["prose"] for s in samples], voice=name,
                                  exemplars=exemplars)


def distribution_report(samples):
    """The shapes the aggregate table averages away.

    Openers, connectors, contractions, hedges and sign-offs. None of these is a
    threshold and none of them ends up in the rules file: they are what a person
    reads before writing the profile markdown, which is the half no counter
    reaches. The script's job here is the same as everywhere else in it, which
    is to make the question specific.
    """
    out = ["distributions (what the averages above hide)"]

    openers = Counter()
    para_openers = Counter()
    connectors = Counter()
    contractions = Counter()
    hedges = Counter()
    intensifiers = Counter()
    for s in samples:
        d = s["distributions"]
        for entry in d["sentence_openers"]:
            openers[entry["word"]] += entry["n"]
        for entry in d["paragraph_openers"]:
            para_openers[entry["word"]] += entry["n"]
        for group, body in d["connectors"].items():
            connectors[group] += round(body["per_1k"] * d["words"] / 1000.0)
        for entry in d["contractions"]["inventory"]:
            contractions[entry["form"]] += entry["n"]
        for entry in d["hedges"]["used"]:
            hedges[entry["term"]] += entry["n"]
        for entry in d["intensifiers"]["used"]:
            intensifiers[entry["term"]] += entry["n"]

    def line(label, counter, note=""):
        if not counter:
            out.append("  %-22s %s" % (label, "none in these samples"))
            return
        body = ", ".join("%s %d" % (term, n) for term, n in counter.most_common(8))
        out.append("  %-22s %s%s" % (label, body, note))

    line("sentence openers", openers)
    line("paragraph openers", para_openers)
    line("connectors", connectors, "   (per group, whole sample set)")
    line("contractions used", contractions)
    line("hedges", hedges)
    line("intensifiers", intensifiers)
    # No rate here. Each row is the commonest forms per sample summed, so the
    # counts are a shape rather than a total, and the aggregate table above
    # already carries the one contraction number that is exact.
    out.append("")
    out.append("  how each sample ends, verbatim. No counter reaches this, and "
               "how a person signs off")
    out.append("  is the line a profile most often gets wrong:")
    for s in samples:
        closer = s["distributions"]["closer"].strip()
        if closer:
            out.append("    %-20s %s" % (os.path.basename(s["path"])[:20],
                                         closer if len(closer) <= 96
                                         else closer[:93] + "..."))
    return "\n".join(out)


def fingerprint_report(fp, written_to=None):
    band = fp["self_distance"]
    out = ["voice fingerprint (%d samples, %d markers)"
           % (fp["n_samples"], len(stylometry.MARKER_WORDS))]
    out.append("  self-distance          %.2f mean, %.2f max across the samples"
               % (band["mean"], band["max"]))
    out.append("  reading                a later document scoring under %.2f is "
               "indistinguishable" % band["max"])
    out.append("                         from another sample of theirs by this "
               "measure. Past 1.5x that,")
    out.append("                         it is a different register.")
    if fp["thin_samples"]:
        out.append("  note                   %d sample(s) under %d words, so the "
                   "band is wider than it"
                   % (fp["thin_samples"], stylometry.RELIABLE_WORDS))
        out.append("                         should be. Add a longer piece "
                   "before trusting it.")
    if fp["n_samples"] < 3:
        out.append("  note                   2 samples means the band is one "
                   "number. It cannot say how")
        out.append("                         much this person varies, only that "
                   "these two differ by that much.")
    if written_to:
        out.append("  written to             %s" % written_to)
        out.append("  scan.py --voice now reports the distance from it, at P2. "
                   "Nothing enforces it:")
        out.append("  a writer is allowed to sound unlike themselves on purpose.")
    else:
        out.append("  not written. Pass --name <voice> --write-fingerprint to "
                   "save it beside the profile.")
    return "\n".join(out)


def report(samples, agg, suggestions, contaminated, fingerprint=None,
           fingerprint_path=None):
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

    out.append(distribution_report(samples))
    out.append("")

    if fingerprint:
        out.append(fingerprint_report(fingerprint, fingerprint_path))
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
    ap.add_argument("--name", metavar="VOICE",
                    help="the profile these samples belong to. Labels the "
                         "fingerprint, and names the file --write-fingerprint "
                         "writes")
    ap.add_argument("--write-fingerprint", action="store_true",
                    help="save the fingerprint to voices/<name>.fingerprint.json, "
                         "where scan.py --voice will find it. Needs --name")
    ap.add_argument("--with-exemplars", action="store_true",
                    help="embed the writer's own paragraphs in the fingerprint, "
                         "for conditioning a conversion. This copies their prose "
                         "into a file that travels with the plugin, so it is "
                         "opt-in and worth asking them about")
    ap.add_argument("--voices-dir", default=voices_mod.VOICES_DIR,
                    help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.write_fingerprint and not args.name:
        print("measure_voice: --write-fingerprint needs --name <voice>, which "
              "decides the filename and labels the fingerprint", file=sys.stderr)
        return 2

    scan = load_scan()
    samples = [s for s in (measure_one(scan, p) for p in args.samples) if s]
    if not samples:
        print("measure_voice: no readable samples", file=sys.stderr)
        return 2

    agg = aggregate(samples)
    suggestions = suggest_mechanics(samples)
    contaminated = [s for s in samples if s["p0"]]
    fingerprint = build_fingerprint(samples, args.name, args.with_exemplars)

    # Never written from contaminated samples. Every other output of this script
    # is a suggestion a person reads and confirms, and this one is a file a
    # later scan measures against without asking: an assisted sample in it makes
    # the assisted register the target, which is the failure the P0 gate exists
    # to prevent, made permanent.
    written_to = None
    if args.write_fingerprint and fingerprint and not contaminated:
        written_to = os.path.join(args.voices_dir,
                                  args.name + stylometry.FINGERPRINT_SUFFIX)
        try:
            stylometry.save(fingerprint, written_to)
        except OSError as exc:
            print("measure_voice: could not write %s: %s" % (written_to, exc),
                  file=sys.stderr)
            return 2
    elif args.write_fingerprint and not fingerprint:
        print("measure_voice: a fingerprint needs at least 2 samples, and one "
              "sample has no self-distance to calibrate against", file=sys.stderr)
    elif args.write_fingerprint and contaminated:
        print("measure_voice: refused to write a fingerprint from samples that "
              "carry a P0. See the report.", file=sys.stderr)

    if args.json:
        print(json.dumps({
            "samples": [{"path": s["path"], "words": s["words"],
                         "reliability": s["reliability"], "p0": s["p0"],
                         "marks": s["marks"],
                         "distributions": s["distributions"]} for s in samples],
            "aggregate": agg,
            "measured_block": measured_block(agg),
            "mechanics": {k: v for k, v, _ in suggestions},
            "mechanics_evidence": {k: w for k, _, w in suggestions if w},
            "contaminated": [s["path"] for s in contaminated],
            "fingerprint": fingerprint,
            "fingerprint_written_to": written_to,
        }, indent=2))
    else:
        print(report(samples, agg, suggestions, contaminated, fingerprint,
                     written_to))

    return 1 if contaminated else 0


if __name__ == "__main__":
    sys.exit(main())
