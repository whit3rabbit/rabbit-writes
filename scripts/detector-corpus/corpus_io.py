#!/usr/bin/env python3
"""
The labeled-corpus manifest: reading it, and checking a text against it.

PROOF.md says, in the file itself, that a two-sample calibration is the weakest
form of evidence a detector can offer. This is the machinery for replacing it
with a measurement.

The design constraint that shapes everything here: the corpus has to be
*checkable* by somebody who does not trust us, and it cannot be a pile of other
people's prose redistributed without asking. Those pull in opposite directions,
and the resolution is hash-only storage. The manifest records where each sample
came from, when it was published, why that date is credible, and the SHA-256 of
the normalized text. The text itself stays out of git. Anybody can refetch from
the recorded archive URL, run `score.py --verify`, and get the same hashes or
find out the sample moved.

Labels:

    human       prose with evidence it predates general availability of
                chat-based generators. The bar is an archive capture, not an
                author's word.
    generated   prose produced by a named model, with the prompt recorded.

A sample with no provenance is not a sample. `problems()` rejects it, and
score.py refuses to publish a rate over a set that does not validate.

Stdlib only, 3.9+.
"""

import hashlib
import json
import os
import re
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
CORPUS_DIR = os.path.join(REPO_ROOT, "docs", "detector-corpus")
MANIFEST_PATH = os.path.join(CORPUS_DIR, "manifest.json")
# Where the actual text goes. Ignored by git: see the module docstring.
TEXTS_DIR = os.path.join(CORPUS_DIR, "texts")

LABELS = ("human", "generated")

# The date general-purpose chat generation became something a blogger could
# plausibly have used. Anything captured by a web archive before this is prose
# nobody had the tools to generate, which is the only kind of "human" claim that
# does not rest on somebody's say-so.
PRE_GENERATION_CUTOFF = "2022-11-30"

REQUIRED_FIELDS = ("id", "label", "register", "provenance", "sha256", "words")
# A sample id is a filename inside texts/, so it is a slug: lowercase ascii,
# digits, hyphens, and nothing else. Validated in problems() and enforced again
# as a path-containment bound in text_path(), because an id is the one field a
# manifest author types by hand and `../../x` would write outside the texts
# directory. The scheme check in fetch_samples follows the same reasoning: the
# manifest is trusted as code, and a trust boundary is checked everywhere it is
# crossed, not only at the front door.
ID_RX = re.compile(r"[a-z0-9][a-z0-9-]*")
REQUIRED_HUMAN_PROVENANCE = ("source_url", "archive_url", "published", "why_credible")
REQUIRED_GENERATED_PROVENANCE = ("model", "prompt", "generated")

# A human sample can prove its date two ways, and the second one is not a web
# archive at all.
#
# A published research corpus collected years before the cutoff is at least as
# good as a single Wayback capture, and in one way better: the collection date
# is documented, peer-reviewed, and citable, where a capture is one URL that one
# crawler happened to visit. What it needs instead of an archive URL is enough
# to identify the exact row again: the dataset, the revision it was pinned at,
# the split, and the row index. A dataset without a revision is not a citation,
# it is a name that will mean something different next year.
#
# `license` is required here and not for an archive sample, because a research
# corpus comes with terms and a blog post does not come with any. Several of the
# obvious candidates are non-commercial-research-only, which is fine for this and
# is exactly the sort of thing that has to be recorded rather than remembered.
REQUIRED_DATASET_PROVENANCE = ("dataset", "revision", "split", "row",
                               "collected", "license", "why_credible")


def human_provenance_kind(provenance):
    """"archive", "dataset", or None when it is neither.

    Chosen on which identifying key is present rather than on a `kind` field the
    author has to remember to set, so a half-filled entry falls through to
    `problems()` and gets named rather than being silently read as the other
    shape.
    """
    if provenance.get("dataset"):
        return "dataset"
    if provenance.get("archive_url") or provenance.get("source_url"):
        return "archive"
    return None

# Sample sizes below this produce an interval so wide it says nothing. Published
# anyway, with the interval attached, because a wide interval is information and
# a suppressed one is not: what is refused is the *point estimate on its own*.
MIN_SAMPLES_FOR_RATE = 20


