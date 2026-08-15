#!/usr/bin/env python3
"""
The thesaurus research pipeline, tested over synthetic datasets.

Everything here builds its own WordNet database files, frequency counts,
corpus, and thesaurus in a temporary directory. Nothing touches the network:
`01_fetch_datasets.py` is the one stage that would, and the tests that reach
it substitute a stub, the same bargain `test_corpus_harness.py` makes.

The fixture files are ASCII string constants written at run time, never
downloaded, so the suite runs on a checkout with nothing installed and CI
stays offline. The real datasets are exercised exactly once, by the human
session that generates the committed candidates file.

    python3 test_thesaurus_harness.py

Stdlib only, 3.9+.
"""

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
for path in (HERE, ENGINE):
    if path not in sys.path:
        sys.path.insert(0, path)

import thesaurus_io  # noqa: E402
from rwlib import fixes, stylometry  # noqa: E402


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
fetcher = load_stage("01_fetch_datasets.py")

# A stylometry marker word, injected into the fixtures to prove the seed
# filter excludes it. Picked from the list rather than hardcoded, so an edit
# to MARKER_WORDS cannot silently turn this into a non-test.
MARKER = sorted(stylometry.MARKER_WORDS)[0]

# Frequency fixture, count_1w format, descending. The ranks are the line
# numbers and the unit tests pin behavior against them with REACH_MAX_RANK
# patched to 7: seeds are ranks 2-7, everything below is reachable only as
# an overreach term.
COUNTS = "\n".join([
    "%s\t1000000000" % MARKER,   # rank 1: marker, never a seed
    "start\t6000000",            # rank 2: seed
    "keep\t5000000",             # rank 3: seed
    "help\t4000000",             # rank 4: seed
    "want\t3600000",             # rank 5: seed
    "begin\t3500000",            # rank 6: seed, loses commence to start
    "big\t2500000",              # rank 7: seed (adjective, satellite synset)
    "desire\t1000000",           # rank 8: overreach of want, flagged
    "large\t900000",             # rank 9: ratio big/large 2.8, excluded
    "retain\t800000",            # rank 10: overreach of keep, clean
    "keeps\t700000",             # rank 11: inflection of keep, excluded
    "prolong\t60000",            # rank 12: keep's 4th sense, past the cap
    "commence\t50000",           # rank 13: start and begin both reach it
    "facilitate\t40000",         # rank 14: overreach of help
    "vast\t30000",               # rank 15: overreach of big via satellite
    "obtain\t20000",             # rank 16: already shipped, excluded
]) + "\n"

# WordNet database fixtures. index.<pos>: lemma pos synset_cnt p_cnt ptrs
# sense_cnt tagsense_cnt offsets (sense order). data.<pos>: offset lexfile
# ss_type w_cnt(hex) lemma lexid pairs ptr_cnt ... | gloss.
INDEX_VERB = "\n".join([
    "  1 license header line, skipped",
    "start v 1 1 @ 1 1 00000001",
    "keep v 4 1 @ 4 4 00000002 00000003 00000004 00000005",
    "help v 1 1 @ 1 1 00000006",
    "want v 1 1 @ 1 1 00000007",
    "begin v 1 1 @ 1 1 00000008",
    "desire v 3 1 @ 3 3 00000009 00000010 00000011",
    "retain v 2 1 @ 2 2 00000002 00000012",
]) + "\n"

DATA_VERB = "\n".join([
    "  1 license header line, skipped",
    "00000001 29 v 02 start 0 commence 0 000 | take the first step",
    "00000002 29 v 04 keep 0 retain 0 obtain 0 hold_on 0 000 | keep in"
    " one's possession",
    "00000003 29 v 02 keep 0 conserve 0 000 | keep from harm or loss",
    "00000004 29 v 01 keep 0 000 | third sense filler",
    "00000005 29 v 02 keep 0 prolong 0 000 | lengthen in time, past the cap",
    "00000006 29 v 02 help 0 facilitate 0 000 | make easier",
    "00000007 29 v 02 want 0 desire 0 000 | feel a need for",
    "00000008 29 v 02 begin 0 commence 0 000 | set in motion",
]) + "\n"

