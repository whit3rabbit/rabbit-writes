#!/usr/bin/env python3
"""
Calibration tests. Known-slop scores high, known-human scores low, and the
things this skill promises never to touch stay untouched.

Run: python3 tests/test_scan.py   (from the skill root)
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, "scripts", "scan.py")
VERIFY = os.path.join(ROOT, "scripts", "verify.py")
LEXICON = os.path.join(ROOT, "scripts", "lexicon.json")
PATTERNS_MD = os.path.join(ROOT, "references", "patterns.md")
CONTEXT_MD = os.path.join(ROOT, "references", "context.md")
SAMPLES = os.path.join(ROOT, "tests", "samples")

# What each row of the tolerance matrix in references/context.md is called in
# the engine. None means the rule has no pattern and is applied by reading, and
# context.md names those rows in prose for the same reason.
#
# This map is the only way the missing-entry case gets caught. validate.py can
# see a skip set naming an id that does not exist; nothing can see a matrix cell
# that says relaxed and has no entry anywhere, which is how `curly-quote` sat in
# every skip set unable to fire. Adding a row to the matrix without adding a
# line here fails the coverage check below rather than passing silently.
MATRIX_ROW_IDS = {
    "Em dashes": "em-dash-rate",
    "Bold overuse": None,
    "Emoji in headers": "emoji-heading",
    "Excessive bullets": None,
    "Hedging": "hedge-stack",
    "Tier-1 vocabulary": "tier1",
    "Promotional language": "promotional",
    "Significance inflation": "significance-inflation",
    "Copula avoidance": None,
    "Uniform paragraph length": "uniform-paragraphs",
    "Numbered-list inflation": None,
    "Rhetorical questions": "rhetorical-question",
    "Transition phrases": "transition-stack",
    "Generic conclusions": "generic-conclusion",
    "Hashtag stuffing": None,
    "Bullet-NP lists": None,
    "Subjectless fragments": None,
    "Boilerplate clusters": "boilerplate-phrase",
    "Future-narrative closers": "future-narrative",
    "Social endorsement closers": "social-cta",
    "Wall-of-text replies": None,
    "Curly quotes": "curly-quote",
    "Tier-2 clusters": "tier2-cluster",
    "Tier-3 density": "tier3-density",
    "Confidence calibration": "confidence-calibration",
    "Signposting": "signposting",
    "Diff-anchored writing": "diff-anchored",
    "List-label periods": "list-label-period",
}

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


def scan_text(text, *extra):
    """Scan a string. Returns the parsed result and the exit code, so the
    documented --check contract can be asserted rather than assumed."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(text)
        path = fh.name
    try:
        out = subprocess.run([sys.executable, SCAN, path, "--json", *extra],
                             capture_output=True, text=True)
        return json.loads(out.stdout), out.returncode
    finally:
        os.unlink(path)


def scan_with_rules(text, rules, *extra):
    """Scan a string against an inline rules dict.

    Every mechanic in apply_voice_rules is reachable from a user-authored rules
    file, but the two profiles this repo ships exercise one setting each. This
    lets the other branches be tested without inventing a voice to hold them."""
    with tempfile.NamedTemporaryFile("w", suffix=".rules.json", delete=False,
                                     encoding="utf-8") as fh:
        json.dump(rules, fh)
        rules_path = fh.name
    try:
        return scan_text(text, "--voice-rules", rules_path, *extra)
    finally:
        os.unlink(rules_path)


def voice_ids(result):
    return [f["id"] for f in result["findings"] if f["band"] == "voice"]


def tolerance_matrix():
    """[(rule, {register: cell})] from the table in references/context.md."""
    with open(CONTEXT_MD, encoding="utf-8") as fh:
        md = fh.read()
    rows, registers = [], None
    for line in md.split("## Tolerance matrix")[1].split("\n**Extra strict**")[0].splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        if registers is None:
            registers = cells[1:]
            continue
        rows.append((cells[0], dict(zip(registers, cells[1:]))))
    return rows


