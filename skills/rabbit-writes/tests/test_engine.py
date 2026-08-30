#!/usr/bin/env python3
"""
The engine's own machinery: what it detects, what it measures as prose, the
invisible-character tables, and the false positives reviewers found.
"""

import os
import shutil
import tempfile

# Invisible characters are written as escapes here, never as literals, for
# exactly the reason scan.py's HIDDEN_UNICODE says: as literals they are
# invisible, and any tool that normalizes whitespace silently turns them into
# plain spaces. That happened to this file once already, and the fixture that
# was meant to hold five non-breaking spaces held five ordinary ones instead.

from helpers import (ai_result, ids, lexicon, sample, scan_json, scan_module,
                     scan_text, tier1_table_terms, written)


def test_fingerprints_are_detected():
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "tricky.md",
                       "A line with a zero\u200bwidth space.\n\n"
                       "See https://example.com/x?utm_source=chatgpt.com for more.\n\n"
                       "Contact [Your Name] before 2025-XX-XX.\n\n"
                       "As of my last training update, this was true. citeturn0search0\n")
        found = set(ids(scan_json(path)))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    for pattern_id in ("hidden-unicode", "ai-utm", "placeholder",
                       "cutoff-disclaimer", "citation-leak"):
        assert pattern_id in found, "%s missing from %s" % (pattern_id, found)


# --------------------------------------------------------------------------
# the lexicon and patterns.md agree
#
# Drift here is silent and one-directional: the table says replace on sight, the
# engine never flags it, and nobody notices until somebody compares the two by
# hand.
# --------------------------------------------------------------------------

def test_every_section_12_word_resolves_in_tier1():
    lex = lexicon()
    known = ({w.lower() for w in lex["tier1"]}
             | {p.lower() for p in lex["tier1_phrases"]})
    missing = sorted(t for t in tier1_table_terms() if t not in known)
    assert not missing, str(missing)


def test_section_12_is_not_empty():
    """Vacuous if the table parser silently returns nothing, which it has."""
    terms = tier1_table_terms()
    assert len(terms) > 30, "got %d" % len(terms)


def test_the_tiers_do_not_overlap():
    lex = lexicon()
    for a, b in (("tier1", "tier2"), ("tier1", "tier3"), ("tier2", "tier3")):
        overlap = sorted({w.lower() for w in lex[a]} & {w.lower() for w in lex[b]})
        assert not overlap, "%s and %s share %s" % (a, b, overlap)


def test_key_is_not_a_tier3_word():
    assert "key" not in {w.lower() for w in lexicon()["tier3"]}


def test_the_lexicon_declares_a_version():
    """PROOF.md pins its numbers to a catalogue version. Without this key the
    pin is to nothing and the table becomes archaeology."""
    assert lexicon().get("version") is not None


# --------------------------------------------------------------------------
# what counts as prose for the statistics
# --------------------------------------------------------------------------

def test_heading_text_is_not_measured_as_part_of_the_sentence_below_it():
    """A heading is a label and carries no terminal punctuation. With only the
    hashes stripped, the splitter glued the heading onto the first sentence
    below it and every section opener measured two or three words too long."""
    heads, _ = scan_text("## Background and context\n\nThe cluster was retired.\n\n"
                         "## Findings from the work\n\nThe latency improved twice.\n")
    assert heads["stats"]["avg_sentence_words"] == 4.0, heads["stats"]["avg_sentence_words"]
    assert heads["stats"]["sentence_count"] == 2, heads["stats"]["sentence_count"]


def test_heading_words_are_not_counted_as_prose_words():
    heads, _ = scan_text("## Background and context\n\nThe cluster was retired.\n\n"
                         "## Findings from the work\n\nThe latency improved twice.\n")
    assert heads["stats"]["word_count"] == 8, "got %d" % heads["stats"]["word_count"]


def test_a_block_quote_is_exempt_from_the_statistics():
    """Not just from flagging. A half-quotation document used to report the
    rhythm of whoever it was quoting as its own."""
    quoted, _ = scan_text("The cluster was retired.\n\n"
                          "> It was a long and winding road that led us here, "
                          "and we would not walk it again for anything.\n")
    assert quoted["stats"]["word_count"] == 4, "got %d" % quoted["stats"]["word_count"]


# --------------------------------------------------------------------------
# the invisible-character tables
#
# The one place in this engine where a save that normalizes whitespace, or an
# editor that drops a variation selector, changes behaviour without changing
# anything a reader can see. Worst case the U+00A0 key becomes a plain space and
# every space in every document reports as a paste artifact. Assert the
# codepoints, not the keys.
# --------------------------------------------------------------------------

