#!/usr/bin/env python3
"""
Does the repository validator actually fire?

`scripts/validate.py` passing on this repository proves the repository is
valid. It does not prove any individual check works, and a check that can
never fail reads exactly the same from the outside as one that never has.
That gap is not theoretical here: the marketplace manifest shipped a 404
`$schema` for months because nothing was reading it, and `curly-quote` sat
unfirable in every register because the matrix had no per-cell test.

So each check gets driven over a fixture built to break it, in a temporary
copy of the tree, and is required to report. The copy matters: these checks
read the real repository by absolute path, so mutating a fixture in place
would mean editing tracked files to run the tests.

Stdlib only, 3.9+. Takes no arguments.

Usage:
  python3 scripts/test_validate_checks.py

Exit code: 0 when every check fired as expected, 1 otherwise.
"""

import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import validate                                        # noqa: E402

CITATIONS = os.path.join("skills", "rabbit-writes", "references", "citations")
FORMS = os.path.join("skills", "rabbit-writes", "references", "forms")

failures = []
ran = []


def check(name, fn):
    ran.append(name)
    try:
        fn()
    except AssertionError as exc:
        failures.append("%s: %s" % (name, exc))


class sandbox(object):
    """A throwaway copy of the tree, with validate.py pointed at it.

    The checks resolve everything from validate.SKILLS and validate.ROOT, so
    repointing those two is enough to run the real check function over a
    mutated copy without touching anything tracked.
    """

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="rw-validate-")
        self.dest = os.path.join(self.tmp, "repo")
        shutil.copytree(
            ROOT, self.dest,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "dist",
                                          ".pytest_cache", "docs", "scratch"))
        self._saved = (validate.ROOT, validate.SKILLS, validate.problems,
                       validate.notes)
        validate.ROOT = self.dest
        validate.SKILLS = os.path.join(self.dest, "skills")
        validate.problems = []
        validate.notes = []
        return self

    def __exit__(self, *exc):
        (validate.ROOT, validate.SKILLS,
         validate.problems, validate.notes) = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)
        return False

    def path(self, *parts):
        return os.path.join(self.dest, *parts)

    def edit(self, rel, old, new):
        full = self.path(rel)
        with open(full, encoding="utf-8") as fh:
            text = fh.read()
        assert old in text, "fixture text not found in %s: %r" % (rel, old[:60])
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text.replace(old, new, 1))

    def reported(self, needle):
        return [p for p in validate.problems if needle in p]


# --------------------------------------------------------------------------
# the citation checks
# --------------------------------------------------------------------------

def test_the_citation_check_passes_the_shipped_files():
    """The baseline. Without it, every test below passes on a broken check."""
    with sandbox() as s:
        validate.check_citation_files()
        assert not validate.problems, str(validate.problems)
        assert s.reported("") == []


def test_a_quoted_sentence_outside_tells_is_reported():
    """The rule that stops a style file shipping one way to introduce a source.

    A quoted phrase carrying a `<placeholder>` slot is a reference pattern and
    is legal anywhere. A quoted phrase with no slot in it is a sentence, and a
    sentence outside Tells is an example somebody added to be helpful.
    """
    with sandbox() as s:
        s.edit(os.path.join(CITATIONS, "apa7.md"),
               "## In-text\n",
               '## In-text\n\nOpen with "As Smith argues in her 2020 paper" '
               'and name the work.\n')
        validate.check_citation_files()
        hits = s.reported("quoted phrases outside")
        assert hits, "no report: %s" % validate.problems


def test_a_quoted_placeholder_slot_outside_tells_is_allowed():
    """The carve-out, asserted rather than assumed.

    MLA and Chicago quote the titles of shorter works inside their patterns.
    A rule that banned every quotation outside Tells would ban both styles
    from stating their own formats.
    """
    with sandbox() as s:
        s.edit(os.path.join(CITATIONS, "apa7.md"),
               "## In-text\n",
               '## In-text\n\n| `example` | `<Lastname>. "<Title of Work>." '
               '<Publisher>.` |\n')
        validate.check_citation_files()
        assert not s.reported("quoted phrases outside"), str(validate.problems)


