#!/usr/bin/env python3
"""
The property the module is worth shipping for: a held-out document by the same
writer scores inside the self-distance band, a document in a different register
scores outside it, and the contributors name the markers a human would name.

Synthetic voices, so the test owns its own ground truth. Voice A is
contraction-heavy and first person, four samples on four unrelated subjects,
because the fingerprint has to survive a change of topic and a fixture that
varied only the register would prove nothing about that. Voice B is the formal
committee register the connector markers exist to separate from it.

Two of the assertions here are about restraint rather than power. The distance
never reaches P0, and it never fails `--check`: a writer is allowed to sound
unlike themselves on purpose, and a number that blocked a commit over it would
be the humanizer-shaped failure this plugin exists to avoid.

Stdlib only, 3.9+.
"""

import json
import os
import sys
import tempfile

from helpers import SCRIPTS, scan_text

sys.path.insert(0, SCRIPTS)
from rwlib import stylometry                                     # noqa: E402

# Voice A: contraction-heavy, "so"/"also"/"but", first person, short-sentence
# casual register.
A = [
    """So the deploy broke again on Tuesday. I don't think it's the pipeline
    this time, it's the cache config, and honestly we've been ignoring that
    file for a year. I'll fix it tomorrow. Also worth saying: the rollback
    worked, so nobody outside the team even noticed. But we got lucky, and
    I don't want to rely on that again. The fix isn't hard, it's just boring,
    and boring work doesn't get picked up unless someone owns it. So I'm
    owning it. If it slips past Friday, that's on me and I'll say so in
    standup. We're also going to add a check so this can't happen quietly
    again, because the worst part wasn't the break, it was that we didn't
    know for an hour.

    The other thing I noticed is that the alerting config hasn't been
    touched since we migrated, and half the thresholds are for hardware we
    don't run anymore. That's a separate ticket, but it's the same disease:
    config nobody owns rots quietly until it bites. I'm not going to fix all
    of it this week, and I don't think anyone should try, because a giant
    cleanup PR is how you break three unrelated things at once. So the plan
    is one file at a time, each with its own review, and I'll keep a list of
    what's left so it doesn't just live in my head. If we're still finding
    stale config in June, we'll automate the audit. But I'd rather not build
    a tool before we know the shape of the problem, and honestly we don't
    yet.""",
    """I've been reading about soil drainage because the garden flooded
    again. It's not the rain, really, it's the clay layer about a foot down,
    and you can't fix that with mulch. So the plan is a french drain along
    the back fence. I don't love digging, but it's one weekend and then
    it's done. Also, the neighbor did theirs last year and it's held up,
    so there's a working example ten feet away. I'll borrow their trencher
    if they're willing. If it doesn't work we're out a weekend and some
    gravel, and honestly that's a cheap experiment. The tomatoes can't
    take another wet spring, so something has to change this year.

    There's also the question of what to plant along the drain once it's
    in, because bare gravel looks like a construction site and I've promised
    it won't. The nursery guy says daylilies don't mind wet feet, and they're
    cheap, so that's probably the answer. I looked at fancier options and
    they're all either fussy or expensive, and I don't want a border I have
    to babysit. The lawn edge will need redoing too, but that's a next-year
    problem and I'm officially not thinking about it. One project at a time
    is the only way anything gets finished around here, and even that's
    optimistic. If the drain works, everything else is decoration. If it
    doesn't, well, at least the daylilies won't care.""",
    """The book club picked a long one this month and I'm behind. It's good,
    but it's slow, and I don't have the evenings I used to. So I'm doing
    chapters on the train instead. That's actually working better than I
    expected, because the train has no wifi and I can't wander off to my
    phone. Also I've stopped feeling guilty about skimming the battle
    scenes. They're not why I'm reading it and the author won't know. We
    meet Thursday and I'll be done by then, or close enough that I can
    fake the last fifty pages. I don't think anyone finishes every book
    anyway, and the discussion is usually about the first half.

    The funny thing is the book got better right where I stopped caring
    about keeping up. There's a middle section that everyone at the last
    meeting will have skimmed, I'd bet money on it, and then the last third
    actually moves. I'm not going to pretend the pacing works, because it
    doesn't, but the ending mostly earns it. Also I've decided I'm picking
    the next book, and it's going to be short. Not because I can't handle
    long ones, but because the discussions are better when everyone actually
    finished, and that hasn't happened since spring. A two-hundred-page book
    everyone read beats a six-hundred-page book nobody did, and I'll say
    exactly that on Thursday if anyone pushes back.""",
    """We switched the kids to the earlier bus and it's been fine, mostly.
    They don't love the alarm, but they're asleep by nine now, so it evens
    out. The mornings are calmer too, and I didn't expect that. It's not
    the extra time, really, it's that nobody's rushing, and rushing was
    what made everyone snap at each other. Also breakfast happens now,
    which it didn't before, and I'm counting that as a win. If it falls
    apart in winter we'll revisit, but I don't think it will. Kids adjust
    faster than we do, and honestly the hard part was us changing our own
    evenings, not them changing theirs.

    The one real cost is evenings, because dinner moved earlier and that
    ate the gap I used to work out in. I haven't solved that yet. Mornings
    are out, obviously, since the whole point was making mornings calmer,
    and I'm not going to be the person who undoes the fix to protect a gym
    slot. So it's probably lunchtime workouts, which I've always said I hate,
    but I've also never actually tried for more than a week. We'll see.
    Also worth writing down: the kids started doing homework before dinner
    without being asked, and I don't fully understand why, but I'm not going
    to poke at something that's working. Some changes come with free extras
    and you just take them.""",
]