def test_hidden_unicode_holds_exactly_the_thirteen_expected_codepoints():
    expected = [0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0x00A0, 0x202F,
                0x180E, 0x2061, 0x2062, 0x2063, 0x2064]
    got = sorted(ord(c) for c in scan_module().HIDDEN_UNICODE)
    assert got == sorted(expected), str(["U+%04X" % c for c in got])


def test_every_hidden_unicode_key_is_one_character():
    keys = scan_module().HIDDEN_UNICODE
    assert all(len(c) == 1 for c in keys), str([repr(c) for c in keys if len(c) != 1])


def test_space_like_unicode_is_nbsp_and_narrow_nbsp():
    scan = scan_module()
    assert sorted(ord(c) for c in scan.SPACE_LIKE_UNICODE) == [0x00A0, 0x202F]
    assert set(scan.SPACE_LIKE_UNICODE) <= set(scan.HIDDEN_UNICODE)


def test_no_plain_space_leaked_into_the_tables():
    scan = scan_module()
    assert not (set(scan.HIDDEN_UNICODE) & set(" \t\n\r")), str(sorted(scan.HIDDEN_UNICODE))


def test_the_sentence_sentinel_is_a_character_prose_cannot_contain():
    """It used to be U+2024 ONE DOT LEADER, which a writer may legitimately have
    typed, and the swap-back turned theirs into a period inside the copy being
    measured."""
    assert scan_module().SENTENCE_SENTINEL == "\x00"


def test_a_legitimate_dot_leader_survives_the_split():
    parts = scan_module().split_sentences(
        "The dial reads 1․5 in the old style. Dr. Adeyemi signed it off.")
    assert any("1․5" in s for s in parts), str(parts)
    assert len(parts) == 2 and parts[1].startswith("Dr."), str(parts)


def test_emoji_rx_still_matches_the_presentation_selector():
    scan = scan_module()
    m = scan.EMOJI_RX.search("\U0001F680\ufe0f")
    assert m and m.group(0) == "\U0001F680\ufe0f"
    assert not scan.EMOJI_RX.search("\ufe0f")



# --------------------------------------------------------------------------
# false positives the reviewers found
# --------------------------------------------------------------------------

def test_a_mismatched_quote_pair_does_not_exempt_the_span():
    stray = ('The flag is " here. A comprehensive robust seamless meticulous '
             'pivotal delve into it.” Done.\n')
    result, _ = scan_text(stray)
    assert "tier1" in set(ids(result)), str(result["findings"])


def test_a_matched_quote_pair_still_exempts_the_span():
    paired = ('He said "a comprehensive robust seamless meticulous pivotal '
              'delve into it" and left.\n')
    result, _ = scan_text(paired)
    assert "tier1" not in ids(result), str([f["match"] for f in result["findings"]])


def test_a_tier1_phrase_is_one_finding_and_not_two():
    """`delve into` is on both tier-1 lists, so it matched the phrase regex and
    the word regex and produced two P1 findings about one token. The phrase
    takes the span first now, the way facts.numbers() orders its takes."""
    result, _ = scan_text("The team will delve into the findings this week and "
                          "report back to everyone.\n")
    hits = [f for f in result["findings"] if f["id"] == "tier1"]
    assert len(hits) == 1, str([(f["label"], f["match"]) for f in hits])
    assert hits[0]["match"] == "delve into", hits[0]


def test_a_tier1_word_outside_a_phrase_is_still_caught():
    """The other direction: blanking the phrase spans must not blank the word
    pass along with them."""
    result, _ = scan_text("The team will delve deeper on the findings this week "
                          "and report back to everyone.\n")
    hits = [f for f in result["findings"] if f["id"] == "tier1"]
    assert [f["match"] for f in hits] == ["delve"], str(hits)


def test_one_non_breaking_space_is_not_a_p0():
    """Correct French typography, and a document typeset properly should not be
    told it has a credibility problem."""
    result, _ = scan_text("Une phrase\u00a0: le texte qui suit tient sur une ligne.\n")
    assert "hidden-unicode" not in ids(result), str(result["findings"])


def test_non_breaking_spaces_in_quantity_report_at_p2():
    result, _ = scan_text("a\u00a0b\u00a0c\u00a0d\u00a0e\u00a0f words to make a sentence.\n")
    hits = [f for f in result["findings"] if f["id"] == "hidden-unicode"]
    assert len(hits) == 1 and hits[0]["priority"] == "P2", str(hits)


