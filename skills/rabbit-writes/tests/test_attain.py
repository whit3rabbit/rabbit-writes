#!/usr/bin/env python3
"""
attain.py: did the conversion land?

The claim worth testing is the one nothing else in this suite can make.
`verify.py` proves a rewrite broke nothing and cannot tell a real conversion
from eleven punctuation fixes, because both pass every rule it has. That
failure has a name here, `flat`, and most of this file is about it firing when
it should and staying quiet when it should not.

The other half is restraint, and it is the same argument the voice band makes
everywhere else. The default exit is 0 for every verdict. `--check` fails on
exactly two of them, and never on `missed`, because a document that cannot
reach the profile without inventing content is guardrail 1 working rather than
a defect.

Synthetic voices, so the test owns its ground truth. Voice A is short,
contraction-heavy and uneven. Voice B is the long, formal, contraction-free
register a conversion has to move away from. Three A samples build the
fingerprint and a fourth is held out, which is what makes "landed" assertable
without asking a model to write anything.

Stdlib only, 3.9+.
"""

import json
import os
import shutil
import sys
import tempfile

from helpers import ATTAIN, SCRIPTS, load_module, run_attain, written

sys.path.insert(0, SCRIPTS)
from rwlib import stylometry                                       # noqa: E402

# Paragraphs rather than whole documents, so a sample can be built from a
# different mix of them and the three are not three copies of one text. A
# fingerprint over identical samples has a self-distance band of zero, and every
# later measurement then reads as out of range.
A_PARAS = [
    """So the deploy broke again. I don't think it's the pipeline this time.
    It's the cache config, and honestly we've been ignoring that file for a
    year. I'll fix it tomorrow. The rollback worked, so nobody outside the team
    noticed, which is the outcome you want and never get to write about. But we
    got lucky. I don't want to rely on that again, and the fix isn't hard, it's
    just boring.""",
    """The garden flooded again. It isn't the rain, really. It's the clay layer
    about a foot down, and you can't fix that with mulch. So the plan is a
    french drain along the back fence. I don't love digging. It's one weekend
    and then it's done, and the neighbor did theirs last year and it's held up,
    so there's a working example ten feet away.""",
    """We switched the kids to the earlier bus and it's been fine, mostly. They
    don't love the alarm. They're asleep by nine now, so it evens out. The
    mornings are calmer too, and I didn't expect that. It isn't the extra time.
    It's that nobody's rushing, and rushing was what made everyone snap at each
    other.""",
    """I'm behind on the book club pick. It's good, but it's slow. So I'm doing
    chapters on the train instead, which is working better than I expected
    because the train has no wifi and I can't wander off to my phone. Also I've
    stopped feeling guilty about skimming. They're not why I'm reading it.""",
    """The spreadsheet finally balances and I'm not touching it again this
    month. It wasn't the math. We'd been counting the insurance twice, once
    annually and once monthly, so of course the total looked wrong. I found it
    by printing the thing out, which feels ancient, but you see differently on
    paper.""",
    """The alerting config hasn't been touched since we migrated. Half the
    thresholds are for hardware we don't run anymore. That's a separate ticket,
    but it's the same disease: config nobody owns rots quietly until it bites.
    I'm not going to fix all of it this week, and I don't think anyone should
    try.""",
]

B_PARAS = [
    """The committee has reviewed the proposed amendments to the procurement
    framework, and several provisions remain inconsistent with the established
    guidelines. Furthermore, the documentation submitted by the vendor does not
    adequately address the concerns raised during the previous review cycle, and
    the projected costs exceed the allocated budget by a considerable margin
    which the submission does not attempt to justify.""",
    """Additionally, the timeline presented in the submission is contingent upon
    approvals which have not been obtained, and the risk assessment furnished
    with the application is insufficiently detailed for the purposes of the
    evaluation. Therefore, the committee recommends that the proposal be
    returned for revision, and that the revised submission address each
    deficiency enumerated in the appendix.""",
    """Moreover, the committee notes that the references provided by the vendor
    were not independently verified, and that two of the three references pertain
    to engagements which concluded more than five years prior to the current
    submission. The evaluation criteria require references from engagements of
    comparable scope completed within the preceding three years.""",
    """The committee additionally records that no provision has been made for
    the transition period, during which the incumbent supplier will retain
    operational responsibility for the affected services. Arrangements for that
    period should be set out in the revised submission, together with the
    associated cost, which is not presently disclosed anywhere in the material
    submitted.""",
]


