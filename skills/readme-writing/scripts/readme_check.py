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

One check reads outside the file. Given a README that exists on disk, the
licence cross-check walks up to the repository root looking for a LICENSE,
LICENCE, or COPYING file, and reports either direction of the mismatch: a file
the README never names, or a License section over a tree with no file in it.
A walk that never finds a root stays silent rather than guessing.

Usage:
    python3 readme_check.py README.md
    python3 readme_check.py README.md --json
    python3 readme_check.py README.md --check          # exit 1 on any P0
    python3 readme_check.py README.md --no-voice       # no style profile
    python3 readme_check.py README.md --voice-rules path/to/dana.rules.json

Voice resolution, in order: --voice-rules, then a .rabbit-voice file beside
the README or in the working directory, then skills/rabbit-writes/voices/ACTIVE.
A missing voice is reported as a note, never an error: plenty of projects have
no profile, and failing the run would just teach people to pass --no-voice.

--no-voice turns off the style profile, not the reading. Structure, fingerprints
and craft are all still checked, because a pasted citation marker is evidence
about how a file was made and has nothing to do with whose voice it is in.

Exit codes: 0, or 1 with --check when a P0 is present, or 2 when the README
itself cannot be read, or when --voice-rules names a profile that cannot be
read. A voice that cannot be *resolved* is a note and still exits 0, for the
reason above. A profile asked for by name is different, and matches scan.py: a
clean voice band on a profile nobody read is a false pass.
Stdlib only, 3.9+.
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
# rwlib lives beside scan.py. Resolved from SCAN_PATH rather than spelled out
# again, so the two cannot end up pointing at different checkouts.
RWLIB_PARENT = os.path.dirname(SCAN_PATH)
if RWLIB_PARENT not in sys.path:
    sys.path.insert(0, RWLIB_PARENT)

from rwlib import corpus as corpus_mod            # noqa: E402
from rwlib import findings as findings_mod        # noqa: E402
from rwlib import language, sarif, suppress       # noqa: E402
from rwlib import voices as voices_mod            # noqa: E402
from rwlib.markdown import (BARE_URL_RX, FENCE_RX, HEADING_RX,  # noqa: E402
                            HTML_ANCHOR_RX, HTML_IMG_RX, HTML_TAG_LINE_RX,
                            HTML_TAG_RX, IMAGE_RX, INLINE_CODE_RX, LINK_RX,
                            REF_DEF_RX, REF_LINK_RX, TABLE_ROW_RX, blank,
                            is_badge, is_prose_block, line_of, strip_images,
                            strip_wrapped_urls, word_count)
from rwlib.sections import LATE_SECTIONS, classify_heading  # noqa: E402

# ---------------------------------------------------------------------------
# corpus constants. Every number comes from docs/readme-analysis, reduced to the
# subset this script uses and committed as corpus_summary.json so the skill
# still works when installed without the research data.
#
# It used to be a literal dict here with a comment promising it mirrored the
# aggregate. Nothing checked the promise, so regenerating the corpus silently
# orphaned these thresholds: the script kept quoting a median that had moved.
# scripts/validate.py now compares the two whenever the research data is
# present, and 05_export_corpus_summary.py regenerates this file.
# ---------------------------------------------------------------------------

CORPUS = corpus_mod.load(os.path.join(HERE, "corpus_summary.json"))

TOC_MIN_WORDS = 1500          # below this a TOC costs more scroll than it saves
TOC_EXPECTED_WORDS = 2500     # above this its absence is worth a note
# Non-blank lines above the first prose sentence, measured across the corpus:
# median 5, p75 14, p90 23. Past 25 a README is in the worst decile of the
# sample, which is where the named anti-pattern cases sit.
PITCH_HEAVY_HEADER = 15
PITCH_MAX_NONBLANK_LINES = 25
LONG_PARAGRAPH_WORDS = 60     # checklist item 8
BADGE_WALL = 12               # corpus median 5, p75 8, p90 14

# Anchor text that tells a reader nothing out of context, which is how a screen
# reader and a skimmer both encounter it. Kept here rather than in rwlib because
# it is a README convention rather than a fact about markdown.
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


