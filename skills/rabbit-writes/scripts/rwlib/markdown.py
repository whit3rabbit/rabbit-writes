#!/usr/bin/env python3
"""
Markdown spans, one definition each.

Everything in this plugin that has to tell prose from markup reads its patterns
from here. Three scripts used to carry their own copies, with comments asking
the next reader to keep them in sync by hand, and the copies drifted anyway:
the badge host lists disagreed, LINK_RX blanked images in one file and not in
another, and two heading patterns matched different spans. A comment is not a
mechanism. This module is.

Blanking, never deleting. Every blank_* and strip_* function here replaces a
span with the same number of characters, so an offset taken from the blanked
copy still points at the same place in the original. Most callers report line
numbers out of a copy they blanked, and preserving length is what makes that
legal. tests/test_invariants.py checks the property rather than trusting the
comment.

Stdlib only, 3.9+.
"""

import re

# --------------------------------------------------------------------------
# code and literal spans
# --------------------------------------------------------------------------

# The fence as one span, for blanking. Non-greedy to the next line that opens
# with three backticks.
FENCE_RX = re.compile(r"^```.*?^```", re.M | re.S)
# The same fences taken apart, for the corpus study, which counts languages and
# body lines. Two patterns because they answer two questions, not because
# anybody forgot to merge them: this one does not anchor to the line start, so
# it must never be used for blanking.
FENCE_PARTS_RX = re.compile(r"```(\w*)\n(.*?)```", re.S)
INLINE_CODE_RX = re.compile(r"`[^`\n]+`")
FRONTMATTER_RX = re.compile(r"\A---\n(.*?)\n---\n", re.S)
TABLE_ROW_RX = re.compile(r"(?m)^\s*\|.*\|\s*$")
TABLE_SEP_RX = re.compile(r"(?m)^\|?[\s:|-]+\|[\s:|-]+\|?\s*$")
BLOCKQUOTE_RX = re.compile(r"(?m)^\s*>.*$")

# Heading, with the marker and the text captured and the trailing whitespace
# eaten. The whole line, not just the hashes: stripping the marker alone leaves
# heading text carrying no terminal punctuation, so a sentence splitter glues it
# onto the first sentence of the section below and every section opener measures
# two or three words too long.
HEADING_RX = re.compile(r"(?m)^(#{1,6})\s+(.*?)\s*$")
# The same span with nothing captured, for callers that only want it gone.
HEADING_LINE_RX = re.compile(r"(?m)^#{1,6}\s+.*$")

LIST_ITEM_RX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")

# Each quote pair has to close with its own kind. A single alternation over both
# the opening and the closing marks lets one stray straight quote pair with a
# curly one up to 200 characters later, and every word between them stops being
# scored.
QUOTED_RX = re.compile("\"[^\"“”\n]{4,200}\"|“[^\"“”\n]{4,200}”")
CURLY_QUOTE_RX = re.compile("[“”‘’]")

# --------------------------------------------------------------------------
# HTML character references
# --------------------------------------------------------------------------

# Named, decimal, and hex character references. The lengths are bounded so a
# stray `&` in prose followed half a paragraph later by a semicolon is not read
# as one entity swallowing the sentence between them. 31 is HTML5's longest
# named reference (`CounterClockwiseContourIntegral`) plus room.
HTML_ENTITY_RX = re.compile(
    r"&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")

# The dashes again, spelled as character references. A document written with
# `&mdash;` renders an em dash, reads as an em dash, and is an em dash to every
# reader, so it has to be one to the counter as well. Left out, a voice that
# forbids em dashes was a find-and-replace away from passing, and verify.py's
# "no em dashes added" gate let a rewrite add as many as it liked.
EM_DASH_ENTITY = r"&(?:mdash|#8212|#[xX]2014);"
EN_DASH_ENTITY = r"&(?:ndash|#8211|#[xX]2013);"

# Em dashes, and en dashes that are not a numeric range. "2010-2023" written
# with an en dash and "pp. 14-18" are correct typography and the one en dash a
# rewrite legitimately produces; counting them fails a rewrite for getting the
# punctuation right. Only a spaceless en dash flanked by digits is a range,
# because a spaced one is standing in for an em dash. The entity spellings carry
# the same two guards, so `2010&ndash;2023` is a range on both sides of the
# alternation and neither form is stricter than the other.
#
# scan.py scores against this and verify.py gates against it. They were two
# byte-identical copies with a test pinning them together, which is the drift
# this module exists to make impossible: one object, imported twice.
PROSE_DASH_RX = re.compile(
    r"—|%s|–(?!\d)|(?<!\d)–|%s(?!\d)|(?<!\d)%s"
    % (EM_DASH_ENTITY, EN_DASH_ENTITY, EN_DASH_ENTITY))

# --------------------------------------------------------------------------
# links, images, URLs
# --------------------------------------------------------------------------

