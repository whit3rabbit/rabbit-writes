"""Tests for rwlib.ste, the ASD-STE100 structural rules.

Module-level test functions, not TestCase classes: run.py collects `test_*`
functions and silently collected zero from the class-based first version of
this file, so the shipping verification command exercised none of it.
"""

import glob
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from rwlib.ste import (
    ADVISORY_IDS,
    MECHANICAL_IDS,
    STE_FINDING_IDS,
    STE_PRIORITIES,
    check,
    check_banned_verbs,
    check_condition_order,
    check_for_scan,
    check_ing_verbs,
    check_modals,
    check_paragraph_sentences,
    check_passive,
    check_phrasal_verbs,
    check_semicolons,
    check_sentence_lengths,
    classify_passage,
    count_words,
    phrase_regex,
    ste_priority,
    version,
    word_regex,
)

import helpers


# ------------------------------------------------------------- counting ----

def test_count_words_basics():
    assert count_words("Hello world") == 2
    # Backtick pair = 1 word; "Run" + "here" + code span = 3
    assert count_words("Run `console.log('hello world')` here") == 3
    # 50mb = 1 word (number with unit), file = 1 word
    assert count_words("50mb file") == 2
    assert count_words("real-time system") == 2
    # Markdown links: the URL is stripped, the visible link text is counted
    # (a reader sees "click here", not the address it points to)
    assert count_words("[click here](https://example.com)") == 2
    # Image alt text is stripped whole: it is not visible body text
    assert count_words("![a screenshot of the app](https://example.com/x.png)") == 0
    # HTML tags stripped
    assert count_words("<strong>bold</strong> text") == 2


def test_an_alphanumeric_identifier_counts_as_one_word():
    # The unit in NUMBER_WITH_UNIT_RX is optional, so an unguarded pattern
    # matched the digit inside an identifier and counted it twice. With the
    # caps default-on that inflated every technical sentence.
    cases = [
        ("sha256", 1),
        ("v2 release", 2),
        ("utf8 and 20 files", 4),
        ("3rd place", 2),
        ("50mb file", 2),
        ("Wait 1.5s now", 3),
        ("It costs 50%.", 3),
    ]
    for text, expected in cases:
        assert count_words(text) == expected, (text, count_words(text))


# ----------------------------------------------------- sentence lengths ----

def test_procedural_limit_is_20_words():
    text = ("Connect the power cable to the DC input and secure it with the "
            "screwdriver and tighten fully before proceeding to the next "
            "step and then verify the connection is correct and safe.")
    findings = check_sentence_lengths(text, mode="procedural")
    assert len(findings) == 1
    assert findings[0]["id"] == "ste-sentence-procedural"
    assert findings[0]["priority"] == "P1"
    assert check_sentence_lengths("Run the deployment script.",
                                  mode="procedural") == []


def test_descriptive_limit_is_25_words():
    text = ("The software architecture follows a microservices design "
            "pattern that improves scalability and maintainability while "
            "reducing operational complexity across all subsystems and "
            "services in the platform and provides better fault isolation "
            "for production environments.")
    findings = check_sentence_lengths(text, mode="descriptive")
    assert len(findings) == 1
    assert findings[0]["id"] == "ste-sentence-descriptive"


def test_a_forced_mode_reaches_the_length_check_through_check():
    # 22 words: over the procedural limit, under the descriptive one. The
    # first version of check() accepted mode and dropped it, so --ste-mode
    # was a dead flag end to end.
    s = ("The quick brown fox jumps over the lazy dog and then keeps going "
         "for quite a long while after that point today.")
    proc = [f for f in check(s, mode="procedural")
            if f["id"].startswith("ste-sentence")]
    desc = [f for f in check(s, mode="descriptive")
            if f["id"].startswith("ste-sentence")]
    assert len(proc) == 1, proc
    assert desc == [], desc


