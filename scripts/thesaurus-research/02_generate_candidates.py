#!/usr/bin/env python3
"""
Generate candidate thesaurus families from WordNet and the frequency counts.

    python3 scripts/thesaurus-research/02_generate_candidates.py
    python3 scripts/thesaurus-research/02_generate_candidates.py --limit 50
    python3 scripts/thesaurus-research/02_generate_candidates.py --json

Reads the datasets 01 fetched, emits docs/thesaurus-research/candidates.json.
Nothing here lands in the shipped thesaurus.json: a candidate carries its
evidence (frequency ranks, ratio, polysemy, gloss) and a `status` a human
edits to `accepted` or `rejected`, and only 04_merge_accepted.py writes the
shipped file. That review step is not ceremony. `preferred_substitutions`
proposals built from these families are edits fixes.py performs with no
part-of-speech awareness, so a polysemous term accepted carelessly rewrites
prose it should not touch: "state" to "say" turns "state machine" into
"say machine".

Direction comes from frequency: the seed (reach word) is common, the synonym
(overreach) at least RATIO_MIN times rarer. Sense reach comes from WordNet's
own ordering: only a seed's first SEED_SENSES_MAX senses per part of speech
contribute synonyms, which keeps "get = obtain" and drops "get = beget".

Rerunning preserves review: `status` and `note` carry forward for every
family and term still emitted, and a reviewed family that no longer
qualifies is kept with a `stale-evidence` flag rather than silently dropped.

Exit 0 on a written file, 1 when the datasets are missing.
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

import thesaurus_io  # noqa: E402
from rwlib import cli_error, fixes, stylometry  # noqa: E402

# Regular inflection suffixes, mirroring measure_voice.term_rx: a term that is
# just the seed inflected (or the seed a de-inflection of the term) would be
# double-counted by the shipped counter, so it is never a candidate.
SUFFIXES = ("s", "es", "ed", "d", "ing")


def is_inflection_pair(a, b):
    return any(a == b + suffix or b == a + suffix for suffix in SUFFIXES)


def ascii_fold(text):
    """Glosses land in a committed JSON file that gets swept for codepoints
    above 127, so anything WordNet spells outside ASCII is dropped rather
    than smuggled through."""
    return text.encode("ascii", "ignore").decode("ascii")


def shipped_terms(thesaurus):
    """Every word the shipped file already owns, reach and overreach both.
    A candidate colliding with any of them would fail thesaurus_check on
    merge, so it is excluded at the source."""
    out = set()
    for family in thesaurus.get("families", []):
        out.add(family["reach"])
        out.update(family["overreach"])
    return out


def generate(wordnet, counts, ranks, excluded, limit):
    """The candidate families, before carry-forward.

    Returns a list of family dicts sorted for stable diffs. `excluded` is
    every word that may not appear on either side: stylometry markers (the
    function-word families are hand-written territory, and rewriting a
    marker changes what every stored fingerprint measures) and everything
    the shipped thesaurus already owns.
    """
    seeds = [w for w, rank in ranks.items()
             if rank <= thesaurus_io.REACH_MAX_RANK
             and len(w) >= 3
             and thesaurus_io.WORD_RX.fullmatch(w)
             and w not in excluded
             and wordnet.lemma_pos(w)
             and fixes.is_mechanical_substitution(w)]

    # term -> (seed, evidence). One family per term: a term reachable from
    # two seeds goes to the more frequent one, with the loser recorded, so
    # regeneration is deterministic and the reviewer sees the tie.
    claims = {}
    for seed in sorted(seeds):
        seed_count = counts[seed]
        for letter in wordnet.lemma_pos(seed):
            for _offset, lemmas, gloss in wordnet.top_synsets(
                    seed, letter, thesaurus_io.SEED_SENSES_MAX):
                for term in lemmas:
                    if ("_" in term or term == seed
                            or not thesaurus_io.WORD_RX.fullmatch(term)
                            or term in excluded
                            or term in seeds
                            or is_inflection_pair(seed, term)):
                        continue
                    term_count = counts.get(term)
                    ratio = None
                    if term_count:
                        ratio = seed_count / float(term_count)
                        if ratio < thesaurus_io.RATIO_MIN:
                            continue
                    poly = wordnet.polysemy_of(term)
                    cross = len(wordnet.lemma_pos(term)) > 1
                    flags = []
                    if sum(poly.values()) > thesaurus_io.POLYSEMY_MAX:
                        flags.append("polysemy")
                    if cross:
                        flags.append("cross-pos")
                    if term_count is None:
                        flags.append("no-frequency")
                    entry = {
                        "term": term,
                        "rank": ranks.get(term),
                        "ratio": round(ratio, 1) if ratio else None,
                        "gloss": ascii_fold(gloss.split(";")[0].strip()),
                        "polysemy": poly,
                        "cross_pos": cross,
                        "flags": flags,
                        "status": "flagged" if flags else "pending",
                        "note": "",
                    }
                    held = claims.get(term)
                    if held is None:
                        claims[term] = (seed, letter, entry)
                    elif held[0] != seed:
                        # Higher-frequency seed wins, alphabetical tie-break.
                        winner = min((held[0], seed),
                                     key=lambda s: (-counts[s], s))
                        if winner == seed:
                            entry["also_synonym_of"] = sorted(
                                set([held[0]]
                                    + held[2].get("also_synonym_of", [])))
                            claims[term] = (seed, letter, entry)
                        else:
                            held[2].setdefault("also_synonym_of", [])
                            if seed not in held[2]["also_synonym_of"]:
                                held[2]["also_synonym_of"].append(seed)
                                held[2]["also_synonym_of"].sort()

    by_seed = {}
    for term, (seed, letter, entry) in claims.items():
        family = by_seed.setdefault(seed, {"pos": set(), "terms": []})
        family["pos"].add(letter)
        family["terms"].append(entry)

    families = []
    for seed, built in by_seed.items():
        terms = sorted(built["terms"],
                       key=lambda t: (t["rank"] is None, t["rank"], t["term"]))
        families.append({
            "reach": seed,
            "reach_rank": ranks[seed],
            "pos": sorted(built["pos"]),
            "status": "pending",
            "note": "",
            "flags": [],
            "overreach": terms,
            # The strength that decides survival under --limit: the family's
            # best evidence of a real reach gap.
            "_strength": max((t["ratio"] or 0.0) for t in terms),
        })
    families.sort(key=lambda f: (-f["_strength"], f["reach"]))
    families = families[:limit]
    for family in families:
        del family["_strength"]
    families.sort(key=lambda f: (f["reach_rank"], f["reach"]))
    return families


def carry_forward(families, previous):
    """Review survives regeneration.

    `status` and `note` copy over for every family and term still present.
    A family somebody reviewed (anything past `pending`) that no longer
    qualifies is kept whole with a `stale-evidence` flag, because a review
    decision evaporating in a diff nobody reads is how accepted families
    get regenerated into different words.
    """
    if not previous:
        return families
    old_families = {f["reach"]: f for f in previous.get("families", [])}
    emitted = set()
    for family in families:
        old = old_families.get(family["reach"])
        emitted.add(family["reach"])
        if not old:
            continue
        family["status"] = old.get("status", family["status"])
        family["note"] = old.get("note", family["note"])
        old_terms = {t["term"]: t for t in old.get("overreach", [])}
        for term in family["overreach"]:
            held = old_terms.get(term["term"])
            if held:
                term["status"] = held.get("status", term["status"])
                term["note"] = held.get("note", term["note"])
    for reach in sorted(set(old_families) - emitted):
        old = old_families[reach]
        reviewed = old.get("status") != "pending" or any(
            t.get("status") != "pending" for t in old.get("overreach", []))
        if not reviewed:
            continue
        flags = list(old.get("flags", []))
        if "stale-evidence" not in flags:
            flags.append("stale-evidence")
        old["flags"] = flags
        families.append(old)
    families.sort(key=lambda f: (f.get("reach_rank") or 0, f["reach"]))
    return families


def main():
    examples = [
        "python3 scripts/thesaurus-research/02_generate_candidates.py",
        "python3 scripts/thesaurus-research/02_generate_candidates.py --limit 50",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--limit", type=int, default=thesaurus_io.FAMILY_LIMIT,
                    help="cap on emitted families, strongest ratio first "
                         "(default %d, reviewable in one sitting)"
                         % thesaurus_io.FAMILY_LIMIT)
    ap.add_argument("--raw-dir", default=thesaurus_io.RAW_DIR,
                    help=argparse.SUPPRESS)
    ap.add_argument("--out", default=thesaurus_io.CANDIDATES_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--thesaurus", default=thesaurus_io.THESAURUS_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    dict_dir = os.path.join(args.raw_dir, thesaurus_io.DATASETS["wordnet"]
                            .get("extract_dir", "dict"))
    counts_path = os.path.join(args.raw_dir,
                               thesaurus_io.DATASETS["count_1w"]["filename"])
    for needed in (dict_dir, counts_path):
        if not os.path.exists(needed):
            ap.error("missing %s. Run 01_fetch_datasets.py first: the "
                     "datasets are not in git, only their hashes are" % needed)

    counts, ranks = thesaurus_io.load_counts(counts_path)
    wordnet = thesaurus_io.WordNet(dict_dir)
    thesaurus = thesaurus_io.load_json(args.thesaurus)
    excluded = set(stylometry.MARKER_WORDS) | shipped_terms(thesaurus)

    families = generate(wordnet, counts, ranks, excluded, args.limit)
    previous = None
    if os.path.exists(args.out):
        previous = thesaurus_io.load_json(args.out)
    families = carry_forward(families, previous)

    data = {
        "schema_version": thesaurus_io.SCHEMA_VERSION,
        "generated": {
            "thesaurus_version_at_generation": thesaurus["version"],
            "datasets": {key: spec["sha256"]
                         for key, spec in sorted(thesaurus_io.DATASETS.items())},
            "thresholds": dict(thesaurus_io.thresholds(),
                               family_limit=args.limit),
        },
        "families": families,
    }
    problems = thesaurus_io.candidate_problems(data)
    if problems:
        ap.error("refusing to write a file that fails its own schema:\n  "
                 + "\n  ".join(problems))
    thesaurus_io.write_json(args.out, data)

    n_terms = sum(len(f["overreach"]) for f in families)
    flagged = sum(1 for f in families for t in f["overreach"]
                  if t["status"] == "flagged")
    if args.json:
        print(json.dumps({"families": len(families), "terms": n_terms,
                          "flagged": flagged, "out": args.out}, indent=2))
    else:
        print("wrote %d families, %d terms (%d flagged) to %s"
              % (len(families), n_terms, flagged, args.out))
        print("Next: 03_corpus_evidence.py counts every term over the "
              "100-README corpus, then a human reviews `status` fields, "
              "then 04_merge_accepted.py writes the shipped file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