IMAGE_RX = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
LINK_RX = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
REF_LINK_RX = re.compile(r"(?<!!)\[([^\]]+)\]\[([^\]]*)\]")
# The label is captured so a `[a][b]` match can be required to resolve against a
# definition before it is reported. Without that, adjacent brackets in ordinary
# prose read as reference links: `matrix[i][j]` outside a code span is the common
# case, and the finding told the writer to convert a link that does not exist.
REF_DEF_RX = re.compile(r"(?m)^\s*\[([^\]]+)\]:\s*(\S+)")
AUTOLINK_RX = re.compile(r"<https?://[^>]+>")

# Two URL patterns, for two jobs.
#
# URL_RX stops at the first character that closes a wrapper, which is what an
# extractor wants: the URL in `(see https://x.dev/p)` is not the closing paren.
# URL_GREEDY_RX runs to the next whitespace, which is what a *stripper* wants:
# scan.py deletes URLs before measuring prose rhythm, and leaving a stray `)`
# or `"` behind puts markup back into the word counts. Narrowing the greedy one
# to match the other would quietly change every stylometric number this engine
# publishes.
URL_RX = re.compile(r"https?://[^\s)>\]\"']+")
URL_GREEDY_RX = re.compile(r"https?://\S+")
# The same pattern under the name the README checker reports it by. A URL only
# counts as bare once strip_wrapped_urls has blanked every one that already sits
# inside a link, an attribute, an autolink, a reference definition, or a code
# span, which is what makes an extractor pattern the right one here.
BARE_URL_RX = URL_RX

HTML_TAG_RX = re.compile(r"</?[a-zA-Z][^>]*>")
HTML_ATTR_URL_RX = re.compile(r"(?:src|href)\s*=\s*[\"'][^\"']*[\"']", re.I)
HTML_IMG_RX = re.compile(r"<img[^>]+src\s*=\s*[\"']([^\"']+)[\"']", re.I)
HTML_LINK_RX = re.compile(r"<a[^>]+href\s*=\s*[\"']([^\"']+)[\"']", re.I)
# Anchor text, for the vague-link-text check. Non-greedy and DOTALL because a
# centered header routinely puts the badge image and the anchor text on separate
# lines. Nested <a> is not valid HTML, so there is nothing to balance.
HTML_ANCHOR_RX = re.compile(r"<a\b[^>]*>(.*?)</a>", re.I | re.S)
# Any line opening with a tag is markup, not the project description. Kept broad
# on purpose: <details>, <picture>, and <p align=center> all show up in header
# blocks, and listing tags by hand guarantees missing one.
HTML_TAG_LINE_RX = re.compile(r"^\s*</?[a-zA-Z][a-zA-Z0-9]*(?:\s|>|/>)")
HTML_CENTER_RX = re.compile(r"<(p|div|h[1-6])\s+align=[\"']center[\"']", re.I)

# File paths, and only the ones carrying an extension. An extensionless path
# like `voices/ACTIVE` is not tracked, and that is a deliberate ceiling rather
# than an oversight: dropping the extension requirement makes this match every
# slash-separated pair in English prose. Over this repo's own documents that is
# "and/or", "read/write", "TCP/IP", "human/AI", and every `owner/repo` slug.
PATH_RX = re.compile(r"(?<![\w/])(?:\.{0,2}/)?(?:[\w.-]+/)+[\w.-]+\.\w{1,6}\b")

# Substrings, not patterns: is_badge does `h in url`, so a regex written here is
# a literal that never matches. GitHub Actions badges are covered by
# "actions/workflows".
#
# BADGE_HOSTS_CORPUS is what the study counted, and it is frozen: the corpus
# medians in corpus_summary.json were measured with exactly this list, and
# widening it without regenerating the corpus compares a README against a number
# that means something else.
BADGE_HOSTS_CORPUS = (
    "shields.io", "badge.fury.io", "img.shields", "badgen.net", "travis-ci",
    "circleci.com/gh", "codecov.io", "coveralls.io", "actions/workflows",
    "sonarcloud.io", "snyk.io", "discord.com/api/guilds", "opencollective.com",
    "npmjs.com/package", "pypi.org/project", "crates.io/v", "gitpod.io/button",
    "deepwiki.com/badge", "img.badgesize.io", "visitor-badge",
)
# What the checker counts: the study's list plus one catch-all. "/badge" picks up
# the long tail the named hosts miss (trendshift, star-history, repology,
# awesome.re, scorecard): 625 badges against 568 over the committed snapshot, and
# no non-badge image caught by it in that sample. The divergence is deliberate
# and one-directional. The checker is broader than the study, never narrower, so
# a badge-wall finding stays conservative against a corpus median of 5.
BADGE_HOSTS = BADGE_HOSTS_CORPUS + ("/badge",)


