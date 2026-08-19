#!/usr/bin/env python3
"""
Fetch the academic calibration corpus from PLOS. Network, one-shot.

Two modes, and the split is what makes the corpus reproducible.

`--discover` queries the PLOS search API across the subject facets in
academic_io.SUBJECTS and pins whatever it finds into the manifest as DOIs. It
is the only step that decides which papers are in the corpus, and it is run
once and then not again, because rerunning it against a live index returns a
different set and quietly moves every number measured off the old one.

The default mode fetches the DOIs the manifest already names and verifies each
extracted text against its recorded SHA-256. That is the mode anybody checking
a published rate runs, and it needs no judgment: the committed manifest fully
determines the corpus.

The prose lands in docs/academic-corpus/texts/, which git ignores. See
academic_io's module docstring for why hashes travel and 800KB of somebody
else's papers does not.

Usage:
  python3 scripts/academic-research/01_fetch_corpus.py --discover
  python3 scripts/academic-research/01_fetch_corpus.py
  python3 scripts/academic-research/01_fetch_corpus.py --verify

Exit code: 0 on success, 1 on a fetch, license, or hash failure. Stdlib only.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
for path in (HERE, ENGINE):
    if path not in sys.path:
        sys.path.insert(0, path)

import academic_io as aio                               # noqa: E402
from rwlib import cli_error                             # noqa: E402


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": aio.USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def discover():
    """Query PLOS per subject and return manifest entries, unfetched.

    Newest first, inside a date window. Two lessons from the first run, both
    the same lesson. Sorting by id ascending returned PLOS Biology articles
    from 2003 and 2004, which carry no machine-readable <license> element at
    all, so `fetch_one` refused all fifteen of them. They were also the wrong
    papers: this corpus calibrates a register against how people write now, and
    a twenty-year-old paper answers a question nobody asked.

    Newest-first is not reproducible against a live index, which is the point
    of pinning the result into the manifest rather than re-deriving it.
    """
    found = []
    for subject in aio.SUBJECTS:
        query = {
            "q": 'subject:"%s" AND doc_type:full AND article_type:"Research Article"'
                 ' AND publication_date:[%s TO NOW]' % (subject, aio.EARLIEST),
            "fl": "id,journal,publication_date",
            "rows": str(aio.PAPERS_PER_SUBJECT),
            "sort": "publication_date desc",
            "wt": "json",
        }
        url = aio.SEARCH_URL + "?" + urllib.parse.urlencode(query)
        try:
            docs = json.loads(get(url))["response"]["docs"]
        except (urllib.error.URLError, ValueError, KeyError) as exc:
            print("  %-40s FAILED: %s" % (subject[:40], exc), file=sys.stderr)
            continue
        for doc in docs:
            doi = doc.get("id", "")
            if not aio.DOI_RX.match(doi):
                continue
            found.append({
                "doi": doi,
                "journal": doc.get("journal", ""),
                "subject": subject,
                "published": (doc.get("publication_date") or "")[:10],
                "source_url": aio.ARTICLE_URL % doi,
            })
        print("  %-42s %d paper(s)" % (subject[:42], len(docs)))
    return found


def fetch_one(entry):
    """Fetch, license-check, extract, and write one paper. Returns the entry.

    The license check is a refusal rather than a warning. A corpus that holds
    one article nobody may redistribute is a corpus whose whole provenance
    claim has to be re-argued, and the fetcher is where that stays cheap.
    """
    xml = get(entry["source_url"])
    license_url = aio.license_of(xml)
    if not license_url or not aio.LICENSE_OK.search(license_url):
        raise ValueError("license is %r, not plain CC BY" % license_url)

    sections = aio.extract(xml)
    if not sections:
        raise ValueError("no abstract or body sections extracted")
    text = aio.assemble(sections)
    words = aio.word_count(text)
    if words < 200:
        raise ValueError("only %d words, under the scan reliability floor" % words)

    os.makedirs(aio.TEXTS_DIR, exist_ok=True)
    with open(aio.text_path(entry["doi"]), "w", encoding="utf-8") as fh:
        fh.write(text)

    entry = dict(entry)
    entry["license"] = license_url
    entry["sha256"] = aio.sha256(text)
    entry["words"] = words
    entry["sections"] = {k: aio.word_count(v) for k, v in sorted(sections.items())}
    return entry


def verify(manifest):
    """Check every text on disk against its recorded hash. No network."""
    bad = []
    for paper in manifest["papers"]:
        path = aio.text_path(paper["doi"])
        if not os.path.exists(path):
            bad.append("%s: no text on disk, run without --verify" % paper["doi"])
            continue
        with open(path, encoding="utf-8") as fh:
            got = aio.sha256(fh.read())
        if got != paper["sha256"]:
            bad.append("%s: sha256 %s, manifest says %s"
                       % (paper["doi"], got[:12], paper["sha256"][:12]))
    return bad


def main(argv):
    examples = [
        "python3 scripts/academic-research/01_fetch_corpus.py --discover",
        "python3 scripts/academic-research/01_fetch_corpus.py",
        "python3 scripts/academic-research/01_fetch_corpus.py --verify",
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    ap.add_argument("--discover", action="store_true",
                    help="query PLOS and pin a new paper set into the manifest")
    ap.add_argument("--verify", action="store_true",
                    help="hash-check the texts already on disk, no network")
    args = ap.parse_args(argv)

    manifest = aio.load_manifest()

    if args.verify:
        bad = verify(manifest)
        for line in bad:
            print("  FAIL  %s" % line, file=sys.stderr)
        print("verified %d paper(s), %d mismatch(es)"
              % (len(manifest["papers"]), len(bad)))
        return 1 if bad else 0

    if args.discover:
        print("discovering across %d subject(s):" % len(aio.SUBJECTS))
        entries = discover()
        if not entries:
            print("no papers found, so nothing was pinned", file=sys.stderr)
            return 1
        known = {p["doi"]: p for p in manifest["papers"]}
        for entry in entries:
            known.setdefault(entry["doi"], entry)
        manifest["papers"] = [known[d] for d in sorted(known)]
        manifest["source"] = "PLOS search API, one query per subject facet"
    elif not manifest["papers"]:
        print("manifest names no papers. Run with --discover first.",
              file=sys.stderr)
        return 1

    print("fetching %d paper(s):" % len(manifest["papers"]))
    fetched, failed = [], []
    for paper in manifest["papers"]:
        try:
            fetched.append(fetch_one(paper))
            print("  %-34s %5d words" % (paper["doi"], fetched[-1]["words"]))
        except (urllib.error.URLError, ValueError, OSError) as exc:
            failed.append("%s: %s" % (paper["doi"], exc))
            print("  %-34s FAILED: %s" % (paper["doi"], exc), file=sys.stderr)

    manifest["papers"] = sorted(fetched, key=lambda p: p["doi"])
    # Not the clock. The corpus is dated by its own newest paper, so refetching
    # an unchanged set does not move the stamp, which is the same rule
    # readme-research/04_aggregate.py follows for `measured_at`.
    manifest["latest_published"] = max(
        [p.get("published", "") for p in manifest["papers"]] or [""])
    aio.save_manifest(manifest)

    bad = aio.problems(manifest)
    for line in bad:
        print("  INVALID  %s" % line, file=sys.stderr)

    print("\n%d paper(s) in the manifest, %d failed, %d manifest problem(s)"
          % (len(manifest["papers"]), len(failed), len(bad)))
    return 1 if (failed or bad) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
