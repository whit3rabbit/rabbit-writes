#!/usr/bin/env python3
"""
verify.py - preservation validator for a rewrite.

SKILL.md promises the editor will not touch code blocks, frontmatter, tables,
block quotes, inline code, URLs, file paths, or heading structure, and will not
add em dashes or leave a draft with more tells than it started with. Edit mode
writes to files, so a broken promise there is silent and destructive. This is
what checks them.

Usage:
    python3 verify.py original.md rewritten.md
    python3 verify.py original.md rewritten.md --json

Exit codes: 0 clean, 1 a violation, 2 a usage or IO error.

Carve-outs, because the skill instructs both edits:
  - a heading whose text changed only in capitalization (Title Case fix)
  - a URL that lost only an AI tracking parameter
"""

import argparse
import json
import re
import sys

FENCE_RX = re.compile(r"^```.*?^```", re.M | re.S)
INLINE_CODE_RX = re.compile(r"`[^`\n]+`")
FRONTMATTER_RX = re.compile(r"\A---\n(.*?)\n---\n", re.S)
TABLE_ROW_RX = re.compile(r"(?m)^\s*\|.*\|\s*$")
BLOCKQUOTE_RX = re.compile(r"(?m)^\s*>.*$")
HEADING_RX = re.compile(r"(?m)^(#{1,6})\s+(.*?)\s*$")
URL_RX = re.compile(r"https?://[^\s\)\]\>\"']+")
PATH_RX = re.compile(r"(?<![\w/])(?:\.{0,2}/)?(?:[\w.-]+/)+[\w.-]+\.\w{1,6}\b")
AI_PARAM_RX = re.compile(
    r"(utm_source=(chatgpt|openai|copilot|claude|perplexity|gemini)[a-z.]*"
    r"|referrer=grok\.com)\Z", re.I)

TELL_RX = [
    re.compile(r"(?i)\b(delve|tapestry|nestled|showcasing|testament to|"
               r"meticulous|seamless|robust|cutting-edge|pivotal|"
               r"underscores|game-changer|vibrant|bustling|ever-evolving)\b"),
    re.compile(r"(?i)(i hope this helps|great question|let's dive in|"
               r"in conclusion|the future looks bright|it's worth noting|"
               r"experts believe|studies show)"),
    re.compile(r"(?i)(it'?s not (just )?[^.;!?\n]{2,50}[,;] it'?s)"),
]


def extract(text):
    return {
        "fences": FENCE_RX.findall(text),
        "inline_code": INLINE_CODE_RX.findall(text),
        "frontmatter": (FRONTMATTER_RX.search(text).group(1)
                        if FRONTMATTER_RX.search(text) else None),
        "tables": TABLE_ROW_RX.findall(text),
        "blockquotes": BLOCKQUOTE_RX.findall(text),
        "headings": HEADING_RX.findall(text),
        "urls": URL_RX.findall(text),
        "paths": PATH_RX.findall(text),
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
    return out + (hash_sep + fragment if fragment else "")


def count_tells(text):
    return sum(len(rx.findall(text)) for rx in TELL_RX)


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


def validate(original, rewritten):
    a, b = extract(original), extract(rewritten)
    violations = []

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
    a_h = [(lvl, txt) for lvl, txt in a["headings"]]
    b_lower = [(lvl, txt.lower()) for lvl, txt in b["headings"]]
    for lvl, txt in a_h:
        if (lvl, txt.lower()) not in b_lower:
            violations.append({"kind": "heading changed or removed",
                               "detail": "%s %s" % (lvl, txt)})
    if len(a["headings"]) != len(b["headings"]):
        violations.append({
            "kind": "heading count changed",
            "detail": "%d -> %d" % (len(a["headings"]), len(b["headings"])),
        })

    # Em dashes must never be added.
    a_em = original.count("—") + original.count("–")
    b_em = rewritten.count("—") + rewritten.count("–")
    if b_em > a_em:
        violations.append({"kind": "em dashes added",
                           "detail": "%d -> %d" % (a_em, b_em)})

    # A rewrite must not end with more tells than it started with.
    a_t, b_t = count_tells(original), count_tells(rewritten)
    if b_t > a_t:
        violations.append({"kind": "more tells after rewrite",
                           "detail": "%d -> %d" % (a_t, b_t)})

    return {
        "ok": not violations,
        "violations": violations,
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
    args = ap.parse_args()

    try:
        original = open(args.original, encoding="utf-8").read()
        rewritten = open(args.rewritten, encoding="utf-8").read()
    except OSError as exc:
        print("verify: %s" % exc, file=sys.stderr)
        return 2

    result = validate(original, rewritten)

    if args.json:
        print(json.dumps(result, indent=2))
    elif result["ok"]:
        print("preservation OK  |  tells %d -> %d  |  em dashes %d -> %d"
              % (result["tells_before"], result["tells_after"],
                 result["em_dashes_before"], result["em_dashes_after"]))
    else:
        print("preservation FAILED (%d violation(s))" % len(result["violations"]))
        for v in result["violations"]:
            print("  %-32s %s" % (v["kind"], v["detail"]))
        print("\nThe rewrite touched something SKILL.md promises to leave alone, "
              "or moved a counter the wrong way. Restore those spans and re-run.")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