def test_a_zero_width_space_is_still_a_p0():
    result, _ = scan_text("a\u200bb zero width here.\n")
    hits = [f for f in result["findings"] if f["id"] == "hidden-unicode"]
    assert len(hits) == 1 and hits[0]["priority"] == "P0", str(hits)


def test_the_exemption_suppresses_quoted_examples():
    scratch = tempfile.mkdtemp()
    try:
        path = written(scratch, "meta.md",
                       'A guide about AI writing.\n\n'
                       'Avoid phrases like "delve into the rich tapestry of innovation".\n\n'
                       '```\ndelve tapestry nestled showcasing\n```\n\n'
                       '> Experts believe this is a testament to progress.\n')
        with_exempt = scan_json(path)
        without = scan_json(path, "--no-exempt")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert len(with_exempt["findings"]) < len(without["findings"]), "%d vs %d" % (
        len(with_exempt["findings"]), len(without["findings"]))


# --------------------------------------------------------------------------
# the reported shape
# --------------------------------------------------------------------------

def test_json_output_carries_its_schema_and_lexicon_versions():
    """A consumer that pins the schema finds out at parse time when the shape
    moves, and a published measurement names the catalogue that produced it."""
    ai = ai_result()
    assert ai["schema_version"] >= 1
    assert ai["lexicon_version"] is not None
    assert ai["registers_version"] is not None


def test_every_finding_matches_the_schema():
    from rwlib import findings as findings_mod
    problems = findings_mod.validate(ai_result()["findings"])
    assert not problems, str(problems)


# --------------------------------------------------------------------------
# regressions from the review pass
# --------------------------------------------------------------------------

def test_a_citation_marker_inside_a_code_span_is_still_a_p0():
    """The exemption is about content. A chat citation marker is evidence about
    how the file was produced, and a pasted transcript lands in a block quote or
    a fence more often than in running prose, which is where the exemption used
    to hide it."""
    for wrapper in ("> quoting: %s here",
                    "`%s`",
                    "```\n%s\n```",
                    "| a | %s |"):
        text = "# T\n\n" + (wrapper % "citeturn0search0") + "\n"
        found = ids(scan_text(text)[0], "P0")
        assert "citation-leak" in found, "%r produced %s" % (wrapper, found)


def test_a_markdown_link_label_is_not_an_unfilled_placeholder():
    """`[Your name here](https://...)` is a sponsor slot somebody filled in, and
    `[Address book]` is not a placeholder at all. Three trending READMEs in the
    corpus were failed by the version of this pattern that thought otherwise."""
    clean = "# T\n\nSee [Your name here](https://x.example) and [Address book](#ab).\n"
    assert "placeholder" not in ids(scan_text(clean)[0])
    dirty = "# T\n\nContact [Your Name] before shipping this.\n"
    assert "placeholder" in ids(scan_text(dirty)[0], "P0")


def test_a_joiner_inside_an_emoji_is_not_a_paste_artifact():
    """U+1F468 U+200D U+1F4BB is one glyph. Reporting the joiner calls an
    ordinary README a paste artifact, and deleting it turns one emoji into two."""
    emoji = "# T\n\nWritten by humans \U0001F468\u200d\U0001F4BB. Nothing pasted.\n"
    assert "hidden-unicode" not in ids(scan_text(emoji)[0])
    between_letters = "# T\n\nThis wo\u200drd came out of a chat window.\n"
    assert "hidden-unicode" in ids(scan_text(between_letters)[0], "P0")


def test_ordinary_prose_does_not_trip_the_formulaic_challenges_rule():
    """The formula is the pairing, which false-concession owns. Each half on its
    own is a sentence anybody writes."""
    text = ("# T\n\nDespite these challenges, we shipped late.\n\n"
            "The team continues to thrive under pressure.\n")
    assert "formulaic-challenges" not in ids(scan_text(text)[0])


def test_the_full_false_concession_formula_is_still_caught():
    text = ("# T\n\nDespite these challenges, the sector continues to thrive "
            "in every market it enters.\n")
    assert "false-concession" in ids(scan_text(text)[0])


