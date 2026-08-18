#!/usr/bin/env python3
"""
The skill packager, tested over its own archives.

Each zip claims to stand alone. The only honest test of that claim is to
extract one somewhere the sibling engine cannot possibly be found and run the
scripts it ships, from a working directory that is not this repository. So
everything here builds the archives into a temporary dist, extracts them under
a temporary install root, and drives them with subprocesses whose cwd is a
third, empty directory.

The `--apply-safe --write` case exists because that path once broke silently:
scan.py imports verify.py lazily, so a bundle missing it packages fine and
fails only when somebody asks for a fix.

The plugin layout is the other half of the same claim. Installed as a plugin
(or as Codex loose skills), the three skills sit side by side at a path that is
not this repository, and every script must resolve the sibling engine from
there. Both repo suites run from this checkout, which is the blind spot that
shipped two broken hooks, so the `test_plugin_layout_*` half copies `skills/`
to a temporary root and runs the same battery from a foreign working directory.
Copying only `skills/` is deliberate: it is the loose-skills install, the
strictest documented layout, and sibling resolution that survives it also
survives a full-repo install.

    python3 test_package_skills.py

Stdlib only, 3.9+.
"""

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import package_skills  # noqa: E402

WORK = tempfile.mkdtemp(prefix="rwpkg-test-")
atexit.register(shutil.rmtree, WORK, True)

INSTALL = os.path.join(WORK, "install")
PLUGIN = os.path.join(WORK, "plugin")
CWD = os.path.join(WORK, "cwd")

# A paragraph carrying a zero-width space, the one artifact --apply-safe
# always deletes. Written as an escape so no tool can normalize it away
# without changing this file.
FIXABLE = (
    "# Notes\n\n"
    "The rollout fin\u200bished on Tuesday and nobody paged. That is the "
    "outcome the runbook promised, and the graphs agree with it.\n"
)

README_SAMPLE = (
    "# widget\n\n"
    "Parses widget logs into one summary table. Built for operators who read "
    "the logs by hand today.\n\n"
    "## Install\n\n"
    "```bash\n"
    "pip install widget\n"
    "```\n\n"
    "## License\n\n"
    "MIT\n"
)

# A book just long enough for map_structure.py to see two chapters past its
# minimum block span, and nothing else it could mistake for a heading.
READS_BOOK = (
    "Test Book\n\n"
    "Preface\n\n"
    "A short front matter block so the mapper has something to classify.\n"
    "It runs a few lines so the block span rule is satisfied.\n\n"
    "Chapter 1. Alpha\n\n"
    "The first chapter body sits here across several plain lines.\n"
    "None of them look like headings, so only the line above maps.\n"
    "A third line keeps the block past the minimum span.\n\n"
    "Chapter 2. Beta\n\n"
    "The second chapter body follows the same plain shape.\n"
    "Two lines are enough once the chapter line itself is counted.\n"
    "A third line closes the book.\n"
)

# Two docs conforming to the non-fiction book type, sized for the band
# overrides the test passes rather than the shipped 40-70 band. The index
# Source cell is the whole locator off each doc's own Source line, book and
# all, because check_notes compares the two: a cell carrying only the chapter
# is the drift that check exists to catch.
READS_NOTES = {
    "README.md": (
        "# Reads Notes\n\n"
        "| Doc | Source | Kind |\n|---|---|---|\n"
        "| [alpha.md](alpha.md) | Test Book, ch. 1 | practice |\n"
        "| [beta.md](beta.md) | Test Book, ch. 2 | practice |\n"
    ),
    "alpha.md": (
        "# Alpha\n\n"
        "Source: Test Book, ch. 1 (practice)\n\n"
        "## What this is\n\n"
        "The first concept.\n\n"
        "## Practices\n\n"
        "1. Do the first thing.\n"
        "2. Do the second thing.\n"
        "3. Do the third thing.\n\n"
        "## Anti-patterns\n\n"
        "- Doing none of the things.\n\n"
        "## Tests\n\n"
        "- Was the first thing done?\n"
        "- Was the second thing done?\n\n"
        "## See also\n\n"
        "- beta.md\n"
    ),
    "beta.md": (
        "# Beta\n\n"
        "Source: Test Book, ch. 2 (practice)\n\n"
        "## What this is\n\n"
        "The second concept.\n\n"
        "## Practices\n\n"
        "1. Keep it plain.\n"
        "2. Keep it short.\n"
        "3. Keep it linked.\n\n"
        "## Anti-patterns\n\n"
        "- Keeping it ornate.\n\n"
        "## Tests\n\n"
        "- Is it plain?\n"
        "- Is it short?\n\n"
        "## See also\n\n"
        "- alpha.md\n"
    ),
}