# The same writer, held out: same register, new subject.
A_HELD_OUT = """The budget spreadsheet finally balances and I'm not touching
it again this month. It wasn't the math, it was that we'd been counting the
insurance twice, once in the annual row and once monthly, so of course the
total looked wrong. I found it by printing the thing out, which feels
ancient, but you see differently on paper. Also we're overpaying for
streaming, again, so two of those are getting cut. I don't think anyone
will notice. If they do, they can make the case for bringing one back, and
honestly that conversation is overdue anyway. So that's the plan: fix the
double count, cut two subscriptions, and leave it alone until March.

The bigger lesson is that we check the total and never the rows, and the
total lies whenever two rows agree with each other by accident. So I've added
a note at the top of the sheet, in red, that says check the insurance rows
first, because future me will absolutely make this mistake again otherwise.
I know this because past me left no note and here we are. Also the utilities
column has been wrong-ish for months, not badly, just drifting, and I've
stopped pretending I'll reconcile it weekly. Monthly is what actually
happens, so monthly is now the rule. Writing down the rule you actually
follow beats pretending to follow a better one, and it's taken me an
embarrassing number of years to accept that.

The other thing I'm doing differently is checking it on the first of the
month instead of whenever I remember, because whenever I remember turns out
to be never. It's fifteen minutes and it's boring, but so is every useful
habit I've kept. I don't expect this one to stick either, honestly, and I've
put a reminder on the calendar anyway. If it lapses again I'll know within
a month rather than a year, which is the whole point."""

# Voice B: formal report register. However, moreover, therefore, no
# contractions, no first person, long noun phrases.
B_DOC = """The committee has reviewed the proposed amendments to the
procurement framework. However, several provisions remain inconsistent with
the established guidelines, and the documentation submitted by the vendor
does not adequately address the concerns raised during the previous review
cycle. Moreover, the projected costs exceed the allocated budget by a
considerable margin. Therefore, the committee recommends that the proposal
be returned for revision. Additionally, the timeline presented in the
submission is contingent upon approvals which have not been obtained, and
the risk assessment furnished with the application is insufficiently
detailed. The revised submission should address each deficiency enumerated
in the appendix, and should furthermore include the certifications required
under the applicable regulations.

Furthermore, the committee notes that the vendor's references were not
independently verified, and that two of the three references provided pertain
to engagements which concluded more than five years prior to the current
submission. The evaluation criteria require references from engagements of
comparable scope completed within the preceding three years. Accordingly, the
submission does not satisfy the reference requirements as currently
constituted. The committee further observes that the proposed governance
structure assigns overlapping responsibilities to the steering group and the
delivery board, and that the escalation pathway between these bodies is not
defined. Such ambiguity has been identified in previous engagements as a
principal contributor to schedule deterioration, and the revised submission
should therefore delineate these responsibilities explicitly. A resubmission
deadline of the fifteenth is considered appropriate, subject to confirmation
by the secretariat.

The committee additionally records that no provision has been made for the
transition period, during which the incumbent supplier will retain
operational responsibility. Arrangements for that period should be set out
in the revised submission, together with the associated cost, which is not
presently disclosed. Should the revision be received after the stated
deadline, consideration will be deferred to the subsequent meeting."""

_FP = {}


