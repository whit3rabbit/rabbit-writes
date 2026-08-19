#!/usr/bin/env python3
"""
The one home for the academic-corpus pipeline's shared facts.

Why this corpus exists. `registers.json` is about to grow an `academic`
column, and the repository's own rule is that a new detector gets calibrated
against real documents before it is wired to anything. The 100-README corpus
that calibrated the safety band is the wrong instrument here: a README is not
a paper, and the vocabulary question this register turns on (`significant` as
a statistical term, `effective` as an outcome variable) does not arise in one.

Source choice is a decision, so it is recorded where the source is named.
PLOS is the whole corpus because every PLOS article is CC BY 4.0 and says so
in machine-readable form inside its own JATS XML, which `license_of` reads and
`01_fetch_corpus.py` refuses to proceed without. The PMC Open Access subset was
considered and dropped for this pass: its licenses vary per article, several are
non-commercial or no-derivatives, and each one needs a check that PLOS makes
unnecessary. Adding PMC later means adding a fetcher, not relaxing `LICENSE_OK`.

Storage follows `scripts/detector-corpus/`, and for the same reason. The
manifest commits the DOI, the license, the source URL, the per-section word
counts, and a SHA-256 of the extracted text. The prose itself stays out of git.
Anybody can refetch and get the same hashes, which makes a published number
checkable by somebody who does not trust us, without this repository
redistributing 20 papers to make its point. CC BY would permit the
redistribution. It does not oblige it, and hashes travel better than 800KB.

Which sections. Abstract, introduction, results, and discussion or conclusion.
Those four are prose, and they are where the register's characteristic
vocabulary actually lives: `significant` and `effective` in results, the
inflation words in the introduction and discussion. Methods is skipped because
it is procedural text full of equations and reagent lists, and scoring it would
measure the genre of a protocol rather than the register of a paper. References
are skipped for the obvious reason.

Stdlib only, 3.9+.
"""

import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE_SCRIPTS = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")

CORPUS_DIR = os.path.join(REPO_ROOT, "docs", "academic-corpus")
MANIFEST_PATH = os.path.join(CORPUS_DIR, "manifest.json")
SUMMARY_PATH = os.path.join(CORPUS_DIR, "summary.json")
# Where the extracted prose goes. Ignored by git: see the module docstring.
TEXTS_DIR = os.path.join(CORPUS_DIR, "texts")

USER_AGENT = "rabbit-writes-academic-research/1.0 (+https://github.com/whit3rabbit)"

SEARCH_URL = "https://api.plos.org/search"
# The manuscript route serves JATS XML for any PLOS DOI regardless of which
# journal published it, which is why the DOI alone is enough to refetch.
ARTICLE_URL = "https://journals.plos.org/plosone/article/file?id=%s&type=manuscript"

# Subject facets, so the corpus is a register rather than one field's habits.
# A vocabulary exemption calibrated only on computer science would exempt
# whatever computer scientists happen to overuse.
SUBJECTS = (
    "Computer and information sciences",
    "Social sciences",
    "Biology and life sciences",
    "Medicine and health sciences",
    "Physical sciences",
    "Ecology and environmental sciences",
)
PAPERS_PER_SUBJECT = 4
# The oldest paper the discovery query will accept. This corpus calibrates a
# register against how people write now, and PLOS articles from 2003 carry no
# machine-readable <license> element either, so the first discovery run pinned
# fifteen papers the fetcher then refused.
EARLIEST = "2022-01-01T00:00:00Z"

# Exactly Creative Commons Attribution, with no further clause. `by-nc` and
# `by-nd` are rejected rather than judged, because the judgment is a lawyer's
# and the corpus does not need them: PLOS is uniformly plain BY.
LICENSE_OK = re.compile(r"creativecommons\.org/licenses/by/[0-9.]+")

# A DOI is a filename inside TEXTS_DIR once slugified, so it is bounded to the
# PLOS shape rather than trusted. The manifest is trusted as code, and a trust
# boundary is checked everywhere it is crossed.
DOI_RX = re.compile(r"^10\.1371/journal\.[a-z]+\.[0-9]+$")

REQUIRED_FIELDS = ("doi", "journal", "subject", "published", "license",
                   "source_url", "sha256", "words", "sections")

# Section titles that map onto the four slots kept. Matched case-insensitively
# against the whole title, so a section called "Results and discussion" lands
# in both lists once rather than being dropped for matching neither exactly.
SECTION_PATTERNS = (
    ("introduction", re.compile(r"(?i)\b(introduction|background)\b")),
    ("results", re.compile(r"(?i)\bresults?\b")),
    ("discussion", re.compile(r"(?i)\b(discussion|conclusions?|concluding)\b")),
)

# JATS elements whose contents are not prose. Dropped whole, contents included,
# before any tag stripping happens.
DROP_ELEMENTS = ("table-wrap", "fig", "disp-formula", "inline-formula",
                 "tex-math", "supplementary-material", "media", "graphic",
                 "alternatives", "list", "def-list")


def slug(doi):
    """A filename for a DOI. Bounded by DOI_RX before it is ever a path."""
    if not DOI_RX.match(doi):
        raise ValueError("not a PLOS DOI: %r" % doi)
    return doi.split("/", 1)[1].replace(".", "-")


