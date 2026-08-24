#!/usr/bin/env python3
"""
The STE-vocabulary research pipeline, tested over synthetic data.

Everything here builds its own dictionary entries, candidates file, corpus,
and ste_lexicon.json in a temporary directory. Nothing reads the real
ste_dictionary_full.json (2,062 entries) or the real 100-README corpus, the
same bargain test_thesaurus_harness.py makes for its sibling pipeline: a
fixture proves the extraction rule and the calibration logic, not a specific
word's specific ruling.

    python3 test_ste_harness.py

Stdlib only, 3.9+.
"""

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
for path in (HERE, ENGINE):
    if path not in sys.path:
        sys.path.insert(0, path)

import ste_io  # noqa: E402


def load_stage(filename):
    """A numbered stage, loaded by path: '01_extract_candidates' is not a
    legal module name, which is why nothing imports these and this loader
    exists."""
    spec = importlib.util.spec_from_file_location(
        filename.replace(".py", "").replace("0", "stage", 1),
        os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extractor = load_stage("01_extract_candidates.py")
evidence = load_stage("02_corpus_evidence.py")
merger = load_stage("03_merge_accepted.py")

failures = []


def check(name, condition, detail=""):
    if condition:
        print("  pass   %s" % name)
    else:
        print("  FAIL   %s  %s" % (name, detail))
        failures.append(name)


# --------------------------------------------------------------------------
# 01: extraction


def entry(word, pos, meaning, approved=False):
    return {"word": word, "pos": pos, "approved": approved,
           "other_forms": [], "meaning_or_alternatives": meaning}


def test_extract_pulls_the_leading_pos_tagged_alternative():
    e = entry("abandon", "v",
              "GO (v) IF THERE IS A FIRE, If there is a fire, "
              "IMMEDIATELY GO TO immediately abandon A SAFE AREA. the area.")
    result = extractor.extract(e)
    check("extracts GO/v from the interleaved column text",
          result == ("GO", "v"), str(result))


def test_extract_skips_a_bare_phrase_alternative_with_no_pos_tag():
    # "NOT EASY" style entries: no reliable delimiter separates the
    # alternative from the interleaved example text that follows it.
    e = entry("difficult", "adj",
              "NOT EASY IF IT IS NOT EASY TO If the rigging pin is "
              "difficult to install, adjust the length.")
    check("no POS tag means no extraction, not a guess",
          extractor.extract(e) is None)


def test_extract_drops_a_same_word_alternative():
    # "bank (n)" -> "BANK (v)": a real ruling (the noun sense is banned,
    # the verb sense is not), unactionable for a word-boundary regex with
    # no part-of-speech of its own.
    e = entry("bank", "n", "BANK (v) SOME EXAMPLE TEXT bank some example.")
    check("same-spelling alternative is not a candidate",
          extractor.extract(e) is None)


def test_build_candidates_dedupes_repeated_words_and_reports_skips():
    entries = [
        entry("advance", "n", "MOVE (v) TEXT advance text."),
        entry("advance", "v", "GO (v) TEXT advance text."),
        entry("difficult", "adj", "NOT EASY TEXT difficult text."),
        entry("aft", "adj", "AFT (adj) TEXT aft text.", approved=True),
    ]
    candidates, skipped = extractor.build_candidates(entries, {})
    words = {c["word"]: c["alternative"] for c in candidates}
    check("first POS row wins on a repeated word",
          words.get("advance") == "MOVE", str(words))
    check("an approved entry never becomes a candidate",
          "aft" not in words)
    check("the unparseable entry is reported skipped, not silently dropped",
          skipped == ["difficult"], str(skipped))


def test_build_candidates_carries_status_forward_on_a_rerun():
    entries = [entry("abandon", "v", "GO (v) TEXT abandon text.")]
    previous = {"abandon": {"status": "accepted", "flags": ["human-reviewed"]}}
    candidates, _ = extractor.build_candidates(entries, previous)
    check("a prior human decision survives re-extraction",
          candidates[0]["status"] == "accepted"
          and candidates[0]["flags"] == ["human-reviewed"], str(candidates[0]))


# --------------------------------------------------------------------------
# 02: corpus evidence


README_COMMON = "Cross-platform builds abandon the old cache automatically.\n"
README_RARE = "The manual, unrelated to any of this, discusses cats.\n"


def candidate(word, alternative, status="candidate", flags=None):
    return {"word": word, "source_pos": "v", "alternative": alternative,
           "alt_pos": "v", "status": status, "flags": flags or []}


def test_count_all_respects_the_hyphen_aware_boundary():
    texts = [("r1", "This tool is cross-platform and easy to cross a room.")]
    counts = evidence.count_all(["cross"], texts)
    check("cross-platform's cross is not counted",
          counts["cross"]["hits"] == 1, str(counts))


def test_annotate_flags_and_retracts_by_corpus_document_count():
    texts = [("r%d" % i, README_COMMON if i < ste_io.CORPUS_FLAG_DOCS
              else README_RARE) for i in range(10)]
    data = {"candidates": [candidate("abandon", "GO"),
                           candidate("nonexistentword", "X")]}
    demoted = evidence.annotate(data, texts)
    by_word = {c["word"]: c for c in data["candidates"]}
    check("a word in >= CORPUS_FLAG_DOCS readmes is flagged and demoted",
          by_word["abandon"]["status"] == "flagged"
          and "corpus-common" in by_word["abandon"]["flags"], demoted)
    check("a word absent from the corpus stays a candidate",
          by_word["nonexistentword"]["status"] == "candidate")

    # Rerun with a corpus where "abandon" no longer clears the threshold.
    thin_texts = [("r0", README_COMMON)]
    evidence.annotate(data, thin_texts)
    check("evidence retraction lifts the machine's own demotion",
          by_word["abandon"]["status"] == "candidate"
          and by_word["abandon"]["flags"] == [], by_word["abandon"])


def test_annotate_never_touches_a_human_set_status():
    texts = [("r%d" % i, README_COMMON) for i in range(ste_io.CORPUS_FLAG_DOCS)]
    data = {"candidates": [candidate("abandon", "GO", status="rejected")]}
    evidence.annotate(data, texts)
    check("a human's rejected verdict survives corpus-common evidence",
          data["candidates"][0]["status"] == "rejected")


# --------------------------------------------------------------------------
# 03: merge


def test_build_vocabulary_excludes_curated_and_non_mergeable_candidates():
    candidates = [
        candidate("abandon", "GO", status="candidate"),
        candidate("run", "OPERATE", status="candidate"),  # curated elsewhere
        candidate("crossed", "X", status="flagged", flags=["corpus-common"]),
        candidate("badword", "Y", status="rejected"),
        candidate("override", "REPLACE", status="accepted"),
    ]
    curated = {"run"}
    vocab, skipped_curated = merger.build_vocabulary(candidates, curated)
    check("a candidate becomes a vocabulary entry",
          vocab.get("abandon") == "GO")
    check("an accepted candidate is also merged",
          vocab.get("override") == "REPLACE")
    check("a curated word is excluded and reported",
          "run" not in vocab and skipped_curated == ["run"])
    check("a flagged word is excluded",
          "crossed" not in vocab)
    check("a rejected word is excluded",
          "badword" not in vocab)


def test_merge_end_to_end_bumps_version_once_and_is_idempotent():
    base = tempfile.mkdtemp(prefix="rabbit-ste-")
    try:
        candidates_path = os.path.join(base, "candidates.json")
        lexicon_path = os.path.join(base, "ste_lexicon.json")
        with open(candidates_path, "w", encoding="utf-8") as fh:
            json.dump({"candidates": [
                candidate("abandon", "GO", status="candidate")]}, fh)
        with open(lexicon_path, "w", encoding="utf-8") as fh:
            json.dump({"version": 3, "banned_verbs": []}, fh)

        def run():
            return subprocess.run(
                [sys.executable, os.path.join(HERE, "03_merge_accepted.py"),
                 "--candidates", candidates_path, "--lexicon", lexicon_path],
                capture_output=True, text=True)

        first = run()
        with open(lexicon_path, encoding="utf-8") as fh:
            after_first = json.load(fh)
        check("first merge writes the word and bumps version",
              after_first["dictionary_vocabulary"].get("abandon") == "GO"
              and after_first["version"] == 4, first.stdout + first.stderr)

        second = run()
        with open(lexicon_path, encoding="utf-8") as fh:
            after_second = json.load(fh)
        check("a rerun with no candidate change leaves version alone",
              after_second["version"] == 4, second.stdout + second.stderr)
    finally:
        shutil.rmtree(base)


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
