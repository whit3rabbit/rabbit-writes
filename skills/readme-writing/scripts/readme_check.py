#!/usr/bin/env python3
"""
readme_check.py - the mechanical layer of the readme-writing skill.

Checks a README against the conventions measured in docs/README_WRITEUP.md
(100 currently-trending GitHub repos), and, unless told otherwise, runs the
active voice's rules over the prose at the same time. Structure and voice are
two different failure modes and a README has to survive both: the section
order comes from the corpus, the sentence-level mechanics come from whoever
is publishing the thing.

Everything here is something a regex or a counter can decide. Whether the
pitch is *good* is a judgment call and stays in SKILL.md.

Usage:
    python3 readme_check.py README.md
    python3 readme_check.py README.md --json
    python3 readme_check.py README.md --check          # exit 1 on any P0
    python3 readme_check.py README.md --no-voice       # structure only
    python3 readme_check.py README.md --voice-rules path/to/dana.rules.json

Voice resolution, in order: --voice-rules, then a .rabbit-voice file beside
the README or in the working directory, then skills/rabbit-writes/voices/ACTIVE.
A missing voice is reported as a note, never an error: plenty of projects have
no profile, and failing the run would just teach people to pass --no-voice.

Exit codes: 0, or 1 with --check when a P0 is present. Stdlib only, 3.8+.
"""

import argparse
import importlib.util
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SKILL_ROOT))
SCAN_PATH = os.path.join(PLUGIN_ROOT, "skills", "rabbit-writes", "scripts", "scan.py")
VOICES_DIR = os.path.join(PLUGIN_ROOT, "skills", "rabbit-writes", "voices")

# ---------------------------------------------------------------------------
# corpus constants. Every number is from docs/readme-analysis/03_aggregate_summary.json,
# computed over 100 READMEs. Kept here rather than read from docs/ so the script
# still works when the skill is installed without the research data.
# ---------------------------------------------------------------------------

CORPUS = {
    "word_count_percentiles": {"p10": 766, "p25": 1311, "p50": 1846, "p75": 3612, "p90": 6040},
    "avg_paragraph_words": 28.4,
    "sentence_mix_pct": {"short": 37.8, "medium": 36.5, "long": 25.6},
    "median_badge_count": 5,
    "link_style_pct": {"inline": 96.8, "bare": 3.0, "reference": 0.2},
    "avg_link_text_words": 2.2,
    "median_license_words": 13.5,
    "section_avg_position": {
        "features": 0.21, "toc": 0.23, "installation": 0.33, "demo": 0.38,
        "sponsors": 0.39, "related": 0.45, "performance": 0.45,
        "architecture": 0.46, "usage": 0.46, "api": 0.53, "examples": 0.53,
        "security": 0.54, "configuration": 0.56, "support": 0.59, "faq": 0.61,
        "roadmap": 0.63, "testing": 0.66, "changelog": 0.71,
        "contributing": 0.77, "credits": 0.80, "license": 0.93,
    },
}

# Sections that exist for people already sold on the project. A quickstart
# appearing after one of these is the ordering inversion worth flagging.
LATE_SECTIONS = {"contributing", "changelog", "credits", "faq", "testing", "roadmap", "license"}

TOC_MIN_WORDS = 1500          # below this a TOC costs more scroll than it saves
TOC_EXPECTED_WORDS = 2500     # above this its absence is worth a note
# Non-blank lines above the first prose sentence, measured across the corpus:
# median 5, p75 14, p90 23. Past 25 a README is in the worst decile of the
# sample, which is where the named anti-pattern cases sit.
PITCH_HEAVY_HEADER = 15
PITCH_MAX_NONBLANK_LINES = 25
LONG_PARAGRAPH_WORDS = 60     # checklist item 8
BADGE_WALL = 12               # corpus median 5, p75 8, p90 14

