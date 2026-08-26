"""The engine merge, the docs register, and the voice contract."""

import os

from helpers import (SAMPLES, Tree, all_findings, run, run_code, run_raw,
                     sample, structure_ids)

VOICE_RULES = os.path.join(SAMPLES, "test-voice.rules.json")


def test_engine_findings_merge_into_one_sorted_list():
    tree = Tree({
        "CLAUDE.md": (
            "# t\n\nWe delve into the architecture here.\n\n"
            "- This one list item runs far past the cap by describing the "
            "parser and the emitter and the scheduler and the cache and the "
            "flags and the logging and the retry policy and the shutdown "
            "order and the interrupt handling and the exit codes in one "
            "single breath without stopping.\n"),
    })
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        found = all_findings(result)
        bands = {f["band"] for f in found}
        assert "structure" in bands, found
        assert bands - {"structure"}, (
            "engine findings must ride in the same list", found)
        # One list, sorted by the shared key: priorities never interleave.
        pri = [f["priority"] for f in found]
        assert pri == sorted(pri, key=("P0", "P1", "P2").index), pri
    finally:
        tree.close()


def test_rabbit_allow_covers_a_structure_finding():
    tree = Tree({
        "CLAUDE.md": (
            "# t\n\n"
            "<!-- rabbit-allow: claudemd-bullet-length (fixture keeps one "
            "long bullet on purpose) -->\n"
            "- This one list item runs far past the cap by describing the "
            "parser and the emitter and the scheduler and the cache and the "
            "flags and the logging and the retry policy and the shutdown "
            "order and the interrupt handling and the exit codes in one "
            "single breath without stopping.\n"),
    })
    try:
        result = run(tree.file("CLAUDE.md"), "--no-voice")
        bullets = [f for f in all_findings(result)
                   if f["id"] == "claudemd-bullet-length"]
        assert len(bullets) == 1 and "suppressed" in bullets[0], bullets
        assert result["counts"]["suppressed"] >= 1, result["counts"]
    finally:
        tree.close()


def test_runs_under_the_docs_register():
    """One significance-inflation hit passes, two fail, the docs allowance.

    The pair is the point: a single quiet run proves nothing (the rule could
    be off), and the failure at two is what shows the register cell is live.
    """
    one = "# t\n\nThe index plays a crucial role in finding a doc.\n"
    two = one + "\nIts ordering plays a vital role in the reading order.\n"
    for body, want in ((one, 0), (two, 1)):
        tree = Tree({"CLAUDE.md": body})
        try:
            _, code = run_code(tree.file("CLAUDE.md"), "--no-voice", "--check")
            assert code == want, (body, code)
        finally:
            tree.close()


def test_no_voice_disables_the_profile_but_not_the_reading():
    tree = Tree({
        "CLAUDE.md": "# t\n\nFurthermore, the cache works.\n",
    })
    try:
        with_voice = run(tree.file("CLAUDE.md"),
                         "--voice-rules", VOICE_RULES)
        assert any(f["band"] == "voice" for f in all_findings(with_voice)), (
            "the fixture profile bans 'furthermore'", all_findings(with_voice))
        without = run(tree.file("CLAUDE.md"), "--no-voice")
        assert not any(f["band"] == "voice" for f in all_findings(without))
        # The reading itself still ran: stats came back from the engine.
        assert "word_count" in without["files"][0]["stats"]
    finally:
        tree.close()


def test_voice_rules_named_by_hand_must_load():
    stdout, stderr, code = run_raw(
        os.path.abspath(sample("clean-claude.md")),
        "--voice-rules", "/nonexistent/nobody.rules.json")
    assert code == 2, (code, stdout)
    assert "voice" in stderr.lower(), stderr


def test_unresolved_auto_voice_is_a_note_not_an_error():
    tree = Tree({"CLAUDE.md": "# t\n\nPlain content, nobody's voice.\n"})
    try:
        stdout, stderr, code = run_raw(tree.file("CLAUDE.md"), "--json",
                                       cwd=tree.path)
        assert code == 0, stderr
    finally:
        tree.close()


def test_no_ste_silences_the_readability_caps():
    # The docs register drops the first N ste findings per id, so the fixture
    # has to clear that allowance for any to survive. Read N from the engine
    # rather than hardcoding a number the next calibration moves.
    from rwlib import registers
    allowance = registers.relax_table()["docs"]["ste-sentence-descriptive"]
    long_sentence = ("The converter walks tree number %d and reads every "
                     "manifest and checks every entry against the schema "
                     "and prints one line per file that fails there.\n\n")
    body = "# t\n\n" + "".join(long_sentence % i
                               for i in range(allowance + 2))
    tree = Tree({"CLAUDE.md": body})
    try:
        with_ste = run(tree.file("CLAUDE.md"), "--no-voice")
        assert any(f["id"].startswith("ste-") for f in all_findings(with_ste))
        without = run(tree.file("CLAUDE.md"), "--no-voice", "--no-ste")
        assert not any(f["id"].startswith("ste-")
                       for f in all_findings(without))
        # And the structure half is untouched either way.
        assert structure_ids(with_ste) == structure_ids(without)
    finally:
        tree.close()