def normalize(text):
    """The bytes the hash is taken over.

    Line endings and trailing whitespace are normalized away, because a sample
    that fails its hash for having been saved on Windows tells nobody anything.
    Nothing else is touched: the whole point is that the text scored is the text
    hashed.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip() + "\n"


def digest(text):
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def load(path=MANIFEST_PATH):
    if not os.path.exists(path):
        return {"version": 1, "samples": []}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(manifest, path=MANIFEST_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    manifest["samples"].sort(key=lambda s: (s["label"], s["id"]))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")


def text_path(sample, texts_dir=None):
    # Resolved at call time, not bound as a default. A default argument freezes
    # the module global at import, so a caller that points TEXTS_DIR somewhere
    # else keeps reading the old directory and every sample reports as missing.
    # That is not hypothetical: it silently emptied the first run of this
    # module's own test, which then passed by reporting an empty corpus.
    base = texts_dir or TEXTS_DIR
    path = os.path.join(base, sample["id"] + ".txt")
    # Defense in depth alongside the slug check in problems(). An id that
    # reached here without validation, an old manifest or a hand edit, must not
    # read or write outside the texts directory. realpath collapses `..` and
    # symlinks, so the file's real parent has to be the real base.
    if os.path.realpath(os.path.dirname(path)) != os.path.realpath(base):
        raise ValueError("sample id %r resolves outside the texts directory"
                         % sample["id"])
    return path


def read_text(sample, texts_dir=None):
    """The sample's text, or None when this checkout does not have it."""
    path = text_path(sample, texts_dir)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return normalize(fh.read())


# How a sample's text was produced from its source. Recorded per sample, because
# it decides whether a hash is reproducible by anybody else.
#
#   fetch_samples   extract_text() below, over the bytes at archive_url. Anybody
#                   can rerun fetch_samples.py and get the same hash.
#   manual          somebody pasted the prose in by hand. Perfectly valid, and
#                   not reproducible: two people trimming the same page's
#                   navigation by eye do not agree to the byte.
#
# Absent means manual, because every sample added before this key existed was.
EXTRACTION_AUTO = "fetch_samples"


