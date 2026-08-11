#!/usr/bin/env python3
"""
verify.py - preservation validator for a rewrite.

SKILL.md promises the editor will not touch code blocks, frontmatter, tables,
block quotes, inline code, URLs, file paths, or heading structure, and will not
add em dashes or leave a draft with more tells than it started with. Edit mode
writes to files, so a broken promise there is silent and destructive. This is
what checks them.

One of those checks is narrower than the promise: a file path is tracked only
when it carries an extension, for the reason spelled out at PATH_RX. Everything
else on the list is checked in full.

Usage:
    python3 verify.py original.md rewritten.md
    python3 verify.py original.md rewritten.md --json
    python3 verify.py original.md converted.md --allow-structure

Exit codes: 0 clean, 1 a violation, 2 a usage or IO error.

Heading structure is inviolable by default, which is right for `deslop` and
wrong for `voice`: a conversion reorders sections and rewrites headings because
the profile told it to. `--allow-structure` moves those two checks into a
reported `structure_changes` list instead of failing. Nothing else moves with
them, and the default is unchanged.

Carve-outs, because the skill instructs these edits:
  - a heading whose text changed only in capitalization (Title Case fix)
  - a URL that lost only an AI tracking parameter
  - an en dash between digits, which is a numeric range and not a splice
  - a tell or a dash inside a span the skill already promises not to touch:
    code, tables, block quotes, frontmatter, and quoted examples
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# See scan.py: rwlib sits beside this file and is not on anybody's PYTHONPATH.
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from rwlib import lexicon as lexicon_mod                              # noqa: E402
from rwlib.artifacts import norm_url                                  # noqa: E402
# QUOTED_RX is a re-export, not a caller: test_verify.py asserts it is the
# same object scan.py holds. See the note in scan.py.
from rwlib.markdown import (BLOCKQUOTE_RX, FENCE_RX, FRONTMATTER_RX,  # noqa: E402,F401
                            HEADING_RX, INLINE_CODE_RX, PATH_RX,
                            PROSE_DASH_RX, QUOTED_RX, TABLE_ROW_RX,
                            URL_RX, apply_exemptions, blank, context)

LEXICON_PATH = lexicon_mod.LEXICON_PATH

# Used only when the lexicon cannot be read. Kept deliberately short: it is a
# floor, not a copy of the lexicon.
FALLBACK_TELL_RX = [
    re.compile(r"(?i)\b(delve|tapestry|nestled|showcasing|testament to|"
               r"meticulous|seamless|robust|cutting-edge|pivotal|"
               r"underscores|game-changer|vibrant|bustling|ever-evolving)\b"),
    re.compile(r"(?i)(i hope this helps|great question|let's dive in|"
               r"in conclusion|the future looks bright|it's worth noting|"
               r"experts believe|studies show)"),
    re.compile(r"(?i)(it'?s not (just )?[^.;!?\n]{2,50}[,;] it'?s)"),
]


def load_tell_regexes():
    """Count tells against lexicon.json rather than against a copy of it.

    A hardcoded subset drifts the moment the lexicon grows, and it drifts
    quietly: the counter keeps returning a number, it is just the wrong one,
    and the check this script exists to run passes a rewrite that added tells
    the lexicon knows about and this file did not."""
    try:
        lex = lexicon_mod.load()
    except (OSError, ValueError):
        return FALLBACK_TELL_RX
    out = [lexicon_mod.word_regex(lex["tier1"]),
           lexicon_mod.phrase_regex(lex["tier1_phrases"])]
    for p in lex["patterns"]:
        if p.get("band") != "fingerprint":
            continue
        # P2 fingerprints are weak signals and this counter is a hard gate. The
        # one that matters is curly-quote: paste a paragraph through Word,
        # Google Docs, or macOS and the typography curls on its own. Counting
        # that as a tell fails a correct rewrite for something the editor did,
        # which is the false positive references/false-positives.md warns about
        # and the opposite of what this script is for.
        if p.get("priority") == "P2":
            continue
        try:
            out.append(re.compile(p["rx"]))
        except (re.error, KeyError):
            continue
    return out


TELL_RX = load_tell_regexes()


def extract(text):
    # Fences and inline code are compared verbatim and so are read from the raw
    # text. Everything structural is read from a copy with the fences blanked:
    # `# build the image` inside a bash fence is a shell comment, not a heading,
    # and a piped line inside a fence is not a table row. Without this, moving a
    # code block that contains shell comments changes the heading count and
    # fails a conversion that touched no headings at all.
    prose = FENCE_RX.sub(blank, text)
    # A URL carries slashes and a dotted final segment, so PATH_RX matches
    # inside one (.../main/README.md). Left in, an edited URL is reported twice,
    # and the utm-stripping carve-out norm_url grants does not reach the second
    # report.
    #
    # Inline code goes with it, for the same reason and with the same fix. Most
    # paths in a document are written as `scripts/scan.py`, and inline code is
    # compared verbatim two checks above, which is a stricter promise than the
    # path check makes. Left in, one edit to one span reported both "inline code
    # altered" and "file path altered", and a reader counting violations saw two
    # broken promises where there was one.
    unlinked = INLINE_CODE_RX.sub(blank, URL_RX.sub(blank, prose))
    return {
        "fences": FENCE_RX.findall(text),
        "inline_code": INLINE_CODE_RX.findall(text),
        "frontmatter": (FRONTMATTER_RX.search(text).group(1)
                        if FRONTMATTER_RX.search(text) else None),
        "tables": TABLE_ROW_RX.findall(prose),
        "blockquotes": BLOCKQUOTE_RX.findall(prose),
        "headings": HEADING_RX.findall(prose),
        "urls": URL_RX.findall(text),
        "paths": PATH_RX.findall(unlinked),
    }


def tell_hits(text):
    """Every lexicon tell in the prose, as matched strings. Returned rather than
    counted so a failure can name what got added instead of only how many."""
    prose = apply_exemptions(text)
    return [m.group(0).strip() for rx in TELL_RX for m in rx.finditer(prose)]


def dash_hits(text):
    """Prose em and en dashes, each with its surrounding text."""
    prose = apply_exemptions(text)
    return [context(prose, m.start(), m.end())
            for m in PROSE_DASH_RX.finditer(prose)]


def count_tells(text):
    return len(tell_hits(text))


def multiset_lost(before, after):
    """Items present in `before` that are missing from `after`, counting duplicates."""
    remaining = list(after)
    lost = []
    for item in before:
        if item in remaining:
            remaining.remove(item)
        else:
            lost.append(item)
    return lost


def validate(original, rewritten, allow_structure=False):
    a, b = extract(original), extract(rewritten)
    violations = []
    structure_changes = []

    def check(key, name):
        lost = multiset_lost(a[key], b[key])
        for item in lost[:5]:
            snippet = re.sub(r"\s+", " ", str(item))[:110]
            violations.append({"kind": name, "detail": snippet})
        if len(lost) > 5:
            violations.append({"kind": name,
                               "detail": "... and %d more" % (len(lost) - 5)})

    check("fences", "code block altered or removed")
    check("inline_code", "inline code altered or removed")
    check("tables", "table row altered or removed")
    check("blockquotes", "block quote altered or removed")
    check("paths", "file path altered or removed")

    if a["frontmatter"] != b["frontmatter"]:
        violations.append({"kind": "frontmatter altered", "detail": ""})

    # URLs: losing an AI tracking parameter is instructed; anything else is not.
    a_urls = [norm_url(u) for u in a["urls"]]
    b_urls = [norm_url(u) for u in b["urls"]]
    for u in multiset_lost(a_urls, b_urls)[:5]:
        violations.append({"kind": "URL altered or removed", "detail": u[:110]})

    # Headings: a case-only change is the instructed Title Case fix.
    #
    # Compared as a multiset, like every other preservation check. Membership
    # alone hides the duplicate case: a document with two `## Notes` that loses
    # one of them and gains a different heading keeps both the membership test
    # and the count test happy, and a section disappears with nothing reported.
    #
    # A voice conversion reorders sections and rewrites headings on purpose, so
    # --allow-structure downgrades these two to a reported list. It scopes to
    # headings and nothing else: code, tables, quotes, URLs, and the em-dash and
    # tell counters stay hard in both modes. Without the flag a conversion fails
    # its own verification, which is how "restructure freely" turns back into a
    # word swap.
    heading_bucket = structure_changes if allow_structure else violations
    unmatched = [(lvl, txt.lower()) for lvl, txt in b["headings"]]
    for lvl, txt in a["headings"]:
        key = (lvl, txt.lower())
        if key in unmatched:
            unmatched.remove(key)
        else:
            heading_bucket.append({"kind": "heading changed or removed",
                                   "detail": "%s %s" % (lvl, txt)})
    if len(a["headings"]) != len(b["headings"]):
        heading_bucket.append({
            "kind": "heading count changed",
            "detail": "%d -> %d" % (len(a["headings"]), len(b["headings"])),
        })

    # Em dashes must never be added. Both counters diff the actual hits rather
    # than the totals, so a failure names the span that moved the number and the
    # reader can tell a real regression from a false positive without guessing.
    a_dash, b_dash = dash_hits(original), dash_hits(rewritten)
    a_em, b_em = len(a_dash), len(b_dash)
    if b_em > a_em:
        added = multiset_lost(b_dash, a_dash)
        violations.append({"kind": "em dashes added",
                           "detail": "%d -> %d: %s"
                                     % (a_em, b_em, " | ".join(added[:3]))})

    # A rewrite must not end with more tells than it started with.
    a_tells, b_tells = tell_hits(original), tell_hits(rewritten)
    a_t, b_t = len(a_tells), len(b_tells)
    if b_t > a_t:
        added = multiset_lost(b_tells, a_tells)
        violations.append({"kind": "more tells after rewrite",
                           "detail": "%d -> %d: %s"
                                     % (a_t, b_t, ", ".join(added[:5]))})

    return {
        "ok": not violations,
        "violations": violations,
        "structure_changes": structure_changes,
        "tells_before": a_t,
        "tells_after": b_t,
        "em_dashes_before": a_em,
        "em_dashes_after": b_em,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("original")
    ap.add_argument("rewritten")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--allow-structure", action="store_true",
                    help="report heading changes instead of failing on them. For a "
                         "voice conversion, which reorders sections by design. Every "
                         "other preservation check still applies")
    args = ap.parse_args()

    try:
        with open(args.original, encoding="utf-8") as fh:
            original = fh.read()
        with open(args.rewritten, encoding="utf-8") as fh:
            rewritten = fh.read()
    except OSError as exc:
        print("verify: %s" % exc, file=sys.stderr)
        return 2

    result = validate(original, rewritten, allow_structure=args.allow_structure)

    if args.json:
        print(json.dumps(result, indent=2))
    elif result["ok"]:
        print("preservation OK  |  tells %d -> %d  |  em dashes %d -> %d"
              % (result["tells_before"], result["tells_after"],
                 result["em_dashes_before"], result["em_dashes_after"]))
        for c in result["structure_changes"]:
            print("  structure  %-28s %s" % (c["kind"], c["detail"]))
    else:
        print("preservation FAILED (%d violation(s))" % len(result["violations"]))
        for v in result["violations"]:
            print("  %-32s %s" % (v["kind"], v["detail"]))
        print("\nThe rewrite touched something SKILL.md promises to leave alone, "
              "or moved a counter the wrong way. Restore those spans and re-run.")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
