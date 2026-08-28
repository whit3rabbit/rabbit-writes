#!/usr/bin/env python3
"""
Refetch the corpus texts from the archive URLs the manifest records.

    python3 fetch_samples.py                # fetch what this checkout is missing
    python3 fetch_samples.py --all          # refetch everything, verify hashes
    python3 fetch_samples.py --dry-run      # say what it would fetch
    python3 fetch_samples.py --json

`score.py`'s report has always ended with "Refetch from the archive URLs" and
nothing did it, so reproducing a published rate on a fresh clone was a manual
afternoon. This is that sentence, executable.

The texts are not in git, on purpose: the corpus is other people's prose and the
committed claim is the SHA-256, not the words. See corpus_io.py. That design only
works if somebody else can actually get the words back, which is what this is
for.

**This makes network requests.** Nothing else in the repository does, no test
calls it, and it is not wired into CI. It reads URLs out of a file in the
repository and fetches them, so the manifest is as trusted as the code: only
`http` and `https` are followed, and a URL with any other scheme is refused
rather than handed to urllib.

Reproducibility has a limit and the manifest records it per sample. A text
extracted by this script carries `provenance.extraction: "fetch_samples"`, and
refetching it should reproduce the hash exactly. A text somebody pasted in by
hand does not carry it, and will not round-trip: two people trimming the same
page's navigation by eye do not agree to the byte. Those are reported as
"manual" rather than as failures, because they are not failures. A generated
sample cannot be refetched at all, only regenerated from its recorded prompt,
and it says so.

A hash mismatch never overwrites a good local copy. The fetched text goes to
`<id>.fetched.txt` beside it and the two are left for a human, because "the
source changed" and "our extractor changed" look identical from here and only
one of them means the sample is dead.

Exit codes: 0 when everything asked for is present and verified, 1 when
something is missing, moved, or could not be fetched.
Stdlib only, 3.9+.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
for path in (HERE, ENGINE):
    if path not in sys.path:
        sys.path.insert(0, path)


import corpus_io  # noqa: E402
from rwlib import cli_error  # noqa: E402


# Politeness, not rate limiting in any real sense. These fetches go to web
# archives, one request per sample, a few dozen samples. A tool that hammers an
# archive nobody is paying for is a tool that gets the archive to block it.
DELAY_SECONDS = 1.0
TIMEOUT_SECONDS = 30
# A response is read into memory, so it is capped. No corpus sample is anywhere
# close, and the cap is what stops a broken or hostile archive URL from being an
# out-of-memory exit rather than a reported failure. Generous on purpose: the
# largest real page is kilobytes.
MAX_BYTES = 8 * 1024 * 1024
_READ_CHUNK = 64 * 1024
# Some archives serve a redirect chain and a bare urllib request looks enough
# like a scraper to get refused. Identifying the tool is the polite version of
# lying about being a browser.
USER_AGENT = ("rabbit-writes-corpus/1.0 (detector calibration corpus; "
              "https://github.com/whit3rabbit/rabbit-writes)")

ALLOWED_SCHEMES = ("http://", "https://")


# The Hugging Face datasets viewer. Plain JSON over HTTPS, which is why a
# dataset-sourced sample can be refetched without adding `datasets`, `pyarrow`,
# and a hundred megabytes of transitive dependency to a stdlib-only repository.
#
# `revision` is pinned per sample and sent here, so a dataset that gains rows or
# reorders them next year still yields the row the hash was taken over. A
# dataset reference without a revision is a name, not a citation.
DATASETS_SERVER = "https://datasets-server.huggingface.co/rows"
RAW_GITHUB = "https://raw.githubusercontent.com/"


def dataset_row_url(prov):
    """The viewer URL for exactly one row of one revision of one dataset."""
    query = urllib.parse.urlencode({
        "dataset": prov["dataset"],
        "config": prov.get("config", "default"),
        "split": prov["split"],
        "offset": int(prov["row"]),
        "length": 1,
        "revision": prov["revision"],
    })
    return "%s?%s" % (DATASETS_SERVER, query)


def github_jsonl_url(prov):
    """The raw.githubusercontent URL for one pinned file of one repo.

    Used when `loader` is `github-jsonl`: the dataset lives in a git
    repository rather than on the Hub, so the row pin is repo, 40-hex commit
    sha, in-repository path, and 0-based line index, and the URL is built
    from data rather than convention so the manifest records every piece of
    it. A commit sha is immutable the way a Hub revision is, which is what
    makes a refetch reproduce the same bytes.
    """
    return "%s%s/%s/%s" % (RAW_GITHUB, prov["dataset"], prov["revision"],
                           prov["path"])


def fetchable(sample):
    """(url, why_not, prov). What to request for this sample, if anything.

    For an archive sample the archive URL beats the source URL: a live page can
    be edited, and a sample whose credibility rests on "it was published in
    2019" has to be read from something captured in 2019.

    For a dataset sample it is one row of a pinned revision, through the
    viewer API, or one line of a pinned file when the loader is github-jsonl.

    A prompted generated sample is not refetchable: regeneration is a
    different act from retrieval and this script will not do it silently. A
    dataset-generated sample is, because its text is a row lookup like any
    other dataset sample's, and the attribution that labels it is in the row.
    """
    prov = sample.get("provenance", {})
    if sample["label"] != "human" and not (
            corpus_io.human_provenance_kind(prov) == "dataset"):
        return None, ("generated: refetching means regenerating from the "
                      "recorded prompt, which this script will not do "
                      "silently"), prov
    if corpus_io.human_provenance_kind(prov) == "dataset":
        needed = ("dataset", "split", "row", "revision")
        if prov.get("loader") == "github-jsonl":
            needed = ("dataset", "revision", "path", "row")
        missing = [k for k in needed if not str(prov.get(k, "")).strip()]
        if missing:
            return None, ("dataset provenance is missing %s"
                          % ", ".join(missing)), prov
        if prov.get("loader") == "github-jsonl":
            return github_jsonl_url(prov), None, prov
        return dataset_row_url(prov), None, prov
    url = prov.get("archive_url") or prov.get("source_url")
    if not url:
        return None, "no archive_url or source_url in the manifest", prov
    if not url.lower().startswith(ALLOWED_SCHEMES):
        return None, ("refusing scheme in %r, only http and https are "
                      "followed" % url[:40]), prov
    return url, None, prov


def _read_bounded(response, cap):
    """Read up to `cap` bytes, refusing more. Without a cap a single bad URL in
    the manifest is an out-of-memory exit rather than a reported failure, and
    the manifest is trusted as code but the URL it points at is not."""
    chunks, total = [], 0
    while True:
        chunk = response.read(_READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > cap:
            raise ValueError("response is larger than the %d-byte cap" % cap)
        chunks.append(chunk)
    return b"".join(chunks)


def fetch(url, field=None, prov=None):
    """(text, error).

    HTML goes through corpus_io.extract_text. A datasets-viewer response is
    already JSON holding the text, so it is read out of the named column
    instead: running an HTML extractor over a JSON payload would hash the
    payload rather than the prose. A github-jsonl response is the raw text of
    a pinned file, so the named row is json-decoded out of its line, which
    raw.githubusercontent serves as text/plain and the content type cannot
    distinguish from any other file.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = _read_bounded(response, MAX_BYTES)
            charset = response.headers.get_content_charset() or "utf-8"
            content_type = response.headers.get_content_type()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return None, str(exc)
    try:
        body = raw.decode(charset, errors="replace")
    except LookupError:
        body = raw.decode("utf-8", errors="replace")

    if prov and prov.get("loader") == "github-jsonl":
        lines = [line for line in body.splitlines() if line.strip()]
        try:
            row_index = int(prov.get("row"))
        except (TypeError, ValueError):
            return None, "github-jsonl provenance has a non-integer row"
        if not 0 <= row_index < len(lines):
            return None, ("row %d is outside the %d record(s) the pinned "
                          "file holds" % (row_index, len(lines)))
        try:
            record = json.loads(lines[row_index])
        except ValueError as exc:
            return None, "the pinned row is not JSON: %s" % exc
        column = prov.get("field") or field
        if not column or column not in record:
            return None, ("provenance names no `field`, or one the record "
                          "lacks. Keys: %s" % ", ".join(sorted(record)))
        return corpus_io.normalize(str(record[column])), None

    if url.startswith(DATASETS_SERVER) or content_type == "application/json":
        try:
            rows = json.loads(body).get("rows", [])
        except ValueError as exc:
            return None, "the viewer did not return JSON: %s" % exc
        if not rows:
            return None, "the viewer returned no rows for that offset"
        row = rows[0].get("row", {})
        if field:
            if field not in row:
                return None, ("column %r is not in that row. Columns: %s"
                              % (field, ", ".join(sorted(row))))
            value = row[field]
        else:
            # No column named: only unambiguous when there is one string column.
            strings = [k for k, v in row.items() if isinstance(v, str)]
            if len(strings) != 1:
                return None, ("provenance names no `field` and the row has %d "
                              "string columns (%s). Name one, or the sample is "
                              "not identified" % (len(strings), ", ".join(sorted(strings))))
            value = row[strings[0]]
        return corpus_io.normalize(str(value)), None

    return corpus_io.extract_text(body), None


