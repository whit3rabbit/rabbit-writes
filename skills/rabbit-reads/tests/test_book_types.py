#!/usr/bin/env python3
"""
references/book-types/*.md: the shipped specs parse and carry their parts.

These files are the data three tools share, so a malformed one is not a style
problem: check_notes.py loads its battery from the same header lines these
tests parse. When the directory is absent the tests fail naming it rather
than passing over an empty glob, because the files are being authored beside
this suite and a vacuous pass would hide the gap.
"""

import os

from helpers import BOOK_TYPES, parse_book_type

REQUIRED_HEADINGS = (
    "What counts",
    "Segmentation",
    "Concept grain",
    "Template",
    "Kind markers",
    "Fan-out",
)


def shipped_book_types():
    """Sorted .md names in the shipped directory, or a failure naming it."""
    assert os.path.isdir(BOOK_TYPES), (
        "references/book-types does not exist at %s, so the shipped "
        "book-type files are missing. They are being authored beside these "
        "tests and must land before this suite can pass." % BOOK_TYPES)
    names = sorted(name for name in os.listdir(BOOK_TYPES)
                   if name.endswith(".md"))
    assert names, (
        "references/book-types at %s holds no .md files" % BOOK_TYPES)
    return names


def read_book_type(name):
    with open(os.path.join(BOOK_TYPES, name), encoding="utf-8") as fh:
        return fh.read()


def template_fence(text):
    """The first fenced block under ## Template, or the empty string.

    The first block only: the fence is the one place a section name can be
    declared, so a second fence holding the rest would already be a drift
    these tests should surface rather than paper over. Inside the fence a
    `## Section` line is content, not a heading, so only the closing fence
    ends the block.
    """
    lines = text.splitlines()
    collected = []
    in_template = False
    in_fence = False
    for line in lines:
        if in_fence:
            if line.strip().startswith("```"):
                return "\n".join(collected)
            collected.append(line)
            continue
        if line.startswith("## "):
            if in_template:
                break
            in_template = (line[3:].strip() == "Template")
            continue
        if in_template and line.strip().startswith("```"):
            in_fence = True
    return "\n".join(collected)


def test_every_shipped_book_type_parses():
    problems = []
    for name in shipped_book_types():
        spec = parse_book_type(read_book_type(name))
        if not spec["kind_markers"]:
            problems.append("%s declares no kind markers" % name)
        if spec["band"] is None:
            problems.append("%s declares no length band, or not as lo-hi "
                            "integers" % name)
        elif spec["band"][0] > spec["band"][1]:
            problems.append("%s has an inverted band %r" % (name,
                                                            spec["band"]))
        if not spec["sections"]:
            problems.append("%s declares no template sections" % name)
    assert not problems, "\n".join(problems)


def test_every_template_section_is_declared_inside_the_template_fence():
    problems = []
    for name in shipped_book_types():
        text = read_book_type(name)
        spec = parse_book_type(text)
        fence = template_fence(text)
        if not fence:
            problems.append("%s carries no fenced block under ## Template"
                            % name)
            continue
        for section in spec["sections"]:
            if section not in fence:
                problems.append(
                    "%s declares section %r in its header but not inside "
                    "the ## Template fence" % (name, section))
    assert not problems, "\n".join(problems)


def test_every_book_type_carries_the_six_required_headings():
    problems = []
    for name in shipped_book_types():
        lines = read_book_type(name).splitlines()
        for heading in REQUIRED_HEADINGS:
            if ("## " + heading) not in lines:
                problems.append("%s is missing the ## %s heading"
                                % (name, heading))
    assert not problems, "\n".join(problems)