def test_a_missing_source_type_row_is_reported():
    """Every style covers the same set, or picking a style also picks which
    sources the writer may cite."""
    with sandbox() as s:
        s.edit(os.path.join(CITATIONS, "ieee.md"), "| `dataset` |", "| `datasett` |")
        validate.check_citation_files()
        hits = s.reported("no reference-entry row for dataset")
        assert hits, "no report: %s" % validate.problems


def test_a_missing_guardrail_is_reported():
    with sandbox() as s:
        s.edit(os.path.join(CITATIONS, "mla9.md"),
               validate.CITATION_GUARDRAIL, "Formats live here.")
        validate.check_citation_files()
        assert s.reported("format guardrail"), str(validate.problems)


def test_a_missing_heading_is_reported():
    with sandbox() as s:
        s.edit(os.path.join(CITATIONS, "chicago17.md"),
               "## Reference entries", "## Entries")
        validate.check_citation_files()
        assert s.reported("has no '## Reference entries' section"), str(validate.problems)


def test_a_missing_applies_to_line_is_reported():
    with sandbox() as s:
        s.edit(os.path.join(CITATIONS, "apa7.md"), "**Applies to:**", "Applies to:")
        validate.check_citation_files()
        assert s.reported("Applies to"), str(validate.problems)


def test_an_empty_citations_directory_is_reported():
    """Deleting the layer must fail loudly. A check that returns quietly on an
    empty directory passes forever once somebody removes the files."""
    with sandbox() as s:
        for fn in os.listdir(s.path(CITATIONS)):
            os.unlink(s.path(CITATIONS, fn))
        validate.check_citation_files()
        assert s.reported("no style files"), str(validate.problems)


# --------------------------------------------------------------------------
# the form check, which had no test either
# --------------------------------------------------------------------------

def test_the_form_check_passes_the_shipped_files():
    with sandbox() as s:
        validate.check_form_files()
        assert not validate.problems, str(validate.problems)
        assert s.reported("") == []


def test_a_quoted_phrase_outside_tells_in_a_form_is_reported():
    """The form rule has no placeholder carve-out, on purpose: a form file
    states no formats, so every quotation in one is a phrase."""
    with sandbox() as s:
        s.edit(os.path.join(FORMS, "memo.md"),
               "## Slots\n", '## Slots\n\nOpen with "Dear team," every time.\n')
        validate.check_form_files()
        assert s.reported("quoted phrases outside"), str(validate.problems)


def test_a_form_routing_to_a_register_that_does_not_exist_is_reported():
    with sandbox() as s:
        s.edit(os.path.join(FORMS, "memo.md"),
               "**Register:** `formal`", "**Register:** `boardroom`")
        validate.check_form_files()
        assert s.reported("which is not in registers.json"), str(validate.problems)


def test_a_register_nothing_routes_to_is_reported():
    """The other direction. A register no form names is a column of tolerances
    that never applies to a real document."""
    with sandbox() as s:
        for fn in ("linkedin.md",):
            os.unlink(s.path(FORMS, fn))
        validate.check_form_files()
        assert s.reported("no form file routes to linkedin"), str(validate.problems)


# --------------------------------------------------------------------------
# the thesaurus alternatives check
# --------------------------------------------------------------------------

def test_thesaurus_alternatives_passes_shipped_file():
    with sandbox() as s:
        validate.check_thesaurus_alternatives()
        assert not validate.problems, str(validate.problems)
        assert s.reported("") == []


def test_thesaurus_alternatives_anti_tell_rejects_lexicon_matches():
    rel = os.path.join("skills", "rabbit-writes", "scripts", "thesaurus_alternatives.json")
    with sandbox() as s:
        s.edit(rel, '"delve into": [', '"delve into": ["notably,", ')
        validate.check_thesaurus_alternatives()
        assert s.reported("matches lexicon pattern 'confidence-calibration'"), str(validate.problems)



def test_thesaurus_alternatives_uppercase_key_reported():
    rel = os.path.join("skills", "rabbit-writes", "scripts", "thesaurus_alternatives.json")
    with sandbox() as s:
        s.edit(rel, '"delve into":', '"Delve Into":')
        validate.check_thesaurus_alternatives()
        assert s.reported("must be lowercase"), str(validate.problems)