failures = []
_built = False
_plugin_built = False


def check(name, condition, detail=""):
    if condition:
        print("  pass   %s" % name)
    else:
        print("  FAIL   %s  %s" % (name, detail))
        failures.append(name)


def ensure_built():
    """Package and extract all three skills once, into the temp root."""
    global _built
    if _built:
        return
    real_dist = package_skills.DIST_DIR
    package_skills.DIST_DIR = os.path.join(WORK, "dist")
    os.makedirs(package_skills.DIST_DIR, exist_ok=True)
    try:
        for skill in package_skills.SKILL_NAMES:
            if not package_skills.build_skill_zip(skill):
                raise RuntimeError("packaging failed for %s" % skill)
            with zipfile.ZipFile(zip_path(skill)) as zf:
                zf.extractall(INSTALL)
    finally:
        os.makedirs(CWD, exist_ok=True)
        _built = True
        # The temp dist survives for the tests; only the constant goes back.
        package_skills.TEST_DIST_DIR = package_skills.DIST_DIR
        package_skills.DIST_DIR = real_dist


def ensure_plugin_copy():
    """Copy the three skill directories side by side, outside the repo."""
    global _plugin_built
    if _plugin_built:
        return
    for skill in package_skills.SKILL_NAMES:
        shutil.copytree(
            os.path.join(package_skills.SKILLS_DIR, skill),
            os.path.join(PLUGIN, "skills", skill),
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "tests"))
    os.makedirs(CWD, exist_ok=True)
    _plugin_built = True


def plugin_path(skill, *rel):
    return os.path.join(PLUGIN, "skills", skill, *rel)


def zip_path(skill):
    return os.path.join(getattr(package_skills, "TEST_DIST_DIR", package_skills.DIST_DIR), skill + ".zip")


def installed(skill, *rel):
    return os.path.join(INSTALL, skill, *rel)


def run(args, cwd=CWD):
    return subprocess.run([sys.executable] + args, cwd=cwd,
                          capture_output=True, text=True, timeout=300)


def write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def test_archives_pass_the_gate_and_carry_no_plugin_var():
    ensure_built()
    for skill in package_skills.SKILL_NAMES:
        errors = package_skills.gate(zip_path(skill), skill)
        check("gate is clean for %s" % skill, errors == [], "; ".join(errors))
        with zipfile.ZipFile(zip_path(skill)) as zf:
            hits = [n for n in zf.namelist()
                    if b"${CLAUDE_PLUGIN_ROOT}" in zf.read(n)]
        check("no plugin variable anywhere in %s" % skill, hits == [], str(hits))


def test_substitution_drift_fails_the_build_loudly():
    try:
        package_skills.transform_markdown(
            "rabbit-writes", "SKILL.md", "a SKILL.md whose pinned lines were reworded")
    except ValueError as exc:
        check("a reworded source line raises rather than shipping stale",
              "expected exactly 1" in str(exc), str(exc))
    else:
        check("a reworded source line raises rather than shipping stale", False,
              "transform_markdown returned instead of raising")


def test_engine_zip_scans_and_fixes_standalone():
    ensure_built()
    sample = os.path.join(CWD, "engine-sample.md")
    write(sample, FIXABLE)
    scan = installed("rabbit-writes", "scripts", "scan.py")

    r = run([scan, sample, "--json"])
    payload = json.loads(r.stdout or "{}")
    check("scan.py --json runs from an extracted archive",
          r.returncode == 0 and "lexicon_version" in json.dumps(payload),
          r.stderr[:200] or r.stdout[:200])

    r = run([scan, sample, "--apply-safe", "--write"])
    with open(sample, encoding="utf-8") as fh:
        after = fh.read()
    check("--apply-safe --write reaches verify.py and writes",
          r.returncode == 0 and "\u200b" not in after,
          r.stderr[:200] or after[:120])


def test_vendored_engine_fixes_too():
    # The satellite bundles carry their own scan.py + verify.py. This is the
    # pair that shipped broken: vendoring scan.py without verify.py packages
    # fine and dies on the first --apply-safe.
    ensure_built()
    sample = os.path.join(CWD, "vendored-sample.md")
    write(sample, FIXABLE)
    r = run([installed("voice-setup", "scripts", "scan.py"), sample, "--apply-safe", "--write"])
    with open(sample, encoding="utf-8") as fh:
        after = fh.read()
    check("voice-setup's vendored scan.py fixes without the sibling engine",
          r.returncode == 0 and "\u200b" not in after,
          r.stderr[:200])


