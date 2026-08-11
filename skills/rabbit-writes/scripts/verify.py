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
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN_PATH = os.path.join(HERE, "scan.py")
LEXICON_PATH = os.path.join(HERE, "lexicon.json")

FENCE_RX = re.compile(r"^```.*?^```", re.M | re.S)
INLINE_CODE_RX = re.compile(r"`[^`\n]+`")
FRONTMATTER_RX = re.compile(r"\A---\n(.*?)\n---\n", re.S)
TABLE_ROW_RX = re.compile(r"(?m)^\s*\|.*\|\s*$")
BLOCKQUOTE_RX = re.compile(r"(?m)^\s*>.*$")
HEADING_RX = re.compile(r"(?m)^(#{1,6})\s+(.*?)\s*$")
URL_RX = re.compile(r"https?://[^\s\)\]\>\"']+")
# Same pair rule as scan.py's: each kind of quote closes with its own.
QUOTED_RX = re.compile("\"[^\"“”\n]{4,200}\"|“[^\"“”\n]{4,200}”")
# Em dashes, and en dashes that are not a numeric range. "2010–2023" and
# "pp. 14–18" are correct typography and the one en dash a rewrite legitimately
# produces; counting them fails a rewrite for getting the punctuation right.
# Only a spaceless en dash flanked by digits is treated as a range, because a
# spaced one is almost always standing in for an em dash.
PROSE_DASH_RX = re.compile(r"—|–(?!\d)|(?<!\d)–")
# File paths, and only the ones carrying an extension. An extensionless path
# like `voices/ACTIVE` is not tracked, and that is a deliberate ceiling rather
# than an oversight: dropping the extension requirement makes this match every
# slash-separated pair in English prose. Over this repo's own documents that is
# "and/or", "read/write", "TCP/IP", "human/AI", "architecture/API", and every
# `owner/repo` slug. Requiring the right-hand side to be all-caps trims the worst
# of it and still leaves "human/AI" and "build/CI", so a rewrite that correctly
# turns "human/AI writing" into "human and AI writing" would hard-fail on a gate
# that blocks file writes. Under-matching here is the safe direction: the
# instruction to leave paths alone stays in SKILL.md and the checklist, and
# SKILL.md says which half of it this script can actually see.
PATH_RX = re.compile(r"(?<![\w/])(?:\.{0,2}/)?(?:[\w.-]+/)+[\w.-]+\.\w{1,6}\b")
AI_PARAM_RX = re.compile(
    r"(utm_source=(chatgpt|openai|copilot|claude|perplexity|gemini)[a-z.]*"
    r"|referrer=grok\.com)\Z", re.I)

# Used only when the engine is not beside this script. Kept deliberately short:
# it is a floor, not a copy of the lexicon.
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
        spec = importlib.util.spec_from_file_location("rw_scan", SCAN_PATH)
        scan = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scan)
        with open(LEXICON_PATH, encoding="utf-8") as fh:
            lex = json.load(fh)
    except (OSError, ValueError, AttributeError, ImportError):
        return FALLBACK_TELL_RX
    out = [scan.word_regex(lex["tier1"]), scan.phrase_regex(lex["tier1_phrases"])]
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


def blank(match):
    """Same-length whitespace, so offsets and the multiset comparison hold."""
    return re.sub(r"\S", " ", match.group(0))


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
    unlinked = URL_RX.sub(blank, prose)
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


def norm_url(u):
    """Drop AI-tool tracking parameters and rebuild the query string, so a URL
    that lost only its `utm_source=chatgpt.com` compares equal. Any other change
    to a URL is a violation."""
    if "?" not in u:
        return u
    base, _, rest = u.partition("?")
    query, hash_sep, fragment = rest.partition("#")
    kept = [p for p in query.split("&") if p and not AI_PARAM_RX.match(p)]
    out = base + ("?" + "&".join(kept) if kept else "")
    # Keep a bare trailing "#". Dropping it makes a URL that ends in an empty
    # fragment compare unequal to the identical URL on the other side, which is
    # a violation nobody caused.
    return out + hash_sep + fragment


def blank_exempt(text):
    """Blank the spans scan.py exempts, so the two engines count the same prose.

    Every span blanked here is one this script separately checks for verbatim
    preservation, so hiding it from the counters cannot hide a regression: an
    edit to a fence, a table, a block quote, or inline code is already a
    violation by the time these run. Leaving them in is what makes a document
    that quotes a flagged phrase in order to warn about it fail the tell gate,
    which is the false positive the exemption exists to prevent."""
    out = FRONTMATTER_RX.sub(blank, text)
    out = FENCE_RX.sub(blank, out)
    out = INLINE_CODE_RX.sub(blank, out)
    out = TABLE_ROW_RX.sub(blank, out)
    out = BLOCKQUOTE_RX.sub(blank, out)
    out = QUOTED_RX.sub(blank, out)
    return out


def context(text, start, end, pad=30):
    frag = text[max(0, start - pad):end + pad].replace("\n", " ")
    return re.sub(r"\s+", " ", frag).strip()


def tell_hits(text):
    """Every lexicon tell in the prose, as matched strings. Returned rather than
    counted so a failure can name what got added instead of only how many."""
    prose = blank_exempt(text)
    return [m.group(0).strip() for rx in TELL_RX for m in rx.finditer(prose)]


def dash_hits(text):
    """Prose em and en dashes, each with its surrounding text."""
    prose = blank_exempt(text)
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
