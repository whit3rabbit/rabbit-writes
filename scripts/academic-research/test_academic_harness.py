#!/usr/bin/env python3
"""
The academic-corpus pipeline, tested over synthetic JATS. No network.

Everything here builds its own article XML, manifest, and corpus directory in
a temporary tree. `01_fetch_corpus.py` is the one stage that would reach the
network and the tests that touch it substitute a stub for `get`, which is the
same bargain test_thesaurus_harness.py and test_corpus_harness.py make.

The properties worth holding, in the order they cost us something:

  * Nested <sec> is parsed by depth, not by a non-greedy regex. The regex
    version truncates every multi-part Results section to its preamble, and
    the symptom is a corpus that measures shorter and cleaner than the papers
    in it.
  * A license that is not plain CC BY refuses the paper rather than warning.
    A corpus holding one article nobody may redistribute is a corpus whose
    whole provenance claim has to be re-argued.
  * A slugified DOI cannot escape the texts directory. The manifest is trusted
    as code, and a trust boundary is checked everywhere it is crossed.
  * Tables and figures are dropped whole before tags are stripped. Stripped
    the other way round, a table's cells survive as a run of unpunctuated
    noun phrases, which reads to the engine as a list nobody wrote.

    python3 scripts/academic-research/test_academic_harness.py

Stdlib only, 3.9+. Takes no arguments.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
for path in (HERE, ENGINE):
    if path not in sys.path:
        sys.path.insert(0, path)

import academic_io as aio                               # noqa: E402


def load_stage(filename):
    """A numbered stage, loaded by path: `01_fetch_corpus` is not a legal
    module name, which is why nothing imports these and this loader exists."""
    spec = importlib.util.spec_from_file_location(
        filename.replace(".py", "").replace("0", "stage", 1),
        os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CC_BY = 'http://creativecommons.org/licenses/by/4.0/'
CC_BY_NC = 'http://creativecommons.org/licenses/by-nc/4.0/'


def article(license_url=CC_BY, extra_body=""):
    return """<article>
  <front><permissions>
    <license xlink:href="%s" xlink:type="simple"><license-p>Open.</license-p></license>
  </permissions>
  <abstract><p>%s</p></abstract></front>
  <body>
    <sec><title>Introduction</title>
      <p>%s</p>
      <p>A second paragraph of introduction prose sits here.</p>
    </sec>
    <sec><title>Materials and methods</title>
      <p>Reagents were prepared according to the protocol.</p>
    </sec>
    <sec><title>Results</title>
      <p>The first result paragraph reports what the measurement showed.</p>
      <sec><title>Subgroup analysis</title>
        <p>MARKER_NESTED appears only inside a nested section.</p>
      </sec>
      <sec><title>Sensitivity analysis</title>
        <p>A second nested subsection follows the first one here.</p>
      </sec>
    </sec>
    <sec><title>Discussion</title><p>%s</p></sec>
    %s
  </body>
