#!/usr/bin/env python3
"""
map_structure.py: the heading grammar, TOC exclusion, batches, and exits.

Every document is synthetic so a grammar case is one repeatable unit rather
than one chapter of a real book that happens to be handy. Line numbers in the
expected tuples are 1-based and counted by hand from the fixture, so a start
moving by one line is a failure and not a rounding story.
"""

import json
import os
import shutil
import tempfile

from helpers import (BOOK_TYPES, MAP_STRUCTURE, env_with_pythonpath,
                     make_book_type_tree, run, run_env, script_path)

# The arxiv row needs the arxiv-paper reference file, whose name is also the
# grammar key inside map_structure.py (a file named anything else would select
# the generic grammar and find no numbered headings). Shipped file when
# present, otherwise a temp skill-shaped tree carrying our own minimal
# arxiv-paper.md, because --book-type choices are enumerated from that
# directory and an absent file is not a selectable choice anywhere.
ARXIV_TYPE = "arxiv-paper"

ARXIV_FALLBACK = """# arxiv-paper

**Kind markers:** claim, method
**Length band:** 30-60
**Template sections:** Claim, Method, Evidence, Tests, See also
**Source line:** Source: <paper>, <locator> (<kind>)

## What counts

A numbered section of a paper.

## Segmentation

Headings are the numbered forms: a top-level section as "1 Intro" and a
subsection as "2.1 Method", plus the unnumbered Abstract at the top.

## Concept grain

One claim or method per note.

## Template

```
# Title

Source: <paper>, <locator> (<kind>)

## Claim
## Method
## Evidence
## Tests
## See also
```

## Kind markers

claim and method.

## Fan-out

One note per numbered subsection.
"""

_ARXIV_LAUNCH = {}


def arxiv_launch():
    """A memoized (launch, cleanup_path) pair for runs naming arxiv-paper.

    Memoized because building the temp tree per call would copy the scripts
    once per table row, and the tree has to live as long as the launch does.
    """
    if "launch" in _ARXIV_LAUNCH:
        return _ARXIV_LAUNCH["launch"], _ARXIV_LAUNCH.get("cleanup")
    mapper = script_path("map_structure.py")
    if os.path.isfile(os.path.join(BOOK_TYPES, ARXIV_TYPE + ".md")):
        def launch(argv, cwd=None):
            return run([mapper] + argv, cwd=cwd)
        _ARXIV_LAUNCH["launch"] = launch
        _ARXIV_LAUNCH["cleanup"] = None
        return launch, None
    tree = make_book_type_tree({ARXIV_TYPE + ".md": ARXIV_FALLBACK})
    copied = os.path.join(tree, "scripts", "map_structure.py")

    def launch(argv, cwd=None):
        return run_env([copied] + argv, cwd=cwd, env=env_with_pythonpath())
    _ARXIV_LAUNCH["launch"] = launch
    _ARXIV_LAUNCH["cleanup"] = tree
    return launch, tree


def body(prefix, count):
    return ["%s body line %d." % (prefix, i) for i in range(1, count + 1)]


