#!/usr/bin/env python3
"""
Tests for the measured reach-for thesaurus in measure_voice.py.

Every case runs the script as a subprocess against temp samples, the same way
test_voice_setup.py does, because the behavior worth pinning is what the tool
prints for a person building a profile: proposals only when both halves of
the evidence hold, both-used families printed as non-rules, and the JSON
block a caller pastes into a rules file.
"""

import json
import os

from helpers import MEASURE_VOICE, SCRIPTS_DIR, run_cmd, create_temp_file
# helpers puts the engine's scripts/ on sys.path, so rwlib imports the same
# way here as it does in build_voice.py.
from rwlib import fixes

THESAURUS_PATH = os.path.join(SCRIPTS_DIR, "thesaurus.json")


def _report(sample_text):
    path = create_temp_file(sample_text)
    try:
        stdout, stderr, code = run_cmd(MEASURE_VOICE, path)
        assert code == 0, "measure_voice failed: %s" % stderr
        return stdout
    finally:
        os.unlink(path)


def _json(sample_text):
    path = create_temp_file(sample_text)
    try:
        stdout, stderr, code = run_cmd(MEASURE_VOICE, path, "--json")
        assert code == 0, "measure_voice failed: %s" % stderr
        return json.loads(stdout)
    finally:
        os.unlink(path)


def _section(stdout):
    """The thesaurus section: table, paste block, and non-rule notes.

    Runs to the next section of the report (the short-sample note or the
    closing paragraph) rather than to the first blank line, because the
    table, the paste block, and the notes are separated by blank lines
    inside one section.
    """
    start = stdout.index("words to reach for")
    ends = [m for m in (stdout.find("\n\nnote:", start),
                        stdout.find("\nEvery suggestion", start),
                        stdout.find("\nWhere an answer", start))
            if m != -1]
    return stdout[start:min(ends) if ends else len(stdout)]


def test_proposal_needs_both_halves():
    """Plain word attested and overreach at zero proposes the substitution.

    Table-driven over the reach families, one case per row, because the
    stdlib runner takes zero-arg tests and a parametrize would fail its run
    rather than degrade to pytest-only.
    """
    cases = [
        # (sample text, reach word, overreach term expected in the block)
        ("We helped the team twice today.", "help", "facilitate"),
        ("They get plates and cups for every party.", "get", "obtain"),
        ("It was hard to leave early.", "hard", "difficult"),
        ("We figured out the plan together.", "figure out", "ascertain"),
        ("People were tired and went home.", "people", "individuals"),
    ]
    for text, reach, over in cases:
        section = _section(_report(text))
        assert '"%s": "%s"' % (over, reach) in section, \
            "expected %s -> %s in:\n%s" % (over, reach, section)


def test_both_used_is_a_note_not_a_rule():
    """A family the samples use both halves of never lands in the block."""
    data = _json("Maybe it works, or perhaps it fails, and we try to help.")
    assert "perhaps" not in data["substitutions"], \
        "perhaps proposed although the sample uses it"
    kinds = {(n["reach"], n["kind"]) for n in data["substitution_notes"]}
    assert ("maybe", "both") in kinds, kinds
    # And the printed report names it as a non-rule rather than printing a
    # table row that claims the synonym never appears.
    section = _section(_report(
        "Maybe it works, or perhaps it fails, and we try to help."))
    assert "both halves used: 'maybe'" in section
    assert "perhaps" not in _table_rows(section)


def test_inverted_family_is_a_note():
    """Overreach used with the plain word absent is inverted, never a rule."""
    data = _json("The task was difficult and we communicated poorly.")
    assert "difficult" not in data["substitutions"]
    assert "communicate" not in data["substitutions"]
    kinds = {n["kind"] for n in data["substitution_notes"]}
    assert "inverted" in kinds, kinds
    section = _section(_report(
        "The task was difficult and we communicated poorly."))
    assert "inverted: no 'hard' at all" in section
    assert "inverted: no 'talk' at all" in section


def test_silent_family_proposes_nothing():
    """Neither half appearing produces no proposal and no note."""
    data = _json("The cat sat on the mat and the dog slept.")
    assert data["substitution_notes"] == [], data["substitution_notes"]
    section = _section(_report("The cat sat on the mat and the dog slept."))
    assert "no family has its plain word attested" in section


def test_quoted_examples_do_not_attest():
    """A term inside a quoted span does not count toward either half.

    The overreach words must stay at zero for the proposal to exist, and a
    quoted `difficult` would flip the hard/difficult family to both-used.
    """
    data = _json(
        'We worked hard on it. The style guide says "avoid difficult '
        'language" and we agreed.')
    assert data["substitutions"].get("difficult") == "hard", \
        data["substitutions"]
    both = [n for n in data["substitution_notes"] if n["reach"] == "hard"]
    assert both == [], "quoted example flipped the family to a note"