INDEX_NOUN = "\n".join([
    "%s n 1 1 @ 1 1 00000020" % MARKER,
    "desire n 8 1 @ 8 8 00000021 00000022 00000023 00000024 00000025"
    " 00000026 00000027 00000028",
]) + "\n"

INDEX_ADJ = "big a 1 1 @ 1 1 00003000\n"
# ss_type `s` (satellite) in the adj file: the parser folds it into `a` by
# keying on the file, which is what this line proves.
DATA_ADJ = ("00003000 00 s 02 big 0 vast 0 000 | above average in size\n")

README_WITH = "# Tool\n\nThis will facilitate the setup and facilitates use.\n"
README_WITHOUT = "# Tool\n\nA plain readme about nothing in particular.\n"

failures = []


def check(name, condition, detail=""):
    if condition:
        print("  pass   %s" % name)
    else:
        print("  FAIL   %s  %s" % (name, detail))
        failures.append(name)


def write_fixtures(base):
    """The raw-dir layout 01 would have produced, from the constants above."""
    dict_dir = os.path.join(base, "dict")
    os.makedirs(dict_dir, exist_ok=True)
    files = {"index.verb": INDEX_VERB, "data.verb": DATA_VERB,
             "index.noun": INDEX_NOUN, "data.noun": "",
             "index.adj": INDEX_ADJ, "data.adj": DATA_ADJ,
             "index.adv": "", "data.adv": ""}
    for name, content in files.items():
        with open(os.path.join(dict_dir, name), "w", encoding="ascii") as fh:
            fh.write(content)
    with open(os.path.join(base, "count_1w.txt"), "w", encoding="ascii") as fh:
        fh.write(COUNTS)
    return base


def shipped(base):
    """A temp thesaurus owning get/obtain, so the exclusion is testable."""
    path = os.path.join(base, "thesaurus.json")
    thesaurus_io.write_json(path, {
        "version": 1,
        "families": [{"reach": "get", "overreach": ["obtain", "procure"]}],
    })
    return path


def generated(base, limit=150):
    """Run the generator's functions directly over the fixtures, with the
    rank ceiling patched down to the fixture's scale."""
    counts, ranks = thesaurus_io.load_counts(
        os.path.join(base, "count_1w.txt"))
    wordnet = thesaurus_io.WordNet(os.path.join(base, "dict"))
    excluded = (set(stylometry.MARKER_WORDS)
                | gen.shipped_terms(thesaurus_io.load_json(shipped(base))))
    held = thesaurus_io.REACH_MAX_RANK
    thesaurus_io.REACH_MAX_RANK = 7
    try:
        return gen.generate(wordnet, counts, ranks, excluded, limit)
    finally:
        thesaurus_io.REACH_MAX_RANK = held


def family_of(families, reach):
    for family in families:
        if family["reach"] == reach:
            return family
    return None


def terms_of(family):
    return {t["term"]: t for t in family["overreach"]} if family else {}


# --------------------------------------------------------------------------
# Parsers