def _doc(paras, order):
    return "\n\n".join(paras[i % len(paras)] for i in order) + "\n"


A_SAMPLES = [_doc(A_PARAS, r) for r in
             ((0, 1, 2, 3, 4), (1, 3, 5, 0, 2), (2, 4, 0, 5, 1))]
A_HELD_OUT = _doc(A_PARAS, (5, 2, 4, 1, 3, 0))
B_DOC = _doc(B_PARAS, (0, 1, 2, 3, 0, 1))


def build_fixture(voice="tester", with_fingerprint=True):
    """A scratch profile directory: rules, and a v2 fingerprint beside it.

    The measures come from scan.py, the way measure_voice.py builds them, which
    is the whole reason `stylometry.fingerprint` takes them as arguments rather
    than measuring them: this module would otherwise have to import scan.py into
    a library that deliberately does not.
    """
    from helpers import scan_module
    scan = scan_module()
    directory = tempfile.mkdtemp(prefix="rabbit-attain-")
    written(directory, voice + ".rules.json", json.dumps({"voice": voice}))
    if with_fingerprint:
        proses = [scan.strip_for_stats(s) for s in A_SAMPLES]
        fp = stylometry.fingerprint(
            proses, voice=voice,
            sample_measures=[scan.compute_stats(s) for s in A_SAMPLES],
            sentence_lengths=[[len(scan.tokenize(x))
                               for x in scan.split_sentences(p)]
                              for p in proses])
        stylometry.save(fp, os.path.join(directory,
                                         voice + stylometry.FINGERPRINT_SUFFIX))
    return directory


def rules_of(directory, voice="tester"):
    return os.path.join(directory, voice + ".rules.json")


# --------------------------------------------------------------------------
# the verdict the script exists for
# --------------------------------------------------------------------------

def test_a_punctuation_only_edit_reads_as_flat():
    """The failure SKILL.md names three times in prose and nothing measured:
    eleven mechanical hits cleared, the register untouched. Every rule passes,
    so no rule-by-rule report can see it."""
    d = build_fixture()
    try:
        before = written(d, "before.md", B_DOC)
        # A word swap and nothing else, which is exactly the shallow conversion.
        after = written(d, "after.md", B_DOC.replace("Furthermore,", "Also,")
                        .replace("Additionally,", "Also,")
                        .replace("Moreover,", "Also,"))
        result, code = run_attain(before, after, "--voice-rules", rules_of(d))
        assert result["verdict"] == "flat", result["verdict"]
        assert code == 0, "no --check, so no failure"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_check_fails_on_flat_and_the_default_does_not():
    d = build_fixture()
    try:
        before = written(d, "before.md", B_DOC)
        after = written(d, "after.md", B_DOC.replace("Furthermore,", "Also,"))
        _, plain = run_attain(before, after, "--voice-rules", rules_of(d))
        result, checked = run_attain(before, after, "--voice-rules", rules_of(d),
                                     "--check")
        assert plain == 0, "the default exit is 0 for every verdict"
        assert checked == 1, result["verdict"]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_a_conversion_that_reaches_the_register_lands():
    """The other side of `flat`. A held-out piece by the writer the fingerprint
    was built from is what a conversion is trying to become, so if that does not
    read as landed the measure is not measuring anything."""
    d = build_fixture()
    try:
        before = written(d, "before.md", B_DOC)
        after = written(d, "after.md", A_HELD_OUT)
        result, code = run_attain(before, after, "--voice-rules", rules_of(d))
        assert result["verdict"] == "landed", (result["verdict"],
                                               result["summary"])
        assert code == 0, result
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_an_edit_away_from_the_profile_regresses_and_fails_check():
    d = build_fixture()
    try:
        before = written(d, "before.md", A_HELD_OUT)
        after = written(d, "after.md", B_DOC)
        result, code = run_attain(before, after, "--voice-rules", rules_of(d),
                                  "--check")
        assert result["verdict"] == "regressed", result["verdict"]
        assert code == 1, result
    finally:
        shutil.rmtree(d, ignore_errors=True)