def status_of(sample, texts_dir=None):
    """What this checkout already has: verified, moved, or missing."""
    text = corpus_io.read_text(sample, texts_dir)
    if text is None:
        return "missing"
    return "verified" if corpus_io.digest(text) == sample["sha256"] else "moved"


def process(sample, refetch, dry_run, texts_dir=None):
    """One sample. Returns a result row, and writes at most one file."""
    row = {"id": sample["id"], "label": sample["label"],
           "before": status_of(sample, texts_dir)}
    if row["before"] == "verified" and not refetch:
        row["action"] = "kept"
        return row

    url, why_not, prov = fetchable(sample)
    if url is None:
        row["action"] = "skipped"
        row["note"] = why_not
        return row
    row["url"] = url

    if dry_run:
        row["action"] = "would fetch"
        return row

    text, error = fetch(url, prov.get("field"), prov)
    if text is None:
        row["action"] = "failed"
        row["note"] = error
        return row

    row["sha256"] = corpus_io.digest(text)
    row["matched"] = row["sha256"] == sample["sha256"]
    directory = texts_dir or corpus_io.TEXTS_DIR
    os.makedirs(directory, exist_ok=True)
    destination = corpus_io.text_path(sample, texts_dir)

    if row["matched"]:
        with open(destination, "w", encoding="utf-8") as fh:
            fh.write(text)
        row["action"] = "fetched"
        return row

    # A mismatch never lands on a good local copy. "The source changed" and "our
    # extractor changed" are indistinguishable from here and only one of them
    # means the sample is dead.
    beside = destination[:-len(".txt")] + ".fetched.txt"
    with open(beside, "w", encoding="utf-8") as fh:
        fh.write(text)
    row["action"] = "mismatch"
    row["written_to"] = os.path.basename(beside)
    row["note"] = (
        "manual extraction, so a byte-exact refetch was never expected"
        if sample.get("provenance", {}).get("extraction") != corpus_io.EXTRACTION_AUTO
        else "this sample was extracted by this script and no longer reproduces")
    return row


