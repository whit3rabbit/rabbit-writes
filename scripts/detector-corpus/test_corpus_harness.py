#!/usr/bin/env python3
"""
The detector-corpus harness, tested over a synthetic corpus.

The real corpus is empty, which is the whole problem `PROOF.md` admits to. The
harness around it is not, and until now nothing exercised it: the code that will
publish a false-positive rate the day somebody populates it had never run over a
populated corpus. A harness whose first real run is the run that produces the
published number is a harness nobody should believe.

So everything here builds its own manifest and its own texts in a temporary
directory. Nothing touches the network: `fetch()` is the only function that
would, and the two tests that reach it substitute a stub. That is deliberate and
worth stating, because `fetch_samples.py` is the one script in this repository
that makes requests at all.

    python3 test_corpus_harness.py

Stdlib only, 3.9+.
"""

import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import corpus_io  # noqa: E402
import fetch_samples  # noqa: E402

PAGE = ("<html><head><style>body{color:red}</style></head><body>"
        "<nav>Home | About</nav>"
        "<p>The cluster was retired on a Tuesday.</p>"
        "<p>Nobody outside the team noticed, which is the outcome you want.</p>"
        "<script>track()</script></body></html>")

failures = []


def check(name, condition, detail=""):
    if condition:
        print("  pass   %s" % name)
    else:
        print("  FAIL   %s  %s" % (name, detail))
        failures.append(name)


def sample(sid="human-0001", **overrides):
    entry = {
        "id": sid,
        "label": "human",
        "register": "technical-blog",
        "words": 20,
        "sha256": corpus_io.digest(corpus_io.extract_text(PAGE)),
        "provenance": {
            "source_url": "https://example.dev/posts/retired",
            "archive_url": "https://web.archive.org/web/20190304/https://example.dev/posts/retired",
            "published": "2019-03-04",
            "why_credible": "Wayback capture 2019-03-04",
            "extraction": corpus_io.EXTRACTION_AUTO,
        },
    }
    entry.update(overrides)
    return entry


def test_extraction_is_deterministic():
    a, b = corpus_io.extract_text(PAGE), corpus_io.extract_text(PAGE)
    check("extraction is deterministic", a == b)
    check("navigation and script are dropped",
          "Home" not in a and "track()" not in a, repr(a))
    check("prose survives", "cluster was retired" in a, repr(a))


def test_a_fetch_that_matches_writes_the_text():
    directory = tempfile.mkdtemp(prefix="rabbit-corpus-")
    real = fetch_samples.fetch
    try:
        fetch_samples.fetch = lambda url, field=None: (corpus_io.extract_text(PAGE), None)
        row = fetch_samples.process(sample(), False, False, texts_dir=directory)
        check("a matching fetch is recorded as fetched",
              row["action"] == "fetched", str(row))
        check("the text lands where score.py looks for it",
              os.path.exists(os.path.join(directory, "human-0001.txt")))
    finally:
        fetch_samples.fetch = real
        shutil.rmtree(directory, ignore_errors=True)


def test_a_mismatch_does_not_overwrite_a_good_copy():
    """"The source changed" and "our extractor changed" look identical from
    here, and only one of them means the sample is dead."""
    directory = tempfile.mkdtemp(prefix="rabbit-corpus-")
    real = fetch_samples.fetch
    try:
        entry = sample()
        good = os.path.join(directory, "human-0001.txt")
        with open(good, "w", encoding="utf-8") as fh:
            fh.write(corpus_io.extract_text(PAGE))
        fetch_samples.fetch = lambda url, field=None: ("something else entirely\n", None)
        row = fetch_samples.process(entry, True, False, texts_dir=directory)
        check("a mismatch is reported as one", row["action"] == "mismatch", str(row))
        with open(good, encoding="utf-8") as fh:
            kept = fh.read()
        check("the good copy is untouched",
              corpus_io.digest(kept) == entry["sha256"])
        check("the fetched bytes are kept beside it for a human",
              os.path.exists(os.path.join(directory, "human-0001.fetched.txt")))
    finally:
        fetch_samples.fetch = real
        shutil.rmtree(directory, ignore_errors=True)


def test_a_generated_sample_is_not_refetched():
    row = fetch_samples.process(
        sample("gen-0001", label="generated",
               provenance={"model": "claude-sonnet-4-5", "prompt": "write",
                           "generated": "2026-08-11"}),
        False, True)
    check("a generated sample is skipped rather than fetched",
          row["action"] == "skipped", str(row))
    check("and says why", "regenerating" in row.get("note", ""), str(row))