EXPANSIONS = (("don't", "do not"), ("isn't", "is not"), ("it's", "it is"),
              ("I'm", "I am"), ("I'll", "I will"), ("we've", "we have"),
              ("they're", "they are"), ("that's", "that is"),
              ("there's", "there is"), ("can't", "cannot"),
              ("didn't", "did not"), ("hasn't", "has not"),
              ("wasn't", "was not"), ("I've", "I have"), ("I'd", "I would"),
              ("nobody's", "nobody is"), ("we'd", "we would"))


def test_missed_is_never_a_check_failure():
    """A document that cannot reach the target without inventing content is
    guardrail 1 working, not a defect. Only `regressed` and `flat` say the
    editor did something wrong.

    The after here is the writer's own held-out piece with every contraction
    expanded, so the sentence measures land and `contraction_rate` cannot. That
    is the shape of a real conversion against a source with no contractions in
    it to restore: adding them would be inventing a stance the source did not
    have, which guardrail 1 forbids and which is why this must not fail.
    """
    d = build_fixture()
    try:
        formal = A_HELD_OUT
        for short, long in EXPANSIONS:
            formal = formal.replace(short, long)
        before = written(d, "before.md", B_DOC)
        after = written(d, "after.md", formal)
        result, code = run_attain(before, after, "--voice-rules", rules_of(d),
                                  "--check")
        missed = [n for n, r in result["measures"].items()
                  if r["verdict"] == "missed"]
        assert result["verdict"] not in ("flat", "regressed"), result["verdict"]
        assert code == 0, result["verdict"]
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------
# what a regression is, and what it is not
# --------------------------------------------------------------------------

def test_a_measure_inside_tolerance_is_on_target_whichever_way_it_moved():
    """Tolerance is tested before movement.

    A measure that went from a tenth of a sample sd off the profile mean to half
    of one moved away from it and is still somewhere the writer's own samples
    go. Called `regressed`, one such row failed the whole document under
    --check, which is the opposite of what a tolerance band is for.
    """
    attain = load_module("rw_attain_test", ATTAIN)
    assert attain.measure_verdict(0.1, 0.5, True) == "on_target"
    assert attain.measure_verdict(0.1, 2.0, False) == "regressed"
    # The epsilon still stands where the measure ends up outside: a hair of
    # movement in a measure the pass never touched is noise, not a regression.
    assert attain.measure_verdict(1.9, 2.0, False) == "missed"
    assert attain.measure_verdict(None, None, None) == "unmeasured"


def test_a_delta_that_drifts_inside_the_band_is_not_a_regression():
    """The document half of the same rule.

    Both documents here are the writer's own paragraphs and both sit inside the
    self-distance band, so neither is a conversion that went wrong. Before this,
    any growth in the Delta at all was `regressed` with no epsilon, and --check
    exited 1 on noise while the per-measure comparison next to it carefully
    applied one.
    """
    d = build_fixture()
    try:
        from helpers import scan_module
        scan = scan_module()
        fp = stylometry.load(
            os.path.join(d, "tester" + stylometry.FINGERPRINT_SUFFIX))
        band = fp["self_distance"]["max"]
        # Stated as a premise and asserted rather than assumed: this test means
        # nothing if the two documents are not both in range with the second
        # further out.
        pair = [_doc(A_PARAS, r) for r in ((0, 1, 2, 3, 5), (0, 1, 2, 4, 5))]
        deltas = [stylometry.distance(fp, scan.strip_for_stats(t))["delta"]
                  for t in pair]
        assert deltas[0] < deltas[1] <= band, (deltas, band)

        result, code = run_attain(written(d, "before.md", pair[0]),
                                  written(d, "after.md", pair[1]),
                                  "--voice-rules", rules_of(d), "--check")
        assert result["reliable"], result
        assert result["verdict"] != "regressed", (result["verdict"], deltas)
        assert code == 0, result["verdict"]
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------
# what it refuses to do
# --------------------------------------------------------------------------