def report(rows, dry_run):
    out = ["corpus refetch: %d sample(s)" % len(rows), ""]
    if not rows:
        out.append("The manifest is empty. Nothing to fetch, and the "
                   "calibration in PROOF.md still rests on two hand-written "
                   "samples until somebody populates it. "
                   "docs/detector-corpus/README.md has the protocol.")
        return "\n".join(out)

    out.append("  %-18s %-10s %-12s %s" % ("id", "label", "action", "note"))
    for row in rows:
        note = row.get("note", "")
        if row["action"] == "mismatch":
            note = "wrote %s: %s" % (row.get("written_to", "?"), note)
        out.append("  %-18s %-10s %-12s %s"
                   % (row["id"], row["label"], row["action"], note[:70]))
    out.append("")

    tally = {}
    for row in rows:
        tally[row["action"]] = tally.get(row["action"], 0) + 1
    out.append(", ".join("%d %s" % (n, a) for a, n in sorted(tally.items())))

    if dry_run:
        out.append("")
        out.append("Dry run. Nothing was fetched and nothing was written.")

    mismatched = [r for r in rows if r["action"] == "mismatch"]
    if mismatched:
        out.append("")
        out.append("%d sample(s) fetched to different bytes than the manifest "
                   "records. Nothing was overwritten. Read the .fetched.txt "
                   "beside each one: a source that was edited kills the sample, "
                   "and an extraction that drifted is a bug here."
                   % len(mismatched))
    manual = [r for r in rows
              if r["action"] == "mismatch" and "manual" in r.get("note", "")]
    if manual:
        out.append("")
        out.append("%d of those were extracted by hand and never claimed to "
                   "round-trip. That is recorded per sample rather than "
                   "guessed: see provenance.extraction." % len(manual))
    return "\n".join(out)


def main():
    examples = [
        "python3 scripts/detector-corpus/fetch_samples.py",
        "python3 scripts/detector-corpus/fetch_samples.py --all",
        "python3 scripts/detector-corpus/fetch_samples.py --dry-run",
        "python3 scripts/detector-corpus/fetch_samples.py --id human-0001"
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples
    )
    ap.add_argument("--all", action="store_true",
                    help="refetch every sample, including ones already "
                         "verified here, and check they still hash the same")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be fetched, make no requests")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--id", action="append",
                    help="only this sample id. Repeatable")
    args = ap.parse_args()

    manifest = corpus_io.load()
    samples = manifest.get("samples", [])
    bad_ids = sorted({s["id"] for s in samples
                      if "id" in s and not corpus_io.ID_RX.fullmatch(s["id"])})
    if bad_ids:
        print(cli_error.format_llm_error(
            "fetch_samples.py",
            "manifest has ids that are not slugs (lowercase ascii, digits, hyphens), which is a path-traversal vector in texts/: %s"
            % ", ".join(bad_ids),
            parser=ap, examples=examples
        ), file=sys.stderr)
        return 1
    if args.id:
        wanted = set(args.id)
        samples = [s for s in samples if s["id"] in wanted]
        unknown = wanted - {s["id"] for s in samples}
        if unknown:
            print(cli_error.format_llm_error(
                "fetch_samples.py",
                "no such sample id(s): %s" % ", ".join(sorted(unknown)),
                parser=ap, examples=examples
            ), file=sys.stderr)
            return 1


    rows = []
    for index, sample in enumerate(samples):
        if index and not args.dry_run:
            time.sleep(DELAY_SECONDS)
        rows.append(process(sample, args.all, args.dry_run))

    if args.json:
        print(json.dumps({"rows": rows, "dry_run": args.dry_run}, indent=2))
    else:
        print(report(rows, args.dry_run))

    if args.dry_run:
        return 0
    bad = [r for r in rows if r["action"] in ("failed", "mismatch", "skipped")]
    unresolved = [r for r in rows
                  if r["action"] == "kept" and r["before"] != "verified"]
    return 1 if bad or unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
