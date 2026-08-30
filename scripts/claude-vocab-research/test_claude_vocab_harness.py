#!/usr/bin/env python3
"""
The Claude-vocabulary research pipeline, tested over a synthetic snapshot.

Everything here builds its own analysis.js, day files, corpus READMEs, and
lexicon in a temporary directory. Nothing touches the network:
`01_fetch_dataset.py` is the one stage that would, and the tests that reach it
substitute a stub, the same bargain `test_thesaurus_harness.py` makes.

The fixtures are ASCII string constants written at run time, never downloaded,
so the suite runs on a checkout with nothing installed and CI stays offline.
The real snapshot is exercised exactly once, by the human session that
generates the committed candidates file.

    python3 scripts/claude-vocab-research/test_claude_vocab_harness.py

Stdlib only, 3.9+.
"""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
DETECTOR = os.path.join(REPO_ROOT, "scripts", "detector-corpus")
for path in (HERE, ENGINE, DETECTOR):
    if path not in sys.path:
        sys.path.insert(0, path)

import claude_vocab_io  # noqa: E402
import corpus_io  # noqa: E402
from rwlib import lexicon as lexicon_mod  # noqa: E402


def load_stage(filename):
    """A numbered stage, loaded by path: `02_generate_candidates` is not a
    legal module name, which is why nothing imports these and this loader
    exists."""
    spec = importlib.util.spec_from_file_location(
        filename.replace(".py", "").replace("0", "stage", 1),
        os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = load_stage("02_generate_candidates.py")
evidence = load_stage("03_corpus_evidence.py")
picker = load_stage("05_pick_pr_samples.py")
fetcher = load_stage("01_fetch_dataset.py")

failures = []


def check(name, condition, detail=""):
    if condition:
        print("  pass   %s" % name)
    else:
        print("  FAIL   %s  %s" % (name, detail))
        failures.append(name)


def series_for(early, late):
    """A 24-week series: `early` repeated over the first 12 weeks, `late`
    over the last 12, which is exactly the window split trend_of reads."""
    return [early] * 12 + [late] * 12


def build_analysis():
    """The dataset shape in miniature: two components, one lead, parallel
    arrays, a 24-week axis, a non-ascii word, and a duplicate entry."""
    lead_words = [
        "load-bearing", "quietly", "caf\xe9", "flatword",
        "carries", "carrying", "carry", "survives", "seam", "seams",
        "quietly",
    ]
    lead_lifts = [100.0, 50.0, 60.0, 40.0, 30.0, 20.0, 5.0, 25.0, 20.0, 18.0,
                  3.0]
    lead_series = [
        series_for(0, 6), series_for(1, 40), series_for(0, 9),
        series_for(5, 5), series_for(1, 30), series_for(0, 10),
        series_for(1, 8), series_for(0, 0.4), series_for(0, 2),
        series_for(0, 2), series_for(1, 40),
    ]
    return {
        "generated": "2026-08-27",
        "weeks": ["w%02d" % i for i in range(24)],
        "k": 8,
        "components": [
            {"lead": False, "share": 0.2, "start_share": 0.2,
             "end_share": 0.2, "word_list": ["ship", "dock"],
             "word_lift": [3.0, 2.0], "series": None,
             "count": [1] * 24, "appearances": [1] * 24},
            {"lead": True, "share": 0.1, "start_share": 0.009,
             "end_share": 0.44, "word_list": lead_words,
             "word_lift": lead_lifts, "series": lead_series,
             "count": [1] * 24, "appearances": [1] * 24},
        ],
    }


def write_analysis(base, data=None):
    """The snapshot as 01 would have written it."""
    text = claude_vocab_io.ANALYSIS_PREFIX + json.dumps(
        data if data is not None else build_analysis()) + ";\n"
    path = os.path.join(base, "analysis.js")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def minimal_lexicon():
    """A lexicon with the lists the pipeline reads and one catalogue pattern,
    so exclusion and the pattern-covered refusal are testable."""
    return {
        "version": 6,
        "tier1": ["delve"],
        "tier1_phrases": [],
        "tier2": ["crucial", "foster"],
        "tier3": ["very"],
        "clarity": [],
        "clarity_phrases": [],
        "technical_exempt": ["state"],
        "patterns": [{
            "id": "load-bearing", "label": "Load-bearing (metaphorical)",
            "band": "fingerprint", "priority": "P1",
            "rx": "(?i)(?<![\\w-])load[- ]bearing(?![\\w-])"
                "(?!\\s+(?:wall|beam|joist|girder)s?\\b)",
        }],
    }


def write_lexicon(base, lexicon=None):
    path = os.path.join(base, "lexicon.json")
    claude_vocab_io.write_json(path,
                               lexicon if lexicon is not None
                               else minimal_lexicon())
    return path


def run_generate(base, **kwargs):
    """generate() over the fixture, with the pattern check against the temp
    lexicon."""
    with open(os.path.join(base, "analysis.js"), encoding="utf-8") as fh:
        analysis = claude_vocab_io.parse_analysis(fh.read())
    limits = {"lift_min": claude_vocab_io.LIFT_MIN,
              "ratio_min": claude_vocab_io.TREND_RATIO_MIN,
              "late_floor": claude_vocab_io.LATE_FLOOR_ZERO_EARLY,
              "family_limit": kwargs.get("family_limit",
                                         claude_vocab_io.FAMILY_LIMIT)}
    excluded = kwargs.get("excluded", {"delve", "crucial", "foster", "very",
                                       "state"})
    lexicon_path = kwargs.get("lexicon_path",
                              os.path.join(base, "lexicon.json"))
    return gen.generate(
        analysis, excluded,
        lambda word: claude_vocab_io.covered_by_catalogue(word, lexicon_path),
        limits)


def family_of(families, stem):
    for family in families:
        if family["stem"] == stem:
            return family
    return None


def candidates_object(families, thresholds=None, dataset=None):
    return {
        "schema_version": claude_vocab_io.SCHEMA_VERSION,
        "generated": {
            "lexicon_version_at_generation": 6,
            "dataset": dataset or {"commit": "a" * 40, "sha256": "b" * 64,
                                   "url": "https://example/analysis.js"},
            "thresholds": thresholds or claude_vocab_io.thresholds(),
        },
        "families": families,
    }


# --------------------------------------------------------------------------
# Parser


def test_parser():
    base = tempfile.mkdtemp(prefix="rabbit-claude-vocab-")
    try:
        write_analysis(base)
        with open(os.path.join(base, "analysis.js"), encoding="utf-8") as fh:
            data = claude_vocab_io.parse_analysis(fh.read())
        lead = claude_vocab_io.lead_component(data)
        check("prefix and trailing semicolon are stripped",
              data["generated"] == "2026-08-27")
        check("parallel arrays survive parsing",
              len(lead["word_list"]) == len(lead["word_lift"])
              == len(lead["series"]) == 11)
        check("non-lead components with null series are tolerated",
              all(c.get("series") is None
                  for c in data["components"] if not c.get("lead")))
        check("the word shape admits hyphens and refuses accents",
              claude_vocab_io.WORD_RX.fullmatch("load-bearing") is not None
              and claude_vocab_io.WORD_RX.fullmatch("caf\xe9") is None)

        def refuses(mangled, name):
            try:
                claude_vocab_io.parse_analysis(mangled)
                check(name, False, "parsed without complaint")
            except ValueError as exc:
                check(name, True, str(exc))

        refuses(claude_vocab_io.ANALYSIS_PREFIX + "{\"no components\": 1};\n",
                "no lead component is refused")
        data_two_leads = build_analysis()
        data_two_leads["components"][0]["lead"] = True
        refuses(claude_vocab_io.ANALYSIS_PREFIX
                + json.dumps(data_two_leads) + ";\n",
                "two lead components are refused")
        data_short = build_analysis()
        data_short["components"][1]["word_lift"] = data_short[
            "components"][1]["word_lift"][:-1]
        refuses(claude_vocab_io.ANALYSIS_PREFIX
                + json.dumps(data_short) + ";\n",
                "misaligned parallel arrays are refused")
        data_weeks = build_analysis()
        data_weeks["components"][1]["series"][0] = [0, 1]
        refuses(claude_vocab_io.ANALYSIS_PREFIX
                + json.dumps(data_weeks) + ";\n",
                "a series row off the weeks axis is refused")
        refuses("window.SOMETHING_ELSE = {};\n",
                "a changed prefix is refused")
    finally:
        shutil.rmtree(base)


# --------------------------------------------------------------------------
# Trend


def test_trend_boundaries():
    cases = [
        # (series, passes, note)
        (series_for(1, 3.0), True, "ratio exactly at the minimum passes"),
        (series_for(1, 2.9), False, "ratio under the minimum fails"),
        (series_for(0, 1.0), True, "zero early with late at the floor passes"),
        (series_for(0, 0.9), False, "zero early under the floor fails"),
        (series_for(0, 0), False, "an empty word fails everywhere"),
        (series_for(2, 2), False, "a flat word fails the ratio"),
    ]
    for series, expected, note in cases:
        trend = claude_vocab_io.trend_of(series)
        check(note, claude_vocab_io.passes_trend(trend) == expected,
              str(trend))
    trend = claude_vocab_io.trend_of(series_for(0, 6))
    check("growth from zero records ratio None, not a division error",
          trend["ratio"] is None and trend["late_mean"] == 6.0, str(trend))


# --------------------------------------------------------------------------
# Generation


def test_generate_filters_and_families():
    base = tempfile.mkdtemp(prefix="rabbit-claude-vocab-")
    try:
        write_analysis(base)
        write_lexicon(base)
        families = run_generate(base)
        stems = {f["stem"] for f in families}

        check("lift below the minimum is never a candidate",
              all(f["lift"] >= claude_vocab_io.LIFT_MIN for f in families))
        check("non-ascii words are excluded by the word shape",
              all("caf\xe9" not in f["forms"] for f in families),
              str(sorted(f["forms"] for f in families)))
        check("a word already owned by the lexicon is excluded",
              "delve" not in stems and "crucial" not in stems)
        check("a word covered by a catalogue pattern is excluded",
              "load-bearing" not in stems,
              "the temp lexicon carries the load-bearing pattern")
        check("a flat trend fails candidacy",
              "flatword" not in stems)
        check("zero early under the late floor fails candidacy",
              "survives" not in stems)
        check("zero early over the late floor passes candidacy",
              "seam" in stems)
        check("a duplicate word keeps its stronger lift",
              family_of(families, "quietly")["lift"] == 50.0)

        carries = family_of(families, "carries")
        check("inflections group through a below-threshold base word",
              carries is not None
              and carries["forms"] == ["carries", "carrying"],
              str(carries and carries["forms"]))
        check("the stem is the highest-lift member",
              carries["stem"] == "carries" and carries["lift"] == 30.0)
        check("a lone word is its own single-form family",
              family_of(families, "quietly")["forms"] == ["quietly"])
        check("seam and seams are one family",
              family_of(families, "seam")["forms"] == ["seam", "seams"])

        limited = run_generate(base, family_limit=1)
        check("the family cap keeps the strongest family",
              len(limited) == 1 and limited[0]["stem"] == "quietly",
              str([f["stem"] for f in limited]))
    finally:
        shutil.rmtree(base)


def test_carry_forward_preserves_review():
    families = [
        {"stem": "seam", "forms": ["seam"], "lift": 21.0,
         "trend": {"early_mean": 0.0, "late_mean": 2.0, "ratio": None},
         "status": "accepted", "proposed_tier": "tier2", "flags": [],
         "note": "reviewed 2026-08", "corpus": {"readmes": 3, "hits": 5,
                                                "new_tier2_clusters": 0}},
        {"stem": "flatword", "forms": ["flatword"], "lift": 40.0,
         "trend": {"early_mean": 5.0, "late_mean": 5.0, "ratio": 1.0},
         "status": "rejected", "proposed_tier": "tier2", "flags": [],
         "note": "ordinary word"},
        {"stem": "gone", "forms": ["gone"], "lift": 19.0,
         "trend": {"early_mean": 0.0, "late_mean": 2.0, "ratio": None},
         "status": "pending", "proposed_tier": "tier2", "flags": [],
         "note": ""},
    ]
    regenerated = [
        {"stem": "seam", "forms": ["seam"], "lift": 21.0,
         "trend": {"early_mean": 0.0, "late_mean": 2.0, "ratio": None},
         "status": "pending", "proposed_tier": "tier2", "flags": [],
         "note": ""},
        {"stem": "newword", "forms": ["newword"], "lift": 33.0,
         "trend": {"early_mean": 0.0, "late_mean": 3.0, "ratio": None},
         "status": "pending", "proposed_tier": "tier2", "flags": [],
         "note": ""},
    ]
    out = gen.carry_forward(regenerated, {"families": families})
    seam = family_of(out, "seam")
    check("status and note survive a regeneration",
          seam["status"] == "accepted" and seam["note"] == "reviewed 2026-08")
    check("a rejected family that vanished is kept with a flag",
          family_of(out, "flatword") is not None
          and "stale-evidence" in family_of(out, "flatword")["flags"])
    check("a pending family that vanished is dropped",
          family_of(out, "gone") is None)
    check("families stay strongest-first after carry-forward",
              [f["stem"] for f in out] == ["flatword", "newword", "seam"],
              str([f["stem"] for f in out]))


def test_schema_validator_rejects():
    good = {
        "stem": "seam", "forms": ["seam", "seams"], "lift": 20.0,
        "trend": {"early_mean": 0.0, "late_mean": 2.0, "ratio": None},
        "status": "pending", "proposed_tier": "tier2", "flags": [],
        "note": "",
    }
    check("a well-formed candidates object passes",
          claude_vocab_io.candidate_problems(
              candidates_object([good])) == [])
    cases = [
        ("schema_version", lambda d: d.update(schema_version=2)),
        ("thresholds", lambda d: d["generated"]["thresholds"].pop(
            "lift_min")),
        ("dataset pin", lambda d: d["generated"]["dataset"].pop("commit")),
        ("lexicon version echo", lambda d: d["generated"].pop(
            "lexicon_version_at_generation")),
        ("stem", lambda d: d["families"][0].update(stem="")),
        ("forms", lambda d: d["families"][0].update(forms=[])),
        ("stem missing from its own forms",
         lambda d: d["families"][0].update(forms=["seams"])),
        ("lift", lambda d: d["families"][0].update(lift="high")),
        ("trend block", lambda d: d["families"][0].update(trend={})),
        ("status", lambda d: d["families"][0].update(status="maybe")),
        ("tier1 as a merge target",
         lambda d: d["families"][0].update(proposed_tier="tier1")),
        ("flags", lambda d: d["families"][0].update(flags="none")),
        ("duplicate stems",
         lambda d: d["families"].append(dict(d["families"][0]))),
    ]
    for name, break_it in cases:
        data = candidates_object([dict(good)])
        break_it(data)
        problems = claude_vocab_io.candidate_problems(data)
        check("a hand edit breaking %s is rejected" % name,
              problems != [], str(problems))


# --------------------------------------------------------------------------
# Corpus evidence


def write_corpus(base, texts):
    """[(name, text)] into the repos layout, plus the directory back."""
    corpus = os.path.join(base, "repos")
    for name, text in texts:
        directory = os.path.join(corpus, name)
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "README.md"), "w",
                  encoding="utf-8") as fh:
            fh.write(text)
    return corpus