def test_one_document_is_unpaired_rather_than_judged():
    """With no before there is no edit, and every other verdict is a claim about
    a pair. Reporting `partial` there would be grading a conversion nobody
    made."""
    d = build_fixture()
    try:
        result, code = run_attain(written(d, "one.md", B_DOC),
                                  "--voice-rules", rules_of(d), "--check")
        assert result["verdict"] == "unpaired", result["verdict"]
        assert code == 0, result
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_a_profile_with_no_fingerprint_exits_2():
    """The one place this diverges from scan.py, deliberately. There a missing
    fingerprint is the common case and a note. Here you asked for an attainment
    check, and a clean report over nothing measured is a false pass."""
    d = build_fixture(with_fingerprint=False)
    try:
        result, code = run_attain(written(d, "one.md", B_DOC),
                                  "--voice-rules", rules_of(d))
        assert code == 2, result
        assert "fingerprint" in result.get("stderr", ""), result
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_a_profile_named_by_hand_that_does_not_exist_exits_2():
    d = build_fixture()
    try:
        result, code = run_attain(written(d, "one.md", B_DOC),
                                  "--voice", "nobody-by-that-name")
        assert code == 2, result
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_a_short_document_is_unmeasurable_rather_than_wrong():
    d = build_fixture()
    try:
        short = written(d, "short.md", "Two sentences. That is all of it.\n")
        result, code = run_attain(short, "--voice-rules", rules_of(d), "--check")
        assert result["verdict"] == "unmeasurable", result["verdict"]
        assert code == 0, result
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------
# what a rewrite loop reads
# --------------------------------------------------------------------------

def test_the_gap_is_signed_so_a_loop_knows_which_way_to_move():
    """"10 sd off" calls for opposite edits depending on the sign, and a bare
    magnitude tells a rewrite nothing it can act on."""
    d = build_fixture()
    try:
        result, _ = run_attain(written(d, "one.md", B_DOC),
                               "--voice-rules", rules_of(d))
        offs = [row["sd_off_after"] for row in result["measures"].values()
                if row["sd_off_after"] is not None]
        assert offs, result["measures"]
        assert any(v < 0 for v in offs), offs
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_the_payload_names_the_schema_that_produced_it():
    d = build_fixture()
    try:
        result, _ = run_attain(written(d, "one.md", B_DOC),
                               "--voice-rules", rules_of(d))
        assert result["schema_version"] >= 1, result
        assert result["fingerprint_schema"] == stylometry.SCHEMA_VERSION, result
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_plan_emits_bands_and_never_a_per_sentence_script():
    """The design decision, pinned. A sampled list of exact word counts is
    unhittable, and chasing it manufactures the cadence
    references/false-positives.md calls a new fingerprint rather than the
    absence of one."""
    d = build_fixture()
    try:
        result, code = run_attain(written(d, "one.md", B_DOC),
                                  "--voice-rules", rules_of(d), "--plan")
        assert code == 0, result
        targets = result["shape_targets"]
        assert targets, result
        for t in targets:
            assert t["p10"] <= t["median"] <= t["p90"], t
            assert not any(isinstance(v, list) for v in t.values()), t
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_the_distance_contributors_come_through_for_the_next_pass():
    """A bare distance says a document is wrong and not what to change. These
    are the markers to trade."""
    d = build_fixture()
    try:
        result, _ = run_attain(written(d, "one.md", B_DOC),
                               "--voice-rules", rules_of(d))
        assert result["distance"]["contributors_after"], result["distance"]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_stale_fingerprint_raises_exit_code_2_cleanly():
    """A stale fingerprint schema causes attain.py to exit with code 2 without traceback."""
    import subprocess
    d = build_fixture()
    try:
        fp_path = os.path.join(d, "tester.fingerprint.json")
        with open(fp_path, "w", encoding="utf-8") as fh:
            json.dump({"schema_version": 999}, fh)
        doc = written(d, "one.md", B_DOC)
        res = subprocess.run([sys.executable, os.path.join(SCRIPTS, "attain.py"),
                             doc, "--voice-rules", rules_of(d)],
                            capture_output=True, text=True)
        assert res.returncode == 2
        assert "attain.py" in res.stderr
        assert "Traceback" not in res.stderr
    finally:
        shutil.rmtree(d, ignore_errors=True)

