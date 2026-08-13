#!/usr/bin/env python3
"""
The reconstruction harness, over stubbed triples.

The corpus is empty and will be for as long as it takes somebody to gather real
writing with real consent. A scorer nobody has ever run is a scorer that does
not work, so this runs it: synthetic triples with known answers, written so the
arithmetic is checkable by hand.

The assertions that matter are about the metric's shape rather than its
precision. A round trip that landed has to score near 1, one that moved nothing
has to score near 0, and one that went backwards has to come out negative, which
is the reading no per-finding report can give and the whole reason this exists.

Run it directly, or through pytest. Zero-argument test functions, the same
contract the two skill suites hold, so this file behaves identically in both.

Stdlib only, 3.9+.
"""

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import reconstruct                                               # noqa: E402

# Voice A: short sentences, contractions, "so" and "also" and "but". The target.
ORIGINAL = """So the deploy broke again and I don't think it's the pipeline.
It's the cache config. We've been ignoring that file for a year. I'll fix it
tomorrow. The rollback worked, so nobody outside the team noticed. But we got
lucky, and I don't want to rely on that again.

The fix isn't hard. It's boring, and boring work waits until somebody owns it.
So I'm owning it. If it slips past Friday that's on me and I'll say so in
standup. We're also adding a check so this can't happen quietly again, because
the worst part wasn't the break. It was that we didn't know for an hour.

The alerting config hasn't been touched since we migrated either. Half the
thresholds are for hardware we don't run anymore. That's a separate ticket, but
it's the same disease: config nobody owns rots quietly until it bites. I'm not
going to fix all of it this week and I don't think anyone should try.
"""

# The same content in nobody's voice: long sentences, no contractions, formal
# connectors. What a deslop with no profile produces.
NEUTRALIZED = """The deployment failed once more, and the root cause does not
appear to be the pipeline itself but rather the cache configuration, which has
not received attention for approximately one year. Remediation is scheduled for
tomorrow. The rollback procedure executed successfully, and consequently no
external stakeholders observed the incident, although this outcome should be
attributed to fortune rather than to process.

The remediation is not technically complex, however it is unengaging, and
unengaging work tends to remain unaddressed until an individual assumes
ownership of it. Ownership has therefore been assumed. Should the work extend
beyond Friday, responsibility rests with the author and will be communicated
during the standup meeting. Additionally, a verification check will be
introduced so that recurrence cannot occur without detection, since the most
significant aspect of the incident was not the failure itself but the hour
during which it went unobserved.

The alerting configuration has similarly not been revised since the migration
was completed, and approximately half of the configured thresholds correspond
to hardware which is no longer operational. That constitutes a separate work
item, however it reflects the same underlying condition: configuration without
an owner deteriorates without notice until it produces an incident. Complete
remediation is not planned for the current week, and it is not recommended that
any individual attempt it.
"""


