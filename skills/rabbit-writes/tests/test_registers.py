#!/usr/bin/env python3
"""
The tolerance matrix, and whether the engine implements what it documents.

This used to parse the markdown table out of references/context.md and compare
it against two dicts in scan.py, which was the only way to catch a cell claiming
a tolerance nobody had implemented. registers.json replaced all three copies,
so what is left to check is different and smaller: that the data file says what
the docs say, that every id in it is real, and that the tolerances behave.

The one thing worth keeping from the old approach is the coverage check. A rule
listed in the matrix with no engine counterpart is how `curly-quote` sat in
every skip set unable to fire in any register, and rwlib.registers.problems is
where that check lives now.
"""

import glob
import os

from helpers import ROOT, lexicon, scan_module, scan_text

from rwlib import injection, registers
from rwlib.lexicon import SYNTHETIC_FINDING_IDS


def known_ids():
    return {p["id"] for p in lexicon()["patterns"]} | set(SYNTHETIC_FINDING_IDS)


def test_the_matrix_validates():
    problems = registers.problems(known_ids())
    assert not problems, "\n".join(problems)


def test_the_matrix_is_not_empty():
    """A parser that silently returns nothing makes every check above vacuous,
    which is how the previous version of this suite passed for a while."""
    data = registers.load()
    assert len(data["rules"]) >= 25, "got %d rules" % len(data["rules"])
    assert len(registers.registers()) == 7, str(registers.registers())


def test_the_spine_is_a_ladder_of_real_registers():
    """The formality axis a document form maps onto. Data rather than prose, so
    a rung naming nothing fails here instead of reading as a claim context.md
    makes about the matrix."""
    spine = registers.spine()
    assert spine == ("chat", "informal", "blog", "formal"), str(spine)
    assert set(spine) <= set(registers.registers())
    assert registers.default_register() in spine


def test_every_register_is_on_the_spine_or_is_a_genre_column():
    """No third category, and no register in neither. `technical-blog`, `docs`,
    and `linkedin` sit outside the ladder because each carries tolerances no
    formality band captures, which is a different thing from being stricter or
    looser than a rung."""
    assert (set(registers.spine()) | set(registers.genre_registers())
            == set(registers.registers()))
    assert not set(registers.spine()) & set(registers.genre_registers())
    assert registers.genre_registers() == ("technical-blog", "docs", "linkedin")


def test_context_md_matches_the_data_file():
    assert registers.doc_table() == registers.render_table(), (
        "references/context.md has drifted. Run: python3 "
        "skills/rabbit-writes/scripts/rwlib/registers.py --write")


def test_scan_derives_its_tables_from_the_data_file():
    """Not a tautology while scan.py still exports these names: it is what stops
    somebody reintroducing a literal dict beside the import."""
    scan = scan_module()
    assert scan.PROFILE_SKIP == registers.skip_table()
    assert scan.PROFILE_RELAX == registers.relax_table()
    assert scan.VOCAB_EXEMPT_PROFILES == registers.vocab_exempt_registers()
    assert tuple(scan.REGISTERS) == registers.registers()


def test_the_default_register_is_a_real_register():
    assert registers.default_register() in registers.registers()


def test_every_tolerance_names_a_real_register():
    unknown = ((set(registers.skip_table()) | set(registers.relax_table()))
               - set(registers.registers()))
    assert not unknown, str(sorted(unknown))


def test_no_p0_fingerprint_is_skipped_or_relaxed_anywhere():
    """The promise the engine makes about production evidence. A craft P0 may be
    relaxed, because that is a judgment about writing; a fingerprint P0 is
    evidence about how the file was made and applies in every register."""
    lex = lexicon()
    priority = {p["id"]: p["priority"] for p in lex["patterns"]}
    band = {p["id"]: p["band"] for p in lex["patterns"]}
    muffled = sorted(
        pid
        for table in (registers.skip_table(), registers.relax_table())
        for entries in table.values() for pid in entries
        if band.get(pid) == "fingerprint" and priority.get(pid) == "P0")
    assert not muffled, str(muffled)


def test_no_safety_finding_is_skipped_or_relaxed_anywhere():
    """The safety band applies in every register, the way a P0 fingerprint does.
    A register that could switch off injection detection is a register an
    attacker has a reason to ask for, and "chat" is not a claim about whether
    a document is carrying a concealed instruction."""
    muffled = sorted(
        pid
        for table in (registers.skip_table(), registers.relax_table())
        for entries in table.values() for pid in entries
        if pid in injection.FINDING_IDS)
    assert not muffled, str(muffled)