def finding(fid, label, priority, line, detail):
    """A structure finding, in the schema every other checker here uses.

    The explanation goes in `excerpt`, which is where a reporter looks for the
    second line. It used to go in a key called `detail` that only this file
    emitted, so the reporter had to branch on the band to find its own text and
    no downstream consumer could read both checkers with one parser.

    `match` is left empty on purpose. Most of these findings are about the
    document rather than about a span in it, and inventing a span would put a
    matched-text's worth of confidence behind a whole-file judgement.
    """
    return findings_mod.make(fid, label, "structure", priority, line,
                             excerpt=detail)


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

    Returns the line number alone. It used to return a non-blank line count with
    it that no caller used, counted to a different boundary than the one
    check_structure computes for itself (this one included the pitch line), and
    two live definitions of "lines above the pitch" is a drift waiting to happen.
    """
    # Whether a markdown heading is allowed to close an open HTML block, decided
    # once for the whole document rather than at each heading. Inside a
    # well-formed <details> a heading is content: a language bar routinely holds
    # `# Project` and a translated tagline, and treating that heading as the end
    # of the block hands back the collapsed translation as the pitch. When the
    # tags do not balance, no heading can be inside anything, so closing on one
    # is the repair rather than the bug.
    opens = len(HTML_BLOCK_OPEN_RX.findall(raw))
    closes = len(HTML_BLOCK_CLOSE_RX.findall(raw))
    line = scan_for_pitch(raw, heading_closes_blocks=opens != closes)
    if line is None:
        # Backstop for an unclosed <table> or <details>. The depth counter has no
        # way to know a block was never closed, so it stays positive to the end of
        # the file, every later line skips, and a README that describes itself
        # perfectly well reports no-pitch, which is a P0 and a CI failure under
        # --check. Hand-written sponsor grids drop a </table> often enough and
        # GitHub renders them anyway. A pass that ignores the blocks cannot make
        # that mistake, and it only runs when the careful pass found nothing at
        # all, so it costs a well-formed README nothing.
        line = scan_for_pitch(raw, skip_html_blocks=False)
    return line


HTML_BLOCK_OPEN_RX = re.compile(r"(?i)<(?:details|table)\b")
HTML_BLOCK_CLOSE_RX = re.compile(r"(?i)</(?:details|table)>")
# A line that opens a fence, whether or not anything ever closes it. Only used
# as a backstop against FENCE_RX, which requires the pair.
OPEN_FENCE_RX = re.compile(r"^```", re.M)


def scan_for_pitch(raw, skip_html_blocks=True, heading_closes_blocks=False):
    in_comment = False
    details_depth = 0
    for i, line in enumerate(raw.splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        if in_comment:
            in_comment = "-->" not in s
            continue
        if s.startswith("<!--"):
            in_comment = "-->" not in s
            continue
        if s.startswith("#"):
            if heading_closes_blocks:
                details_depth = 0
            continue
        # <details> hides a language bar or an FAQ, and an HTML <table> at the
        # top of a README is a sponsor grid in almost every case. Neither is
        # where the project describes itself.
        # Clamped, because README fragments and hand-written HTML close tags
        # they never opened. Left negative, the counter never climbs back above
        # zero and the next real <details> block reads as prose.
        details_depth += len(HTML_BLOCK_OPEN_RX.findall(s))
        details_depth -= len(HTML_BLOCK_CLOSE_RX.findall(s))
        details_depth = max(0, details_depth)
        if skip_html_blocks and (details_depth > 0
                                 or re.search(r"(?i)<summary\b", s)):
            continue
        if (s.startswith(">") or s.startswith("|")
                or s.startswith("```") or set(s) <= set("-=*_ ")):
            continue
        if HTML_TAG_LINE_RX.match(s):
            s = HTML_TAG_RX.sub(" ", s)
        stripped = IMAGE_RX.sub("", s)
        stripped = LINK_RX.sub(r"\1", stripped)
        stripped = re.sub(r"[*_`#>|]", "", stripped).strip()
        stripped = re.sub(r"^[-*+]\s+", "", stripped)
        if word_count(stripped) >= 5:
            return i
    return None


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
    pitch_line = find_pitch(raw)
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
            "(avg. position 0.34). Give the reader a copy-pasteable path to running it."))
    else:
        install_at = cats.index("installation")
        late_first = next((c for c in cats[:install_at] if c in LATE_SECTIONS), None)
        if late_first:
            findings.append(finding(
                "install-late", "Install comes after %s" % late_first, "P1",
                sections[install_at]["line"],
                "%s sits at avg. position %.2f in the corpus, installation at 0.34. "
                "Get the reader running the thing before the community mechanics."
                % (late_first, CORPUS["section_avg_position"].get(late_first, 0.8))))

    # --- license: last, and short
    if "license" in cats:
        # The last license heading, not the first. A README that mentions the
        # licence early, in a "License and credits" line near the header or in a
        # feature list, and carries the real License section at the end used to
        # have its position checked against the mention: every section between
        # the two counted as "after the license", and a file that ends with its
        # license reported license-not-last. The last one is the one whose
        # position the corpus figure describes.
        idx = len(cats) - 1 - cats[::-1].index("license")
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


# Every spelling of the file, across the licences and the two Englishes. Matched
# case-insensitively against the whole name, because `LICENSE`, `LICENSE.md`,
# `LICENSE.txt`, `license`, and `COPYING` are all in the wild and none of them is
# wrong. `COPYING.LESSER` and `LICENSE-MIT` come along with the prefix test.
LICENSE_FILE_PREFIXES = ("license", "licence", "copying", "copyright")


def find_license_file(readme_path, max_up=8):
    """(path to the licence file or None, whether the repository root was seen).

    Walks up from the README's own directory, because a `docs/README.md` is
    governed by the `LICENSE` at the repository root, and calling that project
    unlicensed is exactly the false assertion this skill's checklist is about.
    The walk stops at the directory holding `.git`: past the repository root the
    answer would be somebody else's licence, or the home directory's.

    The second value is why this returns a pair. A walk that runs out of depth
    without ever finding a root does not know where the project ends, so it
    cannot say a file is *absent* -- only that it did not find one. The caller
    reports a missing licence only when the root was reached. `max_up` is a
    runaway guard on an unbounded walk, not the real limit.
    """
    directory = os.path.dirname(os.path.abspath(readme_path))
    for _ in range(max_up + 1):
        try:
            names = os.listdir(directory)
        except OSError:
            return None, False
        for name in sorted(names):
            if (name.lower().startswith(LICENSE_FILE_PREFIXES)
                    and os.path.isfile(os.path.join(directory, name))):
                return os.path.join(directory, name), True
        if ".git" in names:
            return None, True
        parent = os.path.dirname(directory)
        if parent == directory:
            return None, True          # filesystem root: the walk is over
        directory = parent
    return None, False


def check_license_file(readme_path, findings, stats):
    """Cross-check the README's licence claim against the tree it sits in.

    The checklist has said "check for a LICENSE file rather than guessing" since
    the skill shipped, and nothing did: this script read the README and only the
    README, so both halves of the mismatch were invisible to it. A README's most
    common failure mode is asserting something false, and "MIT" over an empty
    directory is that failure in its purest form.

    Only runs on a README that exists on disk. Scanning a string through a
    temporary file has no tree around it, and every such run would otherwise
    report a missing licence file for a repository nobody named.
    """
    if not readme_path or not os.path.isfile(readme_path):
        return
    has_section = "license" in stats.get("sections", [])
    path, saw_root = find_license_file(readme_path)
    stats["license_file"] = os.path.basename(path) if path else None

    if path and not has_section:
        # The hedge in `no-license` is there because this script could not see
        # the tree. Now that it can, and the file is sitting right there, the
        # finding is a fact rather than a prompt to go and look.
        for entry in findings:
            if entry["id"] == "no-license":
                entry["priority"] = "P1"
                entry["excerpt"] = (
                    "%s is sitting beside this README and the README does not "
                    "name it. 72%% of the corpus does. One line at the end: the "
                    "licence name and a link to the file."
                    % os.path.basename(path))
                break
    elif has_section and not path and saw_root:
        findings.append(finding(
            "license-file-missing",
            "License section with no license file in the tree", "P1", 1,
            "The README has a License section and there is no LICENSE, LICENCE, "
            "or COPYING file here or in any parent up to the repository root. "
            "Either the file is missing from the repository, in which case a "
            "reader cannot act on the section, or it is somewhere this check "
            "does not look. Confirm before publishing: a licence a project does "
            "not actually carry is the most expensive thing a README can get "
            "wrong."))


def check_toc(scored, findings, stats):
    words = stats["prose_words"]
    anchor_links = [u for _, u in LINK_RX.findall(strip_images(scored))
                    if u.startswith("#")]
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


def check_links(scored, findings, stats):
    # Link syntax inside backticks is being talked about, not used. A doc that
    # explains `[text][ref]` should not be reported as using it.
    scored = INLINE_CODE_RX.sub(blank, scored)
    linkable = strip_images(scored)
    inline_matches = list(LINK_RX.finditer(linkable))
    inline = [(m.group(1), m.group(2)) for m in inline_matches]
    # An empty label means the link text is the label: `[Astro][]` resolves
    # against `[astro]: https://...`. Labels are case-insensitive in every
    # markdown implementation GitHub uses.
    defined = {m.group(1).strip().lower()
               for m in REF_DEF_RX.finditer(scored)}
    refs = [(text, label) for text, label in REF_LINK_RX.findall(scored)
            if (label.strip() or text.strip()).lower() in defined]
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

    # Iterated as matches, not as findall pairs: three "here" links searched by
    # text all resolve to the first occurrence, and the writer gets sent to the
    # same line three times.
    #
    # HTML anchors are checked alongside markdown ones. The study counts HTML as
    # the third link style and 76% of the corpus centers its header, so a
    # <a href="...">click here</a> in a header block is exactly where this
    # failure lives, and checking only markdown lets the worst case through.
    vague_candidates = [(m.group(1), m.start()) for m in inline_matches]
    vague_candidates += [(m.group(1), m.start())
                         for m in HTML_ANCHOR_RX.finditer(scored)]
    for text, start in vague_candidates:
        clean = re.sub(r"[*_`]", "", HTML_TAG_RX.sub("", text))
        clean = re.sub(r"\s+", " ", clean).strip().lower().rstrip(".!")
        if clean in VAGUE_LINK_TEXT:
            findings.append(finding(
                "vague-link-text", "Link text %r" % text.strip(), "P1",
                line_of(scored, start),
                "Name the destination in a word or two, corpus average is 2.2 words. "
                "Link text is read out of context by screen readers and skimmers alike."))

    texts = [word_count(t) for t, _ in inline if t.strip()]
    stats["avg_link_text_words"] = round(statistics.mean(texts), 2) if texts else 0


CAVEAT_WINDOW_LINES = 3


def caveat_near(scored, index):
    """True when a caveat sits with the claim at `index` rather than anywhere.

    Scoped, because one "results vary" buried in an FAQ used to excuse every
    headline number in the header, and a caveat the reader never reaches beside
    the number is not a caveat. The primary scope is the section: the span from
    the enclosing heading to the next one. The line window is the escape hatch
    for a caveat that lands just over a heading boundary, and it is deliberately
    small, because widening it far enough to cross a section reinstates the bug.
    """
    starts = [m.start() for m in HEADING_RX.finditer(scored)]
    lo = max((s for s in starts if s <= index), default=0)
    hi = min((s for s in starts if s > index), default=len(scored))
    if CAVEAT_RX.search(scored[lo:hi]):
        return True
    lines = scored.split("\n")
    n = scored.count("\n", 0, index)
    window = "\n".join(lines[max(0, n - CAVEAT_WINDOW_LINES):
                             n + CAVEAT_WINDOW_LINES + 1])
    return bool(CAVEAT_RX.search(window))


def check_media_and_claims(raw, scored, findings, stats):
    # Header blocks are usually raw HTML, so counting only markdown images would
    # report zero badges on the majority of centered READMEs.
    #
    # Read from the fence-blanked copy, not from raw: a README that shows badge
    # markdown inside a fenced example is documenting badges, not wearing them,
    # and counting those inflates badge_count until badge-wall fires on a file
    # with no badge in it. HTML headers are not fenced, so blanking loses
    # nothing. Only the fence count itself has to come from raw.
    image_urls = [u for _, u in IMAGE_RX.findall(scored)] + HTML_IMG_RX.findall(scored)
    badges = [u for u in image_urls if is_badge(u)]
    stats["badge_count"] = len(badges)
    stats["image_count"] = len(image_urls)
    stats["code_blocks"] = len(FENCE_RX.findall(raw))
    if not stats["code_blocks"] and OPEN_FENCE_RX.search(raw):
        # Backstop for a final fence nobody closed, in the shape of the one
        # find_pitch keeps for an unclosed <table>. FENCE_RX needs a closing
        # delimiter, so a README whose last block runs to end of file counts
        # zero and reports no-code-block, which is visibly false: GitHub renders
        # the block anyway. The strict count runs first and this only fires when
        # it found nothing at all, so a well-formed README never reaches it.
        #
        # Only the count is repaired. The unclosed block's body still survives
        # the blanking below and in check_prose_shape, so its contents are
        # measured as prose. Fixing that means teaching FENCE_RX about a fence
        # with no end, which moves every number this file reports.
        stats["code_blocks"] = 1

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
    uncaveated = [m for m in claims if not caveat_near(scored, m.start())]
    stats["uncaveated_claims"] = len(uncaveated)
    if uncaveated:
        m = uncaveated[0]
        findings.append(finding(
            "uncaveated-claim", "Headline number with no caveat near it", "P1",
            line_of(scored, m.start()),
            "%r is asserted with nothing nearby saying what it does not cover. The most "
            "credible READMEs in the study all argue against their own best stat where "
            "the stat is: a number with a caveat reads as engineering, one without reads "
            "as marketing. %d of %d headline numbers here have no caveat in their section."
            % (m.group(0).strip(), len(uncaveated), len(claims))))

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
    for m in IMAGE_RX.finditer(scored):
        prominent.append((m.group(1), line_of(scored, m.start())))

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


def check_prose_shape(raw, findings, stats):
    # Blank rather than delete, so a reported line number still points at the
    # line in the file. Blanked fences and tables also read as paragraph breaks,
    # which is what they are.
    prose = FENCE_RX.sub(blank, raw)
    prose = HEADING_RX.sub(blank, prose)
    prose = TABLE_ROW_RX.sub(blank, prose)
    prose = IMAGE_RX.sub(blank, prose)
    paragraphs, offset = [], 0
    for block in re.split(r"(\n\s*\n)", prose):
        body = block.strip()
        # A markup block is not a paragraph. A centered header or a <details>
        # language bar counts as several hundred "words" and would otherwise
        # dominate the findings while telling the writer nothing.
        if (body and not body.startswith(">") and not body.startswith("<")
                and is_prose_block(body)):
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

# Both from rwlib.voices, which is where a rules path becomes a profile name for
# every other caller too. Restating the suffix here was two homes for one fact.
RULES_SUFFIX = voices_mod.RULES_SUFFIX
strip_rules_suffix = voices_mod.strip_rules_suffix


def resolve_voice(readme_path):
    """Which profile applies to this README, and why.

    A thin alias. The resolution order (`.rabbit-voice`, then `voices/ACTIVE`,
    then a lone installed profile) used to be written out here and nowhere else,
    so `scan.py` next door had none of it and the two checkers in one plugin
    could disagree about whose rules were in force. It lives in rwlib.voices
    now. The name stays because the report and the tests speak it.
    """
    return voices_mod.resolve(readme_path, voices_dir=VOICES_DIR)


def load_scan():
    if not os.path.exists(SCAN_PATH):
        return None
    spec = importlib.util.spec_from_file_location("hw_scan", SCAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_prose_scan(raw, rules_path, required=False):
    """(findings, stats, note) for the prose half of the report.

    A voice that cannot be loaded never cancels the scan. It used to return an
    empty finding list, so `--voice-rules <typo>` printed "No mechanical
    findings" and exited 0 on a README with `citeturn0search0` in it: the
    fingerprint band, which has nothing to do with whose voice it is in,
    disappeared along with the profile.

    `required` is set when --voice-rules named the file by hand. Then the error
    is raised instead, and main() exits 2 the way scan.py does, because
    reporting a clean voice band on a profile nobody read is worse than
    stopping. A profile that was merely *resolved* stays a note: plenty of
    projects have none, and failing there teaches people to pass --no-voice.
    """
    scan = load_scan()
    if scan is None:
        return [], {}, "rabbit-writes/scripts/scan.py not found, prose not scanned"
    rules, note = None, None
    if rules_path:
        try:
            rules = voices_mod.load(rules_path, voices_dir=VOICES_DIR)
        except voices_mod.VoiceError as exc:
            if required:
                raise
            note = ("%s. No voice band in this report, everything else still "
                    "ran" % exc)
    # register 'docs': a README is documentation, not a blog post. The register
    # relaxes general craft rules only, never a voice rule.
    findings, stats = scan.scan(raw, "docs", True, rules,
                                suppressions=False)
    return findings, stats, note


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------

PRIORITY_TITLES = {"P0": "P0  a reader bounces here",
                   "P1": "P1  clear violation of the measured convention",
                   "P2": "P2  polish"}
BAND_TITLES = {"safety": "  safety (concealed text, or text aimed at an agent)",
               "structure": "  structure and format (readme-writing)",
               "voice": "  voice (this writer's own rules)",
               "fingerprint": "  fingerprints (evidence about production)",
               "craft": "  craft (bad writing regardless of author)"}
BAND_ORDER = {"safety": 0, "structure": 1, "voice": 2, "fingerprint": 3,
              "craft": 4}


def report(path, findings, stats, voice_name, notes):
    out = ["readme check: %s" % path,
           "voice: %s   words: %d   sections: %d   badges: %d"
           % (voice_name or "none", stats.get("prose_words", 0),
              len(stats.get("sections", [])), stats.get("badge_count", 0))]
    for note in notes:
        out.append("note: %s" % note)
    out.append("")

    # Held out of the priority sections and printed under their own heading
    # below. Reported, never hidden: see rwlib/suppress.py.
    allowed = suppress.suppressed(findings)
    findings = suppress.live(findings)

    if not findings:
        out.append("No mechanical findings. The judgment still has to happen: "
                   "run references/checklist.md.")
    for pri in ("P0", "P1", "P2"):
        group = [f for f in findings if f["priority"] == pri]
        if not group:
            continue
        out.append(PRIORITY_TITLES[pri])
        for band in ("safety", "structure", "voice", "fingerprint", "craft"):
            sub = [f for f in group if f["band"] == band]
            if not sub:
                continue
            out.append(BAND_TITLES[band])
            shown = {}
            for f in sub:
                shown[f["id"]] = shown.get(f["id"], 0) + 1
                if shown[f["id"]] > 4:
                    continue
                out.append("    L%-4d %s" % (f["line"], f["label"]))
                if band == "structure" and f["excerpt"]:
                    out.append("           %s" % f["excerpt"])
            for fid, n in shown.items():
                if n > 4:
                    out.append("    ... and %d more %s" % (n - 4, fid))
        out.append("")

    if allowed:
        out.append("suppressed by rabbit-allow (%d, not counted above)"
                   % len(allowed))
        for f in allowed:
            out.append("    L%-4d %s" % (f["line"], f["label"]))
            out.append("           allowed at L%d: %s"
                       % (f["suppressed_at"], f["suppressed"]))
        out.append("")

    pct = CORPUS["word_count_percentiles"]
    link = CORPUS["link_style_pct"]
    # Dated, because the study is a frozen snapshot skewed toward whatever was
    # trending the week it was taken. Undated, "100 trending repos" reads as a
    # standing fact, and a reader two years out has no way to discount it
    # without going and finding the writeup.
    measured = CORPUS.get("measured_at")
    out.append("corpus comparison (%d trending repos%s)"
               % (CORPUS["n_repos"], ", %s" % measured if measured else ""))
    rows = [
        ("prose words", stats.get("prose_words"), "median %d, p25 %d, p75 %d"
         % (pct["p50"], pct["p25"], pct["p75"])),
        ("paragraphs", stats.get("paragraph_count"), ""),
        ("first prose line", stats.get("pitch_line"), "the pitch belongs above the decoration"),
        ("code blocks", stats.get("code_blocks"),
         "%g%% of the corpus has at least one" % CORPUS["pct_has_code_blocks"]),
        ("badges", stats.get("badge_count"),
         "corpus median %d, p90 14" % CORPUS["median_badge_count"]),
        ("inline links", stats.get("inline_links"),
         "%g%% of corpus links" % link["inline"]),
        ("bare URLs", stats.get("bare_urls"),
         "%g%% of corpus links, fix every one" % link["bare"]),
        ("avg link text words", stats.get("avg_link_text_words"),
         "corpus %g" % CORPUS["avg_link_text_words"]),
        ("license section words", stats.get("license_words"),
         "corpus median %g" % CORPUS["median_license_words"]),
    ]
    # Reported whichever way it came out, including "none". A checker that only
    # speaks up when it found something leaves the reader unable to tell a clean
    # cross-check from one that never ran.
    if "license_file" in stats:
        rows.append(("license file", stats["license_file"] or "none found",
                     "beside the README or up to the repository root"))
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

    # Takes raw, not scored: it blanks its own fences, because it also has to
    # blank headings, tables, and images, and one copy blanked to one recipe is
    # easier to reason about than a second copy blanked to another.
    check_prose_shape(raw, findings, stats)
    stats["sections"] = []
    check_structure(raw, scored, findings, stats)
    check_toc(scored, findings, stats)
    check_links(scored, findings, stats)
    check_media_and_claims(raw, scored, findings, stats)
    # After check_structure, which is what fills stats["sections"], and after
    # the no-license finding it may sharpen.
    check_license_file(readme_path, findings, stats)

    # The prose scan runs either way. `use_voice` decides whether a person's
    # style rules apply, not whether the document gets read: a pasted citation
    # marker or an unfilled placeholder is a P0 about how the file was produced,
    # and skipping it because nobody set a voice is how the pre-commit hook came
    # to check a stranger's structure while ignoring `citeturn0search0` in it.
    voice_name, rules_path = None, None
    if use_voice:
        rules_path = voice_rules
        if rules_path is None:
            rules_path, voice_name, note = resolve_voice(readme_path)
            if note:
                notes.append(note)
        else:
            voice_name = strip_rules_suffix(os.path.basename(rules_path))
        # The rules file is the floor. Point at the profile prose every run,
        # because a clean scan reads like a pass and the half that decides
        # whether this sounds like anyone is in the markdown.
        if rules_path:
            profile = strip_rules_suffix(rules_path) + ".md"
            if os.path.exists(profile):
                notes.append("read %s too, the rules file is only the "
                             "regex-checkable subset of it" % profile)

    prose_findings, prose_stats, note = run_prose_scan(
        raw, rules_path, required=bool(use_voice and voice_rules))
    if note:
        notes.append(note)
    findings.extend(prose_findings)
    for key in ("avg_sentence_words", "burstiness", "mattr", "em_dashes_per_1k"):
        if key in prose_stats:
            stats[key] = prose_stats[key]

    note = language.note(raw)
    if note:
        notes.append(note)

    # Inline `rabbit-allow` comments cover the structure half too. The prose
    # half arrives already marked, because scan.scan applies them itself, and
    # apply() skips a finding that is already suppressed so the reason does not
    # get overwritten by a second pass over the same comments.
    allowances, problems = suppress.parse(raw)
    used, refused = suppress.apply(findings, allowances)
    findings.extend(suppress.audit(allowances, problems, used,
                                   findings_mod.make, refused))

    findings.sort(key=findings_mod.sort_key)
    return findings, stats, voice_name, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="the README to check")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--sarif", action="store_true",
                    help="SARIF 2.1.0, for GitHub pull request annotations")
    ap.add_argument("--sarif-uri", metavar="PATH",
                    help="the path to record in the SARIF output, relative to the "
                         "repository root. Defaults to the file argument")
    ap.add_argument("--no-voice", action="store_true",
                    help="apply no voice profile. Structure, fingerprints and "
                         "craft are still checked")
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

    try:
        findings, stats, voice_name, notes = check_readme(
            raw, args.file, use_voice=not args.no_voice,
            voice_rules=args.voice_rules)
    except voices_mod.VoiceError as exc:
        # Only reachable from an explicit --voice-rules. Same exit code and same
        # reasoning as scan.py: a profile asked for by name and not read is an
        # error, because the alternative is a clean voice band on a document
        # nobody checked against it.
        print("readme_check: %s" % exc, file=sys.stderr)
        return 2

    if args.sarif:
        print(json.dumps(sarif.build(
            findings, args.sarif_uri or args.file, "rabbit-writes/readme-check",
            tool_version=CORPUS.get("schema_version"),
            information_uri="https://github.com/whit3rabbit/rabbit-writes",
            extra_properties={"corpusRepos": CORPUS["n_repos"],
                              "corpusMeasuredAt": CORPUS.get("measured_at"),
                              "voice": voice_name}), indent=2))
    elif args.json:
        print(json.dumps({
            "schema_version": findings_mod.SCHEMA_VERSION,
            "file": args.file,
            "voice": voice_name,
            "notes": notes,
            "stats": stats,
            "corpus": CORPUS,
            "counts": findings_mod.counts(findings),
            "findings": findings,
        }, indent=2))
    else:
        print(report(args.file, findings, stats, voice_name, notes))

    # A suppressed P0 does not fail the run, the same as scan.py. That is the
    # point of the mechanism, and it is why the reason is mandatory and the
    # finding is printed anyway.
    if args.check and any(f["priority"] == "P0" and "suppressed" not in f
                          for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