def test_corpus_evidence_boundaries():
    base = tempfile.mkdtemp(prefix="rabbit-claude-vocab-")
    empty_base = base + "-empty"
    try:
        # Five docs carry "seam" (one past the demotion threshold), one
        # carries the cluster-boundary paragraphs. "seamless" must not count.
        texts = [("repo-%d" % i, "A seam appeared here.\n") for i in range(5)]
        texts.append(("clusters", (
            "# Clusters\n\nA crucial seam in one paragraph.\n\n"
            "The seam and the seams together.\n\n"
            "A crucial and crucial paragraph that already fired.\n\n"
            "A paragraph with only a seam.\n\n"
            "The seamless surface counts nothing.\n")))
        corpus = write_corpus(base, texts)

        family = {"stem": "seam", "forms": ["seam", "seams"],
                  "lift": 20.0,
                  "trend": {"early_mean": 0.0, "late_mean": 2.0,
                            "ratio": None},
                  "status": "pending", "proposed_tier": "tier2",
                  "flags": [], "note": ""}
        data = candidates_object([family])
        tier2_rx = lexicon_mod.word_regex(["crucial"])
        evidence.annotate(data, evidence.corpus_texts(corpus), tier2_rx)

        check("corpus counts use the scanner's word boundary",
              data["families"][0]["corpus"]["hits"] == 9,
              str(data["families"][0]["corpus"]))
        check("readmes counts docs, not hits",
              data["families"][0]["corpus"]["readmes"] == 6)
        check("a word past the flag threshold is demoted",
              data["families"][0]["status"] == "flagged"
              and data["families"][0]["flags"] == ["technical-vocabulary"])
        check("new_tier2_clusters counts exactly the paragraphs that tip",
              data["families"][0]["corpus"]["new_tier2_clusters"] == 2,
              str(data["families"][0]["corpus"]))

        # Rerunning over the same corpus changes nothing, including flags.
        evidence.annotate(data, evidence.corpus_texts(corpus), tier2_rx)
        check("annotation is idempotent",
              data["families"][0]["flags"].count(
                  "technical-vocabulary") == 1)

        # A rerun over a corpus without the word retracts the machine's own
        # demotion but never a human status.
        empty = write_corpus(empty_base, [("solo", "Nothing to see.\n")])
        data["families"][0]["status"] = "flagged"
        evidence.annotate(data, evidence.corpus_texts(empty), tier2_rx)
        check("an evidence retraction lifts only the machine demotion",
              data["families"][0]["status"] == "pending"
              and data["families"][0]["flags"] == [])
        data["families"][0]["status"] = "accepted"
        evidence.annotate(data, evidence.corpus_texts(empty), tier2_rx)
        check("a human status survives an evidence retraction",
              data["families"][0]["status"] == "accepted")
    finally:
        shutil.rmtree(base)
        shutil.rmtree(empty_base, ignore_errors=True)


