#!/usr/bin/env python3
"""
The one home for the Claude-vocabulary research pipeline's shared facts.

The dataset manifest (URL, commit, SHA-256, license), the generation
thresholds, the paths, the candidates-file schema check, and the parser for
the dataset's analysis.js live here, and the numbered stages import them. A
threshold restated in two stages is two thresholds the moment somebody edits
one.

Dataset choice is a decision, so it is recorded where the data is named.
louisabraham/load-bearing is a corpus of 47,464 pull-request descriptions
sampled daily from 2025-01-06, clustered into 8 vocabulary components. The
lead component ("AI") grew from roughly 1 percent to roughly 45 percent of
word share over 85 weeks, and its per-word lift scores are this pipeline's
nomination signal. Two disclosures travel with that: the author chose k=8 and
MIN_TF=45 by observing outcomes, and the corpus is pull-description prose
rather than any register the engine ships. Lift is therefore evidence for a
human review, never a basis for auto-acceptance, which is what the candidates
file's status gate exists to enforce.

The corpus-evidence stage measures against the 100-README corpus, with the
caveat recorded here rather than forgotten: those READMEs are 2026 trending
repositories and visibly AI-assisted in places, so "corpus-common" partly
means "Claude-common" already. The corpus's role is false-positive cost on a
stranger's document, not ground truth about human writing, and that is the
reading every number from stage 03 gets.

analysis.js is regenerated daily by upstream CI, so the URL pins a commit sha
rather than a branch: raw.githubusercontent.com/<repo>/<sha>/analysis.js is
immutable and the SHA-256 below is the committed claim. Re-pin by fetching a
new commit, recording its hash here, and regenerating.

Stdlib only, 3.9+.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

from rwlib import lexicon as lexicon_mod  # noqa: E402

# Raw downloads live outside git: candidates.json is committed evidence, but
# a 200kB snapshot of somebody else's corpus and five day files of other
# people's pull-request prose are neither. The manifest below commits each
# URL, hash, and license, and 01_fetch_dataset.py refetches and verifies,
# which is the same bargain the detector corpus makes.
RAW_DIR = os.path.join(REPO_ROOT, "docs", "claude-vocab-research", "raw")
CANDIDATES_PATH = os.path.join(REPO_ROOT, "docs", "claude-vocab-research",
                               "candidates.json")
CORPUS_DIR = os.path.join(REPO_ROOT, "docs", "readme-analysis", "repos")
LEXICON_PATH = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts",
                            "lexicon.json")

# The snapshot everything below was pinned at.
COMMIT = "2a233f653fd72b431850b957b2d28c5c4dbdbaa6"
REPO = "louisabraham/load-bearing"
# The license claim rests on direct correspondence with the author (2026-08),
# because the repository carried no LICENSE file at pinning time. Re-check
# when re-pinning: if a LICENSE has landed, cite it instead.
LICENSE_NOTE = ("MIT, confirmed by the author in direct correspondence "
                "2026-08. The repository carried no LICENSE file at pinning "
                "time and this note is the record")
COLLECTED = "2026-08-27"

# Each entry: filename in RAW_DIR, source URL, SHA-256 of the download, byte
# size at pinning time, license. A mismatch on refetch means the source moved
# or the pin is wrong, and both need a human rather than an overwrite.
DATASETS = {
    "analysis": {
        "filename": "analysis.js",
        "url": "https://raw.githubusercontent.com/%s/%s/analysis.js"
               % (REPO, COMMIT),
        "sha256": "15fa8ad1857d9b3ed2ae1818308e658e312c28d8878da3e324a05c89f42d22fa",
        "bytes": 206768,
        "license": LICENSE_NOTE,
    },
}

# Day files, one per selection round of stage 05. Same shape as DATASETS plus
# the in-repository path the URL was built from, because a github-raw sample's
# provenance records that path and the two must not drift. Five days spread
# across the dataset's life, chosen for footer-bearing English yield.
DAY_FILES = {
    "2026-02-09": {
        "filename": "day-2026-02-09.jsonl",
        "path": "data/days/2026-02-09.jsonl",
        "url": "https://raw.githubusercontent.com/%s/%s/data/days/2026-02-09.jsonl"
               % (REPO, COMMIT),
        "sha256": "f52448e3b442c349d9f76d5ce0c4c185ed14feaea7cf7140b18b63fb01ea3ea0",
        "bytes": 142665,
        "license": LICENSE_NOTE,
    },
    "2026-05-18": {
        "filename": "day-2026-05-18.jsonl",
        "path": "data/days/2026-05-18.jsonl",
        "url": "https://raw.githubusercontent.com/%s/%s/data/days/2026-05-18.jsonl"
               % (REPO, COMMIT),
        "sha256": "cb6e4ae8a84ad32703c17d277b8cfe0699d6cae5016b7c3fc880d0afb7da9683",
        "bytes": 172615,
        "license": LICENSE_NOTE,
    },
    "2026-08-10": {
        "filename": "day-2026-08-10.jsonl",
        "path": "data/days/2026-08-10.jsonl",
        "url": "https://raw.githubusercontent.com/%s/%s/data/days/2026-08-10.jsonl"
               % (REPO, COMMIT),
        "sha256": "2b26f0dfc5916774f1c12594a6392d36b9b805fa1c6fe754ea0ab27c1d8a0632",
        "bytes": 203773,
        "license": LICENSE_NOTE,
    },
    "2026-08-17": {
        "filename": "day-2026-08-17.jsonl",
        "path": "data/days/2026-08-17.jsonl",
        "url": "https://raw.githubusercontent.com/%s/%s/data/days/2026-08-17.jsonl"
               % (REPO, COMMIT),
        "sha256": "16c96cc3c6b0261e569a27695d011916289f56ee583099850189ebcc3237b136",
        "bytes": 200880,
        "license": LICENSE_NOTE,
    },
    "2026-08-24": {
        "filename": "day-2026-08-24.jsonl",
        "path": "data/days/2026-08-24.jsonl",
        "url": "https://raw.githubusercontent.com/%s/%s/data/days/2026-08-24.jsonl"
               % (REPO, COMMIT),
        "sha256": "e43f0c03c4b828bbab4be39a03874396e463ca580d8d1ffa8896c9c87618b146",
        "bytes": 181903,
        "license": LICENSE_NOTE,
    },
}

# The whole calibration of 02_generate_candidates.py, echoed into the
# candidates file's `generated` block as a record of what produced it.
#
# LIFT_MIN: the lead cluster publishes lift for 1000 words and the top of that
#   list is signal while the tail is co-occurrence noise (the author's k=8 and
#   MIN_TF=45 were outcome-tuned, so weak lift is weak evidence). At pinning,
#   15.0 leaves 81 ASCII words, which is one sitting of review.
# TREND_RATIO_MIN: mean weekly frequency in the last TREND_WEEKS weeks divided
#   by the first TREND_WEEKS. Guards a word that sits in the cluster by
#   co-occurrence rather than growth. TREND_WEEKS matches the dataset's own
#   trend_weeks, so the pipeline and the upstream dashboard mean the same
#   window.
# LATE_FLOOR_ZERO_EARLY: a word absent from the whole early window has no
#   ratio, and growth from zero is the strongest signal there is, but only
#   once it is not one stray appearance. At least this many mean weekly
#   appearances in the late window, or the word waits for better evidence.
# CORPUS_FLAG_DOCS: a word appearing in this many of the 100 corpus READMEs is
#   ordinary technical vocabulary and is flagged rather than left pending.
# FAMILY_LIMIT: cap on emitted families, reviewable in one sitting.
LIFT_MIN = 15.0
TREND_RATIO_MIN = 3.0
TREND_WEEKS = 12
LATE_FLOOR_ZERO_EARLY = 1.0
CORPUS_FLAG_DOCS = 5
FAMILY_LIMIT = 100

SCHEMA_VERSION = 1
STATUSES = ("pending", "flagged", "accepted", "rejected")
TIERS = ("tier2", "tier3")
THRESHOLD_KEYS = ("lift_min", "trend_ratio_min", "trend_weeks",
                  "late_floor_zero_early", "corpus_flag_docs", "family_limit")

# The dataset is multilingual (French and Korean bodies appear in the day
# files) and hyphen-bearing (byte-identical, pre-fix, fan-out), so the word
# shape admits hyphens and nothing else outside a-z.
WORD_RX = re.compile(r"^[a-z][a-z-]*$")

# analysis.js is "window.ANALYSIS = <one JSON object>;<newline>". The prefix
# and the trailing semicolon are the only JavaScript in the file, which is
# what makes a json.loads parser safe where an eval would not be.
ANALYSIS_PREFIX = "window.ANALYSIS = "


def covered_by_catalogue(word, lexicon_path=LEXICON_PATH):
    """The catalogue pattern id that already flags this word, or None.

    A word a pattern covers (load-bearing, once the carve-out pattern ships)
    needs no tier entry: a flat-list entry cannot carry the pattern's
    negative lookahead and would double-flag every occurrence. Shared by 02's
    candidate filter and 04's merge refusal so the two cannot disagree about
    what is covered.
    """
    for entry, rx in lexicon_mod.compiled_patterns(lexicon_path):
        if rx.search(word):
            return entry["id"]
    return None


def thresholds():
    """The generation constants, keyed the way the candidates file records them."""
    return {
        "lift_min": LIFT_MIN,
        "trend_ratio_min": TREND_RATIO_MIN,
        "trend_weeks": TREND_WEEKS,
        "late_floor_zero_early": LATE_FLOOR_ZERO_EARLY,
        "corpus_flag_docs": CORPUS_FLAG_DOCS,
        "family_limit": FAMILY_LIMIT,
    }


def parse_analysis(text):
    """The JSON object inside analysis.js, validated for alignment.

    The lead component's three parallel arrays (word_list, word_lift, series)
    are the pipeline's input, and a shape change upstream has to fail loudly
    here rather than mis-parse into wrong candidates: lengths are checked
    against each other and against the weeks axis, and there must be exactly
    one lead component to read.
    """
    if not text.startswith(ANALYSIS_PREFIX):
        raise ValueError("analysis.js no longer starts with %r, so the "
                         "upstream file shape changed. Update the parser in "
                         "claude_vocab_io before trusting any candidate"
                         % ANALYSIS_PREFIX)
    body = text[len(ANALYSIS_PREFIX):].strip()
    if body.endswith(";"):
        body = body[:-1]
    data = json.loads(body)
    leads = [c for c in data.get("components", []) if c.get("lead")]
    if len(leads) != 1:
        raise ValueError("expected exactly one lead component, found %d"
                         % len(leads))
    lead = leads[0]
    words, lifts, series = (lead.get("word_list"), lead.get("word_lift"),
                            lead.get("series"))
    for name, value in (("word_list", words), ("word_lift", lifts),
                        ("series", series)):
        if not isinstance(value, list):
            raise ValueError("lead component's %s is %s, not a list. The "
                             "upstream file shape changed"
                             % (name, type(value).__name__))
    if not (len(words) == len(lifts) == len(series)):
        raise ValueError("lead component arrays disagree on length: "
                         "%d words, %d lifts, %d series"
                         % (len(words), len(lifts), len(series)))
    n_weeks = len(data.get("weeks", []))
    for i, row in enumerate(series):
        if not isinstance(row, list) or len(row) != n_weeks:
            raise ValueError("series[%d] (%r) does not match the %d-week axis"
                             % (i, words[i], n_weeks))
    return data


def lead_component(data):
    for component in data["components"]:
        if component.get("lead"):
            return component
    raise ValueError("no lead component")


def trend_of(series, trend_weeks=None, late_floor=None):
    """{"early_mean", "late_mean", "ratio"} over one word's weekly series.

    ratio is None when the early window is empty, which is growth from zero
    rather than missing evidence, and the caller decides with the late floor
    whether that word qualifies.
    """
    trend_weeks = TREND_WEEKS if trend_weeks is None else trend_weeks
    early = series[:trend_weeks]
    late = series[-trend_weeks:]
    early_mean = sum(early) / float(len(early))
    late_mean = sum(late) / float(len(late))
    ratio = None
    if early_mean > 0:
        ratio = round(late_mean / early_mean, 1)
    return {"early_mean": round(early_mean, 3),
            "late_mean": round(late_mean, 3),
            "ratio": ratio}


def passes_trend(trend, ratio_min=None, late_floor=None):
    """The trend half of candidacy, as one predicate the harness can pin.

    A defined ratio clears ratio_min or the word is out. An empty early
    window has no ratio and clears on the late floor instead, so one stray
    appearance in a dead word's late window cannot ride the zero baseline in.
    """
    ratio_min = TREND_RATIO_MIN if ratio_min is None else ratio_min
    late_floor = (LATE_FLOOR_ZERO_EARLY if late_floor is None
                  else late_floor)
    if trend["ratio"] is None:
        return trend["late_mean"] >= late_floor
    return trend["ratio"] >= ratio_min


def candidate_problems(data):
    """Everything wrong with a candidates object, as prose. Empty means valid.

    Called by 02 before writing, 03 before annotating, 04 before merging, and
    the harness, so a hand edit that breaks the shape is caught by whichever
    stage touches the file next rather than by a reviewer's confusion.
    """
    out = []
    if not isinstance(data, dict):
        return ["candidates data is %s, not an object" % type(data).__name__]
    if data.get("schema_version") != SCHEMA_VERSION:
        out.append("schema_version is %r, this code reads %d"
                   % (data.get("schema_version"), SCHEMA_VERSION))
    generated = data.get("generated")
    if not isinstance(generated, dict):
        out.append("no `generated` block recording what produced the file")
    else:
        held = generated.get("thresholds", {})
        for key in THRESHOLD_KEYS:
            if key not in held:
                out.append("generated.thresholds is missing %r" % key)
        for key in ("commit", "sha256", "url"):
            if not generated.get("dataset", {}).get(key):
                out.append("generated.dataset is missing %r" % key)
        if "lexicon_version_at_generation" not in generated:
            out.append("generated.lexicon_version_at_generation is missing, "
                       "which is what makes a rerun after a lexicon change "
                       "visible instead of silent")
    families = data.get("families")
    if not isinstance(families, list):
        return out + ["no families list"]
    seen = set()
    for i, family in enumerate(families):
        if not isinstance(family, dict):
            out.append("family %d is not an object" % i)
            continue
        stem = family.get("stem")
        label = "family %d (stem %r)" % (i, stem)
        if not isinstance(stem, str) or not stem:
            out.append("family %d has no stem" % i)
            continue
        if stem in seen:
            out.append("%s appears twice" % label)
        seen.add(stem)
        forms = family.get("forms")
        if (not isinstance(forms, list) or not forms
                or not all(isinstance(f, str) and f for f in forms)):
            out.append("%s has no forms list of strings" % label)
            continue
        if stem not in forms:
            out.append("%s does not list its own stem as a form" % label)
        if not isinstance(family.get("lift"), (int, float)):
            out.append("%s has no numeric lift" % label)
        trend = family.get("trend")
        if not isinstance(trend, dict) or not all(
                k in trend for k in ("early_mean", "late_mean", "ratio")):
            out.append("%s has no trend block with early_mean, late_mean, "
                       "ratio" % label)
        if family.get("status") not in STATUSES:
            out.append("%s has status %r, not one of %s"
                       % (label, family.get("status"), "/".join(STATUSES)))
        if family.get("proposed_tier") not in TIERS:
            out.append("%s proposes tier %r, not one of %s. tier1 is a hand "
                       "edit gated by the patterns.md section 12 table, not "
                       "a merge target"
                       % (label, family.get("proposed_tier"), "/".join(TIERS)))
        if not isinstance(family.get("flags"), list):
            out.append("%s has no flags list" % label)
        if not isinstance(family.get("note"), str):
            out.append("%s has no note string" % label)
    return out


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, data):
    """indent=2 with a trailing newline, matching lexicon.json, so a
    regeneration with no changes is a byte-identical no-op."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