def test_wordnet_parser():
    base = write_fixtures(tempfile.mkdtemp(prefix="rabbit-thesaurus-"))
    try:
        wn = thesaurus_io.WordNet(os.path.join(base, "dict"))
        check("sense order survives parsing",
              wn.senses[("v", "keep")] == ["00000002", "00000003",
                                           "00000004", "00000005"])
        check("polysemy is per pos and zero-filled",
              wn.polysemy_of("desire") == {"a": 0, "n": 8, "r": 0, "v": 3},
              str(wn.polysemy_of("desire")))
        check("cross-pos lemma reports both letters",
              wn.lemma_pos("desire") == ["n", "v"])
        check("satellite synsets fold into the adjective pos",
              any("vast" in lemmas for _o, lemmas, _g
                  in wn.top_synsets("big", "a", 3)))
        lemmas = wn.top_synsets("keep", "v", 1)[0][1]
        check("multi-word lemmas keep their underscore for the caller",
              "hold_on" in lemmas, str(lemmas))
        check("license header lines are skipped",
              ("v", "1") not in wn.senses)
        counts, ranks = thesaurus_io.load_counts(
            os.path.join(base, "count_1w.txt"))
        check("counts and ranks read off the line order",
              counts["keep"] == 5000000 and ranks["keep"] == 3)
    finally:
        shutil.rmtree(base)


# --------------------------------------------------------------------------
# Generation


def test_direction_and_ratio_boundary():
    base = write_fixtures(tempfile.mkdtemp(prefix="rabbit-thesaurus-"))
    try:
        families = generated(base)
        keep = terms_of(family_of(families, "keep"))
        check("reach is the frequent word, overreach the rare one",
              "retain" in keep and family_of(families, "retain") is None)
        check("a clean term arrives pending, with its evidence",
              keep["retain"]["status"] == "pending"
              and keep["retain"]["ratio"] == 6.2
              and keep["retain"]["rank"] == 10, str(keep.get("retain")))
        big = terms_of(family_of(families, "big"))
        check("a ratio under RATIO_MIN is excluded, not flagged",
              "large" not in big, str(sorted(big)))
        check("a term with no frequency passes with the note",
              keep["conserve"]["ratio"] is None
              and "no-frequency" in keep["conserve"]["flags"]
              and keep["conserve"]["status"] == "flagged",
              str(keep.get("conserve")))
    finally:
        shutil.rmtree(base)


def test_sense_cap_and_seed_filters():
    base = write_fixtures(tempfile.mkdtemp(prefix="rabbit-thesaurus-"))
    try:
        families = generated(base)
        keep = terms_of(family_of(families, "keep"))
        check("a synonym only in the seed's 4th sense is not emitted",
              "prolong" not in keep, str(sorted(keep)))
        check("an inflection of its own reach is not a candidate",
              "keeps" not in keep)
        check("a multi-word lemma is not a candidate",
              "hold_on" not in keep)
        check("shipped terms are excluded on both sides",
              "obtain" not in keep
              and family_of(families, "get") is None)
        check("a stylometry marker word is never a seed",
              family_of(families, MARKER) is None)
        check("every emitted reach passes the fixer's substitution bar",
              all(fixes.is_mechanical_substitution(f["reach"])
                  for f in families))
    finally:
        shutil.rmtree(base)


def test_flags_and_collision():
    base = write_fixtures(tempfile.mkdtemp(prefix="rabbit-thesaurus-"))
    try:
        families = generated(base)
        want = terms_of(family_of(families, "want"))
        check("a polysemous cross-pos term arrives flagged, never dropped",
              "desire" in want
              and want["desire"]["status"] == "flagged"
              and "polysemy" in want["desire"]["flags"]
              and "cross-pos" in want["desire"]["flags"],
              str(want.get("desire")))
        start = terms_of(family_of(families, "start"))
        begin = family_of(families, "begin")
        check("a collision lands in the higher-frequency family",
              "commence" in start and begin is None,
              str(sorted(start)))
        check("the losing seed is recorded for the reviewer",
              start["commence"].get("also_synonym_of") == ["begin"],
              str(start.get("commence")))
        check("generation is deterministic",
              families == generated(base))
    finally:
        shutil.rmtree(base)