class _TextExtractor(HTMLParser):
    """HTML to plain text, deterministically.

    Deterministic is the whole requirement, and it is why this is 30 lines of
    stdlib rather than a real readability implementation. The hash in the
    manifest is a claim that a named URL produces named bytes, and a smarter
    extractor that improves next year turns every committed hash into a
    mismatch. This one is dumb and frozen: drop the non-prose elements, keep the
    text, put a blank line after each block element.
    """

    DROP = {"script", "style", "head", "noscript", "svg", "template", "nav",
            "form", "button", "select", "textarea", "iframe"}
    BLOCK = {"p", "div", "br", "li", "tr", "section", "article", "header",
             "footer", "blockquote", "pre", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.DROP:
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.DROP:
            self._skip = max(0, self._skip - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def extract_text(html):
    """Readable text out of an HTML page, the same way every time.

    Not markup-aware beyond the tag list above, and not trying to be. See
    _TextExtractor on why a better extractor would be a worse one here.
    """
    parser = _TextExtractor()
    parser.feed(html)
    text = "".join(parser.parts)
    # Collapse horizontal runs, keep paragraph breaks. Done after extraction
    # rather than during, so the block-element newlines above survive. The class
    # includes \xa0 (NO-BREAK SPACE), written as an escape never a literal: a
    # literal invisible is normalized to a plain space by some editors, which
    # would silently move every committed hash without a visible diff.
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return normalize(text)


def problems(manifest, registers=()):
    """Everything wrong with the manifest, as messages.

    Strict on purpose. A corpus is evidence, and evidence with a missing
    provenance field is an assertion wearing evidence's clothes.
    """
    out = []
    seen = set()
    for sample in manifest.get("samples", []):
        sid = sample.get("id", "<no id>")
        missing = [f for f in REQUIRED_FIELDS if not sample.get(f)]
        if missing:
            out.append("%s is missing %s" % (sid, ", ".join(missing)))
            continue
        if sid in seen:
            out.append("%s appears twice" % sid)
        seen.add(sid)
        if not ID_RX.fullmatch(sid):
            out.append("%s is not a slug. An id is a filename in texts/, so it "
                       "is lowercase ascii, digits, and hyphens only: anything "
                       "else is a path-traversal vector" % sid)
        if sample["label"] not in LABELS:
            out.append("%s has label %r, not one of %s"
                       % (sid, sample["label"], ", ".join(LABELS)))
            continue
        if registers and sample["register"] not in registers:
            out.append("%s names register %r, which the engine does not have"
                       % (sid, sample["register"]))
        if not re.fullmatch(r"[0-9a-f]{64}", sample["sha256"]):
            out.append("%s has a sha256 that is not a sha256" % sid)

        prov = sample["provenance"]
        if sample["label"] != "human":
            required = REQUIRED_GENERATED_PROVENANCE
        else:
            kind = human_provenance_kind(prov)
            if kind is None:
                out.append("%s is labeled human and its provenance names "
                           "neither an archive capture (source_url, "
                           "archive_url) nor a dataset. One or the other is "
                           "what makes the label evidence rather than a claim"
                           % sid)
                continue
            required = (REQUIRED_DATASET_PROVENANCE if kind == "dataset"
                        else REQUIRED_HUMAN_PROVENANCE)
        for field in required:
            if not prov.get(field):
                out.append("%s provenance is missing %s" % (sid, field))

        # Whichever field carries the date, it is compared against the cutoff
        # the same way. `collected` is when the corpus was gathered, which is
        # the date that bounds when its text could have been written.
        dated = prov.get("published") or prov.get("collected")
        if sample["label"] == "human" and dated:
            prov = dict(prov, published=dated)
        if sample["label"] == "human" and prov.get("published"):
            # The cutoff below is a string comparison, which is exactly right
            # for zero-padded ISO dates and silently wrong for anything else:
            # "3/4/2019" sorts after "2022-11-30" and a 2019 sample would be
            # rejected for being too recent. Checked rather than trusted,
            # because add_sample.py only names the format in its help text.
            # isinstance first. JSON happily holds `"published": 2019`, and both
            # re.fullmatch and the `>=` below raise TypeError on an int, out of
            # a function whose whole job is to return problems rather than throw
            # them at score.py.
            if (not isinstance(prov["published"], str)
                    or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", prov["published"])):
                out.append("%s provenance.published is %r, which is not "
                           "YYYY-MM-DD. The cutoff is compared as a string, so "
                           "any other shape compares wrong"
                           % (sid, prov["published"]))
            elif prov["published"] >= PRE_GENERATION_CUTOFF:
                out.append("%s is labeled human but was published %s, after the "
                           "%s cutoff. A human label after that date rests on "
                           "somebody's word, which is what this corpus exists "
                           "to avoid" % (sid, prov["published"],
                                         PRE_GENERATION_CUTOFF))
    return out


def wilson(successes, trials, z=1.96):
    """The Wilson score interval for a proportion, at 95% by default.

    Not the normal approximation. At the rates this corpus is measuring, a
    detector's false-positive rate near zero over fifty samples, the normal
    interval runs below zero and reports a lower bound that cannot happen. The
    Wilson interval stays inside [0, 1] and does not collapse to a point when
    the count is zero, which is exactly the case that matters here: "0 of 50
    flagged" is not "a 0% false-positive rate", it is "somewhere under 7.2%".

    The upper bound is what to size a sampling round against, and it falls
    slowly: 16.1% at 20 samples, 8.8% at 40, 7.1% at 50, 6.0% at 60, 3.7% at
    100. Fifty-two is where it crosses 7%. Those come from this function rather
    than from the round numbers an earlier version of this docstring quoted.
    """
    if trials == 0:
        return (0.0, 0.0, 1.0)
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    spread = (z / denominator) * ((p * (1 - p) / trials
                                   + z * z / (4 * trials * trials)) ** 0.5)
    return (p, max(0.0, center - spread), min(1.0, center + spread))