def _stub_corpus(triples, texts):
    """A manifest directory and a texts directory, populated and hashed."""
    directory = tempfile.mkdtemp(prefix="rabbit-eval-")
    texts_dir = os.path.join(directory, "texts")
    os.makedirs(texts_dir)
    for name, body in texts.items():
        with open(os.path.join(texts_dir, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    for triple in triples:
        triple.setdefault("sha256", {
            role: reconstruct.sha256(texts[triple[role]])
            for role in reconstruct.ROLES if triple.get(role) in texts})
    manifest = os.path.join(directory, "manifest.json")
    with open(manifest, "w", encoding="utf-8") as fh:
        json.dump({"version": reconstruct.SCHEMA_VERSION, "triples": triples}, fh)
    return directory, manifest, texts_dir


def _triple(reconstructed_body, tid="t1"):
    texts = {"o.md": ORIGINAL, "n.md": NEUTRALIZED, "r.md": reconstructed_body}
    return _stub_corpus([{"id": tid, "original": "o.md", "neutralized": "n.md",
                          "reconstructed": "r.md"}], texts)


def _score(reconstructed_body):
    directory, manifest, texts_dir = _triple(reconstructed_body)
    try:
        rows = reconstruct.score_all(reconstruct.load_manifest(manifest),
                                     texts_dir)
        assert len(rows) == 1 and "error" not in rows[0], rows
        return rows[0]["score"]
    finally:
        shutil.rmtree(directory, ignore_errors=True)


# --------------------------------------------------------------------------
# the metric
# --------------------------------------------------------------------------

def test_a_round_trip_that_landed_scores_near_one():
    """The reconstruction is the original, which is the best a conversion can
    do. Anything but roughly 1 here means the arithmetic is wrong, not the
    pipeline."""
    score = _score(ORIGINAL)
    assert score["delta_recovered"] > 0.9, score["delta_recovered"]


def test_a_conversion_that_moved_nothing_scores_near_zero():
    """The reconstruction is the neutralized text. This is the shallow
    conversion, and the number has to say so plainly."""
    score = _score(NEUTRALIZED)
    assert abs(score["delta_recovered"]) < 0.1, score["delta_recovered"]


def test_a_conversion_that_went_backwards_scores_negative():
    """The reading no per-finding report can give: every rule passed and the
    writing moved further from its author. A metric that floored at zero would
    hide the case worth knowing about."""
    worse = NEUTRALIZED.replace("however", "however, furthermore,")
    worse = worse + "\n\n" + NEUTRALIZED
    score = _score(worse)
    assert score["delta_recovered"] < 0.0, score["delta_recovered"]


def test_the_six_measures_are_scored_apart_from_the_distance():
    """They fail separately. A pass that restores the marker rates and leaves
    every sentence the same length has not brought the writing back, and one
    number covering both would average that away."""
    score = _score(ORIGINAL)
    assert score["measures"], score
    assert score["measures_recovered"] is not None, score


def test_no_gap_to_close_is_none_rather_than_a_perfect_score():
    """When the neutralized text already sits on the target there was nothing to
    recover, and calling that 1.0 lets a weak deslop flatter the conversion that
    follows it."""
    assert reconstruct._recovered(5.0, 5.0, 5.0) is None
    assert reconstruct._recovered(5.0, 9.0, 5.0) == 1.0


# --------------------------------------------------------------------------
# the corpus contract
# --------------------------------------------------------------------------

def test_an_empty_corpus_reports_that_it_is_empty():
    """A rate of 0.0 over nothing is the failure this printing exists to avoid,
    and it is the same contract scripts/detector-corpus/score.py holds."""
    directory, manifest, texts_dir = _stub_corpus([], {})
    try:
        rows = reconstruct.score_all(reconstruct.load_manifest(manifest),
                                     texts_dir)
        assert rows == [], rows
        assert "no triples" in reconstruct.report(rows)
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_the_committed_manifest_is_empty_and_parses():
    """It ships empty on purpose. If it ever stops parsing, every published
    number in PROOF.md that points at it is unverifiable."""
    data = reconstruct.load_manifest()
    assert data["triples"] == [], data["triples"]


def test_a_moved_text_is_caught_by_its_hash():
    """The corpus is hash-only in git, so this is the whole guarantee that the
    texts on a machine are the texts a published number came from."""
    directory, manifest, texts_dir = _triple(ORIGINAL)
    try:
        data = reconstruct.load_manifest(manifest)
        assert reconstruct.verify(data, texts_dir) == []
        with open(os.path.join(texts_dir, "r.md"), "a", encoding="utf-8") as fh:
            fh.write("\nOne more sentence, added after the fact.\n")
        moved = reconstruct.verify(data, texts_dir)
        assert moved and moved[0][1] == "reconstructed", moved
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_a_missing_text_is_an_error_on_its_own_row():
    """One unreadable triple must not take the run down with it: the other rows
    are still measurements somebody wants."""
    directory, manifest, texts_dir = _triple(ORIGINAL)
    try:
        os.unlink(os.path.join(texts_dir, "n.md"))
        rows = reconstruct.score_all(reconstruct.load_manifest(manifest),
                                     texts_dir)
        assert "error" in rows[0], rows
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_a_manifest_from_another_schema_is_refused():
    directory, manifest, _ = _stub_corpus([], {})
    try:
        with open(manifest, "w", encoding="utf-8") as fh:
            json.dump({"version": 999, "triples": []}, fh)
        try:
            reconstruct.load_manifest(manifest)
        except reconstruct.CorpusError:
            return
        raise AssertionError("a manifest from another schema was read anyway")
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def _run():
    """The stdlib runner, matching the two skill suites' contract."""
    tests = sorted(name for name in globals() if name.startswith("test_"))
    failed = []
    for name in tests:
        fn = globals()[name]
        if fn.__code__.co_argcount:
            print("  SKIP   %s takes arguments, so only pytest can run it" % name)
            failed.append(name)
            continue
        try:
            fn()
        except AssertionError as exc:
            print("  FAIL   %s\n         %s" % (name, exc))
            failed.append(name)
        else:
            print("  pass   %s" % name)
    print("\n%d passed, %d failed" % (len(tests) - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run())
