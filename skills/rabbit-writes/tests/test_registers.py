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

from helpers import lexicon, scan_module, scan_text

from rwlib import registers
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
    assert len(registers.registers()) == 6, str(registers.registers())


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