# Classification copied from scripts/readme-research/03_analyze_readme.py so this
# check and the corpus measurement agree on what counts as an "installation"
# section. Diverging here would compare against thresholds derived from a
# different definition.
SECTION_KEYWORDS = [
    ("toc", ["table of contents", "contents", "index"]),
    ("features", ["features", "why ", "highlights", "why use", "what is"]),
    ("demo", ["demo", "screenshot", "preview", "gallery", "in action", "showcase"]),
    ("installation", ["install", "setup", "getting started", "quick start", "quickstart",
                      "requirements", "prerequisites"]),
    ("usage", ["usage", "how to use", "quick example", "basic usage"]),
    ("examples", ["example"]),
    ("configuration", ["config", "options", "settings", "environment variable"]),
    ("api", ["api reference", " api", "documentation", "docs"]),
    ("architecture", ["architecture", "how it works", "design", "internals"]),
    ("contributing", ["contributing", "contribute", "development guide", "developing"]),
    ("testing", ["testing", "run tests", "tests"]),
    ("roadmap", ["roadmap", "todo", "future work", "upcoming"]),
    ("faq", ["faq", "frequently asked", "troubleshoot"]),
    ("license", ["license", "licence"]),
    ("credits", ["acknowledg", "credits", "thanks", "contributors", "inspired by"]),
    ("support", ["support", "community", "contact", "discord", "get help", "help"]),
    ("sponsors", ["sponsor", "backers", "funding"]),
    ("changelog", ["changelog", "release notes", "history", "whats new", "what's new"]),
    ("security", ["security"]),
    ("related", ["related", "see also", "alternatives", "comparison"]),
    ("performance", ["performance", "benchmark"]),
]

FENCE_RX = re.compile(r"^```.*?^```", re.M | re.S)
HEADING_RX = re.compile(r"(?m)^(#{1,6})\s+(.*)$")
IMAGE_RX = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
LINK_RX = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
REF_LINK_RX = re.compile(r"(?<!!)\[([^\]]+)\]\[([^\]]*)\]")
BARE_URL_RX = re.compile(r"https?://[^\s)>\]\"']+")
HTML_ATTR_URL_RX = re.compile(r"(?:src|href)\s*=\s*[\"'][^\"']*[\"']", re.I)
AUTOLINK_RX = re.compile(r"<https?://[^>]+>")
REF_DEF_RX = re.compile(r"(?m)^\s*\[[^\]]+\]:\s*\S+")
INLINE_CODE_RX = re.compile(r"`[^`\n]+`")
HTML_TAG_RX = re.compile(r"</?[a-zA-Z][^>]*>")
HTML_IMG_RX = re.compile(r"<img[^>]+src\s*=\s*[\"']([^\"']+)[\"']", re.I)
# Any line opening with a tag is markup, not the project description. Kept broad
# on purpose: <details>, <picture>, and <p align=center> all show up in header
# blocks, and listing tags by hand guarantees missing one.
HTML_TAG_LINE_RX = re.compile(r"^\s*</?[a-zA-Z][a-zA-Z0-9]*(?:\s|>|/>)")
BADGE_HOSTS = ("shields.io", "badge.fury.io", "badgen.net", "travis-ci", "circleci.com/gh",
               "codecov.io", "coveralls.io", "actions/workflows", "sonarcloud.io", "snyk.io",
               "discord.com/api/guilds", "opencollective.com", "npmjs.com/package",
               "pypi.org/project", "crates.io/v", "gitpod.io/button", "deepwiki.com/badge",
               "img.badgesize.io", "visitor-badge", "/badge")
VAGUE_LINK_TEXT = {"here", "click here", "this", "this link", "link", "read more", "more",
                   "learn more", "see here", "this page", "documentation here"}
CLAIM_RX = re.compile(
    r"(?i)\b(\d+(?:\.\d+)?\s*(?:x|times)\s*(?:faster|smaller|cheaper|less|more|quicker)"
    r"|\d+(?:\.\d+)?\s*%\s*(?:faster|smaller|cheaper|fewer|less|more|reduction|savings?|accura\w+)"
    r"|saves?\s+(?:you\s+)?\d+(?:\.\d+)?\s*%"
    r"|cuts?\s+\w+\s+by\s+\d+(?:\.\d+)?\s*%)")
CAVEAT_RX = re.compile(
    r"(?i)(caveat|varies|vary|depends|depending|measured (on|with|against)|does not (cover|include)"
    r"|doesn't (cover|include)|not a guarantee|your mileage|approximat|excluding|only counts"
    r"|net.negative|worst case|in some cases|under (this|these) conditions|methodolog)")