def test_an_indented_paragraph_reports_its_real_line_and_never_raises():
    # The first version searched text.split("\n") for the paragraph's
    # stripped first line with .index(): ValueError on any indented
    # paragraph, and 11 of the 100 corpus READMEs crashed on it.
    long_sentence = ("The quick brown fox jumps over the lazy dog and then "
                     "keeps going for quite a long while after that point "
                     "today.")
    doc = "Intro line.\n\n   %s\n" % long_sentence
    findings = [f for f in check_sentence_lengths(doc, mode="procedural")]
    assert [f["line"] for f in findings] == [3], findings


def test_classify_passage():
    cases = [
        ("## Install\n\n1. Run the setup script.\n2. Configure it.",
         "procedural"),
        ("### Step 1: Install\n\nRun the script.", "procedural"),
        ("- Run the script\n- Look at the output", "procedural"),
        ("The system consists of a frontend and a backend.", "descriptive"),
        ("## Overview\n\nThe component handles authentication.",
         "descriptive"),
    ]
    for text, want in cases:
        assert classify_passage(text) == want, (text, want)


# --------------------------------------------------------------- modals ----

def test_banned_and_approved_modals():
    for sentence in ("You should verify the config.",
                     "It would fail if not set.",
                     "The file may be deleted.",
                     "It might be ready.",
                     "You could use the flag."):
        findings = check_modals(sentence)
        assert len(findings) == 1, sentence
        assert findings[0]["id"] == "ste-modal"
    for sentence in ("You can set the flag.",
                     "It will fail.",
                     "The flag must be set."):
        assert check_modals(sentence) == [], sentence


def test_the_month_may_is_not_a_modal():
    # Case-insensitive matching flagged every changelog date. Capitalized
    # "May" followed by a digit, or after a month-position word, stands down;
    # the verb keeps firing.
    assert check_modals("Released in May 2026.") == []
    assert check_modals("May 5 is the date.") == []
    assert len(check_modals("You may restart it.")) == 1
    assert len(check_modals("May the config change at runtime?")) == 1


# ---------------------------------------------------------------- verbs ----

def test_banned_verbs_fire_on_the_word_and_not_inside_one():
    for sentence in ("Verify that the file exists.",
                     "Confirm the connection is open.",
                     "Check that the config is loaded.",
                     "Ensure the flag is set."):
        findings = check_banned_verbs(sentence)
        assert len(findings) == 1, sentence
        assert findings[0]["id"] == "ste-banned-verb"
    # The first word_regex spelled its boundary [\\w-] inside a raw string,
    # a character class of backslash, w, hyphen: "recheck" flagged for
    # "check".
    assert check_banned_verbs("Please recheck the checkout flow.") == []


def test_phrasal_verbs_flag_the_rules_own_examples_and_nothing_invented():
    # Rule 9.3 is a productive-grammar constraint, not a lookup table, and
    # the standard says so outright. An earlier lexicon shipped ~555 generic
    # English phrasal verbs ("zone out" -> "relax") that exist nowhere in
    # the Issue 9 PDF; the check now covers exactly the rule's own worked
    # examples and stands down for its named approved exceptions.
    for sentence, want in (("Put out the fire.", "extinguish"),
                           ("The cells give off fumes.", "release")):
        findings = check_phrasal_verbs(sentence)
        assert len(findings) == 1, sentence
        assert findings[0]["id"] == "ste-phrasal-verb"
        assert want in findings[0]["excerpt"], findings[0]
    assert check_phrasal_verbs("Put on the gloves.") == []
    assert check_phrasal_verbs("Set up the server.") == []


def test_the_phrasal_block_is_rule_9_3_not_a_lookup_table():
    import json
    lex_path = os.path.join(os.path.dirname(__file__), "..", "scripts",
                            "ste_lexicon.json")
    lex = json.load(open(lex_path, encoding="utf-8"))
    block = lex["phrasal_verbs"]
    assert block.get("rule") == "9.3", block.get("rule")
    assert block.get("worked_examples"), "the rule lost its examples"
    assert block.get("approved_exceptions"), "the rule lost its exceptions"
    strays = [k for k in block
              if not k.startswith("_")
              and k not in ("rule", "principle", "worked_examples",
                            "approved_exceptions")]
    assert strays == [], strays
    # And no replacement the check offers names a banned verb.
    from rwlib.ste import _phrasal_examples
    banned = set(lex["banned_verbs"])
    circular = {k: v for k, v in _phrasal_examples(lex).items()
                if v in banned}
    assert not circular, circular


