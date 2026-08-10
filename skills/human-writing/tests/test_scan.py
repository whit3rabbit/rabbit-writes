#!/usr/bin/env python3
"""
Calibration tests. Known-slop scores high, known-human scores low, and the
things this skill promises never to touch stay untouched.

Run: python3 tests/test_scan.py   (from the skill root)
"""

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, "scripts", "scan.py")
VERIFY = os.path.join(ROOT, "scripts", "verify.py")
SAMPLES = os.path.join(ROOT, "tests", "samples")

failures = []


def check(name, condition, detail=""):
    if condition:
        print("  pass  %s" % name)
    else:
        print("  FAIL  %s  %s" % (name, detail))
        failures.append(name)


def scan_json(path, *extra):
    out = subprocess.run(
        [sys.executable, SCAN, path, "--json", *extra],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main():
    print("calibration")
    ai = scan_json(os.path.join(SAMPLES, "ai-sample.md"))
    human = scan_json(os.path.join(SAMPLES, "human-sample.md"))

    ai_total = sum(ai["counts"][k] for k in ("P0", "P1", "P2"))
    human_total = sum(human["counts"][k] for k in ("P0", "P1", "P2"))

    check("AI sample raises 20+ findings", ai_total >= 20, "got %d" % ai_total)
    check("AI sample raises P0 findings", ai["counts"]["P0"] >= 3,
          "got %d" % ai["counts"]["P0"])
    check("human sample raises no P0", human["counts"]["P0"] == 0,
          "got %d: %s" % (human["counts"]["P0"],
                          [f["id"] for f in human["findings"]
                           if f["priority"] == "P0"]))
    check("human sample stays under 6 findings", human_total < 6,
          "got %d: %s" % (human_total, [f["id"] for f in human["findings"]]))
    check("AI sample separated by more than 4x", ai_total > human_total * 4,
          "%d vs %d" % (ai_total, human_total))

    print("stylometrics")
    check("human burstiness in range", human["stats"]["burstiness"] >= 0.45,
          "got %s" % human["stats"]["burstiness"])
    check("reliability reported", human["reliability"] in
          ("high", "medium", "low", "insufficient"))

    # Burstiness is an independent axis from vocabulary. A draft can pass every
    # word check and still read as machine output because the rhythm is even.
    metro = scan_json(os.path.join(SAMPLES, "metronomic-sample.md"))
    metro_ids = {f["id"] for f in metro["findings"]}
    check("metronomic sample is clean on vocabulary",
          not ({"tier1", "chatbot-artifact", "generic-conclusion"} & metro_ids),
          str(metro_ids))
    check("metronomic sample still flags uniformity",
          "uniformity" in metro_ids or "uniform-paragraphs" in metro_ids,
          "burstiness %s, para sd %s" % (metro["stats"]["burstiness"],
                                         metro["stats"].get("paragraph_sd")))
    check("metronomic burstiness below human floor",
          metro["stats"]["burstiness"] < 0.45,
          "got %s" % metro["stats"]["burstiness"])
    check("human burstiness beats metronomic",
          human["stats"]["burstiness"] > metro["stats"]["burstiness"],
          "%s vs %s" % (human["stats"]["burstiness"], metro["stats"]["burstiness"]))

    print("bands")
    fp = [f for f in ai["findings"] if f["band"] == "fingerprint"]
    craft = [f for f in ai["findings"] if f["band"] == "craft"]
    check("fingerprints and craft both populated", fp and craft)
    check("wordiness is banded as craft, never fingerprint",
          all(f["band"] == "craft" for f in ai["findings"] if f["id"] == "clarity"))

    print("fingerprint detection")
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                     encoding="utf-8") as fh:
        fh.write("A line with a zero​width space.\n\n"
                 "See https://example.com/x?utm_source=chatgpt.com for more.\n\n"
                 "Contact [Your Name] before 2025-XX-XX.\n\n"
                 "As of my last training update, this was true. citeturn0search0\n")
        tricky = fh.name
    t = scan_json(tricky)
    ids = {f["id"] for f in t["findings"]}
    for pid in ("hidden-unicode", "ai-utm", "placeholder",
                "cutoff-disclaimer", "citation-leak"):
        check("detects %s" % pid, pid in ids)
    os.unlink(tricky)

    print("self-reference exemption")
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                     encoding="utf-8") as fh:
        fh.write('A guide about AI writing.\n\n'
                 'Avoid phrases like "delve into the rich tapestry of innovation".\n\n'
                 '```\ndelve tapestry nestled showcasing\n```\n\n'
                 '> Experts believe this is a testament to progress.\n')
        meta = fh.name
    with_exempt = scan_json(meta)
    without = scan_json(meta, "--no-exempt")
    check("exemption suppresses quoted examples",
          len(with_exempt["findings"]) < len(without["findings"]),
          "%d vs %d" % (len(with_exempt["findings"]), len(without["findings"])))
    os.unlink(meta)

    print("voice rules")
    VOICES = os.path.join(ROOT, "..", "rabbit-writes", "voices")
    whit3rabbit_rules = os.path.join(VOICES, "whit3rabbit.rules.json")
    if not os.path.exists(whit3rabbit_rules):
        check("whit3rabbit.rules.json present", False, whit3rabbit_rules)
    else:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(
                "Good morning,\n\n"
                "We need to circle back on the synergy here — the wild west "
                "of AI driven tooling is a real risk \U0001F680. I'm so excited "
                "to announce our 100% secure platform, live September 12, 2025.\n\n"
                "Attached is the report; it covers everything.\n\n"
                "No.\n\n"
                "Thanks,\n-whit3rabbit\n")
            bad = fh.name

        v = scan_json(bad, "--voice-rules", whit3rabbit_rules)
        vids = {f["id"] for f in v["findings"] if f["band"] == "voice"}
        for pid, why in (
            ("voice-em-dash", "em dash"),
            ("voice-semicolon", "semicolon"),
            ("voice-emoji", "emoji"),
            ("voice-one-word-sentence", "one-word sentence"),
            ("voice-date-format", "US date"),
            ("voice-banned-word", "banned word"),
            ("voice-banned-phrase", "banned phrase"),
            ("absolute-claim", "absolute security claim"),
            ("manufactured-enthusiasm", "manufactured enthusiasm"),
        ):
            check("voice catches %s" % why, pid in vids, str(sorted(vids)))

        check("voice findings are P0", all(
            f["priority"] == "P0" for f in v["findings"]
            if f["band"] == "voice" and f["id"] != "voice-curly-quote"))
        check("voice band reported separately", v["counts"]["voice"] >= 9,
              str(v["counts"]))

        # A register profile relaxes general rules. It must never relax a voice rule.
        relaxed = scan_json(bad, "--voice-rules", whit3rabbit_rules, "--profile", "casual")
        rids = {f["id"] for f in relaxed["findings"] if f["band"] == "voice"}
        check("casual register does not relax voice rules", vids == rids,
              "lost: %s" % (vids - rids))

        # No voice rules means no voice band at all.
        plain = scan_json(bad)
        check("voice band empty without --voice-rules",
              plain["counts"].get("voice", 0) == 0)
        os.unlink(bad)

        # The writer's own sample must not trip the writer's own rules.
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(
                "Good morning,\n\n"
                "Attached is the Q3 incident review. Short version: the outage "
                "came from an expired certificate on the internal proxy, not from "
                "the deploy. We caught it in 22 minutes.\n\n"
                "I really appreciate the time your team spent on the rollback "
                "plan. I know it wasn't easy on a Friday.\n\n"
                "The evidence is in section 3, with the raw logs linked at the "
                "bottom. I believe the fix holds, and I want to re-check the "
                "renewal alerting before we close it out on 12 September 2025.\n\n"
                "Thanks,\n-whit3rabbit\n")
            good_sample = fh.name
        g = scan_json(good_sample, "--voice-rules", whit3rabbit_rules)
        check("whit3rabbit's own register passes their own rules",
              g["counts"]["voice"] == 0,
              str([f["label"] for f in g["findings"] if f["band"] == "voice"]))
        os.unlink(good_sample)

    print("template rules are inert")
    tmpl = os.path.join(VOICES, "TEMPLATE.rules.json")
    if os.path.exists(tmpl):
        t = scan_json(os.path.join(SAMPLES, "human-sample.md"), "--voice-rules", tmpl)
        tids = {f["id"] for f in t["findings"] if f["band"] == "voice"}
        check("template flags nothing on clean prose except its example rule",
              tids <= {"example-rule"}, str(tids))

    print("preservation validator")
    orig = ("# Heading One\n\n"
            "Some prose that delves into the tapestry.\n\n"
            "```python\nx = 1  # delve\n```\n\n"
            "| a | b |\n| - | - |\n\n"
            "See https://example.com/p?utm_source=chatgpt.com&page=2\n")

    good = ("# Heading one\n\n"
            "Some prose that explores the subject.\n\n"
            "```python\nx = 1  # delve\n```\n\n"
            "| a | b |\n| - | - |\n\n"
            "See https://example.com/p?page=2\n")

    bad = ("# Heading One Rewritten\n\n"
           "Some prose that explores the subject, seamlessly.\n\n"
           "```python\nx = 2  # explore\n```\n\n"
           "| a | c |\n| - | - |\n\n"
           "See https://example.com/other\n")

    def run_verify(o, r):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as f1:
            f1.write(o)
            p1 = f1.name
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as f2:
            f2.write(r)
            p2 = f2.name
        res = subprocess.run([sys.executable, VERIFY, p1, p2, "--json"],
                             capture_output=True, text=True)
        os.unlink(p1)
        os.unlink(p2)
        return json.loads(res.stdout), res.returncode

    ok, code = run_verify(orig, good)
    check("clean rewrite passes", ok["ok"] and code == 0,
          str(ok.get("violations")))
    check("title-case heading fix is carved out",
          not any("heading" in v["kind"] for v in ok["violations"]))
    check("stripping an AI utm parameter is carved out",
          not any("URL" in v["kind"] for v in ok["violations"]))

    broken, code = run_verify(orig, bad)
    check("destructive rewrite fails", not broken["ok"] and code == 1)
    kinds = {v["kind"] for v in broken["violations"]}
    check("catches altered code block",
          any("code block" in k for k in kinds), str(kinds))
    check("catches altered table", any("table" in k for k in kinds), str(kinds))
    check("catches rewritten heading", any("heading" in k for k in kinds), str(kinds))

    added_em = run_verify("Plain sentence here.", "Plain sentence — here.")[0]
    check("catches added em dash",
          any("em dashes added" in v["kind"] for v in added_em["violations"]))

    print()
    if failures:
        print("%d failure(s): %s" % (len(failures), ", ".join(failures)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