def fingerprint_a():
    if "a" not in _FP:
        _FP["a"] = stylometry.fingerprint(A, voice="test-a")
    return _FP["a"]


# --------------------------------------------------------------------------
# the measure
# --------------------------------------------------------------------------

def test_a_held_out_sample_by_the_same_writer_stays_in_the_band():
    """The claim the whole module rests on. If a fifth piece by the same
    person scores as a stranger, the band is measuring the topic."""
    result = stylometry.distance(fingerprint_a(), A_HELD_OUT)
    assert result["verdict"] in ("in_range", "near"), result


def test_a_different_register_scores_further_than_the_same_voice():
    same = stylometry.distance(fingerprint_a(), A_HELD_OUT)
    other = stylometry.distance(fingerprint_a(), B_DOC)
    assert other["delta"] > same["delta"], (same["delta"], other["delta"])
    assert other["verdict"] == "out_of_range", other


def test_the_contributors_name_the_connective_tissue():
    """A distance with no receipts tells a rewrite loop nothing. These are the
    words a person would point at, and they are what the loop trades."""
    named = [c["marker"] for c in
             stylometry.distance(fingerprint_a(), B_DOC)["contributors"]]
    assert any(m in named for m in ("however", "moreover", "therefore",
                                    "additionally", "furthermore")), named


def test_one_spiky_marker_cannot_impersonate_a_register_change():
    """Z_CAP's reason for existing. Text in the writer's own register, with one
    unused marker hammered, is still their register."""
    spike = A_HELD_OUT + "\n\n" + ("Moreover it should hold. " * 12)
    plain = stylometry.distance(fingerprint_a(), A_HELD_OUT)
    spiked = stylometry.distance(fingerprint_a(), spike)
    assert spiked["delta"] < 2.0 * plain["delta"], (plain, spiked)


def test_the_contributor_z_is_not_capped():
    """The cap belongs to the average and not to the report: "18 per 1,000
    words against a profile of zero" is the size of the fact."""
    worst = stylometry.distance(fingerprint_a(), B_DOC)["contributors"][0]
    assert abs(worst["z"]) > stylometry.Z_CAP, worst


def test_rates_covers_every_marker_with_absent_as_zero():
    r, _ = stylometry.rates("nothing relevant here")
    assert set(r) == set(stylometry.MARKER_WORDS)
    assert r["furthermore"] == 0.0


def test_a_curly_apostrophe_is_the_same_marker_as_a_straight_one():
    """Half the samples anybody pastes come out of an editor that curls them,
    and a fingerprint that reads the curled form as two tokens is measuring the
    editor."""
    straight, n1 = stylometry.rates("I don't think it's done")
    curled = "I don\u2019t think it\u2019s done"   # escaped, never a literal
    curly, n2 = stylometry.rates(curled)
    assert n1 == n2 == 5, (n1, n2)
    assert straight == curly


def test_one_sample_is_refused_rather_than_calibrated_on_nothing():
    try:
        stylometry.fingerprint([A[0]])
    except ValueError:
        return
    raise AssertionError("one sample produced a fingerprint with no band")


def test_a_thin_sample_is_declared():
    fp = stylometry.fingerprint(["short one here." * 3, "short two here." * 3])
    assert fp["thin_samples"] == 2, fp["thin_samples"]


def test_a_fingerprint_round_trips_through_json():
    directory = tempfile.mkdtemp(prefix="rabbit-fp-")
    path = os.path.join(directory, "fp.json")
    stylometry.save(fingerprint_a(), path)
    reloaded = stylometry.load(path)
    assert (stylometry.distance(reloaded, A_HELD_OUT)["delta"]
            == stylometry.distance(fingerprint_a(), A_HELD_OUT)["delta"])


def test_a_fingerprint_from_another_schema_is_refused():
    """Regenerate rather than compare against a marker list that has moved.
    Silently reading an old file would report a distance measured against a
    baseline nobody built."""
    stale = dict(fingerprint_a(), schema_version=0)
    try:
        stylometry.distance(stale, A_HELD_OUT)
    except ValueError:
        return
    raise AssertionError("a stale fingerprint was measured against anyway")


# --------------------------------------------------------------------------
# exemplars and distributions
# --------------------------------------------------------------------------

def test_exemplars_are_opt_in():
    assert "exemplars" not in fingerprint_a()
    with_them = stylometry.fingerprint(A, voice="test-a", exemplars=True)
    assert with_them["exemplars"], "asked for exemplars and got none"


