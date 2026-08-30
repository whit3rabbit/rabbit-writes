#!/usr/bin/env python3
"""
Pick detector-corpus samples out of the pinned day files.

    python3 scripts/claude-vocab-research/05_pick_pr_samples.py
    python3 scripts/claude-vocab-research/05_pick_pr_samples.py --day 2026-08-17
    python3 scripts/claude-vocab-research/05_pick_pr_samples.py --json

A pull-request body carrying the literal "Generated with Claude Code" footer
is as close to ground truth as a generated-label sample gets outside the lab:
the tooling wrote its own signature under the prose. This stage finds those
bodies in the day files 01 fetched, filters to English-dominant prose long
enough for the tier-3 and uniformity checks to score (they need 120+ words),
writes each one verbatim under scratch/pr-samples/, and prints the exact
add_sample.py command that registers it with dataset provenance.

Nothing is registered. The bodies are other people's prose and the footer is
an attribution, so a human reviews each candidate and runs the printed
command for the ones that hold up. The text stays verbatim, footer included,
because the manifest hash is a claim about exact bytes at an exact row.

The footer text itself matches no catalogue pattern today (only ai-utm
mentions claude, on a utm_source parameter), so scoring the engine over these
samples is not circular. The day a pattern matches the footer, that changes:
such a pattern would make every sample trivially detectable, and the samples
would need relabeling. That fact is recorded in each sample's notes at add
time, not just here.

Exit 0 on a written selection, 1 when the day files are missing or hash-mismatched.
Stdlib only, 3.9+.
"""

import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
DETECTOR = os.path.join(REPO_ROOT, "scripts", "detector-corpus")
for path in (HERE, ENGINE, DETECTOR):
    if path not in sys.path:
        sys.path.insert(0, path)

import claude_vocab_io  # noqa: E402
import corpus_io  # noqa: E402
from rwlib import cli_error  # noqa: E402

# The footer appears in two spellings in the corpus: plain text ("Generated
# with Claude Code") and markdown-linked ("Generated with [Claude Code]
# (https://claude.com/claude-code)"). The bracket form is the common one.
FOOTER_RX = re.compile(r"Generated with \[?Claude Code\]?", re.I)

# English-dominant rather than English-only, because the footer itself
# carries an emoji and the body may quote a line of CJK output. Below this
# ratio the body is usually another language with an English footer stapled
# on, which measures the detector against prose it was never meant to read.
MIN_ASCII_RATIO = 0.95
# The tier-3 density and uniformity checks need 120+ scored words, and a
# body that barely clears that measures nothing but its own brevity.
MIN_WORDS = 150
DEFAULT_TARGET = 30

# What add_sample.py records for every picked sample. `model` names the
# attribution basis rather than a model id, because the body says Claude Code
# wrote it and nothing anywhere says which model Claude Code was driving.
MODEL_NOTE = "claude (self-attributed: Claude Code footer in the body)"
WHY_CREDIBLE = ("the body carries the literal Claude Code attribution "
                "footer, which a human author does not type by hand")
NOTES = ("self-attributed AI text from the load-bearing PR corpus. The "
         "footer matches no catalogue pattern today, so detection is not "
         "circular. If a pattern ever matches the footer, relabel or retire "
         "this sample")


def ascii_ratio(body):
    if not body:
        return 0.0
    return sum(1 for c in body if ord(c) < 128) / float(len(body))


