#!/usr/bin/env python3
"""
Property tests for the invariant everything else assumes.

Half this engine reports a line number taken from a copy of the document with
some spans blanked out. That only works because blanking preserves length, and
until this file existed that fact was asserted in comments in six places and
checked nowhere. Every violation was found the same way: somebody wrote a
finding, pointed at a line, and the line was wrong.

So these are properties rather than examples. A generator builds markdown out of
the fragments that have actually caused trouble (nested badge links, unclosed
fences, mismatched quote pairs, tables with no closing pipe, URLs inside inline
code) and the assertions hold over all of it:

    len(blank(t)) == len(t)                for every blanking function
    line numbers survive the blanking
    strip_wrapped_urls is idempotent
    apply_exemptions is idempotent
    a fix never lands inside a protected span
    fixes.apply output passes verify.py

Seeded, so a failure is reproducible: the seed is printed with the failure and
`python3 tests/test_invariants.py --seed N` replays it. hypothesis would be
better and is not stdlib, and everything else in this repo runs with no
dependencies.

Run: python3 tests/test_invariants.py
"""

import importlib.util
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from rwlib import fixes, markdown as md  # noqa: E402

CASES = 400

# Fragments chosen because each one has broken something. A generator that only
# produces well-formed markdown tests the case nobody was ever going to get
# wrong.
FRAGMENTS = [
    "# A heading",
    "## Another heading with trailing space   ",
    "Plain prose that runs on for a little while and then stops.",
    "A sentence with an em dash — right here.",
    "A range written properly, 2010–2023, which is not a splice.",
    "`inline code with https://example.com/x in it`",
    "```python\nx = 1  # delve\n```",
    "```\nunclosed fence, no terminator",
    "| a | b |\n| - | - |\n| 1 | 2 |",
    "|  ragged table row with no closing pipe",
    "> a block quote that says something",
    '"a properly closed quotation of at least four characters"',
    'a stray " quote mark with no partner anywhere near it',
    '“a curly pair that closes with its own kind”',
    "[![PyPI](https://img.shields.io/pypi/v/w.svg)](https://pypi.org/project/w/)",
    "[a link](https://example.com/page?utm_source=chatgpt.com)",
    "<p align=\"center\"><img src=\"https://acme.example/logo.png\"></p>",
    "See https://example.com/bare/url now.",
    "[ref link][label]\n\n[label]: https://example.com/target",
    "- **Term** — a definition after a typography dash",
    "1. numbered\n2. list\n3. items",
    "---\ntitle: frontmatter\n---",
    "text with a zero\u200bwidth space",
    "text with a non\u00a0breaking\u00a0space\u00a0or\u00a0four\u00a0here",
    "## Leverage the platform, in a heading",
    "# A heading with a zero\u200bwidth space in it",
    "a -- typed dash between words",
    "an entity dash &mdash; right here, and a range 2010&ndash;2023",
    "Ampersands &amp; spaces&nbsp;and &#39;quotes&#39; and a bare & alone;",
    "we should leverage the platform",
    "matrix[i][j] and matrix[row][col] outside a code span",
    "<details>\n<summary>hidden</summary>\nbody\n</details>",
    "<table>\n<tr><td>unclosed sponsor grid",
    "",
]

BLANKERS = [
    ("apply_exemptions", md.apply_exemptions),
    ("strip_images", md.strip_images),
    ("strip_wrapped_urls", md.strip_wrapped_urls),
    ("blank_entities", md.blank_entities),
    ("blank FENCE_RX", lambda t: md.blank_all(t, md.FENCE_RX)),
    ("blank INLINE_CODE_RX", lambda t: md.blank_all(t, md.INLINE_CODE_RX)),
    ("blank TABLE_ROW_RX", lambda t: md.blank_all(t, md.TABLE_ROW_RX)),
    ("blank QUOTED_RX", lambda t: md.blank_all(t, md.QUOTED_RX)),
    ("blank HEADING_RX", lambda t: md.blank_all(t, md.HEADING_RX)),
    ("blank LINK_RX", lambda t: md.blank_all(t, md.LINK_RX)),
]

failures = []


def fail(name, seed, detail):
    print("  FAIL  %s  (seed %d)  %s" % (name, seed, detail))
    failures.append(name)


def document(rng):
    n = rng.randint(1, 9)
    return "\n\n".join(rng.choice(FRAGMENTS) for _ in range(n)) + "\n"


def newline_positions(text):
    return [i for i, c in enumerate(text) if c == "\n"]


def check_lengths(seed, text):
    """Blanking preserves length and newline positions, so an offset taken from
    the blanked copy still points at the same character of the original."""
    ok = True
    for name, fn in BLANKERS:
        out = fn(text)
        if len(out) != len(text):
            fail("%s preserves length" % name, seed,
                 "%d -> %d on %r" % (len(text), len(out), text[:70]))
            ok = False
            continue
        if newline_positions(out) != newline_positions(text):
            fail("%s preserves line breaks" % name, seed, repr(text[:70]))
            ok = False
    return ok