def test_rules_with_no_mechanical_form_are_named():
    """A row applied by reading rather than by regex. Listed rather than
    inferred, so adding a pattern for one of them is a deliberate change."""
    unimplemented = registers.unimplemented_rules()
    assert "Bold overuse" in unimplemented
    assert "Wall-of-text replies" in unimplemented
    assert len(unimplemented) == 8, str(unimplemented)


# --------------------------------------------------------------------------
# the tolerances behave
# --------------------------------------------------------------------------

QUOTES = "A note about %s here.\n" % " ".join('“q%d”' % i for i in range(5))


def test_a_relaxed_rule_still_fires_past_its_allowance():
    relaxed, _ = scan_text(QUOTES, "--profile", "technical-blog")
    hits = [f for f in relaxed["findings"] if f["id"] == "curly-quote"]
    assert hits, str([f["id"] for f in relaxed["findings"]])
    allowance = registers.relax_table()["technical-blog"]["curly-quote"]
    assert len(hits) == 10 - allowance, "got %d" % len(hits)


def test_a_register_that_skips_a_rule_stays_silent():
    strict, _ = scan_text(QUOTES, "--profile", "blog")
    assert not [f for f in strict["findings"] if f["id"] == "curly-quote"]


# --------------------------------------------------------------------------
# every cell changes what the engine reports
# --------------------------------------------------------------------------
#
# The two tests above check one cell each, by hand, and that is how `curly-quote`
# sat in every skip set unable to fire in any register: the cells nobody wrote a
# test for are exactly the ones that quietly stop meaning anything.
#
# So every cell is exercised, from one document per finding id built by repeating
# a unit that raises it. TRIGGERS is required to cover every id the matrix names,
# which is what makes this hold up: adding a cell for a new id fails the coverage
# test until somebody writes the unit that fires it.
#
# FILLER carries the word count for the three rules that only fire on a long
# enough document, and is checked for raising nothing itself.

FILLER = (
    "The team met on Tuesday and went through the backlog one item at a time. "
    "Two of the tickets were closed the same afternoon and a third went back "
    "to the person who filed it, since nobody could work out what the report "
    "was asking for. The build ran green afterwards. We agreed to look at the "
    "queue again on Friday, and to write down what we decided this time so the "
    "next person reading it has somewhere to start. Nothing else came up. The "
    "room was cold and the coffee was old, which is roughly how these go. One "
    "more item went to the list for next month, and then we all went back to "
    "what we had been doing before the meeting started.\n\n")

# id -> (unit that raises it once, joiner, prefix, floor)
#
# `prefix` is filler for a rule that needs a word count before it looks at
# anything. `floor` is a minimum number of units, and it is only legitimate on an
# id with no relaxed cell, because a floor would swallow the allowance the
# relaxed test is measuring. The test below asserts that.
TRIGGERS = {
    "boilerplate-phrase": ("The emerging sector matters here.", " ", "", 0),
    "confidence-calibration": ("It is worth noting that this holds.", " ", "", 0),
    "curly-quote": ("“", "q ", "A note about ", 0),
    "diff-anchored": ("This function was added to replace the old one.", " ", "", 0),
    "em-dash-rate": ("a — b", " and ", "Text: ", 0),
    "emoji-heading": ("# \U0001F680 Heading", "\n\n", "", 0),
    "future-narrative": (
        "It may become one of the most important narratives.", " ", "", 0),
    "generic-conclusion": ("In conclusion, the work is done.", " ", "", 0),
    "hedge-stack": ("This could potentially work.", " ", "", 0),
    "list-label-period": ("- **Label.** Text on the line.", "\n", "", 0),
    "promotional": ("The house is nestled in the hills.", " ", "", 0),
    "rhetorical-question": ("What does this mean?", "\n\n", "", 0),
    "significance-inflation": ("It stands as a testament.", " ", "", 0),
    "signposting": ("Let's dive in.", " ", "", 0),
    "social-cta": ("Bookmark this.", " ", "", 0),
    "tier1": ("We delve into the tapestry.", " ", "", 0),
    "tier2-cluster": ("Harness and streamline the work.", " ", "", 0),
    "tier3-density": ("The result was significant and innovative.", " ", FILLER, 0),
    "transition-stack": ("Moreover, it works.", "\n\n", "", 0),
    # No filler here, deliberately. This rule fires on paragraphs being the same
    # length as each other, so a filler paragraph of a different length is the
    # one thing that stops it, and the word count has to come from the units.
    "uniform-paragraphs": (
        "This is a sentence of a fairly ordinary length right here. "
        "And here is a second one that runs about the same distance.",
        "\n\n", "", 8),
}