# ------------------------------------------------------ clause structure ----

def test_ing_verb_after_a_comma_flags_and_a_gerund_subject_does_not():
    findings = check_ing_verbs("Install the package, making it available.")
    assert len(findings) == 1
    assert "making" in findings[0]["match"]
    assert check_ing_verbs("Running the script is safe.") == []


def test_condition_order_flags_commands_only():
    assert len(check_condition_order(
        "Run the script if the flag is set.")) == 1
    assert len(check_condition_order(
        "Start the server when the port is open.")) == 1
    assert len(check_condition_order(
        "- Run the backup when the queue is empty.")) == 1
    assert check_condition_order(
        "If the flag is set, run the script.") == []
    # A declarative sentence carrying one of the verbs mid-sentence is not a
    # command, and a condition opening the *next* sentence is not this
    # sentence's trailing clause. The first pattern matched both.
    assert check_condition_order("I do not know if it works.") == []
    assert check_condition_order("Run the tool. If it fails, stop.") == []


# -------------------------------------------------------------- passive ----

def test_passive_voice_catches_irregular_participles():
    for sentence in ("The config is loaded.",
                     "The file was updated.",
                     "The file was written by the tool.",
                     "The photo was taken yesterday.",
                     "The change was made upstream."):
        findings = check_passive(sentence)
        assert len(findings) == 1, sentence
        assert findings[0]["id"] == "ste-passive"
    # (\w+ed|en) made the second branch the literal word "en": "was written"
    # never fired, "is en route" and "is red today" did.
    assert check_passive("The team is en route now.") == []
    assert check_passive("The light is red today.") == []
    assert check_passive("The system loads the config.") == []


# ------------------------------------------------------------ semicolons ----

def test_semicolons_flag_in_prose_and_not_in_entities():
    findings = check_semicolons("The config loads; the flag is set.")
    assert len(findings) == 1
    assert findings[0]["id"] == "ste-no-punctuation"
    assert check_semicolons("Use A &amp; B &nbsp; here.") == []


# ---------------------------------------------------------------- vocab ----

def test_ai_slop_is_case_insensitive_and_skips_the_json_commentary():
    # Sentence-initial position is exactly where these fillers sit, and the
    # first pattern was the module's one case-sensitive regex. It also
    # compiled the lexicon's "_comment" key, whose decoded form " comment"
    # matched every "word comment" in anybody's prose.
    assert len(check_ai_slop_text("Simply run it.")) == 1
    assert len(check_ai_slop_text("simply run it.")) == 1
    assert check_ai_slop_text("Read the comment here.") == []
    assert len(check_ai_slop_text("it's important to test.")) == 1
    assert len(check_ai_slop_text("Use A and/or B.")) == 1


def check_ai_slop_text(text):
    from rwlib.ste import check_ai_slop
    return check_ai_slop(text)


# ------------------------------------------------------------ integration ----

def test_full_check_returns_all_categories():
    text = ("You should verify that the file is present. "
            "If the config is loaded then you can run the script, making it "
            "easy to test. The system is configured correctly.")
    ids = {f["id"] for f in check(text)}
    for want in ("ste-modal", "ste-banned-verb", "ste-ing-verb",
                 "ste-passive"):
        assert want in ids, (want, ids)


def test_check_for_scan_adds_ste_version():
    findings = check_for_scan("You should verify the config.")
    assert findings, "the fixture stopped raising anything"
    assert all(f["ste_version"] == version() for f in findings)


def test_scan_format_json_includes_ste_version():
    scan = helpers.load_module("scan", helpers.SCAN)
    findings, stats = scan.scan("A simple test sentence here.\n")
    data = scan.json_payload(findings, stats, "blog", False, "none", [])
    assert "ste_version" in data
    assert data["ste_version"] == version()