def check_line_numbers(seed, text):
    """The consequence the callers actually depend on: a line number computed
    from the scored copy equals the one computed from the file."""
    scored = md.apply_exemptions(text)
    for index in range(0, len(text), 7):
        if md.line_of(scored, index) != md.line_of(text, index):
            fail("line_of agrees across the exemption", seed,
                 "index %d in %r" % (index, text[:70]))
            return False
    return True


def check_idempotence(seed, text):
    ok = True
    once = md.strip_wrapped_urls(text)
    if md.strip_wrapped_urls(once) != once:
        fail("strip_wrapped_urls is idempotent", seed, repr(text[:70]))
        ok = False
    once = md.apply_exemptions(text)
    if md.apply_exemptions(once) != once:
        fail("apply_exemptions is idempotent", seed, repr(text[:70]))
        ok = False
    return ok


def check_mask(seed, text, voice_rules):
    """No edit lands in a span the plugin promises not to touch, and the edits
    the planner returns never overlap."""
    mask = fixes.protected_mask(text)
    if len(mask) != len(text):
        fail("protected_mask covers the whole document", seed,
             "%d vs %d" % (len(mask), len(text)))
        return False
    edits, _ = fixes.plan(text, voice_rules)
    ok = True
    last_end = -1
    for start, end, _, record in edits:
        if start < last_end:
            fail("planned edits do not overlap", seed,
                 "%r at %d after %d" % (record["id"], start, last_end))
            ok = False
        last_end = end
        # The tracking-parameter fix is the one rule allowed inside a URL, which
        # is masked against everything else.
        if record["id"] == "ai-utm":
            continue
        if any(mask[start:end]):
            fail("no fix lands in a protected span", seed,
                 "%r at %d in %r" % (record["id"], start, text[max(0, start - 30):end + 30]))
            ok = False
    return ok


def check_fix_verifies(seed, text, voice_rules, verify):
    """Whatever --apply-safe would write has to survive the same preservation
    gate a model-authored rewrite goes through. This is the closed loop."""
    fixed = fixes.apply(text, voice_rules)[0]
    if fixed == text:
        return True
    result = verify.validate(text, fixed)
    if not result["ok"]:
        fail("a safe fix passes verify.py", seed,
             "%s on %r" % ([v["kind"] for v in result["violations"]], text[:70]))
        return False
    if result["tells_after"] > result["tells_before"]:
        fail("a safe fix never adds a tell", seed, repr(text[:70]))
        return False
    return True


def main(argv):
    base_seed = 20260811
    if "--seed" in argv:
        base_seed = int(argv[argv.index("--seed") + 1])
    cases = CASES
    if "--cases" in argv:
        cases = int(argv[argv.index("--cases") + 1])

    spec = importlib.util.spec_from_file_location(
        "rw_verify_props", os.path.join(SCRIPTS, "verify.py"))
    verify = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verify)

    voice_rules = {
        "voice": "props",
        "mechanics": {"em_dash": "allow"},
        "preferred_substitutions": {"leverage": "use", "circle back": "follow up"},
    }

    print("blanking invariants over %d generated documents (base seed %d)"
          % (cases, base_seed))
    checks = [check_lengths, check_line_numbers, check_idempotence]
    clean = 0
    for i in range(cases):
        seed = base_seed + i
        rng = random.Random(seed)
        text = document(rng)
        ok = all(fn(seed, text) for fn in checks)
        ok = check_mask(seed, text, voice_rules) and ok
        ok = check_fix_verifies(seed, text, voice_rules, verify) and ok
        clean += ok
    print("  %d/%d documents clean" % (clean, cases))

    # The fragments themselves, one at a time. A property that only holds on
    # combinations is hiding a single-fragment failure behind a lucky pairing.
    print("the same invariants on each fragment alone")
    for i, fragment in enumerate(FRAGMENTS):
        text = fragment + "\n"
        for fn in checks:
            fn(-i, text)
        check_mask(-i, text, voice_rules)
    print("  %d fragments checked" % len(FRAGMENTS))

    print("degenerate inputs")
    for label, text in (("empty", ""), ("one newline", "\n"),
                        ("only whitespace", "   \n\t\n"),
                        ("no trailing newline", "a fence\n```\nx"),
                        ("null byte", "text with a \x00 in it")):
        before = len(failures)
        for fn in checks:
            fn(-999, text)
        if len(failures) == before:
            print("  pass  %s" % label)

    print()
    if failures:
        print("%d failure(s): %s" % (len(failures), ", ".join(sorted(set(failures)))))
        return 1
    print("all invariants hold")
    return 0


def test_invariants():
    """pytest entry point."""
    assert main([]) == 0, "%d invariant failure(s)" % len(failures)


def test_rwlib_all_pinned():
    """Ensure rwlib.__all__ includes all python files in rwlib/ directory."""
    import rwlib
    rwlib_dir = os.path.dirname(rwlib.__file__)
    modules = sorted(
        os.path.splitext(f)[0] for f in os.listdir(rwlib_dir)
        if f.endswith(".py") and f != "__init__.py"
    )
    assert sorted(rwlib.__all__) == modules


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