def test_an_empty_vocabulary_list_compiles_to_a_regex_that_matches_nothing():
    """An empty alternation is `()`, which matches at every position. Two
    callers do not filter zero-length matches, so an edited lexicon with an
    empty tier would have reported a cluster in every paragraph."""
    from rwlib import lexicon as lexicon_mod
    for build in (lexicon_mod.word_regex, lexicon_mod.phrase_regex):
        rx = build([])
        assert not rx.findall("hello world. Anything at all here!"), build.__name__
        assert not rx.search(""), build.__name__


def test_every_synthetic_finding_declares_a_priority():
    """A new synthetic id added without one makes the p0-only check in
    registers.problems silently stop covering it."""
    from rwlib import lexicon as lexicon_mod
    missing = set(lexicon_mod.SYNTHETIC_FINDING_IDS) - set(lexicon_mod.SYNTHETIC_PRIORITIES)
    assert not missing, sorted(missing)
    extra = set(lexicon_mod.SYNTHETIC_PRIORITIES) - set(lexicon_mod.SYNTHETIC_FINDING_IDS)
    assert not extra, sorted(extra)


def test_an_undeclared_synthetic_priority_raises_rather_than_defaulting():
    """The lookup is loud. A default is how the table and the engine drifted
    apart before: the miss showed up months later as a register tolerance
    nobody was honouring, rather than at the call site."""
    from rwlib import lexicon as lexicon_mod
    try:
        lexicon_mod.synthetic_priority("no-such-finding")
    except KeyError as exc:
        assert "SYNTHETIC_PRIORITIES" in str(exc), str(exc)
    else:
        raise AssertionError("an undeclared id came back with a priority")


def test_scan_raises_each_synthetic_finding_at_its_declared_priority():
    """The half the set-equality test above cannot reach.

    Every priority in the table is now read by scan.py at the call site, so this
    holds by construction, and that is exactly why it is worth pinning: the next
    person to write `"P1"` inline instead of SYNTH(...) reintroduces the drift
    silently. The document below is built to trip as many of them at once as one
    document can. Anything it does not reach is asserted against the table by
    the ceiling rule instead: nothing may be raised at a priority the table does
    not declare.
    """
    from rwlib import lexicon as lexicon_mod
    declared = lexicon_mod.SYNTHETIC_PRIORITIES
    # Metronomic on purpose: even sentences, a reused trigram, one flat
    # paragraph shape, and a zero-width space. That is uniformity,
    # trigram-repetition, uniform-paragraphs, hidden-unicode and the vocabulary
    # tiers in one file.
    beat = ("We must leverage the platform to deliver the outcome — quickly. "
            "We utilize the innovative platform to deliver the value — daily. ")
    doc = "\n\n".join([beat * 3] * 6) + "\n\nA delve into the​tapestry.\n"
    result, _ = scan_text(doc)
    seen = {}
    for finding in result["findings"]:
        if finding["id"] in declared:
            seen.setdefault(finding["id"], set()).add(finding["priority"])
    # Pinned, not just non-empty. Without this the ceiling rule below passes
    # vacuously the day the fixture stops tripping anything.
    assert set(seen) >= {"hidden-unicode", "tier1", "clarity", "tier2-cluster",
                         "tier3-density", "uniformity", "low-diversity",
                         "trigram-repetition", "em-dash-rate"}, sorted(seen)
    # "P0" sorts before "P2" and is the *more* severe of the two, so the ceiling
    # test reads backwards: a raised priority may be no smaller than the
    # declared worst case.
    for finding_id, priorities in sorted(seen.items()):
        for priority in priorities:
            assert priority >= declared[finding_id], (
                "%s raised at %s, worse than the %s the table declares"
                % (finding_id, priority, declared[finding_id]))


