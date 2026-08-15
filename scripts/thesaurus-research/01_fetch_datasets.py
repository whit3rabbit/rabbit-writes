#!/usr/bin/env python3
"""
Fetch the thesaurus research datasets into docs/thesaurus-research/raw/.

    python3 scripts/thesaurus-research/01_fetch_datasets.py
    python3 scripts/thesaurus-research/01_fetch_datasets.py --dry-run
    python3 scripts/thesaurus-research/01_fetch_datasets.py --json

**This makes network requests**, the way `fetch_samples.py` in the detector
corpus does, and like it this is a one-shot research tool: no test calls it
and it is not wired into CI. The URLs come out of `thesaurus_io.DATASETS`, so
the manifest is as trusted as the code: only `http` and `https` are followed,
every download is read under a byte cap, and the bytes must hash to the
pinned SHA-256 or nothing is kept. A mismatch means the source moved, and
"the source changed" needs a human, not an overwrite.

The WordNet tarball is unpacked after verification. Member names are checked
by hand before extraction, because `tarfile`'s `filter="data"` is 3.12+ and
the floor here is 3.9: an absolute path or a name that escapes the raw
directory refuses the whole archive.

Exit 0 when everything is present and verified, 1 otherwise.
Stdlib only, 3.9+.
"""

import argparse
import hashlib
import json
import os
import sys
import tarfile
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
for path in (HERE, ENGINE):
    if path not in sys.path:
        sys.path.insert(0, path)

import thesaurus_io  # noqa: E402
from rwlib import cli_error  # noqa: E402

TIMEOUT_SECONDS = 60
# Both files are under 17MB. The cap stops a moved URL that now serves
# something enormous from being an out-of-memory exit rather than a reported
# failure.
MAX_BYTES = 64 * 1024 * 1024
_READ_CHUNK = 64 * 1024
USER_AGENT = ("rabbit-writes-thesaurus/1.0 (vocabulary research datasets; "
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


def safe_members(archive, destination):
    """The archive's members, or a ValueError naming the one that escapes.

    A member with an absolute name or one whose normalized join lands outside
    `destination` refuses the archive whole: partially extracting a hostile
    tarball is worse than extracting none of it.
    """
    members = archive.getmembers()
    base = os.path.realpath(destination)
    for member in members:
        name = member.name
        if name.startswith(("/", "\\")) or (len(name) > 1 and name[1] == ":"):
            raise ValueError("archive member %r has an absolute path" % name)
        target = os.path.realpath(os.path.join(base, name))
        if target != base and not target.startswith(base + os.sep):
            raise ValueError("archive member %r escapes the raw directory" % name)
        if member.islnk() or member.issym():
            raise ValueError("archive member %r is a link" % name)
    return members


def unpack(tar_path, destination):
    """Extract a verified tarball, guarding member names by hand."""
    with tarfile.open(tar_path, "r:gz") as archive:
        archive.extractall(destination, members=safe_members(archive, destination))


def status_of(key):
    """What this checkout already has for one dataset."""
    spec = thesaurus_io.DATASETS[key]
    path = os.path.join(thesaurus_io.RAW_DIR, spec["filename"])
    if not os.path.exists(path):
        return "missing"
    with open(path, "rb") as fh:
        return "verified" if digest(fh.read()) == spec["sha256"] else "moved"


def process(key, dry_run):
    """One dataset. Returns a result row, writes only on a verified hash."""
    spec = thesaurus_io.DATASETS[key]
    row = {"dataset": key, "url": spec["url"], "before": status_of(key)}
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
    if row["sha256"] != spec["sha256"]:
        # Nothing is written. The pinned hash is the committed claim, and a
        # download that does not match it is a fact for a human to look at.
        row["action"] = "mismatch"
        row["note"] = ("fetched %d bytes hashing %s against pinned %s. The "
                       "source moved, or the pin is wrong: decide which "
                       "before re-pinning in thesaurus_io.DATASETS"
                       % (len(raw), row["sha256"][:12], spec["sha256"][:12]))
        return row

    os.makedirs(thesaurus_io.RAW_DIR, exist_ok=True)
    destination = os.path.join(thesaurus_io.RAW_DIR, spec["filename"])
    with open(destination, "wb") as fh:
        fh.write(raw)
    if spec.get("extract_dir"):
        try:
            unpack(destination, thesaurus_io.RAW_DIR)
        except (ValueError, tarfile.TarError) as exc:
            row["action"] = "failed"
            row["note"] = "refused to unpack: %s" % exc
            return row
    row["action"] = "fetched"
    return row


def main():
    examples = [
        "python3 scripts/thesaurus-research/01_fetch_datasets.py",
        "python3 scripts/thesaurus-research/01_fetch_datasets.py --dry-run",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="say what would be fetched, make no requests")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = [process(key, args.dry_run) for key in sorted(thesaurus_io.DATASETS)]
    if args.json:
        print(json.dumps({"rows": rows, "dry_run": args.dry_run}, indent=2))
    else:
        for row in rows:
            print("  %-10s %-12s %s"
                  % (row["dataset"], row["action"], row.get("note", "")))
        if args.dry_run:
            print("\nDry run. Nothing was fetched and nothing was written.")
    if args.dry_run:
        return 0
    bad = [r for r in rows if r["action"] not in ("kept", "fetched")]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
