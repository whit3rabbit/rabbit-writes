#!/usr/bin/env python3
"""
Score the whole pipeline end to end, with labels nobody had to write.

Every other measurement in this repository scores one detector. This scores the
conversion: take a piece the writer actually wrote, deslop it into a neutral
register, convert it back into their voice, and measure how close the round trip
landed. The original is the answer key, so there is no human judgement anywhere
in the metric.

    python3 reconstruct.py                 # score every triple in the corpus
    python3 reconstruct.py --json
    python3 reconstruct.py --verify        # hashes only: has any text moved?

A triple is three documents and a profile:

    original       something the writer wrote, and the target
    neutralized    the same piece deslopped into a neutral register
    reconstructed  the neutralized text converted back through the skill

The two middle steps need a model, so they are a procedure a person or an agent
runs and this script does not. Everything here is offline arithmetic over the
three texts, which is what makes it testable with the corpus empty.

**What the numbers mean, and what they do not.**

`recovered` is the share of the distance the conversion closed:
`(neutralized - reconstructed) / (neutralized - original)`. 1.0 means the
reconstruction sits exactly as close to the original as the original does to
itself, and 0.0 means the conversion moved nothing. It can go negative, and that
is the reading worth having: the conversion made it *less* like them.

It is a measurement of a pipeline and never a claim about a person. A
reconstruction that scores 0.4 says the round trip lost some of the register,
not that the writer is inconsistent, and it certainly says nothing about who
wrote anything. `references/false-positives.md` applies here with the rest.

**Why the corpus is empty and this file is not.** The same reason
`scripts/detector-corpus/` ships a scorer over no samples: gathering real
writing from a real person, with their consent, is the expensive part, and a
harness written afterwards gets written to fit whatever data turned up. Until
somebody populates it, `PROOF.md` says the calibration rests on the synthetic
fixtures in the test suite, and this prints that it has no triples rather than a
score of 0.0 over nothing.

Exit codes: 0 always when the manifest reads, 1 when --verify finds a moved
text, 2 when the manifest will not parse.

Stdlib only, 3.9+.
"""

import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import scan as scan_mod                                          # noqa: E402
from rwlib import stylometry                                     # noqa: E402

CORPUS_DIR = os.path.join(REPO_ROOT, "docs", "voice-eval")
MANIFEST_PATH = os.path.join(CORPUS_DIR, "manifest.json")
TEXTS_DIR = os.path.join(CORPUS_DIR, "texts")

# Bumped when a stored field changes meaning, the same reason every other
# schema constant in this repository exists.
SCHEMA_VERSION = 1

ROLES = ("original", "neutralized", "reconstructed")


class CorpusError(Exception):
    pass


def load_manifest(path=MANIFEST_PATH):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        raise CorpusError("cannot read %s: %s" % (path, exc))
    except ValueError as exc:
        raise CorpusError("%s does not parse: %s" % (path, exc))
    if data.get("version") != SCHEMA_VERSION:
        raise CorpusError("%s is version %r and this reads %d"
                          % (path, data.get("version"), SCHEMA_VERSION))
    return data


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_texts(triple, texts_dir=TEXTS_DIR):
    """{role: text} for one triple, or a CorpusError naming what is missing."""
    out = {}
    for role in ROLES:
        name = triple.get(role)
        if not name:
            raise CorpusError("triple %r has no %s" % (triple.get("id"), role))
        path = os.path.join(texts_dir, name)
        try:
            with open(path, encoding="utf-8") as fh:
                out[role] = fh.read()
        except OSError as exc:
            raise CorpusError("triple %r: %s" % (triple.get("id"), exc))
    return out


def score_triple(texts, fingerprint=None):
    """How much of the writer's register the round trip got back.

    Two independent readings, because they fail differently. The Delta half is
    the register measurement the whole plugin is built on. The stats half is the
    six measures, and a conversion can recover one and not the other: a pass
    that restores the marker rates while leaving every sentence the same length
    has not brought the writing back.

    `fingerprint` is optional. Without one the Delta half is measured against a
    fingerprint built from the original itself, which is a weaker baseline and
    is stated as such in the output: it has no self-distance band, so a distance
    against it is a raw number rather than a calibrated one.
    """
    prose = {role: scan_mod.strip_for_stats(body) for role, body in texts.items()}
    stats = {role: scan_mod.compute_stats(body) for role, body in texts.items()}

    if fingerprint is not None:
        base = fingerprint
        calibrated = True
    else:
        # Two "samples" from the one document we have, so fingerprint() has the
        # two it insists on. The band this produces is a within-document number
        # and means less than a real one, which is what `calibrated` says.
        halves = _halve(prose["original"])
        base = stylometry.fingerprint(halves, voice=None)
        calibrated = False

    deltas = {role: stylometry.distance(base, prose[role])["delta"]
              for role in ROLES}
    measures = {}
    for name in stylometry.MEASURES:
        values = {role: stats[role].get(name) for role in ROLES}
        if any(v is None for v in values.values()):
            continue
        measures[name] = dict(values, recovered=_recovered(
            values["original"], values["neutralized"], values["reconstructed"]))

    return {
        "calibrated": calibrated,
        "delta": deltas,
        "delta_recovered": _recovered(deltas["original"], deltas["neutralized"],
                                      deltas["reconstructed"]),
        "measures": measures,
        "measures_recovered": _mean([m["recovered"] for m in measures.values()
                                     if m["recovered"] is not None]),
        "words": {role: stats[role].get("word_count", 0) for role in ROLES},
        "reliable": all(stats[role].get("word_count", 0)
                        >= stylometry.RELIABLE_WORDS for role in ROLES),
    }