def test_regex_empty_fallbacks_never_match():
    # (?!) must never match any string
    rx_word = word_regex([])
    rx_phrase = phrase_regex([])
    assert rx_word.pattern == r"(?!)"
    assert rx_phrase.pattern == r"(?!)"
    assert rx_word.search("hello world") is None
    assert rx_phrase.search("hello world") is None
    assert rx_word.search("") is None
    assert rx_phrase.search("") is None


def test_every_ste_id_is_declared_with_a_priority():
    # The two collections are one: STE_FINDING_IDS derives from
    # STE_PRIORITIES, and neither carries the suppression-* ids, which
    # rwlib/lexicon.py owns.
    assert STE_FINDING_IDS == frozenset(STE_PRIORITIES)
    for fid in STE_FINDING_IDS:
        assert fid.startswith("ste-"), fid
        assert ste_priority(fid) in ("P0", "P1", "P2"), fid
    for f in check("You should verify the config; check it."):
        assert f["id"] in STE_FINDING_IDS, f["id"]
        assert f["priority"] == ste_priority(f["id"]), f


def test_scan_runs_ste_over_the_exempted_copy():
    # A semicolon in a code fence is not prose. STE used to scan raw text:
    # 1,069 of its corpus semicolon hits were exactly this. No ste argument
    # now: the semicolon check is mechanical and runs in every plain scan.
    #
    # Three prose semicolons against the blog allowance of two, so exactly
    # one survives and it is the last of them. The fence carries two more
    # on one line: counted, it would be the earliest hit, the allowance
    # would eat a prose line instead, and two would come back rather than
    # one.
    scan = helpers.load_module("scan", helpers.SCAN)
    text = ("A plain sentence here.\n\n"
            "```c\nint a = 1; int b = 2;\n```\n\n"
            "The first one has a real semicolon; it counts.\n"
            "The second one has a real semicolon; it counts.\n"
            "The third one has a real semicolon; it counts.\n")
    findings, _ = scan.scan(text)
    semis = [f for f in findings if f["id"] == "ste-no-punctuation"]
    assert len(semis) == 1, semis
    assert semis[0]["line"] == 9, semis


def test_a_rabbit_allow_comment_reaches_ste_findings():
    # STE findings joined the suppression pass when they moved inside
    # scan(); appended after it, the comment below reported itself unused.
    # ste="all" because ste-modal is advisory now and no longer runs by
    # default; the suppression contract it proves is the same either way.
    scan = helpers.load_module("scan", helpers.SCAN)
    text = ("<!-- rabbit-allow: ste-modal (quoting the standard) -->\n"
            "You should restart it.\n")
    findings, _ = scan.scan(text, ste="all")
    modal = [f for f in findings if f["id"] == "ste-modal"]
    assert len(modal) == 1, modal
    assert modal[0].get("suppressed"), modal
    assert not any(f["id"] == "suppression-unused" for f in findings)


def test_ste_never_fails_check_on_its_own():
    # Report-only is a priority claim: every ste-* id is P1 or P2, and the
    # --check gate is P0-only.
    assert all(p in ("P1", "P2") for p in STE_PRIORITIES.values()), \
        STE_PRIORITIES


def test_ste_completes_over_the_whole_readme_corpus():
    # The calibration mandate from CLAUDE.md, asserted rather than reported:
    # every corpus document scans without an exception, through the same
    # exempted copy scan() passes. Before the offset rewrite, 11 of these
    # 100 raised ValueError.
    scan = helpers.load_module("scan", helpers.SCAN)
    paths = sorted(glob.glob(os.path.join(
        os.path.dirname(__file__), "..", "..", "..",
        "docs", "readme-analysis", "repos", "*", "README.md")))
    if not paths:
        return  # the research corpus is not part of a packaged checkout
    assert len(paths) == 100, len(paths)
    for path in paths:
        text = io.open(path, encoding="utf-8").read()
        check(scan.apply_exemptions(text))


# ------------------------------------------------ default, advisory, voice ----