def is_badge(url, hosts=BADGE_HOSTS):
    lu = url.lower()
    return any(h in lu for h in hosts)


# --------------------------------------------------------------------------
# blanking
# --------------------------------------------------------------------------

def blank(match):
    """Replace a span with same-length whitespace, so offsets stay stable.

    Written as a re.sub replacement function. Newlines survive, because a
    blanked block that loses its line breaks moves every line number below it.
    """
    return re.sub(r"\S", " ", match.group(0))


def blank_all(text, *patterns):
    for rx in patterns:
        text = rx.sub(blank, text)
    return text


def strip_images(text):
    """Blank every markdown image, so LINK_RX sees links and not badge wrappers.

    A badge-wrapped link is `[![alt](badge.svg)](target)`, and it is one of the
    most common shapes in a README. LINK_RX's outer `[` stops at the first `]`,
    which is the one closing the alt text, so left alone it captures `![alt` as
    the link text and the *badge image URL* as the destination: a pseudo-link
    that is not in the file, counted as a link and averaged into link text
    length. Blanking the image first leaves `[     ](target)`, which matches
    with the real destination and with whitespace for text, and whitespace text
    is already dropped from the average.
    """
    return IMAGE_RX.sub(blank, text)


def blank_entities(text):
    """Blank every HTML character reference, so the `;` that closes one is not
    read as prose punctuation.

    `&amp;`, `&nbsp;`, and `&#39;` are ordinary in a README, and each one ends in
    a semicolon that belongs to the markup rather than to the sentence. A voice
    that forbids semicolons reported one finding per entity, which on a header
    block full of `&nbsp;` is a wall of findings about punctuation the writer
    never typed.

    Deliberately not folded into apply_exemptions. The dash counters want to see
    `&mdash;`, and a blanket blank here would hide it from them.
    """
    return HTML_ENTITY_RX.sub(blank, text)


def strip_wrapped_urls(text):
    """Blank every URL that already lives inside a link, an HTML attribute, an
    autolink, a reference definition, or inline code. What survives is bare.

    A URL inside backticks is part of a command or a config value, not a link
    the reader is meant to click. Telling someone to wrap `curl https://...` in
    markdown would break the thing they are supposed to paste.
    """
    out = strip_images(text)
    return blank_all(out, LINK_RX, HTML_ATTR_URL_RX, AUTOLINK_RX, REF_DEF_RX,
                     INLINE_CODE_RX)


def apply_exemptions(text):
    """Blank the spans this plugin promises never to rewrite, so a document that
    quotes AI patterns in order to warn about them does not score as one.

    Every span blanked here is one verify.py separately checks for verbatim
    preservation, so hiding it from the counters cannot hide a regression: an
    edit to a fence, a table, a block quote, or inline code is already a
    violation by the time the counters run. Leaving them in is what makes a
    document that quotes a flagged phrase fail the tell gate, which is the false
    positive the exemption exists to prevent.
    """
    return blank_all(text, FRONTMATTER_RX, FENCE_RX, INLINE_CODE_RX,
                     TABLE_ROW_RX, BLOCKQUOTE_RX, QUOTED_RX)


# --------------------------------------------------------------------------
# offsets and shapes
# --------------------------------------------------------------------------

def line_of(text, index):
    return text.count("\n", 0, index) + 1


def excerpt(text, start, end, pad=34):
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    frag = text[lo:hi].replace("\n", " ")
    return re.sub(r"\s+", " ", frag).strip()


def context(text, start, end, pad=30):
    """excerpt() with the narrower window verify.py reports violations in."""
    return excerpt(text, start, end, pad=pad)


def word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", text))


def is_prose_block(block):
    """True when a block is prose rather than a list, a table, or a heading.

    Two rules, because the same block was read wrong from both directions.

    A block that *opens* with a bullet is a list, whatever the ratio says. Items
    that wrap over several lines each drive the bullet share below half, so a
    six-item list with three-line items scored as one long paragraph and the
    voice paragraph-length cap fired on it. `CHANGELOG.md` reported five of
    those and every one was a bullet list. Nothing that starts with a bullet is a
    paragraph, so the ratio never needed a vote here.

    Past the first line, the majority rule stands. One sentence of lead-in
    followed by eight bullets has a first line that is prose, and matching only
    the first line let the whole thing score as a single 90-word paragraph. A
    lead-in plus one or two bullets is still a paragraph with a list under it,
    which is why that half is a majority rather than any bullet at all.
    """
    lines = [ln for ln in block.strip().split("\n") if ln.strip()]
    if not lines:
        return False
    first = lines[0].lstrip()
    if first.startswith(("#", ">", "|", "```", "    ")):
        return False
    if LIST_ITEM_RX.match(lines[0]):
        return False
    listish = sum(1 for ln in lines if LIST_ITEM_RX.match(ln))
    return listish * 2 < len(lines)