# --------------------------------------------------------------------------
# the packaging metadata check
# --------------------------------------------------------------------------

def test_the_packaging_check_passes_the_shipped_files():
    with sandbox() as s:
        validate.check_packaging_metadata()
        assert not validate.problems, str(validate.problems)
        assert s.reported("") == []


def test_an_undeclared_endpoint_env_var_is_reported():
    """A var endpoint.py grows that no bundle declares is a rejected
    publish, and the check has to catch it before clawhub's scanner does."""
    with sandbox() as s:
        s.edit(os.path.join("skills", "rabbit-writes", "scripts", "rwlib",
                            "endpoint.py"),
               'ENV_API_KEY = "RABBIT_MODEL_API_KEY"',
               'ENV_API_KEY = "RABBIT_MODEL_API_KEY"\n'
               'ENV_TOKEN = "RABBIT_MODEL_TOKEN"')
        validate.check_packaging_metadata()
        assert s.reported("does not declare RABBIT_MODEL_TOKEN"), \
            "no report: %s" % validate.problems


def test_a_drifted_skill_version_is_reported():
    with sandbox() as s:
        s.edit(os.path.join("skills", "voice-setup", "SKILL.md"),
               'version: "0.1.0"', 'version: "0.2.0"')
        validate.check_packaging_metadata()
        assert s.reported("skills/voice-setup/SKILL.md says version"), \
            "no report: %s" % validate.problems


def test_a_blanked_env_description_is_reported():
    with sandbox() as s:
        s.edit(os.path.join("scripts", "package_skills.py"),
               '''    _endpoint.ENV_MODEL: (
        "Model name for --apply-model. Read only when scan.py runs with "
        "--apply-model. Falls back to local when unset."
    ),''',
               '    _endpoint.ENV_MODEL: "",')
        validate.check_packaging_metadata()
        assert s.reported("has an empty description"), \
            "no report: %s" % validate.problems


# --------------------------------------------------------------------------
# the rabbit-reads layout check
# --------------------------------------------------------------------------

LAYOUTS = os.path.join("skills", "rabbit-reads", "references", "layouts")


def test_the_layout_check_passes_the_shipped_files():
    with sandbox() as s:
        validate.check_layout_files()
        assert s.reported("") == []


def test_a_missing_layout_header_is_reported():
    with sandbox() as s:
        s.edit(os.path.join(LAYOUTS, "obsidian.md"),
               "**Frontmatter keys:** source, kind, tags, aliases",
               "Frontmatter keys are declared nowhere.")
        validate.check_layout_files()
        assert s.reported("has no Frontmatter keys header line"), \
            str(validate.problems)


def test_a_bad_spine_band_pair_is_reported():
    with sandbox() as s:
        s.edit(os.path.join(LAYOUTS, "obsidian.md"),
               "**Spine notes:** chapter:8-20, topic:8-25, summary:20-40",
               "**Spine notes:** chapter:20-8")
        validate.check_layout_files()
        assert s.reported("kind:min-max"), str(validate.problems)


def test_an_unknown_link_syntax_is_reported():
    with sandbox() as s:
        s.edit(os.path.join(LAYOUTS, "cheatsheets.md"),
               "**Link syntax:** markdown",
               "**Link syntax:** org-mode")
        validate.check_layout_files()
        assert s.reported("neither markdown nor wikilink"), \
            str(validate.problems)


TESTS = [(name, fn) for name, fn in sorted(globals().items())
         if name.startswith("test_") and callable(fn)]


def main():
    for name, fn in TESTS:
        check(name, fn)
    for name in ran:
        print("  %s  %s" % ("FAIL" if any(f.startswith(name + ":") for f in failures)
                            else "pass", name))
    if failures:
        print("\n%d failure(s):" % len(failures))
        for f in failures:
            print("  %s" % f)
        return 1
    print("\n%d checks fired as expected" % len(ran))
    return 0


if __name__ == "__main__":
    sys.exit(main())