def write_doc(lines):
    scratch = tempfile.mkdtemp(prefix="rr-map-")
    path = os.path.join(scratch, "book.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return path, scratch


def json_run(lines, args=(), launch=None):
    path, scratch = write_doc(lines)
    try:
        if launch is None:
            rc, out, err = run([script_path("map_structure.py"), path, "--json"]
                               + list(args))
        else:
            rc, out, err = launch([path, "--json"] + list(args))
        assert rc == 0, "map_structure exited %d: %s" % (rc, err[:400])
        return json.loads(out)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def triples(payload):
    return [(s["title"], s["kind"], s["start"]) for s in payload["sections"]]


def batch_size(batch):
    """The material one batch covers, whichever shape the payload uses."""
    if "start" in batch and "end" in batch:
        return batch["end"] - batch["start"] + 1
    lines = batch.get("lines")
    if isinstance(lines, int):
        return lines
    return len(batch.get("sections", []))


# --------------------------------------------------------------------------
# the grammar table
# --------------------------------------------------------------------------

def test_heading_grammar_table():
    launch = None
    cleanup = None
    try:
        # Each row is (extra args, lines, expected [(title, kind, start)]).
        # Leading prose is kept off every row except where a blank line is
        # part of what is being tested, so an untitled preamble does not
        # turn into a phantom section nobody asked about.
        cases = [
            ([],
             ["Chapter 1. Opening Moves"] + body("First", 12)
             + ["", "Chapter 2: The Middle"] + body("Second", 12),
             [("Chapter 1. Opening Moves", "chapter", 1),
              ("Chapter 2: The Middle", "chapter", 15)]),

            (["--min-lines", "4"],
             # The bare-number grammar wants a blank before the heading and
             # a block at least --min-lines long, and this row supplies both.
             ["Plain prose before any heading appears here.",
              "",
              "3. The Third Practice"] + body("Third", 6),
             [("Preamble", "preamble", 1),
              ("3. The Third Practice", "chapter", 3)]),

            ([],
             ["Chapter 1. One"] + body("One", 12)
             + ["", "Part II"] + body("Two", 12),
             [("Chapter 1. One", "chapter", 1),
              ("Part II", "part", 15)]),

            ([],
             ["Preface"] + body("Pre", 12)
             + ["", "Chapter 1. Beginnings"] + body("Begin", 12),
             [("Preface", "front", 1),
              ("Chapter 1. Beginnings", "chapter", 15)]),

            ([],
             ["Chapter 1. Body"] + body("Body", 12)
             + ["", "Glossary"] + body("Gloss", 8)
             + ["", "Index"] + body("Index", 8),
             [("Chapter 1. Body", "chapter", 1),
              ("Glossary", "back", 15),
              ("Index", "back", 25)]),

            (["--book-type", ARXIV_TYPE],
             # Under the arxiv grammar a top-level number is a chapter and
             # only a dotted subsection is a section, so "1 Intro" maps as
             # the chapter that "2.1 Method" sits inside.
             ["1 Intro"] + body("Intro", 8)
             + ["2.1 Method"] + body("Method", 8),
             [("1 Intro", "chapter", 1),
              ("2.1 Method", "section", 10)]),
        ]
        for args, lines, expected in cases:
            if "--book-type" in args:
                if launch is None:
                    launch, cleanup = arxiv_launch()
                payload = json_run(lines, args, launch=launch)
            else:
                payload = json_run(lines, args)
            got = triples(payload)
            assert got == expected, "args %r: %r != %r" % (args, got, expected)
    finally:
        if cleanup:
            shutil.rmtree(cleanup, ignore_errors=True)
            _ARXIV_LAUNCH.clear()


def test_preamble_before_first_heading_is_mapped_as_section():
    lines = (["This is an untitled preamble before the book starts.",
              "It contains important framing prose for the whole work.",
              "",
              "Chapter 1. Opening Moves"]
             + body("First", 12))
    payload = json_run(lines)
    got = triples(payload)
    assert got[0] == ("Preamble", "preamble", 1)
    assert got[1] == ("Chapter 1. Opening Moves", "chapter", 4)
    assert payload["sections"][0]["end"] == 3


def test_available_types_includes_all_grammars():
    import sys
    sys.modules.pop("_bootstrap", None)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
    import map_structure
    types = map_structure.available_types()
    for key in map_structure.GRAMMARS:
        assert key in types, "%s missing from available_types: %r" % (key, types)


# --------------------------------------------------------------------------
# TOC exclusion and near misses
# --------------------------------------------------------------------------

def test_a_toc_block_is_detected_and_excluded_from_the_body_map():
    lines = (["The Book Title",
              "",
              "Chapter 1. Opening Moves  3",
              "Chapter 2: The Middle  21",
              "Glossary  40",
              "Index  44",
              "Bibliography  45",
              "",
              "Chapter 1. Opening Moves"]
             + body("First", 12))
    payload = json_run(lines)
    assert payload["toc"], "a 5-line page-numbered run went undetected as a toc"
    starts = [s["start"] for s in payload["sections"]]
    titles = [s["title"] for s in payload["sections"]]
    assert min(starts) >= 9, "body map starts inside the toc block: %r" % starts
    assert "Chapter 1. Opening Moves  3" not in titles, titles
    assert "Chapter 1. Opening Moves" in titles, titles


def test_prose_ending_in_small_numbers_is_not_mistaken_for_a_toc():
    # Regression: PAGE_TAIL_RX used to accept a single plain space before the
    # trailing number, the same shape an ordinary sentence has, so five such
    # sentences in a row misdetected as a table of contents.
    lines = (["The introduction opens with only 1",
              "the next line closes with just 2",
              "then continues on to reach 3",
              "and settles finally near 4",
              "before wrapping up around 5",
              "",
              "Chapter 1. Real Start"]
             + body("First", 12))
    payload = json_run(lines)
    assert payload["toc"] is None, (
        "single-space prose misdetected as a toc: %r" % payload["toc"])


def test_a_numbered_list_inside_body_prose_is_not_a_chapter():
    lines = (["Chapter 1. Lists",
              "An intro sentence.",
              "",
              "1. First item",
              "2. Second item",
              "",
              "A closing line."]
             + body("Tail", 6))
    payload = json_run(lines, ["--min-lines", "4"])
    got = triples(payload)
    # The two-item list block is shorter than --min-lines, so only the real
    # chapter maps. A list that promoted itself would appear as a chapter
    # titled "1. First item".
    assert got == [("Chapter 1. Lists", "chapter", 1)], got


def test_an_ill_formed_roman_looking_word_is_not_a_part():
    # Regression: roman_value() used to sum any string built from
    # {I,V,X,L,C,D,M}, so a play-script cue or a lettered marker that happens
    # to spell out of those letters (e.g. "DIM") false-positived as a book
    # Part with no span evidence required. A well-formed numeral like "IV"
    # or "II" still has to work, which test_heading_grammar_table covers.
    lines = (["Chapter 1. Scenes"] + body("First", 12)
             + ["", "DIM. Lights fade to black."]
             + body("Second", 12))
    payload = json_run(lines)
    got = triples(payload)
    assert got == [("Chapter 1. Scenes", "chapter", 1)], got


def test_fiction_book_type_disables_bare_numbered_chapters():
    # Regression: GRAMMARS used to key this grammar "novel" while the shipped
    # reference file is fiction.md, so --book-type fiction (the only valid
    # choice, per available_types()) silently fell back to DEFAULT_FEATURES
    # (numbered: True) instead of the fiction grammar, which turns bare
    # numbered chapters off so a numbered list in narrative prose cannot
    # false-positive as a chapter boundary.
    lines = (["Chapter 1. Opening"] + body("First", 12)
             + ["", "5. A list item in the text, not a chapter."]
             + body("Second", 12))
    payload = json_run(lines, ["--book-type", "fiction"])
    got = triples(payload)
    assert got == [("Chapter 1. Opening", "chapter", 1)], got


# --------------------------------------------------------------------------
# extents and batches
# --------------------------------------------------------------------------

def test_section_end_is_next_start_minus_one():
    lines = (["Chapter 1. Opening Moves"] + body("First", 12)
             + ["", "Chapter 2: The Middle"] + body("Second", 12))
    payload = json_run(lines)
    sections = payload["sections"]
    assert len(sections) == 2, sections
    assert sections[0]["end"] == sections[1]["start"] - 1, sections
    total = payload["lines"]
    if isinstance(total, list):
        total = len(total)
    assert sections[-1]["end"] == total, (sections, total)


def test_batches_split_the_material_roughly_evenly():
    lines = []
    for number in range(1, 7):
        lines.append("Chapter %d. Unit %d" % (number, number))
        lines.extend(body("Unit%d" % number, 8))
    payload = json_run(lines, ["--batches", "3"])
    batches = payload["batches"]
    assert len(batches) == 3, batches
    sizes = [batch_size(b) for b in batches]
    assert all(size > 0 for size in sizes), sizes
    assert max(sizes) < 2 * min(sizes), sizes


# --------------------------------------------------------------------------
# exits and output shapes
# --------------------------------------------------------------------------

def test_a_document_with_no_headings_exits_1():
    path, scratch = write_doc(body("Plain", 10))
    try:
        rc, out, err = run([script_path("map_structure.py"), path])
        assert rc == 1, "nothing recognized must exit 1, got %d" % rc
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_json_section_count_equals_the_markdown_row_count():
    lines = (["Chapter 1. Opening Moves"] + body("First", 12)
             + ["", "Chapter 2: The Middle"] + body("Second", 12))
    path, scratch = write_doc(lines)
    try:
        mapper = script_path("map_structure.py")
        rc, out, err = run([mapper, path, "--json"])
        assert rc == 0, err
        payload = json.loads(out)
        rc2, plain, err2 = run([mapper, path])
        assert rc2 == 0, err2
        rows = [line for line in plain.splitlines()
                if line.lstrip().startswith("|")]
        assert rows, "the markdown render has no table rows:\n%s" % plain[:400]
        if set(rows[1].strip()) <= set("|:- "):
            rows = rows[2:]
        assert len(rows) == len(payload["sections"]), (
            "markdown rows %d vs json sections %d\n%s"
            % (len(rows), len(payload["sections"]), plain[:400]))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# --------------------------------------------------------------------------
# markdown headings: ATX, fences, setext
# --------------------------------------------------------------------------

def test_markdown_atx_headings_map_to_sections():
    lines = ["# A", "", "text", "", "## B", "", "body", "", "## C"]
    payload = json_run(lines)
    assert triples(payload) == [("A", "chapter", 1),
                                ("B", "section", 5),
                                ("C", "section", 9)], triples(payload)


def test_an_atx_heading_inside_a_fence_is_not_a_heading():
    lines = (["Chapter 1. Opening"] + body("First", 12)
             + ["```python", "## not a heading", "print('x')", "```"]
             + body("Second", 12))
    payload = json_run(lines)
    got = triples(payload)
    assert all("not a heading" != t for t, _, _ in got), got


def test_a_setext_pair_maps_as_its_underline_kind():
    lines = ["Title One", "=========", "", "body under one.", "",
             "Title Two", "---------", "", "body under two."]
    payload = json_run(lines)
    got = triples(payload)
    assert ("Title One", "chapter", 1) in got, got
    assert ("Title Two", "section", 6) in got, got


def test_batch_columns_sum_to_the_document_counts():
    lines = (["Chapter 1. Opening Moves"] + body("First", 12)
             + ["Chapter 2. Middle Moves"] + body("Second", 12)
             + ["Chapter 3. Closing Moves"] + body("Third", 12))
    payload = json_run(lines, args=["--batches", "2"])
    batches = payload["batches"]
    doc_words = sum(len(l.split()) for l in lines)
    assert sum(b["words"] for b in batches) == doc_words
    from rwlib.endpoint import estimate_tokens
    doc_tokens = estimate_tokens("\n".join(lines))
    # Each batch estimates over its own slice; the whole-document estimate
    # sits between the largest batch and their sum plus per-batch slack.
    assert all(b["tokens"] > 0 for b in batches)
    assert max(b["tokens"] for b in batches) <= doc_tokens