def matrix_ids():
    out = set()
    for table in (registers.skip_table(), registers.relax_table()):
        for entries in table.values():
            out |= set(entries)
    return out


def trigger_doc(finding_id, n):
    unit, joiner, prefix, floor = TRIGGERS[finding_id]
    return prefix + joiner.join([unit] * max(n, floor)) + "\n"


def hits_for(text, register, finding_id):
    payload, _ = scan_text(text, "--profile", register)
    return len([f for f in payload["findings"] if f["id"] == finding_id])


def test_every_id_in_the_matrix_has_a_trigger_document():
    """The coverage half, and the reason the test below cannot rot. A cell added
    for an id with no unit here fails right now rather than passing vacuously."""
    missing = sorted(matrix_ids() - set(TRIGGERS))
    assert not missing, "no trigger document for: %s" % ", ".join(missing)

    relaxed = {fid for entries in registers.relax_table().values()
               for fid in entries}
    floored = {fid for fid, spec in TRIGGERS.items() if spec[3]}
    both = sorted(relaxed & floored)
    assert not both, ("%s has a unit floor and a relaxed cell. The floor would "
                      "swallow the allowance, so the relaxed test would pass "
                      "without measuring anything" % ", ".join(both))


def test_every_trigger_document_actually_fires():
    """A probe that raises nothing makes every assertion about it vacuous, which
    is the shape of the bug this whole section exists to catch."""
    dead = []
    for finding_id in sorted(TRIGGERS):
        biggest = max([0] + [r.get(finding_id, 0)
                             for r in registers.relax_table().values()])
        text = trigger_doc(finding_id, biggest + 3)
        if not any(hits_for(text, register, finding_id)
                   for register in registers.registers()):
            dead.append(finding_id)
    assert not dead, "trigger raises nothing in any register: %s" % ", ".join(dead)


def test_every_skip_cell_silences_a_document_that_would_otherwise_report():
    skip = registers.skip_table()
    failures = []
    for register, ids in sorted(skip.items()):
        for finding_id in sorted(ids):
            biggest = max([0] + [r.get(finding_id, 0)
                                 for r in registers.relax_table().values()])
            text = trigger_doc(finding_id, biggest + 3)
            got = hits_for(text, register, finding_id)
            if got:
                failures.append("%s x %s reported %d despite skipping it"
                                % (register, finding_id, got))
    assert not failures, "\n".join(failures)


def test_every_relaxed_cell_honours_its_allowance_and_still_fires_past_it():
    """Both halves, because relaxing is not skipping. A cell that reported at
    the allowance would be strict wearing a tolerance, and one that stayed
    silent past it would be a skip with an allowance written beside it, which is
    the confusion that left `curly-quote` unfirable everywhere."""
    failures = []
    for register, entries in sorted(registers.relax_table().items()):
        for finding_id, allowance in sorted(entries.items()):
            at = hits_for(trigger_doc(finding_id, allowance), register, finding_id)
            if at:
                failures.append(
                    "%s x %s reported %d at its allowance of %d"
                    % (register, finding_id, at, allowance))
            past = hits_for(trigger_doc(finding_id, allowance + 3), register,
                            finding_id)
            if not past:
                failures.append(
                    "%s x %s stayed silent %d past its allowance of %d, so the "
                    "cell is a skip rather than a tolerance"
                    % (register, finding_id, 3, allowance))
    assert not failures, "\n".join(failures)


def test_a_p0_only_cell_on_a_p0_finding_is_rejected():
    """skip_table folds p0-only in with skip on the stated grounds that every id
    it names is P1 or P2. Nothing checked that, so a p0-only cell on a P0 id
    would have read in the docs as "the credibility killers still fire here" and
    behaved as a full suppression of one."""
    real = registers.priorities()
    assert real["hidden-unicode"] == "P0", real["hidden-unicode"]
    assert real["tier1"] == "P1", real["tier1"]
    assert not registers.problems(known_ids(), id_priorities=real)

    lying = dict(real, tier1="P0")
    complaints = registers.problems(known_ids(), id_priorities=lying)
    assert any("p0-only" in c for c in complaints), complaints


# --------------------------------------------------------------------------
# register auto-detection
# --------------------------------------------------------------------------
#
# One representative document per detectable form, plus the negative cases
# that document why chat and technical-blog are NOT in DETECTABLE_REGISTERS:
# both were tried and both produced false positives against real prose
# (a plain blog blurb for chat, most of the 100-README corpus for
# technical-blog) before being dropped. That history is why the fallback
# tests below exist, not just the positive ones.

DOCS_SAMPLE = (
    "# Setup\n\n## Prerequisites\n\n- Python 3.9+\n\n"
    "## Installation\n\nRun pip install.\n\n## Usage\n\nRun the script.\n"
)