def test_json_payload_shape():
    """--json carries the raw totals, the proposals, and the version.

    The version is read from thesaurus.json rather than pinned as a literal,
    because the merge script's whole job is bumping it, and a literal here
    would fail the suite on the first merge without anything being wrong.
    """
    data = _json("We helped and we got plates. It was hard.")
    with open(THESAURUS_PATH, encoding="utf-8") as fh:
        shipped_version = json.load(fh)["version"]
    assert data["thesaurus_version"] == shipped_version
    assert data["thesaurus_totals"]["help"] == 1
    assert data["thesaurus_totals"]["obtain"] == 0
    assert data["substitutions"]["facilitate"] == "help"
    assert "1 times" in data["substitutions_evidence"]["facilitate"]


def test_vocabulary_line_lists_content_words():
    """The distributions block carries the load-bearing words, counted."""
    report = _report(
        "The gardener planted mercy and more mercy beside the tomatoes, "
        "because mercy grows in bad soil. The gardener watered everything.")
    line = [l for l in report.splitlines() if "load-bearing words" in l]
    assert line, "no load-bearing words line in the distributions block"
    assert "mercy 3" in line[0], line[0]
    # Function words stay out of the vocabulary line even when frequent.
    assert "the" not in line[0].split("load-bearing words")[1].split(",")


def test_thesaurus_data_shape():
    """The shipped families pass the same rules validate.py enforces.

    Checked here as well, because a broken family should fail the
    voice-setup suite even on a checkout where the repo validator does not
    exist, which is what a loose copy of the three skills is.
    """
    with open(THESAURUS_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data.get("version"), int)
    seen_reach, seen_over = set(), set()
    for family in data["families"]:
        reach, over = family["reach"], family["overreach"]
        assert fixes.is_mechanical_substitution(reach), reach
        assert over, family
        assert reach not in seen_reach
        seen_reach.add(reach)
        for term in over:
            assert term != reach, family
            assert term not in seen_reach, (term, family)
            assert term not in seen_over, (term, family)
            seen_over.add(term)


def test_questions_route_asks_thesaurus_only_for_both():
    """The interview asks about a family only when both halves are attested.

    Table-driven inside the body, zero args, per the run.py rule. The
    question is searched in kept and dropped together, because the budget
    trims by rank and where the cut lands is not what this test pins. What
    it pins: a both-used family raises the question with the counts held in
    the evidence key, and a one-sided family raises no question at all,
    since the samples already answered it.
    """
    cases = [
        # (sample text, thesaurus question expected)
        ("Maybe it works, or perhaps it fails, and we try again.", True),
        ("We helped the team and got plates for every party.", False),
    ]
    for text, expected in cases:
        data = _json(text)
        asked = [q for q in data["questions"] + data["questions_dropped"]
                 if q["id"] == "thesaurus"]
        if not expected:
            assert asked == [], asked
            continue
        assert len(asked) == 1, asked
        q = asked[0]
        assert "maybe" in q["evidence"] and "vs" in q["evidence"], q
        # The counts stay in the evidence block. A digit in the question
        # text is the leading question the interview exists to avoid.
        assert not any(ch.isdigit() for ch in q["question"]), q


def test_substitutions_round_trip_through_fixes():
    """A proposed block is an edit, not documentation.

    The paste block's whole claim is that scan.py --apply-safe rewrites
    each key to its value. Prove it: take the proposals off a reach-heavy
    sample, apply them through fixes to a draft using the overreach terms,
    and require the reach words to land, case preserved, with the pair
    passing the same verify gate that decides whether --write writes.
    """
    import verify

    data = _json("We get plates and it was hard to leave early.")
    subs = data["substitutions"]
    assert subs.get("obtain") == "get", subs
    assert subs.get("difficult") == "hard", subs

    rules = {"preferred_substitutions": subs}
    before = ("We must obtain plates for the party. "
              "Difficult choices come later.")
    fixed, applied, _skipped = fixes.apply(before, rules)
    assert "obtain" not in fixed.lower(), fixed
    assert "get plates" in fixed, fixed
    # Sentence-initial term keeps its case through the rewrite.
    assert "Hard choices" in fixed, fixed
    assert any(r["id"] == "voice-substitution" for r in applied), applied
    assert verify.validate(before, fixed)["ok"], \
        verify.validate(before, fixed)


def _table_rows(section):
    """Just the table half of the section, before the paste block.

    Falls back to the whole section when there are no proposals, which is
    the case the callers are asserting about anyway.
    """
    return section.split("proposed for the rules file")[0]