def test_a_catalogue_entry_missing_a_key_is_dropped_rather_than_crashing():
    """`rx` but no `id` used to compile fine here and then raise KeyError out of
    scan.py's `relax.get(p["id"])`, which is the whole-scan outage the guard was
    written to prevent, moved one file along. Every key scan.py reads has to be
    present before the entry is handed over."""
    import json
    import shutil
    import tempfile

    from rwlib import lexicon as lexicon_mod

    good = lexicon_mod.load()
    data = json.loads(json.dumps(good))
    before = len(lexicon_mod.compiled_patterns())
    data["patterns"].append({"label": "no id", "band": "craft",
                             "priority": "P2", "rx": "zzzz"})
    data["patterns"].append({"id": "no-label", "band": "craft",
                             "priority": "P2", "rx": "qqqq"})
    data["patterns"].append({"id": "no-rx", "label": "x", "band": "craft",
                             "priority": "P2"})
    scratch = tempfile.mkdtemp()
    try:
        path = os.path.join(scratch, "lexicon.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        lexicon_mod._CACHE.pop(path, None)
        entries = lexicon_mod.compiled_patterns(path=path)
        assert len(entries) == before, "%d vs %d" % (len(entries), before)
        for entry, _ in entries:
            for key in lexicon_mod.REQUIRED_PATTERN_KEYS:
                assert entry.get(key), (entry.get("id"), key)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_a_register_that_skips_hidden_unicode_is_honoured():
    """Every other finding the engine raises itself is gated on the skip set.
    This one ran before anything read it, so a cell naming it in registers.json
    would have been a silent no-op that read in the rendered matrix as a
    tolerance somebody was honouring."""
    import scan as scan_mod

    # Escape, never a literal: a normalizing save turns a literal joiner
    # into nothing at all and deletes the check without changing a
    # visible character. See rwlib/artifacts.py.
    text = "# T\n\nA wo\u200drd out of a chat window.\n"
    assert "hidden-unicode" in {f["id"] for f in scan_mod.scan(text)[0]}
    real = scan_mod.PROFILE_SKIP.get("blog", set())
    scan_mod.PROFILE_SKIP["blog"] = set(real) | {"hidden-unicode"}
    try:
        quiet = {f["id"] for f in scan_mod.scan(text)[0]}
    finally:
        scan_mod.PROFILE_SKIP["blog"] = real
    assert "hidden-unicode" not in quiet, quiet


def test_a_wrapped_bullet_list_is_a_list_and_not_one_long_paragraph():
    """The parked false positive, actioned. A list whose items wrap over several
    lines each drives the bullet share below half, so the ratio rule alone read
    it as a paragraph and the voice cap fired on it. `CHANGELOG.md` reported
    five of these and every one was a bullet list."""
    from rwlib.markdown import is_prose_block
    wrapped = ("- The first item runs on for long enough that it wraps\n"
               "  across two more lines before it finishes saying what it\n"
               "  came to say about the change.\n"
               "- The second item does exactly the same thing, at exactly\n"
               "  the same length, because that is what a changelog entry\n"
               "  looks like when somebody writes a real one.\n")
    assert not is_prose_block(wrapped)


def test_a_paragraph_with_a_short_list_under_it_is_still_a_paragraph():
    """The other half of the rule, unchanged. A lead-in sentence plus one or two
    bullets is a paragraph with a list under it, and reading it as a list is the
    mirror-image false negative."""
    from rwlib.markdown import is_prose_block
    mixed = ("There are two ways to do this, and the second is usually right.\n"
             "The first costs less and the second is easier to undo later.\n"
             "- do it the first way\n")
    assert is_prose_block(mixed)


def test_a_lead_in_followed_by_many_bullets_is_a_list():
    from rwlib.markdown import is_prose_block
    mixed = "A lead-in sentence.\n" + "".join("- item %d\n" % i for i in range(8))
    assert not is_prose_block(mixed)


def test_vague_attribution_stands_down_when_a_citation_follows():
    """`studies show` with a source named after it is an attribution rather than
    a vague one. The lookahead is scoped to the sentence and not to a character
    window, because over the 19-paper academic corpus the citation marker sits
    55 to 170 characters past the phrase and never inside 40. Both marker shapes
    are covered, since the plugin ships numeric and author-year citation styles.
    """
    import scan as scan_mod
    cases = [
        # (text, should the finding fire)
        ("Studies show that engagement improves outcomes.", True),
        ("Experts believe it plays a crucial role in the result.", True),
        ("Research suggests adoption doubled (Q1 2024 data) last year.", True),
        ("Studies show that engagement improves outcomes. See [12].", True),
        ("Studies show a correlation between attendance and health [22,41].", False),
        ("Research suggests designing programmes around coaches [16,83].", False),
        ("Studies show that engagement improves outcomes (Smith, 2020).", False),
        ("Studies show that engagement improves outcomes (Smith and Jones 2020).", False),
        ("Studies show that engagement improves outcomes (Smith et al., 2020).", False),
    ]
    for text, should_fire in cases:
        ids = {f["id"] for f in scan_mod.scan(text)[0]}
        fired = "vague-attribution" in ids
        assert fired == should_fire, "%r fired=%s" % (text, fired)


def test_vague_attribution_still_reports_the_uncited_papers_in_the_corpus():
    """The narrowing is a narrowing and not a mute. The corpus texts are
    gitignored, so this pins the committed measurement they produced: three of
    the nineteen papers use one of these phrases with no citation in the
    sentence, and those three are still a P0 in every register. No existence
    guard, deliberately. `summary.json` is committed beside these tests and a
    test that skips itself when its evidence goes missing reads exactly like one
    that passes."""
    import json
    import os
    summary = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))),
        "docs", "academic-corpus", "summary.json")
    data = json.load(open(summary, encoding="utf-8"))
    for register, findings in data["registers"].items():
        cell = findings.get("vague-attribution")
        assert cell, "no vague-attribution row for %s" % register
        assert cell["docs"] == 3, "%s: %d docs" % (register, cell["docs"])
        assert cell["hits"] == 4, "%s: %d hits" % (register, cell["hits"])