def _halve(text):
    """Two halves of one document, split on a paragraph boundary."""
    blocks = [b for b in text.split("\n\n") if b.strip()]
    mid = max(1, len(blocks) // 2)
    return ["\n\n".join(blocks[:mid]), "\n\n".join(blocks[mid:]) or blocks[0]]


def _recovered(target, start, end):
    """The share of the gap the conversion closed, or None with no gap.

    None rather than 1.0 when the neutralized text already sat on the target.
    There was nothing to recover, and calling that a perfect recovery would let
    a weak deslop flatter the conversion that follows it.
    """
    gap = start - target
    if abs(gap) < 1e-9:
        return None
    return round((start - end) / gap, 3)


def _mean(values):
    return round(sum(values) / len(values), 3) if values else None


def verify(data, texts_dir=TEXTS_DIR):
    """[(id, role, why)] for every stored hash that no longer matches.

    The corpus is hash-only in git, so this is what says the texts on this
    machine are the texts the numbers were published from.
    """
    moved = []
    for triple in data.get("triples", []):
        for role in ROLES:
            name = triple.get(role)
            stored = (triple.get("sha256") or {}).get(role)
            if not name or not stored:
                moved.append((triple.get("id"), role, "no stored hash"))
                continue
            path = os.path.join(texts_dir, name)
            try:
                with open(path, encoding="utf-8") as fh:
                    actual = sha256(fh.read())
            except OSError as exc:
                moved.append((triple.get("id"), role, str(exc)))
                continue
            if actual != stored:
                moved.append((triple.get("id"), role, "content changed"))
    return moved


def score_all(data, texts_dir=TEXTS_DIR):
    """[{id, voice, score or error}] for every triple in the manifest."""
    out = []
    for triple in data.get("triples", []):
        row = {"id": triple.get("id"), "voice": triple.get("voice")}
        try:
            texts = read_texts(triple, texts_dir)
        except CorpusError as exc:
            row["error"] = str(exc)
            out.append(row)
            continue
        row["score"] = score_triple(texts, _fingerprint_for(triple))
        out.append(row)
    return out


def _fingerprint_for(triple):
    voice = triple.get("voice")
    if not voice:
        return None
    from rwlib import voices as voices_mod
    path = stylometry.path_for(os.path.join(voices_mod.VOICES_DIR,
                                            voice + voices_mod.RULES_SUFFIX))
    if not path:
        return None
    try:
        return stylometry.load(path)
    except (OSError, ValueError):
        return None


def report(rows):
    if not rows:
        return ("voice reconstruction eval: no triples.\n\n"
                "The harness is here and the corpus is not. Building one means "
                "three documents per entry and a person's consent to keep their "
                "prose in this repository, which is the expensive half. "
                "docs/voice-eval/README.md has the protocol, and PROOF.md says "
                "what the calibration rests on until somebody does it.")
    out = ["voice reconstruction eval: %d triple(s)" % len(rows), ""]
    out.append("  %-24s %-12s %-10s %-10s %s"
               % ("triple", "voice", "delta", "measures", "note"))
    scored = []
    for row in rows:
        if "error" in row:
            out.append("  %-24s %-12s %s" % (row["id"], row.get("voice") or "-",
                                             row["error"]))
            continue
        s = row["score"]
        scored.append(s)
        note = []
        if not s["calibrated"]:
            note.append("no profile fingerprint, so the band is uncalibrated")
        if not s["reliable"]:
            note.append("under %d words" % stylometry.RELIABLE_WORDS)
        out.append("  %-24s %-12s %-10s %-10s %s"
                   % (row["id"], row.get("voice") or "-",
                      s["delta_recovered"], s["measures_recovered"],
                      "; ".join(note)))
    if scored:
        out.append("")
        out.append("  1.0 is a round trip that landed exactly on the original. "
                   "0.0 moved nothing.")
        out.append("  A negative number means the conversion made it less like "
                   "the writer, which is")
        out.append("  the reading this eval exists to surface and the one no "
                   "per-finding report can give.")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="check the stored hashes and score nothing")
    ap.add_argument("--manifest", default=MANIFEST_PATH,
                    help=argparse.SUPPRESS)
    ap.add_argument("--texts", default=TEXTS_DIR, help=argparse.SUPPRESS)
    args = ap.parse_args()

    try:
        data = load_manifest(args.manifest)
    except CorpusError as exc:
        print("reconstruct: %s" % exc, file=sys.stderr)
        return 2

    if args.verify:
        moved = verify(data, args.texts)
        if args.json:
            print(json.dumps({"moved": moved}, indent=2))
        elif moved:
            for tid, role, why in moved:
                print("  %-24s %-14s %s" % (tid, role, why))
        else:
            print("%d triple(s), every stored hash matches"
                  % len(data.get("triples", [])))
        return 1 if moved else 0

    rows = score_all(data, args.texts)
    if args.json:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "triples": rows},
                         indent=2))
    else:
        print(report(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