def load_day(raw_dir, day):
    """(records, error) for one pinned day, hash-checked on the way in."""
    spec = claude_vocab_io.DAY_FILES[day]
    path = os.path.join(raw_dir, spec["filename"])
    if not os.path.exists(path):
        return None, ("%s is missing. Run 01_fetch_dataset.py --days first"
                      % path)
    with open(path, "rb") as fh:
        data = fh.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != spec["sha256"] or len(data) != spec["bytes"]:
        return None, ("%s hashes to %s (%d bytes) against the pinned %s "
                      "(%d bytes), so it is not the snapshot the selection "
                      "was defined over"
                      % (path, digest[:12], len(data), spec["sha256"][:12],
                         spec["bytes"]))
    records = []
    for line in data.decode("utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records, None


def pick(records, day, seen_digests):
    """The qualifying records of one day, deduplicated against earlier days."""
    out = []
    for row, record in enumerate(records):
        body = record.get("body") or ""
        if not FOOTER_RX.search(body):
            continue
        if len(body.split()) < MIN_WORDS:
            continue
        if ascii_ratio(body) < MIN_ASCII_RATIO:
            continue
        digest = corpus_io.digest(body)
        if digest in seen_digests:
            continue
        seen_digests.add(digest)
        out.append({
            "id": "gen-lb-%s-r%d" % (day.replace("-", ""), row),
            "day": day,
            "row": row,
            "words": len(body.split()),
            "sha256": digest,
            "ts": record.get("ts", ""),
            "repo": record.get("repo", ""),
            "body": body,
        })
    return out


def add_sample_command(sample, register, out_path):
    """The exact add_sample.py invocation that registers this sample."""
    generated = sample["ts"][:10] or sample["day"]
    return " ".join([
        "python3 scripts/detector-corpus/add_sample.py", out_path,
        "--id", sample["id"],
        "--label", "generated",
        "--register", register,
        "--model", json.dumps(MODEL_NOTE),
        "--generated", generated,
        "--dataset", claude_vocab_io.REPO,
        "--revision", claude_vocab_io.COMMIT,
        "--loader", "github-jsonl",
        "--path", claude_vocab_io.DAY_FILES[sample["day"]]["path"],
        "--split", sample["day"],
        "--row", str(sample["row"]),
        "--field", "body",
        "--collected", claude_vocab_io.COLLECTED,
        "--license", json.dumps(claude_vocab_io.LICENSE_NOTE),
        "--why-credible", json.dumps(WHY_CREDIBLE),
        "--notes", json.dumps(NOTES),
    ])


def main():
    examples = [
        "python3 scripts/claude-vocab-research/05_pick_pr_samples.py",
        "python3 scripts/claude-vocab-research/05_pick_pr_samples.py --day 2026-08-17",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--day", action="append",
                    help="only this pinned day. Repeatable. Default: all "
                         "pinned days, oldest first")
    ap.add_argument("--target", type=int, default=DEFAULT_TARGET,
                    help="stop after this many candidates (default %d)"
                         % DEFAULT_TARGET)
    ap.add_argument("--register", default="docs",
                    help="register to file the samples under (default docs, "
                         "the closest the engine has to PR-description prose)")
    ap.add_argument("--raw-dir", default=claude_vocab_io.RAW_DIR,
                    help=argparse.SUPPRESS)
    ap.add_argument("--out-dir",
                    default=os.path.join(REPO_ROOT, "scratch", "pr-samples"),
                    help=argparse.SUPPRESS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    days = args.day or sorted(claude_vocab_io.DAY_FILES)
    unknown = [d for d in days if d not in claude_vocab_io.DAY_FILES]
    if unknown:
        ap.error("no day %r pinned in claude_vocab_io.DAY_FILES. Pinned: %s"
                 % (unknown[0], ", ".join(sorted(claude_vocab_io.DAY_FILES))))

    picked, seen = [], set()
    for day in days:
        records, error = load_day(args.raw_dir, day)
        if error:
            ap.error(error)
        found = pick(records, day, seen)
        picked.extend(found)
        if len(picked) >= args.target:
            picked = picked[:args.target]
            break

    if not picked:
        ap.error("no candidates passed the filters (footer, %d+ words, "
                 "%d%% ascii). Check the pinned days or loosen nothing: a "
                 "thin sample round measures nothing"
                 % (MIN_WORDS, int(MIN_ASCII_RATIO * 100)))

    os.makedirs(args.out_dir, exist_ok=True)
    commands = []
    for sample in picked:
        out_path = os.path.join(args.out_dir, sample["id"] + ".txt")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(corpus_io.normalize(sample["body"]))
        commands.append(add_sample_command(sample, args.register,
                                           os.path.relpath(out_path,
                                                           REPO_ROOT)))

    if args.json:
        print(json.dumps({
            "days": days,
            "picked": [{k: v for k, v in s.items() if k != "body"}
                       for s in picked],
            "commands": commands}, indent=2))
    else:
        print("%d candidate(s) across %s, written under %s"
              % (len(picked), ", ".join(days), args.out_dir))
        print("Review each text, then register the ones that hold up:\n")
        for command in commands:
            print(command + "\n")
        print("The bodies are verbatim, footer included. add_sample.py "
              "refuses a duplicate hash, so a body already in the corpus "
              "stops the round rather than double-counting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