def tier1_table_terms():
    """Every word in the section 12 replace-on-sight table."""
    with open(PATTERNS_MD, encoding="utf-8") as fh:
        md = fh.read()
    section = md.split("## 12. Tier-1 vocabulary")[1].split("\n## 13.")[0]
    terms = []
    for line in section.splitlines():
        if not line.startswith("|") or line.startswith("|---") or "| Replace |" in line:
            continue
        cell = re.sub(r"\*\([^)]*\)\*", "", line.split("|")[1])
        terms += [t.strip().strip("`").lower() for t in re.split(r"[/,]", cell) if t.strip()]
    return terms


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
        fh.write("A line with a zero\u200bwidth space.\n\n"
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

    print("lexicon and patterns.md agree")
    # Documentation drift here is silent and one-directional: the table says
    # replace on sight, the engine never flags it, and nobody notices until
    # somebody compares the two by hand.
    with open(LEXICON, encoding="utf-8") as fh:
        lex = json.load(fh)
    tier1_known = ({w.lower() for w in lex["tier1"]}
                   | {p.lower() for p in lex["tier1_phrases"]})
    table = tier1_table_terms()
    missing = sorted(t for t in table if t not in tier1_known)
    check("every section 12 word resolves in tier1", not missing, str(missing))
    check("section 12 is not empty", len(table) > 30, "got %d" % len(table))
    for a, b in (("tier1", "tier2"), ("tier1", "tier3"), ("tier2", "tier3")):
        overlap = sorted({w.lower() for w in lex[a]} & {w.lower() for w in lex[b]})
        check("%s and %s do not overlap" % (a, b), not overlap, str(overlap))
    check("'key' is not a tier-3 word", "key" not in {w.lower() for w in lex["tier3"]})

    print("register profiles relax as well as skip")
    spec = importlib.util.spec_from_file_location("rw_scan_test", SCAN)
    scan_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scan_mod)

    # The invisible-character tables are the one place in this engine where a
    # save that normalizes whitespace, or an editor that drops a variation
    # selector, changes behaviour without changing anything a reader can see.
    # Worst case the U+00A0 key becomes a plain space and every space in every
    # document reports as a paste artifact. Assert the codepoints, not the keys.
    print("invisible-character tables")
    expected_hidden = [0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0x00A0, 0x202F]
    got_hidden = sorted(ord(c) for c in scan_mod.HIDDEN_UNICODE)
    check("HIDDEN_UNICODE holds exactly the eight expected codepoints",
          got_hidden == sorted(expected_hidden),
          str(["U+%04X" % c for c in got_hidden]))
    check("every HIDDEN_UNICODE key is one character",
          all(len(c) == 1 for c in scan_mod.HIDDEN_UNICODE),
          str([repr(c) for c in scan_mod.HIDDEN_UNICODE if len(c) != 1]))
    check("SPACE_LIKE_UNICODE is U+00A0 and U+202F",
          sorted(ord(c) for c in scan_mod.SPACE_LIKE_UNICODE) == [0x00A0, 0x202F],
          str(["U+%04X" % ord(c) for c in scan_mod.SPACE_LIKE_UNICODE]))
    check("SPACE_LIKE_UNICODE is a subset of HIDDEN_UNICODE",
          set(scan_mod.SPACE_LIKE_UNICODE) <= set(scan_mod.HIDDEN_UNICODE))
    check("no plain space or ASCII character leaked into the tables",
          not (set(scan_mod.HIDDEN_UNICODE) & set(" \t\n\r")),
          str(sorted(scan_mod.HIDDEN_UNICODE)))
    check("EMOJI_RX still matches the presentation selector U+FE0F",
          bool(scan_mod.EMOJI_RX.search("\ufe0f"))
          and bool(scan_mod.EMOJI_RX.search("\U0001F680")))
    known_ids = ({p["id"] for p in lex["patterns"]}
                 | {"hidden-unicode", "tier1", "clarity", "tier2-cluster",
                    "tier3-density", "uniformity", "low-diversity",
                    "trigram-repetition", "uniform-paragraphs", "em-dash-rate"})
    for table_name, mapping in (("PROFILE_SKIP", scan_mod.PROFILE_SKIP),
                                ("PROFILE_RELAX", scan_mod.PROFILE_RELAX)):
        unknown = sorted({pid for entries in mapping.values() for pid in entries}
                         - known_ids)
        check("%s names only real ids" % table_name, not unknown, str(unknown))

    print("every matrix cell has an engine counterpart")
    matrix = tolerance_matrix()
    check("the tolerance matrix parsed", len(matrix) >= 25, "got %d rows" % len(matrix))
    unmapped = sorted(rule for rule, _ in matrix if rule not in MATRIX_ROW_IDS)
    check("every matrix row is mapped to an id or to None", not unmapped, str(unmapped))
    stale = sorted(set(MATRIX_ROW_IDS) - {rule for rule, _ in matrix})
    check("no mapped row has disappeared from the matrix", not stale, str(stale))

    priority = {p["id"]: p["priority"] for p in lex["patterns"]}
    band = {p["id"]: p["band"] for p in lex["patterns"]}
    muffled = sorted(pid for table in (scan_mod.PROFILE_SKIP, scan_mod.PROFILE_RELAX)
                     for entries in table.values() for pid in entries
                     if band.get(pid) == "fingerprint" and priority.get(pid) == "P0")
    check("no P0 fingerprint is skipped or relaxed anywhere", not muffled, str(muffled))
    gaps = []
    for rule, cells in matrix:
        pid = MATRIX_ROW_IDS.get(rule)
        if pid is None:
            continue
        for register, cell in cells.items():
            skipped = pid in scan_mod.PROFILE_SKIP.get(register, set())
            relaxed = pid in scan_mod.PROFILE_RELAX.get(register, {})
            low = cell.lower()
            if low.startswith("skip"):
                if not skipped:
                    gaps.append("%s x %s says skip, %s is not in PROFILE_SKIP"
                                % (register, rule, pid))
            elif low.startswith("relaxed"):
                if not relaxed:
                    gaps.append("%s x %s says relaxed and nothing implements it"
                                % (register, rule))
            elif low.startswith("**partial**"):
                if register not in scan_mod.VOCAB_EXEMPT_PROFILES:
                    gaps.append("%s x %s says partial but the register has no "
                                "vocabulary exemption" % (register, rule))
            elif low.startswith("p0 only"):
                if not skipped:
                    gaps.append("%s x %s says P0 only, %s still runs"
                                % (register, rule, pid))
            elif "strict" in low:
                if skipped or relaxed:
                    gaps.append("%s x %s says strict, but the engine %s it"
                                % (register, rule, "skips" if skipped else "relaxes"))
    check("no matrix cell is left unimplemented", not gaps, "\n        ".join(gaps))

    quotes = "A note about %s here.\n" % " ".join('“q%d”' % i for i in range(5))
    relaxed, _ = scan_text(quotes, "--profile", "technical-blog")
    strict_off, _ = scan_text(quotes, "--profile", "blog")
    n_relaxed = len([f for f in relaxed["findings"] if f["id"] == "curly-quote"])
    check("curly-quote fires in a register that relaxes it", n_relaxed > 0,
          str([f["id"] for f in relaxed["findings"]]))
    check("the relax allowance is honoured, not ignored",
          n_relaxed == 10 - scan_mod.PROFILE_RELAX["technical-blog"]["curly-quote"],
          "got %d" % n_relaxed)
    check("a register that skips it stays silent",
          not [f for f in strict_off["findings"] if f["id"] == "curly-quote"])

    print("--check exit code")
    clean, code = scan_text("The certificate expired on the internal proxy. "
                            "We caught it in 22 minutes.\n", "--check")
    check("--check exits 0 with no P0", code == 0 and clean["counts"]["P0"] == 0,
          "code %d, %s" % (code, clean["counts"]))
    dirty, code = scan_text("As of my last training update, this was true.\n", "--check")
    check("--check exits 1 on a P0", code == 1 and dirty["counts"]["P0"] >= 1,
          "code %d, %s" % (code, dirty["counts"]))
    _, code = scan_text("As of my last training update, this was true.\n")
    check("without --check a P0 still exits 0", code == 0, "code %d" % code)

    print("false positives the reviewers found")
    stray = ('The flag is " here. A comprehensive robust seamless meticulous '
             'pivotal delve into it.” Done.\n')
    d, _ = scan_text(stray)
    check("a mismatched quote pair does not exempt the span",
          {f["id"] for f in d["findings"]} & {"tier1"}, str(d["findings"]))
    paired = ('He said "a comprehensive robust seamless meticulous pivotal '
              'delve into it" and left.\n')
    d, _ = scan_text(paired)
    check("a matched quote pair still exempts the span",
          not [f for f in d["findings"] if f["id"] == "tier1"],
          str([f["match"] for f in d["findings"]]))

    d, _ = scan_text("Une phrase\u00a0: le texte qui suit tient sur une ligne.\n")
    check("one non-breaking space is not a P0",
          not [f for f in d["findings"] if f["id"] == "hidden-unicode"],
          str(d["findings"]))
    d, _ = scan_text("a\u00a0b\u00a0c\u00a0d\u00a0e\u00a0f words to make a sentence.\n")
    nbsp = [f for f in d["findings"] if f["id"] == "hidden-unicode"]
    check("non-breaking spaces in quantity report at P2",
          len(nbsp) == 1 and nbsp[0]["priority"] == "P2", str(nbsp))
    d, _ = scan_text("a\u200bb zero width here.\n")
    zw = [f for f in d["findings"] if f["id"] == "hidden-unicode"]
    check("a zero-width space is still a P0",
          len(zw) == 1 and zw[0]["priority"] == "P0", str(zw))

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
    VOICES = os.path.join(ROOT, "voices")
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

        # Priorities are read out of the rules file, not out of a list written
        # here. The previous version asserted P0 for everything in the band with
        # two ids excused by name, which held only because this fixture happens
        # to miss hedge-softener (P1), numeric-date (P1), and efficiency-overuse
        # (P2). Adding any of those to the fixture broke an assertion that had
        # nothing to do with the change.
        with open(whit3rabbit_rules, encoding="utf-8") as fh:
            wr = json.load(fh)
        default_pri = wr.get("default_priority", "P0")
        # scan.py hard-codes P2 for these two whatever the voice default is:
        # no regex settles a serial comma, and an editor curls quotes on its own.
        declared = {"voice-curly-quote": "P2", "voice-oxford-comma": "P2"}
        for entry in wr.get("banned_regex", []):
            declared[entry["id"]] = entry.get("priority", default_pri)
        for entry in wr.get("required_when", []):
            declared[entry["id"]] = entry.get("priority", "P2")
        mismatched = [(f["id"], f["priority"], declared.get(f["id"], default_pri))
                      for f in v["findings"] if f["band"] == "voice"
                      and f["priority"] != declared.get(f["id"], default_pri)]
        check("every voice finding reports the priority its rule declares",
              not mismatched, str(mismatched))
        check("and this voice's default is P0, so the band is mostly P0",
              default_pri == "P0"
              and any(f["priority"] == "P0" for f in v["findings"]
                      if f["band"] == "voice"), default_pri)
        check("voice band reported separately", v["counts"]["voice"] >= 9,
              str(v["counts"]))

        # A register profile relaxes general rules. It must never relax a voice rule.
        relaxed = scan_json(bad, "--voice-rules", whit3rabbit_rules, "--profile", "casual")
        rids = {f["id"] for f in relaxed["findings"] if f["band"] == "voice"}
        check("casual register does not relax voice rules", vids == rids,
              "lost: %s" % (vids - rids))

        print("serial comma, the advisory mechanic")
        # TEMPLATE.rules.json documents oxford_comma and nothing read the key
        # until this test existed. Advisory means reported, not enforced: it
        # lands at P2 and it has to stay off the shapes it cannot decide.
        ox, _ = scan_text(
            "We shipped the parser, the linter and the formatter this week.\n\n"
            "Read the catalog with more examples, and the checklist at the end "
            "of any draft or edit.\n\n"
            "She left the room, and he stayed behind to finish it.\n",
            "--voice-rules", whit3rabbit_rules)
        hits = [f for f in ox["findings"] if f["id"] == "voice-oxford-comma"]
        check("a three-item list without the serial comma is reported",
              len(hits) == 1, str([(f["line"], f["match"]) for f in hits]))
        check("the advisory reports at P2, never at the voice default",
              all(f["priority"] == "P2" for f in hits), str(hits))
        check("a compound sentence is not reported",
              all(f["line"] == 1 for f in hits), str([f["line"] for f in hits]))

        # The forbid side had no guard at all: a bare `,\s+(?:and|or)` matches
        # every compound sentence in the language, and nothing exercised the
        # branch, so an entire mechanic shipped reporting on correct punctuation.
        forbid_rules = {"voice": "t", "default_priority": "P0",
                        "mechanics": {"oxford_comma": "forbid"}}
        ox_f, _ = scan_with_rules(
            "We shipped the parser, the linter, and the formatter this week.\n\n"
            "She left the room, and he stayed behind to finish it.\n\n"
            "Read the catalog with more examples, and the checklist at the end.\n",
            forbid_rules)
        fhits = [f for f in ox_f["findings"] if f["id"] == "voice-oxford-comma"]
        check("a serial comma is reported when the voice omits it",
              len(fhits) == 1, str([(f["line"], f["match"]) for f in fhits]))
        check("and it lands on the list, not on the compound sentences",
              all(f["line"] == 1 for f in fhits), str([f["line"] for f in fhits]))
        check("the forbid side is advisory at P2 too",
              all(f["priority"] == "P2" for f in fhits), str(fhits))
        clean_f, _ = scan_with_rules(
            "We shipped the parser, the linter and the formatter this week.\n\n"
            "She left the room, and he stayed behind to finish it.\n",
            forbid_rules)
        check("prose with no serial comma is silent under forbid",
              not [f for f in clean_f["findings"] if f["id"] == "voice-oxford-comma"],
              str(voice_ids(clean_f)))

        print("voice mechanics the shipped profiles do not exercise")
        # Every one of these is reachable from a user-authored rules file, so a
        # regression in any of them ships without a symptom here.
        over, _ = scan_with_rules(
            "The plan — such as it is — has three parts — and a deadline.\n",
            {"voice": "t", "default_priority": "P0",
             "mechanics": {"em_dash": "limit", "max_em_dashes_per_1000w": 2}})
        check("em_dash 'limit' fires above the per-1000-word cap",
              "voice-em-dash-rate" in voice_ids(over), str(voice_ids(over)))
        check("and 'limit' does not also raise the forbid finding",
              "voice-em-dash" not in voice_ids(over), str(voice_ids(over)))
        under, _ = scan_with_rules(
            "The plan has three parts and a deadline, and nobody argued.\n",
            {"voice": "t", "default_priority": "P0",
             "mechanics": {"em_dash": "limit", "max_em_dashes_per_1000w": 2}})
        check("em_dash 'limit' stays quiet under the cap",
              not voice_ids(under), str(voice_ids(under)))

        mdy = {"voice": "t", "default_priority": "P0",
               "mechanics": {"date_format": "mdy"}}
        d_mdy, _ = scan_with_rules("The review closed on 12 September 2025.\n", mdy)
        check("date_format 'mdy' flags day-month-year",
              "voice-date-format" in voice_ids(d_mdy), str(voice_ids(d_mdy)))
        d_ok, _ = scan_with_rules("The review closed on September 12, 2025.\n", mdy)
        check("and leaves month-day-year alone", not voice_ids(d_ok),
              str(voice_ids(d_ok)))

        iso = {"voice": "t", "default_priority": "P0",
               "mechanics": {"date_format": "iso"}}
        d_us, _ = scan_with_rules("The review closed on September 12, 2025.\n", iso)
        d_dmy, _ = scan_with_rules("The review closed on 12 September 2025.\n", iso)
        d_iso, _ = scan_with_rules("The review closed on 2025-09-12.\n", iso)
        check("date_format 'iso' flags both spelled forms",
              "voice-date-format" in voice_ids(d_us)
              and "voice-date-format" in voice_ids(d_dmy),
              "%s / %s" % (voice_ids(d_us), voice_ids(d_dmy)))
        check("and leaves an ISO date alone", not voice_ids(d_iso),
              str(voice_ids(d_iso)))

        # The quote sits inside a quoted span on purpose: that span is blanked
        # in the scored copy, so building the excerpt from it reported a line of
        # spaces and the writer could not see what was being flagged.
        curly, _ = scan_with_rules(
            "He said “the build is green” and closed the ticket.\n",
            {"voice": "t", "default_priority": "P0",
             "mechanics": {"curly_quotes": "forbid"}})
        cq = [f for f in curly["findings"] if f["id"] == "voice-curly-quote"]
        check("curly_quotes 'forbid' finds both marks", len(cq) == 2, str(cq))
        check("and reports at P2, not at the voice default",
              all(f["priority"] == "P2" for f in cq), str(cq))
        check("and the excerpt shows the text, not a blanked span",
              all("build is green" in f["excerpt"] for f in cq),
              str([f["excerpt"] for f in cq]))
        straight, _ = scan_with_rules(
            "He said \"the build is green\" and closed the ticket.\n",
            {"voice": "t", "default_priority": "P0",
             "mechanics": {"curly_quotes": "forbid"}})
        check("and straight quotes are left alone", not voice_ids(straight),
              str(voice_ids(straight)))

        print("required_when, both directions")
        # The suite proved a letter with a closer passes. Nothing proved the
        # check fires without one, so the gate could have been stuck shut.
        no_closer, _ = scan_text(
            "Good morning,\n\n"
            "Attached is the Q3 incident review. The outage came from an "
            "expired certificate on the internal proxy, not from the deploy.\n",
            "--voice-rules", whit3rabbit_rules)
        check("correspondence with no closer fires missing-closer",
              "missing-closer" in voice_ids(no_closer), str(voice_ids(no_closer)))
        with_closer, _ = scan_text(
            "Good morning,\n\n"
            "Attached is the Q3 incident review. The outage came from an "
            "expired certificate on the internal proxy, not from the deploy.\n\n"
            "Thanks,\n-whit3rabbit\n",
            "--voice-rules", whit3rabbit_rules)
        check("and the same letter with one does not",
              "missing-closer" not in voice_ids(with_closer),
              str(voice_ids(with_closer)))
        not_a_letter, _ = scan_text(
            "The certificate expired on the internal proxy at 02:14. We caught "
            "it in 22 minutes and rotated the key.\n",
            "--voice-rules", whit3rabbit_rules)
        check("the when_rx gate keeps it off a document that is not a letter",
              "missing-closer" not in voice_ids(not_a_letter),
              str(voice_ids(not_a_letter)))

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

    print("--allow-structure, for voice conversions")

    def run_verify_flag(o, r):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as f1:
            f1.write(o)
            p1 = f1.name
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as f2:
            f2.write(r)
            p2 = f2.name
        res = subprocess.run([sys.executable, VERIFY, p1, p2, "--json",
                              "--allow-structure"], capture_output=True, text=True)
        os.unlink(p1)
        os.unlink(p2)
        return json.loads(res.stdout), res.returncode

    restructured = ("# Heading one, rewritten to lead with the point\n\n"
                    "Some prose that explores the subject.\n\n"
                    "```python\nx = 1  # delve\n```\n\n"
                    "| a | b |\n| - | - |\n\n"
                    "## A section the conversion added\n\n"
                    "See https://example.com/p?page=2\n")

    strict, strict_code = run_verify(orig, restructured)
    check("a reordered rewrite fails without the flag",
          not strict["ok"] and strict_code == 1,
          str(strict.get("violations")))

    loose, loose_code = run_verify_flag(orig, restructured)
    check("the same rewrite passes with --allow-structure",
          loose["ok"] and loose_code == 0, str(loose.get("violations")))
    check("heading changes are reported, not silently dropped",
          len(loose["structure_changes"]) >= 2, str(loose.get("structure_changes")))

    # The flag must scope to headings only, or it becomes a way to wave through
    # a rewrite that ate a code block.
    scoped, scoped_code = run_verify_flag(orig, bad)
    check("--allow-structure still fails on an altered code block",
          not scoped["ok"] and scoped_code == 1,
          str({v["kind"] for v in scoped["violations"]}))
    em_flagged = run_verify_flag("Plain sentence here.", "Plain sentence — here.")[0]
    check("--allow-structure still fails on an added em dash",
          not em_flagged["ok"])

    print("verify.py reads structure out of prose, not out of code")
    fenced = ("# Title\n\nSome prose here.\n\n"
              "```bash\n# install it\n| --flag | what it does |\nmake\n```\n")
    moved = ("# Title\n\nDifferent prose entirely.\n\n"
             "```bash\n# install it\n| --flag | what it does |\nmake\n```\n")
    res, code = run_verify(fenced, moved)
    check("a shell comment in a fence is not a heading", res["ok"] and code == 0,
          str(res["violations"]))

    urly = "See https://raw.githubusercontent.com/user/repo/main/README.md now.\n"
    res, _ = run_verify(urly, urly.replace("now", "here"))
    check("a path inside a URL is not reported as a path",
          not any("path" in v["kind"] for v in res["violations"]),
          str(res["violations"]))

    hashed = "See https://x.dev/p?utm_source=chatgpt.com# for the writeup.\n"
    res, code = run_verify(hashed, "See https://x.dev/p# for the writeup.\n")
    check("a URL ending in a bare fragment survives normalization",
          res["ok"] and code == 0, str(res["violations"]))

    res, _ = run_verify("Plain sentence about locking.\n",
                        "A holistic sentence about locking.\n")
    check("tells come from the lexicon, not a frozen copy of it",
          any("more tells" in v["kind"] for v in res["violations"]),
          str(res["violations"]))

    # An editor that auto-curls quotes is not a tell generator. Building the
    # counter from every fingerprint pattern swept curly-quote in with the real
    # ones and hard-failed a correct rewrite for something Word did.
    curled, code = run_verify('He said "the lock is a directory" and moved on.\n',
                              'He said “the lock is a directory” and left it there.\n')
    check("auto-curled typography is not counted as a tell",
          curled["ok"] and code == 0, str(curled["violations"]))
    check("and the tell count did not move",
          curled["tells_before"] == curled["tells_after"],
          "%d -> %d" % (curled["tells_before"], curled["tells_after"]))

    # Both hard gates used to run on the raw text, so they fired on things the
    # editor was told to do. A numeric range is correct typography, and a tell
    # quoted in order to warn about it is the exemption scan.py already grants.
    ranged, code = run_verify("The study ran from 2010 to 2023 across four sites.\n",
                              "The study ran 2010–2023 across four sites.\n")
    check("an en dash in a numeric range is not an added em dash",
          ranged["ok"] and code == 0, str(ranged["violations"]))
    spliced = run_verify("Plain sentence here.\n", "Plain sentence — here.\n")[0]
    check("a prose em dash is still caught",
          any(v["kind"] == "em dashes added" for v in spliced["violations"]),
          str(spliced["violations"]))
    check("and the failure names the span that moved the counter",
          any("Plain sentence" in v["detail"] for v in spliced["violations"]
              if v["kind"] == "em dashes added"), str(spliced["violations"]))

    fenced_tell = ("Notes on the draft.\n\n```\nplain\n```\n")
    quoted_tell = ("Notes on the draft.\n\n```\nplain\n```\n\n"
                   'Cut "a word like delve" wherever it turns up.\n')
    exempted, code = run_verify(fenced_tell, quoted_tell)
    check("a tell inside a quoted example does not move the tell gate",
          exempted["ok"] and code == 0, str(exempted["violations"]))
    unquoted = run_verify(fenced_tell, "Notes on the draft.\n\n"
                                       "```\nplain\n```\n\nWe delve into it.\n")[0]
    check("the same tell in running prose still fails",
          any("more tells" in v["kind"] for v in unquoted["violations"]),
          str(unquoted["violations"]))
    check("and the failure names the tell",
          any("delve" in v["detail"] for v in unquoted["violations"]),
          str(unquoted["violations"]))

    # Membership alone hid the duplicate case: drop one of two identical
    # headings, add a different one, and both the membership test and the count
    # test stay happy while a section disappears.
    dup_before = "## Notes\n\nFirst body.\n\n## Notes\n\nSecond body.\n"
    dup_after = "## Notes\n\nFirst body.\n\n## Other\n\nSecond body.\n"
    dup, code = run_verify(dup_before, dup_after)
    check("a dropped duplicate heading is caught",
          not dup["ok"] and code == 1
          and any("heading" in v["kind"] for v in dup["violations"]),
          str(dup["violations"]))
    kept, code = run_verify(dup_before, dup_before)
    check("two identical headings that both survive still pass",
          kept["ok"] and code == 0, str(kept["violations"]))

    print("conversion-depth fixtures")
    # These do not prove the model chose a deep rewrite: mode choice is prompt
    # behaviour and no script can assert it. They prove the measurements the
    # conversion offer is built from actually fire on a document that needs one,
    # and stay quiet on a document that does not.
    rules = os.path.join(VOICES, "whit3rabbit.rules.json")
    if os.path.exists(rules):
        needs = scan_json(os.path.join(SAMPLES, "needs-conversion.md"),
                          "--voice-rules", rules)
        ids = [f["id"] for f in needs["findings"]]
        check("structurally wrong document reports over-cap paragraphs",
              ids.count("voice-paragraph-length") >= 4,
              "got %d" % ids.count("voice-paragraph-length"))
        check("and trips the uniformity detector", "uniformity" in ids, str(set(ids)))
        check("and raises enough voice findings to be worth offering a conversion",
              needs["counts"]["voice"] >= 5, str(needs["counts"]))
        check("and is long enough for the numbers to mean something",
              needs["reliability"] == "high", needs["reliability"])

        clean = scan_json(os.path.join(SAMPLES, "already-in-voice.md"),
                          "--voice-rules", rules)
        check("a document already in the voice raises nothing",
              sum(clean["counts"][k] for k in ("P0", "P1", "P2")) == 0,
              str([f["id"] for f in clean["findings"]]))

    print()
    if failures:
        print("%d failure(s): %s" % (len(failures), ", ".join(failures)))
        return 1
    print("all checks passed")
    return 0


def test_all():
    """Entry point for pytest. The suite is one ordered run over shared
    fixtures, not independent cases, so it stays a single test. Without this,
    pytest collects nothing here and exits green on a file named test_*.py."""
    assert main() == 0, "%d check(s) failed: %s" % (len(failures),
                                                    ", ".join(failures))


if __name__ == "__main__":
    sys.exit(main())