def test_carry_forward_preserves_review():
    base = write_fixtures(tempfile.mkdtemp(prefix="rabbit-thesaurus-"))
    try:
        first = generated(base)
        previous = {"families": json.loads(json.dumps(first))}
        keep = family_of(previous["families"], "keep")
        keep["status"] = "accepted"
        terms_of(keep)["retain"].update(status="accepted",
                                        note="use it, it is him")
        vanished = {"reach": "shrink", "reach_rank": 99, "pos": ["v"],
                    "status": "accepted", "note": "", "flags": [],
                    "overreach": [{"term": "diminish", "rank": None,
                                   "ratio": None, "gloss": "", "polysemy": {},
                                   "cross_pos": False, "flags": [],
                                   "status": "accepted", "note": ""}]}
        unreviewed = dict(vanished, reach="drift", status="pending",
                          overreach=[dict(vanished["overreach"][0],
                                          status="pending")])
        previous["families"] += [vanished, unreviewed]

        second = gen.carry_forward(generated(base), previous)
        keep2 = family_of(second, "keep")
        check("family and term review survive regeneration",
              keep2["status"] == "accepted"
              and terms_of(keep2)["retain"]["note"] == "use it, it is him")
        stale = family_of(second, "shrink")
        check("a reviewed family that vanished is kept as stale evidence",
              stale is not None and "stale-evidence" in stale["flags"],
              str(stale))
        check("an unreviewed vanished family just drops",
              family_of(second, "drift") is None)
    finally:
        shutil.rmtree(base)


def test_schema_validator_rejects():
    good = {"schema_version": 1,
            "generated": {"thresholds": thesaurus_io.thresholds()},
            "families": [{"reach": "keep", "reach_rank": 3, "pos": ["v"],
                          "status": "pending", "note": "", "flags": [],
                          "overreach": [{"term": "retain", "rank": 10,
                                         "ratio": 6.2, "gloss": "",
                                         "polysemy": {}, "cross_pos": False,
                                         "flags": [], "status": "pending",
                                         "note": ""}]}]}
    check("a valid object has no problems",
          thesaurus_io.candidate_problems(good) == [],
          str(thesaurus_io.candidate_problems(good)))
    bad_status = json.loads(json.dumps(good))
    bad_status["families"][0]["overreach"][0]["status"] = "maybe"
    check("a status outside the vocabulary is rejected",
          any("maybe" in p for p in
              thesaurus_io.candidate_problems(bad_status)))
    bare = json.loads(json.dumps(good))
    del bare["families"][0]["overreach"][0]["polysemy"]
    check("a term missing its evidence is rejected",
          any("polysemy" in p for p in thesaurus_io.candidate_problems(bare)))


# --------------------------------------------------------------------------
# Fetch guards (network stubbed)


def test_fetch_guards():
    check("a non-http scheme is refused before urllib sees it",
          fetcher.fetch("ftp://example.dev/x")[1] is not None)
    raw_dir = tempfile.mkdtemp(prefix="rabbit-thesaurus-")
    held_fetch, held_raw = fetcher.fetch, thesaurus_io.RAW_DIR
    fetcher.fetch = lambda url: (b"not the dataset", None)
    thesaurus_io.RAW_DIR = raw_dir
    try:
        row = fetcher.process("count_1w", dry_run=False)
        check("a hash mismatch is reported and writes nothing",
              row["action"] == "mismatch"
              and not os.listdir(raw_dir), str(row))
    finally:
        fetcher.fetch, thesaurus_io.RAW_DIR = held_fetch, held_raw
        shutil.rmtree(raw_dir)


def test_tar_traversal_is_refused():
    base = tempfile.mkdtemp(prefix="rabbit-thesaurus-")
    try:
        evil = os.path.join(base, "evil.tar.gz")
        with tarfile.open(evil, "w:gz") as archive:
            payload = io.BytesIO(b"owned")
            info = tarfile.TarInfo("../escaped.txt")
            info.size = len(b"owned")
            archive.addfile(info, payload)
        destination = os.path.join(base, "raw")
        os.makedirs(destination)
        try:
            fetcher.unpack(evil, destination)
            escaped = True
        except ValueError:
            escaped = False
        check("a member that escapes the raw directory refuses the archive",
              not escaped and not os.path.exists(
                  os.path.join(base, "escaped.txt")))
    finally:
        shutil.rmtree(base)