def test_exemplars_skip_lists_and_headings():
    """A bullet demonstrates nothing about how this person writes a
    paragraph."""
    text = ("# A heading\n\n- one bullet about the thing\n- another bullet "
            "about the thing\n\n" + A[0])
    for para in stylometry.paragraphs(text):
        assert not para.startswith(("#", "-")), para


def test_nearest_exemplars_prefers_the_writers_own_register():
    """The retrieval a conversion runs. Given a target in voice A, the closest
    of a mixed pool should be an A paragraph and not the committee report."""
    pool = stylometry.paragraphs("\n\n".join(A)) + stylometry.paragraphs(B_DOC)
    picked = stylometry.nearest_exemplars(A_HELD_OUT, pool, k=3)
    assert picked, pool
    assert "committee" not in picked[0].lower(), picked[0]


def test_distributions_separate_two_registers_a_mean_would_hide():
    a_dist = stylometry.distributions("\n\n".join(A))
    b_dist = stylometry.distributions(B_DOC)
    assert a_dist["contractions"]["per_1k"] > b_dist["contractions"]["per_1k"]
    assert (b_dist["connectors"]["additive"]["per_1k"]
            + b_dist["connectors"]["causal"]["per_1k"]) > 0
    assert a_dist["sentence_openers"], a_dist
    assert a_dist["closer"], "no closer captured, and how a person signs off is "\
                             "the question a profile most often gets wrong"


def test_distributions_report_a_share_per_opener_and_not_only_a_count():
    """Two writers with the same 18-word average write nothing alike if one
    opens half her sentences with the same word. The share is that fact."""
    for entry in stylometry.distributions("\n\n".join(A))["sentence_openers"]:
        assert 0.0 < entry["share"] <= 1.0, entry


# --------------------------------------------------------------------------
# the engine
# --------------------------------------------------------------------------

def _with_fingerprint(fp, rules):
    """(rules path, fingerprint path) in a scratch directory, named so that
    stylometry.path_for finds one from the other."""
    directory = tempfile.mkdtemp(prefix="rabbit-voice-")
    rules_path = os.path.join(directory, "tester.rules.json")
    with open(rules_path, "w", encoding="utf-8") as fh:
        json.dump(rules, fh)
    stylometry.save(fp, os.path.join(directory, "tester.fingerprint.json"))
    return rules_path


def test_scan_reports_a_distance_and_never_fails_the_build_over_it():
    """P2 forever. A writer may sound unlike themselves on purpose, and a
    number that blocked a commit over it is the humanizer-shaped failure."""
    rules_path = _with_fingerprint(fingerprint_a(), {"voice": "tester"})
    result, code = scan_text(B_DOC, "--voice-rules", rules_path, "--check")
    hits = [f for f in result["findings"] if f["id"] == "voice-distance"]
    assert hits, [f["id"] for f in result["findings"]]
    assert hits[0]["priority"] == "P2", hits[0]
    assert code == 0, result["counts"]


def test_scan_says_nothing_when_the_document_is_in_the_voice():
    rules_path = _with_fingerprint(fingerprint_a(), {"voice": "tester"})
    result, _ = scan_text(A_HELD_OUT, "--voice-rules", rules_path)
    assert not [f for f in result["findings"] if f["id"] == "voice-distance"], \
        result["findings"]


def test_scan_publishes_the_measurement_for_a_rewrite_loop():
    """The contributors are the actionable half, so --json carries them whether
    or not the verdict crossed the reporting threshold."""
    rules_path = _with_fingerprint(fingerprint_a(), {"voice": "tester"})
    result, _ = scan_text(B_DOC, "--voice-rules", rules_path)
    measured = result["voice_distance"]
    assert measured["verdict"] == "out_of_range", measured
    assert measured["contributors"], measured


def test_a_short_document_is_measured_but_not_reported():
    """Under the reliability floor the marker rates are sampling noise. The
    number stays in --json with `reliable: false` beside it, and no finding is
    raised off it."""
    rules_path = _with_fingerprint(fingerprint_a(), {"voice": "tester"})
    short = " ".join(B_DOC.split()[:60])
    result, _ = scan_text(short, "--voice-rules", rules_path)
    assert result["voice_distance"]["reliable"] is False, result["voice_distance"]
    assert not [f for f in result["findings"] if f["id"] == "voice-distance"]


