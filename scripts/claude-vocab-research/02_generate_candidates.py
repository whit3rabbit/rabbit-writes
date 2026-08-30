#!/usr/bin/env python3
"""
Generate Claude-vocabulary candidates from the dataset's lead cluster.

    python3 scripts/claude-vocab-research/02_generate_candidates.py
    python3 scripts/claude-vocab-research/02_generate_candidates.py --limit 50
    python3 scripts/claude-vocab-research/02_generate_candidates.py --json

Reads the analysis.js snapshot 01 fetched, emits
docs/claude-vocab-research/candidates.json. Nothing here lands in the shipped
lexicon.json: a candidate carries its evidence (lift, weekly-trend summary)
and a `status` a human edits to `accepted` or `rejected`, and only
04_merge_accepted.py writes the shipped file. That review step is not
ceremony. The dataset's lift scores come from a k=8 clustering whose
parameters were outcome-tuned, and the corpus is pull-description prose, so
the top of the list is real signal (load-bearing, quietly) while the middle
is ordinary words an AI happens to reach for (nothing, alone, whose). Lift
nominates, the corpus stage calibrates, a human decides.

Inflections group into families before review, because the lexicon spells
inflections as separate flat entries (foster, fosters, fostering) and a
reviewer should accept or reject "carries, carrying, carried" as one decision.
Grouping links two candidates only through the regular inflection forms of a
word the cluster itself contains, which cannot link unrelated words.

Rerunning preserves review: `status` and `note` carry forward for every
family still emitted, and a reviewed family that no longer qualifies is kept
with a `stale-evidence` flag rather than silently dropped.

Exit 0 on a written file, 1 when the snapshot is missing.
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

import claude_vocab_io  # noqa: E402
from rwlib import cli_error, inflect, lexicon as lexicon_mod  # noqa: E402


def lexicon_words(lexicon):
    """Every word the shipped lexicon already owns, any list, lowercased.

    A candidate colliding with any of them would double-flag or land in two
    tiers at merge, so it is excluded at the source.
    """
    out = set()
    for key in ("tier1", "tier1_phrases", "tier2", "tier3", "clarity",
                "clarity_phrases", "technical_exempt", "academic_exempt"):
        for word in lexicon.get(key, []):
            out.add(word.lower())
    return out


def group_families(candidates, cluster_words):
    """{stem: [forms]} over the candidate words, keyed by strongest member.

    Two candidates group when both sit in the regular inflection set of some
    word the cluster contains (forms() of that word plus the word itself).
    Linking through the full word list rather than only through candidates is
    what joins carries, carrying, and carried: the bare "carry" carries the
    lift below the threshold, but its form set still ties the three together.

    The stem is the highest-lift member, so the family's evidence block is
    its strongest member's, and the tie is broken alphabetically for
    deterministic regeneration.
    """
    candidate_set = set(candidates)
    parent = {word: word for word in candidates}

    def find(word):
        while parent[word] != word:
            parent[word] = parent[parent[word]]
            word = parent[word]
        return word

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for base in cluster_words:
        members = [w for w in ([base] + inflect.forms(base))
                   if w in candidate_set]
        for member in members[1:]:
            union(members[0], member)

    groups = {}
    for word in candidates:
        groups.setdefault(find(word), []).append(word)
    return {sorted(members, key=lambda w: (-candidates[w], w))[0]:
            sorted(members) for members in groups.values()}


def generate(analysis, excluded, covered, limits):
    """The candidate families, before carry-forward.

    `excluded` is every word the shipped lexicon already owns. `covered` maps
    a word to the catalogue pattern id already flagging it, and such words are
    dropped rather than flagged: there is nothing left to decide about them.
    `limits` holds lift_min, ratio_min, late_floor, and the family cap.
    """
    lead = claude_vocab_io.lead_component(analysis)
    words, lifts, series = lead["word_list"], lead["word_lift"], lead["series"]

    candidates = {}
    for i, word in enumerate(words):
        if (lifts[i] < limits["lift_min"]
                or not claude_vocab_io.WORD_RX.fullmatch(word)
                or word in excluded
                or covered(word)):
            continue
        # The list runs lift-descending, so a word appearing twice keeps its
        # stronger evidence rather than being overwritten by the weaker copy.
        if word in candidates:
            continue
        trend = claude_vocab_io.trend_of(series[i])
        if not claude_vocab_io.passes_trend(
                trend, limits["ratio_min"], limits["late_floor"]):
            continue
        candidates[word] = lifts[i]

    families = []
    for stem, forms in group_families(candidates, words).items():
        i = words.index(stem)
        families.append({
            "stem": stem,
            "forms": forms,
            "lift": candidates[stem],
            "trend": claude_vocab_io.trend_of(series[i]),
            "status": "pending",
            "proposed_tier": "tier2",
            "flags": [],
            "note": "",
        })
    # Strongest evidence first, so the cap keeps the review load small
    # without silently dropping the interesting half.
    families.sort(key=lambda f: (-f["lift"], f["stem"]))
    return families[:limits["family_limit"]]


def carry_forward(families, previous):
    """Review survives regeneration.

    `status` and `note` copy over for every family still present. A family
    somebody reviewed (anything past `pending`) that no longer qualifies is
    kept whole with a `stale-evidence` flag, because a review decision
    evaporating in a diff nobody reads is how accepted words get regenerated
    into different ones.
    """
    if not previous:
        return families
    old_families = {f["stem"]: f for f in previous.get("families", [])}
    emitted = set()
    for family in families:
        emitted.add(family["stem"])
        old = old_families.get(family["stem"])
        if not old:
            continue
        for key in ("status", "note", "proposed_tier"):
            if key in old:
                family[key] = old[key]
    for stem in sorted(set(old_families) - emitted):
        old = old_families[stem]
        if old.get("status") == "pending":
            continue
        flags = list(old.get("flags", []))
        if "stale-evidence" not in flags:
            flags.append("stale-evidence")
        old["flags"] = flags
        families.append(old)
    families.sort(key=lambda f: (-f["lift"], f["stem"]))
    return families


def main():
    examples = [
        "python3 scripts/claude-vocab-research/02_generate_candidates.py",
        "python3 scripts/claude-vocab-research/02_generate_candidates.py --limit 50",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--limit", type=int, default=claude_vocab_io.FAMILY_LIMIT,
                    help="cap on emitted families, highest lift first "
                         "(default %d, reviewable in one sitting)"
                         % claude_vocab_io.FAMILY_LIMIT)
    ap.add_argument("--raw-dir", default=claude_vocab_io.RAW_DIR,
                    help=argparse.SUPPRESS)
    ap.add_argument("--out", default=claude_vocab_io.CANDIDATES_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--lexicon", default=claude_vocab_io.LEXICON_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    analysis_path = os.path.join(
        args.raw_dir, claude_vocab_io.DATASETS["analysis"]["filename"])
    if not os.path.exists(analysis_path):
        ap.error("missing %s. Run 01_fetch_dataset.py first: the snapshot is "
                 "not in git, only its hash is" % analysis_path)
    with open(analysis_path, encoding="utf-8") as fh:
        analysis = claude_vocab_io.parse_analysis(fh.read())

    lexicon = lexicon_mod.load(args.lexicon)
    excluded = lexicon_words(lexicon)

    def covered(word):
        return claude_vocab_io.covered_by_catalogue(word, args.lexicon)
    limits = {"lift_min": claude_vocab_io.LIFT_MIN,
              "ratio_min": claude_vocab_io.TREND_RATIO_MIN,
              "late_floor": claude_vocab_io.LATE_FLOOR_ZERO_EARLY,
              "family_limit": args.limit}
    families = generate(analysis, excluded, covered, limits)

    previous = None
    if os.path.exists(args.out):
        previous = claude_vocab_io.load_json(args.out)
    families = carry_forward(families, previous)

    spec = claude_vocab_io.DATASETS["analysis"]
    data = {
        "schema_version": claude_vocab_io.SCHEMA_VERSION,
        "generated": {
            "lexicon_version_at_generation": lexicon.get("version"),
            "dataset": {"commit": claude_vocab_io.COMMIT,
                        "sha256": spec["sha256"], "url": spec["url"]},
            "thresholds": dict(claude_vocab_io.thresholds(),
                               family_limit=args.limit),
        },
        "families": families,
    }
    problems = claude_vocab_io.candidate_problems(data)
    if problems:
        ap.error("refusing to write a file that fails its own schema:\n  "
                 + "\n  ".join(problems))
    claude_vocab_io.write_json(args.out, data)

    pending = sum(1 for f in families if f["status"] == "pending")
    if args.json:
        print(json.dumps({"families": len(families), "pending": pending,
                          "out": args.out}, indent=2))
    else:
        print("wrote %d families (%d pending review) to %s"
              % (len(families), pending, args.out))
        print("Next: 03_corpus_evidence.py counts every family over the "
              "100-README corpus, then a human reviews `status` fields, then "
              "04_merge_accepted.py writes the shipped lexicon.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