</article>""" % (license_url, "Summary sentence here. " * 40,
                 "OPENING_MARKER and then more prose. " * 40,
                 "Closing sentence here. " * 40, extra_body)


failures = []
ran = []


def check(name, fn):
    ran.append(name)
    try:
        fn()
    except AssertionError as exc:
        failures.append("%s: %s" % (name, exc))


class sandbox(object):
    """A temporary corpus directory, with academic_io pointed at it."""

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="rw-academic-")
        self._saved = (aio.CORPUS_DIR, aio.MANIFEST_PATH, aio.TEXTS_DIR,
                       aio.SUMMARY_PATH)
        aio.CORPUS_DIR = self.tmp
        aio.MANIFEST_PATH = os.path.join(self.tmp, "manifest.json")
        aio.TEXTS_DIR = os.path.join(self.tmp, "texts")
        aio.SUMMARY_PATH = os.path.join(self.tmp, "summary.json")
        return self

    def __exit__(self, *exc):
        (aio.CORPUS_DIR, aio.MANIFEST_PATH,
         aio.TEXTS_DIR, aio.SUMMARY_PATH) = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)
        return False


# --------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------

def test_the_four_prose_slots_are_extracted():
    secs = aio.extract(article())
    assert set(secs) == {"abstract", "introduction", "results", "discussion"}, \
        str(sorted(secs))


def test_methods_is_not_extracted():
    """Procedural text full of reagents and equations would measure the genre
    of a protocol rather than the register of a paper."""
    secs = aio.extract(article())
    joined = " ".join(secs.values())
    assert "Reagents were prepared" not in joined, joined[:200]


def test_a_nested_subsection_survives():
    """The bug a non-greedy `<sec>.*?</sec>` would cause, asserted directly.
    Truncated, Results would stop at its first paragraph and the corpus would
    measure shorter and cleaner than the papers in it."""
    secs = aio.extract(article())
    assert "MARKER_NESTED" in secs["results"], secs["results"][:300]
    assert "second nested subsection" in secs["results"], secs["results"][:300]


def test_the_section_title_is_not_glued_to_the_prose():
    """assemble() writes the heading. Left in, every section opened with its
    own name as a bare word attached to the first sentence."""
    secs = aio.extract(article())
    assert secs["introduction"].startswith("OPENING_MARKER"), \
        secs["introduction"][:80]
    assert "Introduction" not in secs["introduction"], secs["introduction"][:80]


def test_a_table_is_dropped_whole():
    """Dropped after tag-stripping instead, a table's cells survive as a run of
    unpunctuated noun phrases the engine reads as a list."""
    xml = article(extra_body="<sec><title>Results</title><table-wrap>"
                             "<table><tr><td>CELLTEXT</td></tr></table>"
                             "</table-wrap><p>Prose.</p></sec>")
    secs = aio.extract(xml)
    assert "CELLTEXT" not in " ".join(secs.values()), str(secs)[:200]


def test_paragraph_boundaries_survive():
    """Paragraph length and uniformity are among the cells being calibrated, so
    a corpus flattened to one block would measure a document nobody wrote."""
    secs = aio.extract(article())
    assert "\n\n" in secs["introduction"], repr(secs["introduction"][:200])


def test_assemble_orders_the_slots_and_writes_headings():
    doc = aio.assemble(aio.extract(article()))
    for slot in ("Abstract", "Introduction", "Results", "Discussion"):
        assert "## " + slot in doc, doc[:200]
    assert doc.index("## Abstract") < doc.index("## Discussion")


# --------------------------------------------------------------------------
# license and provenance
# --------------------------------------------------------------------------

def test_plain_cc_by_is_accepted():
    assert aio.LICENSE_OK.search(aio.license_of(article()))


def test_a_non_commercial_license_is_refused():
    """Rejected rather than judged. The judgment is a lawyer's, and PLOS is
    uniformly plain BY so the corpus never needs it."""
    assert not aio.LICENSE_OK.search(aio.license_of(article(CC_BY_NC)))


def test_an_article_with_no_license_element_is_refused():
    assert aio.license_of("<article><body><p>Hi.</p></body></article>") is None


def test_fetch_refuses_a_non_cc_by_article():
    stage = load_stage("01_fetch_corpus.py")
    stage.get = lambda url, timeout=60: article(CC_BY_NC)
    with sandbox():
        try:
            stage.fetch_one({"doi": "10.1371/journal.pone.0000001",
                             "source_url": "stub"})
        except ValueError as exc:
            assert "CC BY" in str(exc), str(exc)
        else:
            raise AssertionError("a by-nc article was accepted")


def test_fetch_writes_the_text_and_records_a_hash():
    stage = load_stage("01_fetch_corpus.py")
    stage.get = lambda url, timeout=60: article()
    with sandbox():
        entry = stage.fetch_one({"doi": "10.1371/journal.pone.0000001",
                                 "source_url": "stub"})
        path = aio.text_path(entry["doi"])
        assert os.path.exists(path), path
        with open(path, encoding="utf-8") as fh:
            assert aio.sha256(fh.read()) == entry["sha256"]
        assert entry["words"] > 200, entry["words"]
        assert set(entry["sections"]) == {"abstract", "introduction",
                                          "results", "discussion"}


def test_verify_catches_an_edited_text():
    """The property that makes a published rate checkable by somebody who does
    not trust us. Without it the manifest hash is decoration."""
    stage = load_stage("01_fetch_corpus.py")
    stage.get = lambda url, timeout=60: article()
    with sandbox():
        entry = stage.fetch_one({"doi": "10.1371/journal.pone.0000001",
                                 "source_url": "stub"})
        manifest = {"papers": [entry]}
        assert not stage.verify(manifest), str(stage.verify(manifest))
        with open(aio.text_path(entry["doi"]), "a", encoding="utf-8") as fh:
            fh.write("An extra sentence nobody published.\n")
        assert stage.verify(manifest), "an edited text verified clean"


# --------------------------------------------------------------------------
# the manifest is trusted as code, so its ids are bounded
# --------------------------------------------------------------------------

def test_a_doi_that_would_escape_the_texts_directory_is_refused():
    for doi in ("../../etc/passwd", "10.1371/../../x", "/abs/path",
                "10.9999/journal.pone.1"):
        try:
            aio.slug(doi)
        except ValueError:
            continue
        raise AssertionError("slug accepted %r" % doi)


def test_a_slugged_path_stays_inside_the_texts_directory():
    with sandbox():
        path = os.path.abspath(aio.text_path("10.1371/journal.pone.0000001"))
        assert path.startswith(os.path.abspath(aio.TEXTS_DIR) + os.sep), path


def test_problems_rejects_a_manifest_missing_provenance():
    bad = aio.problems({"papers": [{"doi": "10.1371/journal.pone.0000001"}]})
    for field in ("license", "sha256", "source_url"):
        assert any(field in p for p in bad), str(bad)


def test_problems_rejects_a_non_cc_by_entry():
    bad = aio.problems({"papers": [{
        "doi": "10.1371/journal.pone.0000001", "journal": "PLOS One",
        "subject": "x", "published": "2026-01-01", "license": CC_BY_NC,
        "source_url": "u", "sha256": "0" * 64, "words": 900, "sections": {}}]})
    assert any("not plain CC BY" in p for p in bad), str(bad)


def test_problems_rejects_a_duplicate_paper():
    entry = {"doi": "10.1371/journal.pone.0000001", "journal": "PLOS One",
             "subject": "x", "published": "2026-01-01", "license": CC_BY,
             "source_url": "u", "sha256": "0" * 64, "words": 900, "sections": {}}
    bad = aio.problems({"papers": [entry, dict(entry)]})
    assert any("twice" in p for p in bad), str(bad)


def test_problems_rejects_a_sample_under_the_reliability_floor():
    """Under 120 words the engine's own stylometrics mean little, and 200 is
    the margin. Publishing a rate over noise is worse than publishing none."""
    entry = {"doi": "10.1371/journal.pone.0000001", "journal": "PLOS One",
             "subject": "x", "published": "2026-01-01", "license": CC_BY,
             "source_url": "u", "sha256": "0" * 64, "words": 40, "sections": {}}
    bad = aio.problems({"papers": [entry]})
    assert any("reliability floor" in p for p in bad), str(bad)


def test_the_shipped_manifest_validates():
    """The real one, if it is present. A committed manifest that does not pass
    its own checker is the failure this whole module exists to prevent."""
    manifest = aio.load_manifest(os.path.join(
        REPO_ROOT, "docs", "academic-corpus", "manifest.json"))
    if not manifest.get("papers"):
        return
    bad = aio.problems(manifest)
    assert not bad, "\n".join(bad)


# --------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------

def test_measure_counts_documents_and_hits_separately():
    """A rule firing five times in one paper is one document and five hits, and
    conflating them turns one wordy author into a register fact."""
    stage = load_stage("02_measure.py")
    text = "We delve into the tapestry. " * 20
    papers = [({"doi": "10.1371/journal.pone.0000001", "journal": "PLOS One"},
               text)] * 2
    stats = stage.measure(papers, "blog")
    assert "tier1" in stats, str(sorted(stats))
    assert stats["tier1"]["docs"] == 2, stats["tier1"]
    assert stats["tier1"]["hits"] >= stats["tier1"]["docs"], stats["tier1"]


def test_measure_records_the_terms_that_drove_a_finding():
    """The terms are what separates a register fact from one author's habit,
    which is the distinction that set the exemption list."""
    stage = load_stage("02_measure.py")
    papers = [({"doi": "10.1371/journal.pone.0000001", "journal": "PLOS One"},
               "We delve into the tapestry. " * 20)]
    stats = stage.measure(papers, "blog")
    terms = stats["tier1"]["terms"]
    assert "tapestry" in terms, str(terms)
    # The phrase list reports the phrase, not its head word. Asserted because
    # the exemption list is built by reading these keys, and a key that is not
    # the string the lexicon holds cannot be exempted by name.
    assert "delve into" in terms, str(terms)


TESTS = [(n, f) for n, f in sorted(globals().items())
         if n.startswith("test_") and callable(f)]


def main():
    for name, fn in TESTS:
        check(name, fn)
    for name in ran:
        failed = any(f.startswith(name + ":") for f in failures)
        print("  %s  %s" % ("FAIL" if failed else "pass", name))
    if failures:
        print("\n%d failure(s):" % len(failures))
        for f in failures:
            print("  %s" % f)
        return 1
    print("\n%d passed" % len(ran))
    return 0


if __name__ == "__main__":
    sys.exit(main())