# --------------------------------------------------------------------------
# Corpus evidence


def test_corpus_evidence_boundary():
    stage = load_stage("03_corpus_evidence.py")
    base = tempfile.mkdtemp(prefix="rabbit-thesaurus-")
    try:
        corpus = os.path.join(base, "repos")
        for i in range(6):
            repo = os.path.join(corpus, "repo-%d" % i)
            os.makedirs(repo)
            with open(os.path.join(repo, "README.md"), "w",
                      encoding="utf-8") as fh:
                # `facilitate` in 5 of 6 READMEs, `retain` in 4.
                fh.write(README_WITH if i < 5 else README_WITHOUT)
                if i < 4:
                    fh.write("\nRetained settings are retained.\n")
        texts = stage.corpus_texts(corpus)
        term_rx = stage.load_measure_voice().term_rx
        check("counting agrees with the shipped counter on inflections",
              stage.counts_for("retain", texts, term_rx)["readmes"] == 4)
        data = {"families": [
            {"reach": "help", "reach_rank": 4, "pos": ["v"],
             "status": "pending", "note": "", "flags": [], "overreach": [
                 {"term": "facilitate", "rank": 14, "ratio": 100.0,
                  "gloss": "", "polysemy": {}, "cross_pos": False,
                  "flags": [], "status": "pending", "note": ""}]},
            {"reach": "keep", "reach_rank": 3, "pos": ["v"],
             "status": "pending", "note": "", "flags": [], "overreach": [
                 {"term": "retain", "rank": 10, "ratio": 6.2, "gloss": "",
                  "polysemy": {}, "cross_pos": False, "flags": [],
                  "status": "pending", "note": ""}]}]}
        stage.annotate(data, texts, term_rx)
        facilitate = terms_of(family_of(data["families"], "help"))["facilitate"]
        retain = terms_of(family_of(data["families"], "keep"))["retain"]
        check("a term in CORPUS_FLAG_DOCS readmes is flagged and demoted",
              "technical-vocabulary" in facilitate["flags"]
              and facilitate["status"] == "flagged", str(facilitate))
        check("one readme under the line stays pending",
              retain["flags"] == [] and retain["status"] == "pending",
              str(retain))
        stage.annotate(data, texts, term_rx)
        check("annotation is idempotent",
              facilitate["flags"].count("technical-vocabulary") == 1)
    finally:
        shutil.rmtree(base)


# --------------------------------------------------------------------------
# Merge, end to end


