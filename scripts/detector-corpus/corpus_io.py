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

Stdlib only, 3.8+.
"""

import hashlib
import json
import os
import re

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
REQUIRED_HUMAN_PROVENANCE = ("source_url", "archive_url", "published", "why_credible")
REQUIRED_GENERATED_PROVENANCE = ("model", "prompt", "generated")

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
    return os.path.join(texts_dir or TEXTS_DIR, sample["id"] + ".txt")


def read_text(sample, texts_dir=None):
    """The sample's text, or None when this checkout does not have it."""
    path = text_path(sample, texts_dir)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return normalize(fh.read())


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
        required = (REQUIRED_HUMAN_PROVENANCE if sample["label"] == "human"
                    else REQUIRED_GENERATED_PROVENANCE)
        for field in required:
            if not prov.get(field):
                out.append("%s provenance is missing %s" % (sid, field))
        if sample["label"] == "human" and prov.get("published"):
            if prov["published"] >= PRE_GENERATION_CUTOFF:
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
    flagged" is not "a 0% false-positive rate", it is "somewhere under 7%".
    """
    if trials == 0:
        return (0.0, 0.0, 1.0)
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    spread = (z / denominator) * ((p * (1 - p) / trials
                                   + z * z / (4 * trials * trials)) ** 0.5)
    return (p, max(0.0, center - spread), min(1.0, center + spread))