# --------------------------------------------------------------------------
# the load-bearing carve-out and the Claude-vocabulary tier-2 additions
#
# The word arrived from outside: it is the top-lift mark of the Claude
# PR-description corpus (louisabraham/load-bearing, lift 123 over 85 weeks),
# and the carve-out documented in patterns.md section 12 is enforced by the
# `load-bearing` catalogue pattern. quietly, seam, seams, and survived joined
# tier 2 from the same corpus, each cluster-gated at two hits per paragraph.


def test_load_bearing_fires_on_the_metaphor_and_not_the_wall():
    """The negative lookahead stands the rule down before exactly the four
    structural nouns patterns.md names, plurals included, and nowhere else.
    Predicate position still fires ("the beam is load-bearing"), because the
    documented rule carves out the attributive position only and the corpus
    showed no literal predicate use in a hundred real READMEs. A hyphen-
    compound like `missing-load-bearing` sits behind a hyphen, which the word
    boundary already excludes."""
    scan = scan_module()
    cases = [
        # (text, should the finding fire)
        ("The load-bearing comment in this module is the cache guard.", True),
        ("Surface load-bearing assumptions before writing the plan.", True),
        ("The load-bearing structure of his argument is the second premise.", True),
        ("Remove the load-bearing wall before renovating.", False),
        ("The beam is load-bearing, so the joist spacing stays.", True),
        ("Load-bearing beams and load-bearing joists carry the roof.", False),
        ("A load-bearing girder spans the room.", False),
        ("The missing-load-bearing criterion stays in criteria.md.", False),
    ]
    for text, should_fire in cases:
        found = {f["id"] for f in scan.scan(text)[0]}
        fired = "load-bearing" in found
        assert fired == should_fire, "%r fired=%s" % (text, fired)


def test_claude_vocabulary_calibration_over_the_100_readme_corpus():
    """The calibration the repo demands before wiring any detector, pinned:
    across the 100 real READMEs the carve-out pattern fires exactly once (the
    phuryn__pm-skills README, "surface load-bearing assumptions" in a list of
    Claude-skill descriptions, reviewed as a true hit), the four tier-2
    additions tip exactly one new cluster (headroomlabs-ai__headroom, "seam"
    twice in one list block), and neither id reaches P0 on any document. No
    existence guard, deliberately: a calibration test that skips itself when
    its corpus goes missing reads exactly like one that passes."""
    import glob
    scan = scan_module()
    corpus = sorted(glob.glob(os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))),
        "docs", "readme-analysis", "repos", "*", "README.md")))
    assert len(corpus) == 100, "expected the 100-README corpus, found %d" % len(corpus)
    new_words = ("quietly", "seam", "seams", "survived")
    lb_docs, cluster_docs, p0_new = [], [], 0
    for path in corpus:
        slug = os.path.basename(os.path.dirname(path))
        with open(path, encoding="utf-8", errors="replace") as fh:
            findings = scan.scan(fh.read(), ste="off")[0]
        for finding in findings:
            if finding["id"] == "load-bearing":
                lb_docs.append(slug)
                assert finding["priority"] == "P1", finding
            if finding["id"] in ("load-bearing", "tier2-cluster") \
                    and finding["priority"] == "P0":
                p0_new += 1
            if finding["id"] == "tier2-cluster":
                matched = [w.strip() for w in finding["match"].split(",")]
                if any(w in new_words for w in matched):
                    cluster_docs.append(slug)
    assert lb_docs == ["phuryn__pm-skills"], lb_docs
    assert cluster_docs == ["headroomlabs-ai__headroom"], cluster_docs
    assert p0_new == 0, "the new ids must never reach P0 on a stranger's document"