def run_stage(filename, *args):
    result = subprocess.run(
        [sys.executable, os.path.join(HERE, filename), *args],
        capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


def test_merge_end_to_end():
    base = write_fixtures(tempfile.mkdtemp(prefix="rabbit-thesaurus-"))
    try:
        thesaurus_path = shipped(base)
        candidates_path = os.path.join(base, "candidates.json")
        corpus = os.path.join(base, "repos")
        os.makedirs(os.path.join(corpus, "repo-0"))
        with open(os.path.join(corpus, "repo-0", "README.md"), "w",
                  encoding="utf-8") as fh:
            fh.write(README_WITHOUT)

        out, err, code = run_stage(
            "02_generate_candidates.py", "--raw-dir", base,
            "--out", candidates_path, "--thesaurus", thesaurus_path)
        check("02 writes a schema-valid candidates file",
              code == 0 and os.path.exists(candidates_path), err)
        out, err, code = run_stage(
            "03_corpus_evidence.py", "--candidates", candidates_path,
            "--corpus-dir", corpus)
        check("03 annotates in place", code == 0, err)

        data = thesaurus_io.load_json(candidates_path)
        check("the full run passes its own schema",
              thesaurus_io.candidate_problems(data) == [])
        start = family_of(data["families"], "start")
        check("corpus blocks landed on every term",
              all("corpus" in t for f in data["families"]
                  for t in f["overreach"]))

        out, err, code = run_stage(
            "04_merge_accepted.py", "--candidates", candidates_path,
            "--thesaurus", thesaurus_path)
        before = open(thesaurus_path, encoding="utf-8").read()
        check("zero accepted families is an error, not a no-op write",
              code != 0 and "get" in json.loads(before)["families"][0]["reach"],
              err)

        start["status"] = "accepted"
        terms_of(start)["commence"]["status"] = "accepted"
        thesaurus_io.write_json(candidates_path, data)
        out, err, code = run_stage(
            "04_merge_accepted.py", "--candidates", candidates_path,
            "--thesaurus", thesaurus_path)
        merged = thesaurus_io.load_json(thesaurus_path)
        check("an accepted family merges and bumps the version",
              code == 0 and merged["version"] == 2
              and family_of(merged["families"], "start")["overreach"]
              == ["commence"], err or str(merged))
        check("hand-written families keep their place",
              merged["families"][0]["reach"] == "get")

        first_bytes = open(thesaurus_path, encoding="utf-8").read()
        out, err, code = run_stage(
            "04_merge_accepted.py", "--candidates", candidates_path,
            "--thesaurus", thesaurus_path)
        check("a re-merge with nothing new is a byte-identical no-op",
              code == 0
              and open(thesaurus_path, encoding="utf-8").read() == first_bytes
              and thesaurus_io.load_json(thesaurus_path)["version"] == 2, err)

        import thesaurus_check
        check("the merged file passes the shared shape check",
              thesaurus_check.problems(merged) == [])
        fixed, applied, _skipped = fixes.apply(
            "We commence the rollout today.",
            {"preferred_substitutions": {
                t: f["reach"] for f in merged["families"]
                for t in f["overreach"]}})
        check("merged families round-trip through the fixer",
              fixed == "We start the rollout today." and applied, fixed)
    finally:
        shutil.rmtree(base)


def test_merge_refusals():
    base = write_fixtures(tempfile.mkdtemp(prefix="rabbit-thesaurus-"))
    try:
        thesaurus_path = shipped(base)
        candidates_path = os.path.join(base, "candidates.json")
        term = {"term": "procure", "rank": None, "ratio": None, "gloss": "",
                "polysemy": {}, "cross_pos": False, "flags": [],
                "status": "accepted", "note": ""}
        data = {"schema_version": 1,
                "generated": {"thresholds": thesaurus_io.thresholds()},
                "families": [{"reach": "land", "reach_rank": 20,
                              "pos": ["v"], "status": "accepted", "note": "",
                              "flags": [], "overreach": [term]}]}
        thesaurus_io.write_json(candidates_path, data)
        before = open(thesaurus_path, encoding="utf-8").read()

        out, err, code = run_stage(
            "04_merge_accepted.py", "--candidates", candidates_path,
            "--thesaurus", thesaurus_path)
        check("uncalibrated candidates are refused without the flag",
              code != 0 and "corpus" in err, err[:200])

        # `procure` is already the shipped get-family's overreach term, so
        # the merged object fails the shared check and nothing is written.
        out, err, code = run_stage(
            "04_merge_accepted.py", "--candidates", candidates_path,
            "--thesaurus", thesaurus_path, "--allow-uncalibrated")
        check("a collision with a shipped family refuses the merge whole",
              code != 0
              and open(thesaurus_path, encoding="utf-8").read() == before,
              err[:200])

        out, err, code = run_stage(
            "04_merge_accepted.py", "--candidates", candidates_path,
            "--thesaurus", thesaurus_path, "--allow-uncalibrated",
            "--dry-run")
        check("dry run writes nothing",
              open(thesaurus_path, encoding="utf-8").read() == before)
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