def test_a_non_http_url_is_refused():
    """The manifest is a file in the repository, so it is as trusted as the
    code. Handing an arbitrary scheme to urllib is not a thing to do on the
    strength of that."""
    for bad in ("file:///etc/passwd", "ftp://example.dev/x", "javascript:x"):
        entry = sample()
        entry["provenance"]["archive_url"] = bad
        url, why = fetch_samples.fetchable(entry)
        check("refuses %s" % bad.split(":")[0], url is None and "scheme" in (why or ""),
              str((url, why)))


def test_a_runaway_response_is_refused_not_read_whole():
    """`response.read()` into memory with no cap is an out-of-memory exit on a
    broken or hostile archive URL. The cap turns it into a reported failure."""
    import urllib.request

    class RunawayHeaders:
        def get_content_charset(self):
            return "utf-8"

        def get_content_type(self):
            return "text/html"

    class RunawayResponse:
        headers = RunawayHeaders()

        def read(self, n=None):
            # Keep serving bytes forever; the cap has to be what stops this.
            return b"x" * (n or fetch_samples._READ_CHUNK)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    real = urllib.request.urlopen
    try:
        urllib.request.urlopen = lambda *a, **k: RunawayResponse()
        text, err = fetch_samples.fetch("https://example.dev/x")
        check("an oversized response is refused",
              text is None and "cap" in (err or ""), str((text, err)))
    finally:
        urllib.request.urlopen = real


def test_a_verified_sample_is_not_refetched_without_all():
    directory = tempfile.mkdtemp(prefix="rabbit-corpus-")
    try:
        entry = sample()
        with open(os.path.join(directory, "human-0001.txt"), "w",
                  encoding="utf-8") as fh:
            fh.write(corpus_io.extract_text(PAGE))
        row = fetch_samples.process(entry, False, True, texts_dir=directory)
        check("an already-verified sample is left alone",
              row["action"] == "kept", str(row))
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_the_manifest_validator_still_rejects_a_late_human():
    entry = sample()
    entry["provenance"]["published"] = "2024-01-01"
    issues = corpus_io.problems({"samples": [entry]}, ("technical-blog",))
    check("a human sample after the cutoff is rejected",
          any("cutoff" in i for i in issues), str(issues))


def test_problems_rejects_an_id_that_is_not_a_slug():
    """An id is a filename inside texts/, so a slash, a `..`, or a space is a
    path-traversal vector rather than a naming quirk. Slug-only, the same trust
    boundary the URL-scheme check holds."""
    for bad in ("../../etc/passwd", "a/b", "Upper", "has space"):
        entry = sample(bad)
        issues = corpus_io.problems({"samples": [entry]}, ("technical-blog",))
        check("rejects id %r" % bad, any("slug" in i for i in issues), str(issues))
    clean = corpus_io.problems({"samples": [sample("human-0001")]},
                               ("technical-blog",))
    check("a slug id raises no slug problem",
          not any("slug" in i for i in clean), str(clean))


def test_text_path_refuses_to_escape_the_texts_directory():
    """Defense in depth behind the slug check: an id that reached text_path
    without validation must not read or write outside the texts directory."""
    directory = tempfile.mkdtemp(prefix="rabbit-corpus-")
    try:
        for bad in ("../../etc/passwd", "sub/x", "/abs"):
            raised = False
            try:
                corpus_io.text_path({"id": bad}, texts_dir=directory)
            except ValueError:
                raised = True
            check("refuses id %r" % bad, raised, "no ValueError raised")
        legit = corpus_io.text_path({"id": "human-0001"}, texts_dir=directory)
        check("a slug id resolves inside the texts dir",
              legit == os.path.join(directory, "human-0001.txt"), legit)
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_wilson_does_not_collapse_on_zero():
    """"0 of 20 flagged" is not "a 0% false-positive rate". It is "somewhere
    under 17%", and the interval is the honest half of the claim."""
    rate, lo, hi = corpus_io.wilson(0, 20)
    check("zero successes gives a zero point estimate", rate == 0.0)
    check("and an interval that is not zero", hi > 0.15, str((lo, hi)))
    # Pinned against the real numbers, not the round ones. Fifty samples is
    # 7.14%, not "under 7%", and 52 is where it crosses. A test asserting the
    # rounder claim would have left the docstring wrong, which it was.
    _, _, hi50 = corpus_io.wilson(0, 50)
    check("fifty samples gives 7.1 percent, not under 7",
          0.071 < hi50 < 0.072, str(hi50))
    check("fifty-one is still above 7 percent",
          corpus_io.wilson(0, 51)[2] > 0.07, str(corpus_io.wilson(0, 51)[2]))
    check("fifty-two is where it crosses",
          corpus_io.wilson(0, 52)[2] < 0.07, str(corpus_io.wilson(0, 52)[2]))