def test_the_bands_partition_the_declared_ids():
    # MECHANICAL_IDS is the one home for the split and ADVISORY_IDS is
    # derived from it, so together they must be exactly the declared ids,
    # disjointly, or the split has grown a second copy somewhere.
    assert MECHANICAL_IDS | ADVISORY_IDS == STE_FINDING_IDS
    assert not MECHANICAL_IDS & ADVISORY_IDS
    assert "ste-paragraph-sentences" in MECHANICAL_IDS


def test_every_advisory_id_is_p2():
    # Advisory strength is the priority claim: a vocabulary suggestion
    # never outranks a counted rule. A demotion back to P1 would move the
    # id into the default report's P1 section under --ste without anyone
    # deciding that.
    for fid in ADVISORY_IDS:
        assert STE_PRIORITIES[fid] == "P2", (fid, STE_PRIORITIES[fid])


def test_a_seven_sentence_paragraph_fires_and_six_does_not():
    six = " ".join("Sentence %d stays short." % i for i in range(1, 7))
    seven = " ".join("Sentence %d stays short." % i for i in range(1, 8))
    assert check_paragraph_sentences(six) == []
    hits = check_paragraph_sentences(seven)
    assert len(hits) == 1, hits
    assert hits[0]["line"] == 1 and hits[0]["priority"] == "P1", hits


def test_a_list_block_is_not_a_paragraph_for_rule_six_six():
    # Ten bullets are ten "sentences" and 6.6's own answer to them is the
    # vertical list, so flagging the list reports the fix as the problem.
    lst = "\n".join("- Do step %d with care." % i for i in range(1, 11))
    assert check_paragraph_sentences(lst) == []


def test_the_paragraph_cap_comes_from_the_lexicon():
    from rwlib import ste as ste_mod
    entry = ste_mod.load_ste_lexicon()["punctuation_and_word_count"] \
        ["max_sentences_per_paragraph"]
    assert ste_mod._paragraph_cap() == entry["max_sentences"]
    assert entry["rule"] == "6.6"


def test_mechanical_scope_leaves_the_advisory_checks_out():
    text = "You should verify it; utilize the tool.\n"
    mech = {f["id"] for f in check(text, scope="mechanical")}
    everything = {f["id"] for f in check(text, scope="all")}
    assert "ste-no-punctuation" in mech
    assert not mech & {"ste-modal", "ste-banned-verb", "ste-vocab"}, mech
    assert {"ste-modal", "ste-banned-verb", "ste-vocab"} <= everything


def test_a_word_cap_replaces_both_mode_caps():
    long_sentence = ("The system provides a measurement over documents "
                     + " ".join("item%d" % i for i in range(30)) + ".")
    default_hits = check_sentence_lengths(long_sentence, mode="descriptive")
    assert default_hits and "limit 25" in default_hits[0]["label"]
    assert check_sentence_lengths(
        long_sentence, mode="descriptive", word_cap=60) == []
    forced = check_sentence_lengths(long_sentence, mode="descriptive",
                                    word_cap=10)
    assert forced and "limit 10" in forced[0]["label"], forced
    assert "Voice profile cap" in forced[0]["excerpt"], forced


def past_allowance(unit, joiner, finding_id, extra=1):
    """Repeat `unit` until the default register's tolerance is used up.

    Every mechanical id carries a cell in registers.json, so one trigger
    sentence proves nothing about the wiring below: the check runs, the
    finding exists, and the allowance eats it. The matrix's own suite
    measures the tolerances (tests/test_registers.py). These tests are
    about scan() running the check at all, so they clear the allowance
    from the data rather than restating a number that moves.
    """
    from rwlib import registers
    n = registers.relax_table().get("blog", {}).get(finding_id, 0) + extra
    return joiner.join([unit] * n) + "\n"