def text_path(doi):
    return os.path.join(TEXTS_DIR, slug(doi) + ".txt")


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_manifest(path=MANIFEST_PATH):
    if not os.path.exists(path):
        return {"papers": []}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_manifest(data, path=MANIFEST_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


def problems(data):
    """Everything wrong with a manifest, as messages.

    A paper with no license field is not a paper this corpus may hold, and a
    paper with no hash is a claim rather than a sample. Both are rejected here
    so `02_measure.py` can publish a rate over a set that validates, the way
    detector-corpus/score.py refuses to publish over one that does not.
    """
    out = []
    papers = data.get("papers")
    if not isinstance(papers, list):
        return ["manifest has no `papers` list"]
    seen = set()
    for i, p in enumerate(papers):
        where = p.get("doi") or "papers[%d]" % i
        for field in REQUIRED_FIELDS:
            if field not in p:
                out.append("%s has no %r" % (where, field))
        doi = p.get("doi", "")
        if not DOI_RX.match(doi):
            out.append("%s is not a PLOS DOI" % where)
        elif doi in seen:
            out.append("%s appears twice" % where)
        else:
            seen.add(doi)
        lic = p.get("license", "")
        if lic and not LICENSE_OK.search(lic):
            out.append("%s carries license %r, which is not plain CC BY. The "
                       "corpus holds one license so nobody has to reason about "
                       "a second one" % (where, lic))
        if isinstance(p.get("words"), int) and p["words"] < 200:
            out.append("%s extracted only %d words, which is under the scan's "
                       "own reliability floor and would publish noise"
                       % (where, p["words"]))
    return out


# --------------------------------------------------------------------------
# JATS extraction
# --------------------------------------------------------------------------

def license_of(xml):
    """The license URL the article states about itself, or None."""
    m = re.search(r'<license[^>]*xlink:href="([^"]+)"', xml)
    return m.group(1) if m else None


def _strip_markup(fragment):
    """JATS fragment to plain prose.

    Non-prose elements go first, whole. Then tags, then entities, then
    whitespace. Order matters: stripping tags first would leave a table's cell
    text behind as a run of unpunctuated noun phrases, which reads to the
    engine as a bullet-NP list nobody wrote.
    """
    for el in DROP_ELEMENTS:
        fragment = re.sub(r"(?s)<%s\b.*?</%s>" % (el, el), " ", fragment)
        fragment = re.sub(r"<%s\b[^>]*/>" % el, " ", fragment)
    # Paragraph boundaries survive as blank lines, because paragraph-length and
    # uniformity findings are among the cells being calibrated.
    fragment = re.sub(r"(?s)</p>", "\n\n", fragment)
    fragment = re.sub(r"(?s)<[^>]+>", "", fragment)
    fragment = (fragment.replace("&amp;", "&").replace("&lt;", "<")
                        .replace("&gt;", ">").replace("&quot;", '"')
                        .replace("&apos;", "'"))
    fragment = re.sub(r"&#x?[0-9A-Fa-f]+;", "", fragment)
    fragment = re.sub(r"[ \t]+", " ", fragment)
    fragment = re.sub(r"\n[ \t]+", "\n", fragment)
    fragment = re.sub(r"\n{3,}", "\n\n", fragment)
    return fragment.strip()


def _top_level_sections(body):
    """(title, inner_xml) for each top-level <sec> in a <body>.

    Written as a depth counter rather than a regex, because JATS nests <sec>
    inside <sec> and a non-greedy match closes on the first inner </sec>. That
    bug silently truncates every multi-part Results section to its preamble,
    which is exactly the prose this corpus is being built to measure.
    """
    out = []
    for m in re.finditer(r"<sec\b[^>]*>", body):
        start = m.start()
        depth, pos = 0, m.start()
        while pos < len(body):
            nxt = re.search(r"<sec\b[^>]*>|</sec>", body[pos:])
            if not nxt:
                break
            pos += nxt.end()
            depth += 1 if nxt.group(0).startswith("<sec") else -1
            if depth == 0:
                break
        inner = body[start:pos]
        # Only top level: skip a section already inside one we emitted.
        if out and start < out[-1][2]:
            continue
        title = re.search(r"<title>(.*?)</title>", inner, re.S)
        out.append((_strip_markup(title.group(1)) if title else "", inner, pos))
    return [(t, i) for t, i, _ in out]


def extract(xml):
    """{slot: prose} for the four slots this corpus keeps.

    A section matching two slots (`Results and discussion`) is filed under the
    first it matches and not duplicated, because counting the same paragraph
    twice would inflate every rate this corpus publishes.
    """
    out = {}
    abstract = re.search(r"(?s)<abstract\b[^>]*>(.*?)</abstract>", xml)
    if abstract:
        out["abstract"] = _strip_markup(abstract.group(1))

    body = re.search(r"(?s)<body\b[^>]*>(.*?)</body>", xml)
    if not body:
        return out
    for title, inner in _top_level_sections(body.group(1)):
        for slot, rx in SECTION_PATTERNS:
            if rx.search(title) and slot not in out:
                # The section's own <title> goes, because assemble() writes a
                # heading for the slot. Left in, every extracted section opened
                # with its own name as a bare word glued to the first sentence.
                out[slot] = _strip_markup(
                    re.sub(r"(?s)<title>.*?</title>", "", inner, count=1))
                break
    return out


def assemble(sections):
    """The four slots as one document, in reading order, with headings.

    Headings are real markdown because the engine's paragraph and uniformity
    measures work off block structure, and a wall of concatenated sections
    would measure a document nobody wrote.
    """
    order = ("abstract", "introduction", "results", "discussion")
    parts = []
    for slot in order:
        if sections.get(slot):
            parts.append("## %s\n\n%s" % (slot.capitalize(), sections[slot]))
    return "\n\n".join(parts) + "\n"


def word_count(text):
    return len(text.split())
