#!/usr/bin/env python3
"""
Fetch the load-bearing dataset snapshot into docs/claude-vocab-research/raw/.

    python3 scripts/claude-vocab-research/01_fetch_dataset.py
    python3 scripts/claude-vocab-research/01_fetch_dataset.py --dry-run
    python3 scripts/claude-vocab-research/01_fetch_dataset.py --json

**This makes network requests**, the way `01_fetch_datasets.py` in the
thesaurus pipeline and `fetch_samples.py` in the detector corpus do, and like
them this is a one-shot research tool: no test calls it and it is not wired
into CI. The URLs come out of `claude_vocab_io.DATASETS` and
`claude_vocab_io.DAY_FILES`, so the manifest is as trusted as the code: only
`http` and `https` are followed, every download is read under a byte cap, and
the bytes must hash and size to the pinned values or nothing is kept.

analysis.js is regenerated daily upstream, which is why the pinned URL names a
commit rather than a branch. A hash mismatch means the pin is wrong or
somebody re-pinned badly, and either one needs a human rather than an
overwrite.

Exit 0 when everything is present and verified, 1 otherwise.
Stdlib only, 3.9+.
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
for path in (HERE, ENGINE):
    if path not in sys.path:
        sys.path.insert(0, path)

import claude_vocab_io  # noqa: E402
from rwlib import cli_error  # noqa: E402

TIMEOUT_SECONDS = 60
# analysis.js is 207kB and the day files are smaller. The cap stops a moved
# URL that now serves something enormous from being an out-of-memory exit
# rather than a reported failure.
MAX_BYTES = 64 * 1024 * 1024
_READ_CHUNK = 64 * 1024
USER_AGENT = ("rabbit-writes-claude-vocab/1.0 (vocabulary research dataset; "
              "https://github.com/whit3rabbit/rabbit-writes)")
ALLOWED_SCHEMES = ("http://", "https://")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url):
    """(bytes, error)."""
    if not url.lower().startswith(ALLOWED_SCHEMES):
        return None, "refusing scheme in %r, only http and https are followed" % url[:40]
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            chunks, total = [], 0
            while True:
                chunk = response.read(_READ_CHUNK)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BYTES:
                    return None, "response is larger than the %d-byte cap" % MAX_BYTES
                chunks.append(chunk)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return None, str(exc)
    return b"".join(chunks), None


def status_of(raw_dir, spec):
    """What this checkout already has for one pinned file."""
    path = os.path.join(raw_dir, spec["filename"])
    if not os.path.exists(path):
        return "missing"
    with open(path, "rb") as fh:
        data = fh.read()
    if digest(data) != spec["sha256"]:
        return "moved"
    return "verified" if len(data) == spec["bytes"] else "resized"


def process(key, spec, raw_dir, dry_run):
    """One pinned file. Returns a result row, writes only on a verified hash."""
    row = {"dataset": key, "url": spec["url"],
           "before": status_of(raw_dir, spec)}
    if row["before"] == "verified":
        row["action"] = "kept"
        return row
    if dry_run:
        row["action"] = "would fetch"
        return row

    raw, error = fetch(spec["url"])
    if raw is None:
        row["action"] = "failed"
        row["note"] = error
        return row
    row["sha256"] = digest(raw)
    row["bytes"] = len(raw)
    if row["sha256"] != spec["sha256"] or len(raw) != spec["bytes"]:
        # Nothing is written. The pinned hash is the committed claim, and a
        # download that does not match it is a fact for a human to look at.
        row["action"] = "mismatch"
        row["note"] = ("fetched %d bytes hashing %s against pinned %s (%d "
                       "bytes). The pin is wrong or the source moved: decide "
                       "which before re-pinning in claude_vocab_io"
                       % (len(raw), row["sha256"][:12], spec["sha256"][:12],
                          spec["bytes"]))
        return row

    os.makedirs(raw_dir, exist_ok=True)
    with open(os.path.join(raw_dir, spec["filename"]), "wb") as fh:
        fh.write(raw)
    row["action"] = "fetched"
    return row


def main():
    examples = [
        "python3 scripts/claude-vocab-research/01_fetch_dataset.py",
        "python3 scripts/claude-vocab-research/01_fetch_dataset.py --dry-run",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="say what would be fetched, make no requests")
    ap.add_argument("--days", action="store_true",
                    help="also fetch the pinned day files stage 05 selects "
                         "samples from")
    ap.add_argument("--raw-dir", default=claude_vocab_io.RAW_DIR,
                    help=argparse.SUPPRESS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    specs = dict(claude_vocab_io.DATASETS)
    if args.days:
        for day, spec in claude_vocab_io.DAY_FILES.items():
            specs["day-" + day] = spec
    rows = [process(key, spec, args.raw_dir, args.dry_run)
            for key, spec in sorted(specs.items())]
    if args.json:
        print(json.dumps({"rows": rows, "dry_run": args.dry_run}, indent=2))
    else:
        for row in rows:
            print("  %-16s %-12s %s"
                  % (row["dataset"], row["action"], row.get("note", "")))
        if args.dry_run:
            print("\nDry run. Nothing was fetched and nothing was written.")
    if args.dry_run:
        return 0
    bad = [r for r in rows if r["action"] not in ("kept", "fetched")]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