def test_no_fingerprint_is_not_an_error():
    """Most profiles will never have one, and a scan that failed over its
    absence would teach people to drop the flag."""
    directory = tempfile.mkdtemp(prefix="rabbit-voice-")
    rules_path = os.path.join(directory, "tester.rules.json")
    with open(rules_path, "w", encoding="utf-8") as fh:
        json.dump({"voice": "tester"}, fh)
    result, code = scan_text(A_HELD_OUT, "--voice-rules", rules_path, "--check")
    assert code == 0, result
    assert result["voice_distance"] is None, result["voice_distance"]


# --------------------------------------------------------------------------
# per-register fingerprints
# --------------------------------------------------------------------------
#
# A person's chat register and their essay register are two different
# statistical objects, and averaging them produces a fingerprint of nobody,
# which is the fact `per_sample_median` already exists to make visible. This is
# the layer where document forms actually diverge: the refusals in a profile
# carry across forms unchanged, the mechanics carry with the per-register
# overrides the writer authored, and the statistical target switches wholesale.


def test_a_fingerprint_records_the_register_it_measured():
    fp = stylometry.fingerprint(A, voice="tester", register="chat")
    assert fp["register"] == "chat", fp["register"]
    assert stylometry.fingerprint(A, voice="tester")["register"] is None


def test_recording_the_register_did_not_move_the_schema():
    """Additive, so a stored fingerprint from before this key means exactly what
    it always meant: the general one. A bump would have invalidated every
    fingerprint anybody had built."""
    assert stylometry.SCHEMA_VERSION == 3
    assert (stylometry.fingerprint(A, voice="tester", register="chat")
            ["schema_version"] == 3)


def test_path_for_prefers_the_register_and_falls_back_to_the_general_one():
    directory = tempfile.mkdtemp(prefix="rabbit-voice-")
    rules_path = os.path.join(directory, "tester.rules.json")
    with open(rules_path, "w", encoding="utf-8") as fh:
        json.dump({"voice": "tester"}, fh)
    general = os.path.join(directory, "tester.fingerprint.json")
    stylometry.save(stylometry.fingerprint(A, voice="tester"), general)

    # No scoped file yet: every register falls back, silently, because almost no
    # profile will ever carry more than one.
    assert stylometry.path_for(rules_path, "chat") == general
    assert stylometry.path_for(rules_path) == general

    scoped = stylometry.register_fingerprint_path(rules_path, "chat")
    stylometry.save(stylometry.fingerprint(A, voice="tester", register="chat"),
                    scoped)
    assert stylometry.path_for(rules_path, "chat") == scoped
    assert stylometry.path_for(rules_path, "formal") == general
    assert stylometry.path_for(rules_path) == general


def test_register_of_reads_the_scope_off_the_filename():
    """The filename decides which file is loaded, so it is what the scope is
    read from. The stored `register` field is then checked against it, because a
    file renamed by hand measures one register while claiming another."""
    assert stylometry.register_of("a/tester.chat.fingerprint.json") == "chat"
    assert stylometry.register_of("a/tester.fingerprint.json") is None
    assert stylometry.register_of("a/tester.rules.json") is None


def test_scan_measures_against_the_register_it_was_given():
    """The whole point of the scoped file. The two fingerprints below are built
    from different writers, so a scan under `chat` and a scan with no register
    cannot report the same distance unless the scoping did nothing."""
    directory = tempfile.mkdtemp(prefix="rabbit-voice-")
    rules_path = os.path.join(directory, "tester.rules.json")
    with open(rules_path, "w", encoding="utf-8") as fh:
        json.dump({"voice": "tester"}, fh)
    stylometry.save(fingerprint_a(),
                    os.path.join(directory, "tester.fingerprint.json"))
    # The scoped one is built from the formal-register document's own
    # paragraphs, so it is that register's target rather than voice A's.
    stylometry.save(
        stylometry.fingerprint(B_DOC.split("\n\n"), voice="tester",
                               register="chat"),
        stylometry.register_fingerprint_path(rules_path, "chat"))

    general, _ = scan_text(B_DOC, "--voice-rules", rules_path)
    scoped, _ = scan_text(B_DOC, "--voice-rules", rules_path, "--profile", "chat")
    assert general["voice_distance"] is not None
    assert scoped["voice_distance"] is not None
    assert (scoped["voice_distance"]["delta"]
            < general["voice_distance"]["delta"]), (
        "B measured against B's own chat fingerprint should sit closer than B "
        "measured against A: %s vs %s"
        % (scoped["voice_distance"], general["voice_distance"]))