def test_voice_setup_checks_a_shipped_profile():
    ensure_built()
    r = run([installed("voice-setup", "scripts", "build_voice.py"), "--check", "whit3rabbit"])
    check("build_voice.py --check resolves a shipped profile by name",
          r.returncode == 0, (r.stderr or r.stdout)[:300])


def test_scan_resolves_a_voice_by_name_from_vendored_voices():
    ensure_built()
    sample = os.path.join(CWD, "voiced-sample.md")
    write(sample, README_SAMPLE)
    r = run([installed("voice-setup", "scripts", "scan.py"), sample, "--voice", "whit3rabbit"])
    check("scan.py --voice <name> resolves against the archive's voices/",
          r.returncode == 0 and "whit3rabbit" in r.stdout,
          (r.stderr or r.stdout)[:300])


def test_readme_check_runs_and_finds_its_voices_dir():
    ensure_built()
    pinned = os.path.join(WORK, "pinned-project")
    os.makedirs(pinned, exist_ok=True)
    write(os.path.join(pinned, "README.md"), README_SAMPLE)
    write(os.path.join(pinned, ".rabbit-voice"), "whit3rabbit\n")
    r = run([installed("readme-writing", "scripts", "readme_check.py"), "README.md", "--json"],
            cwd=pinned)
    payload = json.loads(r.stdout or "{}")
    check("readme_check.py runs standalone",
          r.returncode == 0, (r.stderr or r.stdout)[:300])
    check("a .rabbit-voice pin resolves against the vendored voices/",
          "whit3rabbit" in json.dumps(payload.get("voice", payload)),
          json.dumps(payload)[:300])


def test_rabbit_reads_extracts_maps_and_checks_standalone():
    ensure_built()
    book = os.path.join(CWD, "reads-book.txt")
    write(book, READS_BOOK)
    scripts = installed("rabbit-reads", "scripts")

    r = run([os.path.join(scripts, "extract_text.py"), book, "--stdout"])
    check("extract_text.py runs from an extracted archive",
          r.returncode == 0 and "Chapter 2. Beta" in r.stdout,
          (r.stderr or r.stdout)[:300])

    r = run([os.path.join(scripts, "map_structure.py"), book, "--json"])
    check("map_structure.py maps two chapters standalone",
          r.returncode == 0 and '"sections"' in r.stdout,
          (r.stderr or r.stdout)[:300])

    notes = os.path.join(CWD, "reads-notes")
    os.makedirs(notes, exist_ok=True)
    for name, text in READS_NOTES.items():
        write(os.path.join(notes, name), text)
    r = run([os.path.join(scripts, "check_notes.py"), notes,
             "--book-type", "non-fiction",
             "--min-lines", "8", "--max-lines", "60"])
    check("check_notes.py passes a conforming folder standalone",
          r.returncode == 0, (r.stderr or r.stdout)[:400])


def test_plugin_layout_rabbit_reads_reaches_the_sibling_engine():
    # The satellite carries no vendored rwlib of its own beyond what packaging
    # vendors for every non-engine skill, so this run proves _bootstrap
    # resolves the sibling engine from the loose-skills layout.
    ensure_plugin_copy()
    docx = os.path.join(CWD, "reads-sample.docx")
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main"><w:body>'
        '<w:p><w:r><w:t>The plateau holds at dawn.</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>The second paragraph names the river.</w:t></w:r></w:p>'
        '</w:body></w:document>'
    )
    with zipfile.ZipFile(docx, "w") as zf:
        zf.writestr("word/document.xml", document)
    r = run([plugin_path("rabbit-reads", "scripts", "extract_text.py"),
             docx, "--stdout"])
    check("plugin layout: extract_text.py reads a docx off the sibling engine",
          r.returncode == 0 and "plateau holds at dawn" in r.stdout,
          (r.stderr or r.stdout)[:300])