# --------------------------------------------------------------------------
# dataset-sourced samples
# --------------------------------------------------------------------------
#
# A published research corpus collected years before the cutoff proves a date at
# least as well as a single Wayback capture, and is easier to cite. What it
# needs instead of an archive URL is enough to find the exact row again.

def dataset_sample(**overrides):
    entry = {
        "id": "human-ds-0001",
        "label": "human",
        "register": "casual",
        "words": 400,
        "sha256": "0" * 64,
        "provenance": {
            "dataset": "example/corpus",
            "config": "default",
            "split": "train",
            "row": 17,
            "revision": "abc1234",
            "field": "text",
            "collected": "2018-06-01",
            "license": "MIT",
            "why_credible": "Published corpus, collection date in the paper",
        },
    }
    entry.update(overrides)
    return entry


def test_a_dataset_sample_is_recognised_as_provenance():
    kind = corpus_io.human_provenance_kind(dataset_sample()["provenance"])
    check("a dataset row counts as provenance", kind == "dataset", str(kind))
    issues = corpus_io.problems({"samples": [dataset_sample()]}, ("casual",))
    check("and validates without an archive_url", not issues, str(issues))


def test_a_dataset_sample_still_has_to_predate_the_cutoff():
    """`collected` bounds when the text could have been written, so it is
    compared the same way `published` is. A corpus gathered in 2024 proves
    nothing about whether a generator wrote its rows."""
    late = dataset_sample()
    late["provenance"]["collected"] = "2024-05-01"
    issues = corpus_io.problems({"samples": [late]}, ("casual",))
    check("a corpus collected after the cutoff is rejected",
          any("cutoff" in i for i in issues), str(issues))


def test_a_dataset_sample_without_a_revision_is_rejected():
    """A dataset name with no revision is a name, not a citation: the rows move
    and the hash stops meaning anything."""
    loose = dataset_sample()
    del loose["provenance"]["revision"]
    issues = corpus_io.problems({"samples": [loose]}, ("casual",))
    check("a missing revision is a problem",
          any("revision" in i for i in issues), str(issues))
    url, why = fetch_samples.fetchable(loose)
    check("and it is not fetchable", url is None and "revision" in (why or ""),
          str((url, why)))


def test_a_sample_with_neither_kind_of_provenance_is_named():
    bare = dataset_sample()
    bare["provenance"] = {"why_credible": "trust me"}
    issues = corpus_io.problems({"samples": [bare]}, ("casual",))
    check("a human label with no evidence at all is rejected",
          any("neither" in i for i in issues), str(issues))


def test_the_row_url_pins_the_revision():
    url = fetch_samples.dataset_row_url(dataset_sample()["provenance"])
    for part in ("revision=abc1234", "offset=17", "split=train",
                 "dataset=example%2Fcorpus"):
        check("row URL carries %s" % part.split("=")[0], part in url, url)


def test_a_viewer_response_is_read_as_json_not_as_html():
    """Running the HTML extractor over a JSON payload would hash the payload
    rather than the prose."""
    import json as _json
    import urllib.request

    payload = _json.dumps({"rows": [{"row": {"text": "Real prose here.",
                                             "label": 1}}]}).encode("utf-8")

    class FakeHeaders:
        def get_content_charset(self):
            return "utf-8"

        def get_content_type(self):
            return "application/json"

    class FakeResponse:
        headers = FakeHeaders()

        def __init__(self):
            self.rest = payload

        def read(self, n=None):
            # A stream, not one whole-body read: `fetch` reads through
            # `_read_bounded` in chunks, and a fake that ignores `n` and returns
            # the body forever would never terminate.
            take, self.rest = self.rest[:n], self.rest[n:]
            return take

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    real = urllib.request.urlopen
    try:
        urllib.request.urlopen = lambda *a, **k: FakeResponse()
        text, err = fetch_samples.fetch(fetch_samples.DATASETS_SERVER + "?x=1", "text")
        check("the named column is what gets hashed",
              err is None and text.strip() == "Real prose here.", str((text, err)))
        _, err2 = fetch_samples.fetch(fetch_samples.DATASETS_SERVER + "?x=1", "nope")
        check("a column that is not there is an error, not a guess",
              err2 is not None and "nope" in err2, str(err2))
    finally:
        urllib.request.urlopen = real


# --------------------------------------------------------------------------
# Runner. Stays at the bottom: main() collects tests off globals(), so anything
# defined below it is invisible to a stdlib run and only pytest would find it.
# Six tests sat under the guard that way.

def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            print(name)
            fn()
    print("\n%d check(s) failed" % len(failures) if failures else "\nall checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