LINKEDIN_SAMPLE = (
    ("Excited to share our latest release. " * 20)
    + "\n\n#buildinpublic #python #opensource\n"
)

FORMAL_SAMPLE = (
    "Subject: Quick question about the release\n\n"
    "Hi Alice,\n\n"
    "Could you confirm the release date for next week? I want to line up "
    "the changelog.\n\n"
    "Thanks,\nBob\n"
)

AMBIGUOUS_SHORT_SAMPLE = (
    "This is a short, plain paragraph with no headings, no greeting, and no "
    "code fence. It reads like the opening of a blog post, not a chat "
    "message, but nothing here structurally rules that out.\n"
)


def test_detect_register_finds_docs_shaped_headings():
    register, confidence, signals = registers.detect_register(
        DOCS_SAMPLE, path="SETUP.md")
    assert register == "docs", (register, signals)
    assert confidence == "detected"


def test_detect_register_carves_out_readme_from_docs():
    """references/forms/docs.md routes a file literally named README.md to
    the separate readme-writing skill instead. A README with docs-shaped
    headings must not be auto-detected as docs."""
    register, confidence, signals = registers.detect_register(
        DOCS_SAMPLE, path="README.md")
    assert register == registers.default_register(), (register, signals)
    assert confidence == "default"


def test_detect_register_finds_a_linkedin_shaped_post():
    register, confidence, signals = registers.detect_register(LINKEDIN_SAMPLE)
    assert register == "linkedin", (register, signals)
    assert confidence == "detected"


def test_detect_register_finds_an_email_shaped_document():
    register, confidence, signals = registers.detect_register(FORMAL_SAMPLE)
    assert register == "formal", (register, signals)
    assert confidence == "detected"


def test_detect_register_falls_back_to_default_for_ambiguous_prose():
    """The regression case: a short, headingless, greeting-free paragraph is
    NOT evidence for chat. It is what a chat message looks like and also what
    the first paragraph of a blog post looks like, which is exactly why chat
    was tried and dropped from DETECTABLE_REGISTERS."""
    register, confidence, signals = registers.detect_register(
        AMBIGUOUS_SHORT_SAMPLE)
    assert register == registers.default_register(), (register, signals)
    assert confidence == "default"
    assert signals == []


def test_detect_register_only_returns_declared_detectable_registers():
    assert set(registers.DETECTABLE_REGISTERS) <= set(registers.registers())
    assert "chat" not in registers.DETECTABLE_REGISTERS
    assert "technical-blog" not in registers.DETECTABLE_REGISTERS


def test_profile_auto_flows_through_scan_py():
    payload, code = scan_text(DOCS_SAMPLE, "--profile", "auto")
    assert code == 0, payload
    assert payload["profile"] == "docs", payload
    assert any("auto-detected" in n for n in payload["notes"]), payload["notes"]


def test_profile_auto_defaults_when_nothing_matches():
    payload, code = scan_text(AMBIGUOUS_SHORT_SAMPLE, "--profile", "auto")
    assert code == 0, payload
    assert payload["profile"] == registers.default_register(), payload
    assert any("auto-detected" in n for n in payload["notes"]), payload["notes"]


def test_explicit_profile_still_wins_over_auto_shaped_content():
    """--profile is never overridden by detection; 'auto' has to be asked for
    by name, exactly like --voice auto."""
    payload, code = scan_text(DOCS_SAMPLE, "--profile", "chat")
    assert code == 0, payload
    assert payload["profile"] == "chat", payload


README_CORPUS = sorted(glob.glob(os.path.join(
    ROOT, "..", "..", "docs", "readme-analysis", "repos", "*", "README.md")))


def test_detect_register_calibrated_against_the_100_readme_corpus():
    """Calibrate before wiring, the same discipline every other detector in
    this repo follows. This corpus is what caught technical-blog's real
    false-positive rate (62 of 100, even after narrowing the unit regex it
    was still 17) before this shipped, so it stays as a regression test:
    every README here is expected to fall through to the default register,
    since none of them are docs (the README carve-out), linkedin, or
    email/letter shaped."""
    assert len(README_CORPUS) >= 90, (
        "expected the docs/readme-analysis corpus, found %d files"
        % len(README_CORPUS))
    default = registers.default_register()
    misdetected = []
    for readme in README_CORPUS:
        with open(readme, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        register, _, signals = registers.detect_register(text, path=readme)
        if register != default:
            misdetected.append("%s -> %s %s" % (readme, register, signals))
    assert not misdetected, "\n".join(misdetected)