def test_plugin_layout_scans_fixes_and_applies_a_voice():
    ensure_plugin_copy()
    sample = os.path.join(CWD, "plugin-sample.md")
    write(sample, FIXABLE)
    scan = plugin_path("rabbit-writes", "scripts", "scan.py")

    r = run([scan, sample, "--voice", "whit3rabbit"])
    check("plugin layout: scan.py resolves a voice from the sibling voices/",
          r.returncode == 0 and "whit3rabbit" in r.stdout,
          (r.stderr or r.stdout)[:300])

    r = run([scan, sample, "--apply-safe", "--write"])
    with open(sample, encoding="utf-8") as fh:
        after = fh.read()
    check("plugin layout: --apply-safe --write works from a foreign cwd",
          r.returncode == 0 and "\u200b" not in after,
          r.stderr[:200])


def test_plugin_layout_voice_setup_reaches_the_sibling_engine():
    ensure_plugin_copy()
    r = run([plugin_path("voice-setup", "scripts", "build_voice.py"),
             "--check", "whit3rabbit"])
    check("plugin layout: build_voice.py --check runs off the sibling engine",
          r.returncode == 0, (r.stderr or r.stdout)[:300])


def test_plugin_layout_sibling_engine_wins_over_a_vendored_copy():
    # _bootstrap inserts HERE first and the engine's scripts/ second, leaving
    # the sibling at sys.path[0] when both carry an rwlib. The decoy has no
    # modules in it, so if it ever won, the import below would die instead of
    # reporting the wrong winner quietly.
    ensure_plugin_copy()
    decoy = plugin_path("voice-setup", "scripts", "rwlib")
    os.makedirs(decoy, exist_ok=True)
    write(os.path.join(decoy, "__init__.py"), "")
    code = (
        "import sys\n"
        "sys.path.insert(0, %r)\n"
        "import _bootstrap\n"
        "from rwlib import voices\n"
        "print(voices.__file__)\n" % plugin_path("voice-setup", "scripts"))
    try:
        r = run(["-c", code])
        sibling = os.path.join("rabbit-writes", "scripts")
        check("plugin layout: the sibling engine wins over a vendored rwlib",
              r.returncode == 0 and sibling in r.stdout,
              (r.stderr or r.stdout)[:300])
    finally:
        shutil.rmtree(decoy, ignore_errors=True)


def test_plugin_layout_rabbit_reads_sibling_engine_wins_over_a_vendored_copy():
    # Same regression as the voice-setup version above, for rabbit-reads' own
    # _bootstrap.py: HERE first, RWLIB_PARENT second in the sys.path insert
    # loop, leaving the sibling engine at sys.path[0] when both carry an rwlib.
    ensure_plugin_copy()
    decoy = plugin_path("rabbit-reads", "scripts", "rwlib")
    os.makedirs(decoy, exist_ok=True)
    write(os.path.join(decoy, "__init__.py"), "")
    code = (
        "import sys\n"
        "sys.path.insert(0, %r)\n"
        "import _bootstrap\n"
        "from rwlib import cli_error\n"
        "print(cli_error.__file__)\n" % plugin_path("rabbit-reads", "scripts"))
    try:
        r = run(["-c", code])
        sibling = os.path.join("rabbit-writes", "scripts")
        check("plugin layout: rabbit-reads' sibling engine wins over a "
              "vendored rwlib",
              r.returncode == 0 and sibling in r.stdout,
              (r.stderr or r.stdout)[:300])
    finally:
        shutil.rmtree(decoy, ignore_errors=True)


def test_plugin_layout_readme_check_uses_the_sibling_voices():
    # The regression this pins: VOICES_DIR is derived from wherever rwlib
    # loaded, so in this layout it must land on the sibling engine's voices/,
    # not on a path relative to this repository.
    ensure_plugin_copy()
    project = os.path.join(WORK, "plugin-project")
    os.makedirs(project, exist_ok=True)
    write(os.path.join(project, "README.md"), README_SAMPLE)
    write(os.path.join(project, ".rabbit-voice"), "whit3rabbit\n")
    r = run([plugin_path("readme-writing", "scripts", "readme_check.py"),
             "README.md", "--json"], cwd=project)
    payload = json.loads(r.stdout or "{}")
    check("plugin layout: readme_check.py runs from a stranger's project",
          r.returncode == 0, (r.stderr or r.stdout)[:300])
    check("plugin layout: a .rabbit-voice pin resolves in the sibling voices/",
          "whit3rabbit" in json.dumps(payload.get("voice", payload)),
          json.dumps(payload)[:300])


# --------------------------------------------------------------------------
# Runner. Stays at the bottom: main() collects tests off globals(), so anything
# defined below it is invisible to a stdlib run and only pytest would find it.

def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            print(name)
            fn()
    print("\n%d check(s) failed" % len(failures) if failures else "\nall checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