# --------------------------------------------------------------------------
# Merge, end to end


def run_stage(filename, *args):
    result = subprocess.run(
        [sys.executable, os.path.join(HERE, filename), *args],
        capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


def test_merge_end_to_end():
    base = tempfile.mkdtemp(prefix="rabbit-claude-vocab-")
    try:
        write_analysis(base)
        lexicon_path = write_lexicon(base)
        candidates_path = os.path.join(base, "candidates.json")
        corpus = write_corpus(base, [("solo", "Plain prose.\n")])

        out, err, code = run_stage(
            "02_generate_candidates.py", "--raw-dir", base,
            "--out", candidates_path, "--lexicon", lexicon_path)
        check("02 writes a schema-valid candidates file",
              code == 0 and os.path.exists(candidates_path), err)
        out, err, code = run_stage(
            "03_corpus_evidence.py", "--candidates", candidates_path,
            "--corpus-dir", corpus, "--lexicon", lexicon_path)
        check("03 annotates in place", code == 0, err)

        data = claude_vocab_io.load_json(candidates_path)
        check("the full run passes its own schema",
              claude_vocab_io.candidate_problems(data) == [])
        check("corpus blocks landed on every family",
              all("corpus" in f for f in data["families"]))

        out, err, code = run_stage(
            "04_merge_accepted.py", "--candidates", candidates_path,
            "--lexicon", lexicon_path)
        check("zero accepted families is an error, not a no-op write",
              code != 0, err)

        seam = family_of(data["families"], "seam")
        seam["status"] = "accepted"
        claude_vocab_io.write_json(candidates_path, data)
        out, err, code = run_stage(
            "04_merge_accepted.py", "--candidates", candidates_path,
            "--lexicon", lexicon_path)
        merged = claude_vocab_io.load_json(lexicon_path)
        check("an accepted family merges and bumps the version",
              code == 0 and merged["version"] == 7
              and "seam" in merged["tier2"]
              and "seams" in merged["tier2"], err or str(merged["tier2"]))
        check("existing tier entries keep their place",
              merged["tier2"][:2] == ["crucial", "foster"])

        first_bytes = open(lexicon_path, encoding="utf-8").read()
        out, err, code = run_stage(
            "04_merge_accepted.py", "--candidates", candidates_path,
            "--lexicon", lexicon_path)
        check("a re-merge with nothing new is a byte-identical no-op",
              code == 0
              and open(lexicon_path, encoding="utf-8").read() == first_bytes
              and claude_vocab_io.load_json(lexicon_path)["version"] == 7,
              err)
    finally:
        shutil.rmtree(base)


def test_merge_refusals():
    base = tempfile.mkdtemp(prefix="rabbit-claude-vocab-")
    try:
        lexicon_path = write_lexicon(base)
        before = open(lexicon_path, encoding="utf-8").read()

        def family(stem, forms, tier="tier2", corpus=True):
            record = {"stem": stem, "forms": forms, "lift": 20.0,
                      "trend": {"early_mean": 0.0, "late_mean": 2.0,
                                "ratio": None},
                      "status": "accepted", "proposed_tier": tier,
                      "flags": [], "note": ""}
            if corpus:
                record["corpus"] = {"readmes": 1, "hits": 1,
                                    "new_tier2_clusters": 0}
            return record

        # (name, families, allow_uncalibrated, needle in stderr)
        cases = [
            ("uncalibrated candidates are refused without the flag",
             [family("seam", ["seam"], corpus=False)], False, "corpus"),
            ("tier1 is not a merge target",
             [family("ladder", ["ladder"], tier="tier1")], True, "tier1"),
            ("a word already in another tier is refused",
             [family("very", ["very"])], True, "already in"),
            ("a word covered by a catalogue pattern is refused",
             [family("load-bearing", ["load-bearing"])], True, "pattern"),
        ]
        for name, families, allow, needle in cases:
            candidates_path = os.path.join(base, "candidates.json")
            claude_vocab_io.write_json(
                candidates_path, candidates_object(families))
            args = ["--candidates", candidates_path,
                    "--lexicon", lexicon_path]
            if allow:
                args.append("--allow-uncalibrated")
            out, err, code = run_stage("04_merge_accepted.py", *args)
            check(name, code != 0 and needle in err, err[:200])
            check("%s, and nothing was written" % name,
                  open(lexicon_path, encoding="utf-8").read() == before)
    finally:
        shutil.rmtree(base)


# --------------------------------------------------------------------------
# Sample picking

LONG_BODY = ("We rebuilt the parser and the seam it sat on. " * 20).strip()
LINKED_FOOTER = ("\n\nGenerated with "
                 "[Claude Code](https://claude.com/claude-code)")
PLAIN_FOOTER = "\n\nGenerated with Claude Code"
# CJK escapes: a body that is long but not English, which the ascii floor
# exists to drop.
CJK_BODY = ("\u30c6\u30b9\u30c8\u306e\u6587\u7ae0\u3067\u3059 " * 40).strip()


def write_day(base, day, records):
    path = os.path.join(base, "day-%s.jsonl" % day)
    with open(path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")
    return path


def test_pick_filters_and_commands():
    records = [
        {"ts": "2026-08-24T05:45:00Z", "repo": "a/demo", "author": "who",
         "body": LONG_BODY + LINKED_FOOTER},
        # Same body one row down: the duplicate hash must not survive.
        {"ts": "2026-08-24T05:46:00Z", "repo": "a/demo", "author": "who",
         "body": LONG_BODY + LINKED_FOOTER},
        # Footer but too short.
        {"ts": "2026-08-24T06:00:00Z", "repo": "a/demo", "author": "who",
         "body": "Short." + PLAIN_FOOTER},
        # Footer and long but another language.
        {"ts": "2026-08-24T07:00:00Z", "repo": "a/demo", "author": "who",
         "body": CJK_BODY + LINKED_FOOTER},
        # Long and English, no footer.
        {"ts": "2026-08-24T08:00:00Z", "repo": "a/demo", "author": "who",
         "body": LONG_BODY},
        # Plain-text footer spelling, long enough.
        {"ts": "2026-08-24T09:00:00Z", "repo": "b/demo", "author": "who",
         "body": LONG_BODY + " Again." + PLAIN_FOOTER},
    ]
    picked = picker.pick(records, "2026-08-24", set())
    check("both footer spellings match",
          any(p["row"] == 0 for p in picked)
          and any(p["row"] == 5 for p in picked),
          str([p["row"] for p in picked]))
    check("short bodies are dropped", all(p["row"] != 2 for p in picked))
    check("non-English bodies are dropped", all(p["row"] != 3 for p in picked))
    check("footerless bodies are dropped", all(p["row"] != 4 for p in picked))
    again = picker.pick(records, "2026-08-24", {picked[0]["sha256"]})
    check("a duplicate hash across days is dropped",
          all(p["row"] != 0 for p in again))

    sample = picked[0]
    check("ids are slugs the corpus can use as filenames",
          corpus_io.ID_RX.fullmatch(sample["id"]) is not None, sample["id"])
    command = picker.add_sample_command(sample, "docs", "scratch/x.txt")
    for fragment in ("--label generated", "--loader github-jsonl",
                     "--row 0", "--split 2026-08-24", "--field body",
                     "--dataset louisabraham/load-bearing"):
        check("the add command carries %s" % fragment,
              fragment in command, command)
    check("the command quotes the free-text provenance",
          json.dumps(picker.WHY_CREDIBLE) in command, command)


def test_day_file_guards():
    base = tempfile.mkdtemp(prefix="rabbit-claude-vocab-")
    try:
        records = [{"ts": "2026-08-24T05:45:00Z", "repo": "a/demo",
                    "author": "who", "body": LONG_BODY + LINKED_FOOTER}]
        path = write_day(base, "2026-08-24", records)
        payload = open(path, "rb").read()
        held = dict(claude_vocab_io.DAY_FILES)
        try:
            claude_vocab_io.DAY_FILES["2026-08-24"] = {
                "filename": "day-2026-08-24.jsonl",
                "path": "data/days/2026-08-24.jsonl",
                "url": "https://example/day.jsonl",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload), "license": "synthetic",
            }
            loaded, error = picker.load_day(base, "2026-08-24")
            check("a hash-matching day file loads",
                  error is None and len(loaded) == 1, str(error))
            # The pinned hash no longer describes the bytes on disk.
            claude_vocab_io.DAY_FILES["2026-08-24"] = dict(
                held["2026-08-24"])
            loaded, error = picker.load_day(base, "2026-08-24")
            check("a hash-mismatched day file is refused",
                  loaded is None and "pinned" in error, str(error))
        finally:
            claude_vocab_io.DAY_FILES.clear()
            claude_vocab_io.DAY_FILES.update(held)
    finally:
        shutil.rmtree(base)


# --------------------------------------------------------------------------
# Fetch guards


def test_fetch_guards():
    base = tempfile.mkdtemp(prefix="rabbit-claude-vocab-")
    try:
        analysis_path = write_analysis(base)
        payload = open(analysis_path, "rb").read()
        os.remove(analysis_path)
        spec = {
            "filename": "analysis.js",
            "url": "https://example/analysis.js",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload), "license": "synthetic",
        }
        held = dict(claude_vocab_io.DATASETS)
        real_fetch = fetcher.fetch
        fetcher.fetch = lambda url: (payload, None)
        try:
            row = fetcher.process("analysis", spec, base, dry_run=False)
            check("a verified fetch is written",
                  row["action"] == "fetched"
                  and os.path.exists(analysis_path), str(row))
            row = fetcher.process("analysis", spec, base, dry_run=False)
            check("an already-verified file is kept without a request",
                  row["action"] == "kept", str(row))

            claude_vocab_io.DATASETS["analysis"] = dict(spec,
                                                        sha256="0" * 64)
            row = fetcher.process("analysis", claude_vocab_io.DATASETS[
                "analysis"], base, dry_run=False)
            check("a hash mismatch refuses and keeps nothing",
                  row["action"] == "mismatch"
                  and "claude_vocab_io" in row["note"], str(row))
        finally:
            fetcher.fetch = real_fetch
            claude_vocab_io.DATASETS.clear()
            claude_vocab_io.DATASETS.update(held)

        _bytes, error = fetcher.fetch("ftp://example/analysis.js")
        check("a non-http scheme is refused",
              _bytes is None and "scheme" in error, str(error))
    finally:
        shutil.rmtree(base)


# --------------------------------------------------------------------------
# Runner. Stays at the bottom: main() collects tests off globals(), so
# anything defined below it is invisible to a stdlib run.


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            print(name)
            fn()
    print("\n%d check(s) failed" % len(failures) if failures
          else "\nall checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