def test_a_plain_scan_runs_the_mechanical_band_and_not_the_advisory():
    scan = helpers.load_module("scan", helpers.SCAN)
    text = past_allowance("You should utilize the robust tool; it "
                          "facilitates outcomes.", "\n", "ste-no-punctuation")
    ids = {f["id"] for f in scan.scan(text)[0]}
    assert "ste-no-punctuation" in ids
    assert "ste-modal" not in ids and "ste-vocab" not in ids, ids
    full = {f["id"] for f in scan.scan(text, ste="all")[0]}
    assert {"ste-modal", "ste-vocab"} <= full


def test_ste_off_silences_the_mechanical_band():
    scan = helpers.load_module("scan", helpers.SCAN)
    text = past_allowance("This one has a real semicolon; it counts.",
                          "\n", "ste-no-punctuation")
    assert any(f["id"] == "ste-no-punctuation" for f in scan.scan(text)[0])
    quiet = scan.scan(text, ste="off")[0]
    assert not [f for f in quiet if f["id"].startswith("ste-")], quiet


def test_the_tri_state_rejects_its_old_boolean_form():
    # 'off' is a truthy string and the boolean form used to mean 'all', so
    # a silent acceptance here is the --no-ste no-op bug arriving by the
    # back door.
    scan = helpers.load_module("scan", helpers.SCAN)
    for bad in (True, False, "sometimes", None):
        try:
            scan.scan("Some text here.\n", ste=bad)
        except ValueError:
            continue
        raise AssertionError("ste=%r was accepted" % (bad,))


def test_a_profile_with_a_semicolon_ruling_stands_down_the_ste_copy():
    # Either value is a ruling: 'allow' is the writer's own sentence
    # shape, 'forbid' already flags every semicolon as voice-semicolon at
    # the profile's priority. The ste copy underneath is noise about the
    # same character.
    scan = helpers.load_module("scan", helpers.SCAN)
    text = past_allowance("This one has a real semicolon; it counts.",
                          "\n", "ste-no-punctuation")
    assert any(f["id"] == "ste-no-punctuation" for f in scan.scan(text)[0])
    allow = scan.scan(text, voice_rules={
        "voice": "t", "mechanics": {"semicolon": "allow"}})[0]
    forbid = scan.scan(text, voice_rules={
        "voice": "t", "mechanics": {"semicolon": "forbid"}})[0]
    assert not [f for f in allow if f["id"] == "ste-no-punctuation"]
    assert not [f for f in forbid if f["id"] == "ste-no-punctuation"]
    assert any(f["id"] == "voice-semicolon" for f in forbid)


def test_a_profile_paragraph_cap_stands_down_rule_six_six():
    # max_paragraph_sentences raises voice-paragraph-length itself; the
    # ste 6.6 copy would double-report the same block.
    scan = helpers.load_module("scan", helpers.SCAN)
    para = past_allowance(
        " ".join("Sentence %d stays short." % i for i in range(1, 9)),
        "\n\n", "ste-paragraph-sentences")
    assert any(f["id"] == "ste-paragraph-sentences" for f in scan.scan(para)[0])
    with_cap = scan.scan(para, voice_rules={
        "voice": "t", "mechanics": {"max_paragraph_sentences": 10}})[0]
    assert not [f for f in with_cap if f["id"] == "ste-paragraph-sentences"]


def test_a_profile_sentence_cap_replaces_the_ste_caps():
    scan = helpers.load_module("scan", helpers.SCAN)
    words = " ".join("word%d" % i for i in range(1, 15))
    text = past_allowance(
        "Run the installer and then check the settings: %s." % words,
        " ", "ste-sentence-procedural")
    ids = {f["id"] for f in scan.scan(text)[0]}
    assert "ste-sentence-procedural" in ids
    raised = scan.scan(text, voice_rules={
        "voice": "t", "mechanics": {"max_sentence_words": 30}})[0]
    assert not [f for f in raised if f["id"].startswith("ste-sentence")]
    lowered = scan.scan(text, voice_rules={
        "voice": "t", "mechanics": {"max_sentence_words": 15}})[0]
    hits = [f for f in lowered if f["id"] == "ste-sentence-procedural"]
    assert hits and "limit 15" in hits[0]["label"], hits