NUMBER_NOUN_RX = re.compile(r"\b(\d[\d,]*)\s+([A-Za-z][A-Za-z-]{3,20})\b")
# Units of measure legitimately take different numbers in one document ("13 words",
# "6,040 words"). Only a countable noun naming the same set twice is a real conflict.
MEASURE_NOUNS = {"word", "line", "char", "character", "byte", "kilobyte", "megabyte", "second",
                 "minute", "hour", "day", "week", "month", "year", "percent", "token", "time",
                 "step", "point", "version", "item", "case", "example", "column", "row", "level",
                 "page", "sentence", "paragraph", "commit", "star", "issue", "entrie", "entry"}
LIST_ITEM_RX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")


def blank(match):
    """Same-length whitespace, so line numbers survive the substitution."""
    return re.sub(r"\S", " ", match.group(0))


def classify_heading(text):
    t = re.sub(r"[^\w\s'-]", " ", text.strip().lower().lstrip("#").strip())
    for cat, kws in SECTION_KEYWORDS:
        if any(kw in t for kw in kws):
            return cat
    return "other"


def is_badge(url):
    lu = url.lower()
    return any(h in lu for h in BADGE_HOSTS)


def word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", text))


def line_of(text, index):
    return text.count("\n", 0, index) + 1


def finding(fid, label, priority, line, detail):
    return {"id": fid, "label": label, "band": "structure", "priority": priority,
            "line": line, "detail": detail}


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------

def find_pitch(raw):
    """Line number of the first sentence that describes the project.

    Skipped on the way down: headings, images, badge rows, horizontal rules,
    comments, callouts, and collapsed <details> blocks. A security callout above
    the pitch is a pattern the corpus rewards, so it does not count as burying
    anything.

    HTML lines are read, not skipped. 76% of the corpus centers its header, and
    in a centered header the tagline lives inside <p align="center"> or <h3>.
    Treating markup as decoration would report a buried pitch on most of the
    good READMEs in the study.
    """
    nonblank = 0
    in_comment = False
    details_depth = 0
    for i, line in enumerate(raw.splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        nonblank += 1
        if in_comment:
            in_comment = "-->" not in s
            continue
        if s.startswith("<!--"):
            in_comment = "-->" not in s
            continue
        # <details> hides a language bar or an FAQ, and an HTML <table> at the
        # top of a README is a sponsor grid in almost every case. Neither is
        # where the project describes itself.
        details_depth += len(re.findall(r"(?i)<(?:details|table)\b", s))
        details_depth -= len(re.findall(r"(?i)</(?:details|table)>", s))
        if details_depth > 0 or re.search(r"(?i)<summary\b", s):
            continue
        if (s.startswith("#") or s.startswith(">") or s.startswith("|")
                or s.startswith("```") or set(s) <= set("-=*_ ")):
            continue
        if HTML_TAG_LINE_RX.match(s):
            s = HTML_TAG_RX.sub(" ", s)
        stripped = IMAGE_RX.sub("", s)
        stripped = LINK_RX.sub(r"\1", stripped)
        stripped = re.sub(r"[*_`#>|]", "", stripped).strip()
        stripped = re.sub(r"^[-*+]\s+", "", stripped)
        if word_count(stripped) >= 5:
            return i, nonblank
    return None, nonblank


def check_structure(raw, scored, findings, stats):
    lines = raw.splitlines()

    # --- headings and section inventory
    headings = []
    for m in HEADING_RX.finditer(scored):
        cat = classify_heading(m.group(2))
        headings.append({"level": len(m.group(1)), "text": m.group(2).strip(),
                         "category": cat, "line": line_of(scored, m.start()),
                         "pos": m.start()})
    sections = [h for h in headings if h["category"] != "other"]
    stats["sections"] = [h["category"] for h in sections]
    stats["heading_count"] = len(headings)

    # --- the pitch, and what sits above it
    pitch_line, _ = find_pitch(raw)
    stats["pitch_line"] = pitch_line
    if pitch_line is None:
        findings.append(finding(
            "no-pitch", "No descriptive sentence found", "P0", 1,
            "Nothing in this file states what the project is in prose. A reader "
            "deciding whether to keep scrolling has nothing to decide on."))
    else:
        head = "\n".join(lines[:pitch_line - 1])
        nonblank_above = len([l for l in lines[:pitch_line - 1] if l.strip()])
        urls_above = [u for _, u in IMAGE_RX.findall(head)] + HTML_IMG_RX.findall(head)
        badges_above = len([u for u in urls_above if is_badge(u)])
        images_above = len(urls_above)
        sponsorish = re.search(r"(?i)\b(sponsors?|sponsorship|backers?|funding|patreon|"
                               r"open ?collective|buy me a coffee|our partners)\b", head)
        stats["nonblank_lines_above_pitch"] = nonblank_above
        stats["badges_above_pitch"] = badges_above
        if nonblank_above > PITCH_MAX_NONBLANK_LINES:
            findings.append(finding(
                "pitch-buried", "Pitch is buried", "P0", pitch_line,
                "%d non-blank lines (%d images, %d badges) come before the first prose "
                "sentence, which puts this in the worst 10%% of the corpus (median 5). "
                "Check what that first sentence actually is, too: in the anti-pattern "
                "cases it turns out to be sponsor copy, and the real description is "
                "further down still." % (nonblank_above, images_above, badges_above)))
        elif nonblank_above > PITCH_HEAVY_HEADER:
            findings.append(finding(
                "heavy-header", "%d non-blank lines above the pitch" % nonblank_above,
                "P2", pitch_line,
                "Corpus median is 5, 75th percentile 14. Not fatal, but every line here "
                "is one the reader scrolls past before learning what this is."))
        if sponsorish:
            findings.append(finding(
                "promo-before-pitch", "Promotional block above the pitch", "P1",
                line_of(head, sponsorish.start()),
                "Sponsor or funding content sits before the project description. "
                "Every future reader pays for that placement, move it below the quickstart."))

    # --- install position
    cats = [h["category"] for h in sections]
    if "installation" not in cats:
        findings.append(finding(
            "no-install", "No installation or quickstart section", "P1", 1,
            "84% of the corpus has one and it is the earliest structural section "
            "(avg. position 0.33). Give the reader a copy-pasteable path to running it."))
    else:
        install_at = cats.index("installation")
        late_first = next((c for c in cats[:install_at] if c in LATE_SECTIONS), None)
        if late_first:
            findings.append(finding(
                "install-late", "Install comes after %s" % late_first, "P1",
                sections[install_at]["line"],
                "%s sits at avg. position %.2f in the corpus, installation at 0.33. "
                "Get the reader running the thing before the community mechanics."
                % (late_first, CORPUS["section_avg_position"].get(late_first, 0.8))))

    # --- license: last, and short
    if "license" in cats:
        idx = cats.index("license")
        lic = sections[idx]
        after = [c for c in cats[idx + 1:] if c != "credits"]
        if after:
            findings.append(finding(
                "license-not-last", "License is not the final section", "P2", lic["line"],
                "License sits at avg. position 0.93 across the corpus. Sections after it here: "
                "%s." % ", ".join(after)))
        nxt = next((h for h in headings if h["pos"] > lic["pos"]), None)
        body = scored[lic["pos"]:nxt["pos"] if nxt else len(scored)]
        body = HEADING_RX.sub("", body, count=1)
        lic_words = word_count(body)
        stats["license_words"] = lic_words
        if lic_words > 80:
            findings.append(finding(
                "license-long", "License section is %d words" % lic_words, "P2", lic["line"],
                "Corpus median is 13. Name the license and link the file, nobody reads "
                "restated legal text in a README."))
    else:
        findings.append(finding(
            "no-license", "No license section", "P2", 1,
            "72% of the corpus names one. Check for a LICENSE file rather than guessing, "
            "and if there is none, say so."))

    return sections


def check_toc(scored, findings, stats):
    words = stats["prose_words"]
    anchor_links = [u for _, u in LINK_RX.findall(scored) if u.startswith("#")]
    has_heading = "toc" in stats["sections"]
    has_toc = has_heading or len(anchor_links) >= 3
    stats["has_toc"] = has_toc
    if has_toc and words < TOC_MIN_WORDS:
        findings.append(finding(
            "toc-unneeded", "Table of contents on a %d-word README" % words, "P2", 1,
            "A TOC earns its scroll past roughly 1,500 words. Below that it is the first "
            "screen spent on navigation the reader did not need."))
    elif not has_toc and words > TOC_EXPECTED_WORDS:
        findings.append(finding(
            "toc-missing", "No table of contents at %d words" % words, "P2", 1,
            "Optional, not required (an explicit TOC heading appears in 12% of the corpus, "
            "anchor-list navigation in 32%), but this document is long enough to justify one."))


def strip_wrapped_urls(scored):
    """Blank every URL that already lives inside a link, an HTML attribute, an
    autolink, or a reference definition. What survives is bare. Blanking keeps
    the offsets, so the line numbers still point at the right place."""
    out = IMAGE_RX.sub(blank, scored)
    out = LINK_RX.sub(blank, out)
    out = HTML_ATTR_URL_RX.sub(blank, out)
    out = AUTOLINK_RX.sub(blank, out)
    out = REF_DEF_RX.sub(blank, out)
    # A URL inside backticks is part of a command or a config value, not a link
    # the reader is meant to click. Telling someone to wrap `curl https://...`
    # in markdown would break the thing they are supposed to paste.
    out = INLINE_CODE_RX.sub(blank, out)
    return out


def check_links(scored, findings, stats):
    # Link syntax inside backticks is being talked about, not used. A doc that
    # explains `[text][ref]` should not be reported as using it.
    scored = INLINE_CODE_RX.sub(blank, scored)
    inline = LINK_RX.findall(scored)
    refs = REF_LINK_RX.findall(scored)
    bare = list(BARE_URL_RX.finditer(strip_wrapped_urls(scored)))
    stats["inline_links"] = len(inline)
    stats["reference_links"] = len(refs)
    stats["bare_urls"] = len(bare)

    for m in bare[:20]:
        findings.append(finding(
            "bare-url", "Bare URL", "P1", line_of(scored, m.start()),
            "Wrap it: [what it is](%s). Only 3%% of corpus links are bare, and a bare one "
            "gives a screen reader nothing to announce." % m.group(0)[:60]))
    if len(bare) > 20:
        findings.append(finding(
            "bare-url", "%d more bare URLs" % (len(bare) - 20), "P1", 1,
            "Same fix throughout."))

    if refs:
        findings.append(finding(
            "reference-links", "%d reference-style links" % len(refs), "P2", 1,
            "Reference style is 0.2%% of corpus links, 14 out of 5,851. Use inline "
            "[text](url) unless the same few destinations repeat dozens of times."))

    for text, _url in inline:
        clean = re.sub(r"[*_`]", "", text).strip().lower().rstrip(".!")
        if clean in VAGUE_LINK_TEXT:
            m = re.search(re.escape("[" + text + "]"), scored)
            findings.append(finding(
                "vague-link-text", "Link text %r" % text, "P1",
                line_of(scored, m.start()) if m else 1,
                "Name the destination in a word or two, corpus average is 2.2 words. "
                "Link text is read out of context by screen readers and skimmers alike."))

    texts = [word_count(t) for t, _ in inline if t.strip()]
    stats["avg_link_text_words"] = round(statistics.mean(texts), 2) if texts else 0


def check_media_and_claims(raw, scored, findings, stats):
    # Header blocks are usually raw HTML, so counting only markdown images would
    # report zero badges on the majority of centered READMEs.
    image_urls = [u for _, u in IMAGE_RX.findall(raw)] + HTML_IMG_RX.findall(raw)
    badges = [u for u in image_urls if is_badge(u)]
    stats["badge_count"] = len(badges)
    stats["image_count"] = len(image_urls)
    stats["code_blocks"] = len(FENCE_RX.findall(raw))

    if len(badges) > BADGE_WALL:
        findings.append(finding(
            "badge-wall", "%d badges" % len(badges), "P2", 1,
            "Corpus median is 5 and the types that recur are license, version, stars, "
            "chat, and build. Past a dozen the marginal badge carries no information and "
            "dilutes the ones wired to something real."))

    if not stats["code_blocks"]:
        findings.append(finding(
            "no-code-block", "No code blocks", "P2", 1,
            "97% of the corpus has at least one. A command someone can paste beats a "
            "paragraph describing the command."))

    claims = list(CLAIM_RX.finditer(scored))
    stats["headline_claims"] = len(claims)
    if claims and not CAVEAT_RX.search(scored):
        m = claims[0]
        findings.append(finding(
            "uncaveated-claim", "Headline number with no caveat anywhere", "P1",
            line_of(scored, m.start()),
            "%r is asserted with nothing saying what it does not cover. The most credible "
            "READMEs in the study all argue against their own best stat somewhere: a number "
            "with a caveat reads as engineering, one without reads as marketing."
            % m.group(0).strip()))

    # Same noun, two different numbers. The failure mode of a README edited
    # piecemeal over months: a badge says "84 UI Styles" while a heading further
    # down says "Available Styles (67)".
    #
    # Only headings and badge alt text are compared. Running this over body prose
    # produced more than one finding per README in the corpus, nearly all of them
    # version strings and list counts, and a check that cries wolf gets ignored
    # along with the one real hit.
    prominent = []
    for m in HEADING_RX.finditer(scored):
        prominent.append((m.group(2), line_of(scored, m.start())))
    for m in IMAGE_RX.finditer(raw):
        prominent.append((m.group(1), line_of(raw, m.start())))

    pairs = {}
    for text, line in prominent:
        for m in NUMBER_NOUN_RX.finditer(text):
            noun = m.group(2).lower().rstrip("s")
            if noun in MEASURE_NOUNS or noun in {"the", "and", "for", "with", "from", "that", "this"}:
                continue
            pairs.setdefault(noun, {}).setdefault(m.group(1).replace(",", ""), line)
    for noun, values in pairs.items():
        if len(values) > 1 and len(noun) > 3:
            shown = ", ".join("%s (L%d)" % (v, ln) for v, ln in sorted(values.items()))
            findings.append(finding(
                "inconsistent-number", "%r appears with different numbers" % noun, "P2",
                min(values.values()),
                "%s. If it is the same count in both places it should be the same number, "
                "if it is not, say which is which." % shown))


def check_prose_shape(raw, scored, findings, stats):
    # Blank rather than delete, so a reported line number still points at the
    # line in the file. Blanked fences and tables also read as paragraph breaks,
    # which is what they are.
    prose = FENCE_RX.sub(blank, raw)
    prose = HEADING_RX.sub(blank, prose)
    prose = re.sub(r"(?m)^\|.*\|\s*$", blank, prose)
    prose = IMAGE_RX.sub(blank, prose)
    paragraphs, offset = [], 0
    for block in re.split(r"(\n\s*\n)", prose):
        body = block.strip()
        # A markup block is not a paragraph. A centered header or a <details>
        # language bar counts as several hundred "words" and would otherwise
        # dominate the findings while telling the writer nothing.
        if (body and not LIST_ITEM_RX.match(body) and not body.startswith(">")
                and not body.startswith("<")):
            paragraphs.append((body, offset))
        offset += len(block)
    stats["prose_words"] = word_count(prose)
    stats["paragraph_count"] = len(paragraphs)

    for body, off in paragraphs:
        n = word_count(body)
        if n > LONG_PARAGRAPH_WORDS:
            findings.append(finding(
                "long-paragraph", "Paragraph of %d words" % n, "P2", line_of(prose, off),
                "Corpus average is 28. Even the dense technical READMEs break into short "
                "paragraphs and tables rather than prose blocks."))

    pct = CORPUS["word_count_percentiles"]
    if stats["prose_words"] > pct["p90"]:
        findings.append(finding(
            "very-long", "%d words, above the corpus 90th percentile (%d)"
            % (stats["prose_words"], pct["p90"]), "P2", 1,
            "Long is fine when it is depth after a real quickstart. Check the quickstart is "
            "still on the first screen, and move reference material to docs/."))


# ---------------------------------------------------------------------------
# voice
# ---------------------------------------------------------------------------

def installed_voices():
    """Profile names in voices/, excluding the template."""
    if not os.path.isdir(VOICES_DIR):
        return []
    return sorted(f[:-len(".rules.json")] for f in os.listdir(VOICES_DIR)
                  if f.endswith(".rules.json") and not f.startswith("TEMPLATE"))


def resolve_voice(readme_path):
    """(path_to_rules, voice_name, note).

    Whoever is active governs. Nothing here knows or prefers a particular
    person: a `.rabbit-voice` file pins a repo's house voice, otherwise
    `voices/ACTIVE` decides, and only when neither exists does the one profile
    sitting in `voices/` get used as a fallback. That last case is announced in
    a note rather than assumed, because writing in the wrong person's register
    is worse than writing in none.
    """
    for base in (os.path.dirname(os.path.abspath(readme_path)), os.getcwd()):
        pin = os.path.join(base, ".rabbit-voice")
        if os.path.exists(pin):
            name = open(pin, encoding="utf-8").read().strip()
            rules = os.path.join(VOICES_DIR, name + ".rules.json")
            if os.path.exists(rules):
                return rules, name, "voice pinned by %s" % pin
            return None, name, ("%s names %r but voices/%s.rules.json does not exist"
                                % (pin, name, name))

    active = os.path.join(VOICES_DIR, "ACTIVE")
    name = ""
    if os.path.exists(active):
        name = open(active, encoding="utf-8").read().strip()
    if name:
        rules = os.path.join(VOICES_DIR, name + ".rules.json")
        if os.path.exists(rules):
            return rules, name, None
        return None, name, ("active voice %r has no .rules.json, so none of its rules are "
                            "mechanically enforced" % name)

    why = "voices/ACTIVE is missing" if not os.path.exists(active) else "voices/ACTIVE is empty"
    others = installed_voices()
    if len(others) == 1:
        return (os.path.join(VOICES_DIR, others[0] + ".rules.json"), others[0],
                "%s, falling back to the only profile installed (%s). Say so in the "
                "report, and offer voice-setup: this is probably not the user's voice"
                % (why, others[0]))
    if others:
        return None, None, ("%s and %d profiles are installed (%s). Name one with "
                            "--voice-rules rather than guessing"
                            % (why, len(others), ", ".join(others)))
    return None, None, "%s and no profile is installed, prose checked against craft rules only" % why


def load_scan():
    if not os.path.exists(SCAN_PATH):
        return None
    spec = importlib.util.spec_from_file_location("hw_scan", SCAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_prose_scan(raw, rules_path):
    scan = load_scan()
    if scan is None:
        return [], {}, "rabbit-writes/scripts/scan.py not found, prose not scanned"
    rules = None
    if rules_path:
        try:
            with open(rules_path, encoding="utf-8") as fh:
                rules = json.load(fh)
        except (OSError, ValueError) as exc:
            return [], {}, "could not read voice rules: %s" % exc
    # register 'docs': a README is documentation, not a blog post. The register
    # relaxes general craft rules only, never a voice rule.
    findings, stats = scan.scan(raw, "docs", True, rules)
    return findings, stats, None


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------

PRIORITY_TITLES = {"P0": "P0  a reader bounces here",
                   "P1": "P1  clear violation of the measured convention",
                   "P2": "P2  polish"}
BAND_TITLES = {"structure": "  structure and format (readme-writing)",
               "voice": "  voice (this writer's own rules)",
               "fingerprint": "  fingerprints (evidence about production)",
               "craft": "  craft (bad writing regardless of author)"}
BAND_ORDER = {"structure": 0, "voice": 1, "fingerprint": 2, "craft": 3}


def report(path, findings, stats, voice_name, notes):
    out = ["readme check: %s" % path,
           "voice: %s   words: %d   sections: %d   badges: %d"
           % (voice_name or "none", stats.get("prose_words", 0),
              len(stats.get("sections", [])), stats.get("badge_count", 0))]
    for note in notes:
        out.append("note: %s" % note)
    out.append("")

    if not findings:
        out.append("No mechanical findings. The judgment still has to happen: "
                   "run references/checklist.md.")
    for pri in ("P0", "P1", "P2"):
        group = [f for f in findings if f["priority"] == pri]
        if not group:
            continue
        out.append(PRIORITY_TITLES[pri])
        for band in ("structure", "voice", "fingerprint", "craft"):
            sub = [f for f in group if f["band"] == band]
            if not sub:
                continue
            out.append(BAND_TITLES[band])
            shown = {}
            for f in sub:
                shown[f["id"]] = shown.get(f["id"], 0) + 1
                if shown[f["id"]] > 4:
                    continue
                detail = f.get("detail") or f.get("match", "")
                out.append("    L%-4d %s" % (f["line"], f["label"]))
                if detail and band == "structure":
                    out.append("           %s" % detail)
            for fid, n in shown.items():
                if n > 4:
                    out.append("    ... and %d more %s" % (n - 4, fid))
        out.append("")

    pct = CORPUS["word_count_percentiles"]
    out.append("corpus comparison (100 trending repos)")
    rows = [
        ("prose words", stats.get("prose_words"), "median %d, p25 %d, p75 %d"
         % (pct["p50"], pct["p25"], pct["p75"])),
        ("paragraphs", stats.get("paragraph_count"), ""),
        ("first prose line", stats.get("pitch_line"), "the pitch belongs above the decoration"),
        ("code blocks", stats.get("code_blocks"), "97% of the corpus has at least one"),
        ("badges", stats.get("badge_count"), "corpus median 5, p90 14"),
        ("inline links", stats.get("inline_links"), "96.8% of corpus links"),
        ("bare URLs", stats.get("bare_urls"), "3.0% of corpus links, fix every one"),
        ("avg link text words", stats.get("avg_link_text_words"), "corpus 2.2"),
        ("license section words", stats.get("license_words"), "corpus median 13"),
    ]
    for name, value, note in rows:
        if value is None:
            continue
        out.append("  %-24s %-8s %s" % (name, value, note))
    if stats.get("avg_sentence_words"):
        out.append("  %-24s %-8s corpus median 13.3, mean 20.1"
                   % ("avg sentence words", stats["avg_sentence_words"]))
    if stats.get("burstiness"):
        out.append("  %-24s %-8s human range 0.45-1.10"
                   % ("burstiness", stats["burstiness"]))
    return "\n".join(out)


def check_readme(raw, readme_path, use_voice=True, voice_rules=None):
    scored = FENCE_RX.sub(blank, raw)
    findings, stats, notes = [], {}, []

    check_prose_shape(raw, scored, findings, stats)
    stats["sections"] = []
    check_structure(raw, scored, findings, stats)
    check_toc(scored, findings, stats)
    check_links(scored, findings, stats)
    check_media_and_claims(raw, scored, findings, stats)

    voice_name = None
    if use_voice:
        rules_path = voice_rules
        if rules_path is None:
            rules_path, voice_name, note = resolve_voice(readme_path)
            if note:
                notes.append(note)
        else:
            voice_name = os.path.basename(rules_path).replace(".rules.json", "")
        # The rules file is the floor. Point at the profile prose every run,
        # because a clean scan reads like a pass and the half that decides
        # whether this sounds like anyone is in the markdown.
        if rules_path:
            profile = rules_path.replace(".rules.json", ".md")
            if os.path.exists(profile):
                notes.append("read %s too, the rules file is only the "
                             "regex-checkable subset of it" % profile)
        prose_findings, prose_stats, note = run_prose_scan(raw, rules_path)
        if note:
            notes.append(note)
        findings.extend(prose_findings)
        for key in ("avg_sentence_words", "burstiness", "mattr", "em_dashes_per_1k"):
            if key in prose_stats:
                stats[key] = prose_stats[key]

    findings.sort(key=lambda f: ({"P0": 0, "P1": 1, "P2": 2}[f["priority"]],
                                 BAND_ORDER.get(f["band"], 9), f["line"]))
    return findings, stats, voice_name, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="the README to check")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--no-voice", action="store_true",
                    help="skip the prose and voice scan, check structure only")
    ap.add_argument("--voice-rules", metavar="PATH",
                    help="a voice's <name>.rules.json; overrides .rabbit-voice and ACTIVE")
    ap.add_argument("--check", action="store_true", help="exit 1 if any P0 finding is present")
    args = ap.parse_args()

    try:
        with open(args.file, encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as exc:
        print("readme_check: %s" % exc, file=sys.stderr)
        return 2

    findings, stats, voice_name, notes = check_readme(
        raw, args.file, use_voice=not args.no_voice, voice_rules=args.voice_rules)

    if args.json:
        print(json.dumps({
            "file": args.file,
            "voice": voice_name,
            "notes": notes,
            "stats": stats,
            "corpus": CORPUS,
            "counts": {
                "P0": sum(1 for f in findings if f["priority"] == "P0"),
                "P1": sum(1 for f in findings if f["priority"] == "P1"),
                "P2": sum(1 for f in findings if f["priority"] == "P2"),
                "structure": sum(1 for f in findings if f["band"] == "structure"),
                "voice": sum(1 for f in findings if f["band"] == "voice"),
                "fingerprint": sum(1 for f in findings if f["band"] == "fingerprint"),
                "craft": sum(1 for f in findings if f["band"] == "craft"),
            },
            "findings": findings,
        }, indent=2))
    else:
        print(report(args.file, findings, stats, voice_name, notes))

    if args.check and any(f["priority"] == "P0" for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
