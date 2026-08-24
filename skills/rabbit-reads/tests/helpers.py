#!/usr/bin/env python3
"""
Shared helpers for the rabbit-reads tests.

Three jobs. It puts this skill's own scripts directory and the engine's
(skills/rabbit-writes/scripts) on sys.path, so a test can import rwlib the
same way the scripts under test do. It runs those scripts as subprocesses and
hands back the three things a CLI test needs (exit code, stdout, stderr)
instead of printing into the runner. And it writes fixture trees in one call,
which is how every notes folder gets built, so no fixture is ever a committed
binary the way test_docx.py in the engine suite insists on.

Stdlib only, 3.9+.
"""

import os
import shutil
import subprocess
import sys
import tempfile

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
BOOK_TYPES = os.path.join(SKILL_DIR, "references", "book-types")

EXTRACT_TEXT = os.path.join(SCRIPTS_DIR, "extract_text.py")
MAP_STRUCTURE = os.path.join(SCRIPTS_DIR, "map_structure.py")
CHECK_NOTES = os.path.join(SCRIPTS_DIR, "check_notes.py")

_ENGINE_CACHE = {}


def engine_dir():
    """The engine scripts directory, found by walking up from this file.

    Resolved by walking rather than by a fixed count of .. segments so the
    skill directory can move without editing the tests inside it, the same
    rule the scripts themselves follow. Memoized because it is pure
    filesystem probing and every fresh import of a test module would
    otherwise repeat it.
    """
    if "engine" in _ENGINE_CACHE:
        return _ENGINE_CACHE["engine"]
    here = TESTS_DIR
    found = None
    while True:
        candidate = os.path.join(here, "skills", "rabbit-writes", "scripts")
        if os.path.isdir(os.path.join(candidate, "rwlib")):
            found = candidate
            break
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    _ENGINE_CACHE["engine"] = found
    return found


ENGINE = engine_dir()

# Both directories, engine first, so `from rwlib import x` in a test resolves
# the same package the scripts under test resolve. Without the engine entry
# the scripts can import rwlib while the tests covering them cannot, which
# reads as rwlib being private to one skill.
for _path in (ENGINE, SCRIPTS_DIR):
    if _path and _path not in sys.path:
        sys.path.insert(0, _path)


def script_path(name):
    """Absolute path to one script under test, refusing a missing one.

    The scripts are developed beside these tests and may not exist yet, so a
    clear assertion naming the absent file beats a subprocess error that
    names only a path nobody created.
    """
    path = os.path.join(SCRIPTS_DIR, name)
    assert os.path.isfile(path), (
        "%s has not been written yet, so the rabbit-reads scripts are "
        "incomplete and this suite cannot exercise them" % path)
    return path


def run(cmd_args, cwd=None):
    """(returncode, stdout, stderr) for one CLI invocation.

    A first argument ending in .py runs under the current interpreter, so the
    suite never depends on any python being on PATH.
    """
    argv = list(cmd_args)
    if argv and argv[0].endswith(".py"):
        argv.insert(0, sys.executable)
    res = subprocess.run(argv, capture_output=True, text=True, cwd=cwd)
    return res.returncode, res.stdout, res.stderr


def run_env(cmd_args, cwd=None, env=None):
    """run() with an environment override, for the PATH-shim and temp-tree
    cases. run() itself stays signature-stable for the ordinary calls."""
    argv = list(cmd_args)
    if argv and argv[0].endswith(".py"):
        argv.insert(0, sys.executable)
    res = subprocess.run(argv, capture_output=True, text=True, cwd=cwd, env=env)
    return res.returncode, res.stdout, res.stderr


def env_with_pythonpath(extra=None):
    """An environment whose PYTHONPATH reaches the engine and this skill.

    For runs against a script copy inside a temp book-type tree: the copy
    exists only to give --book-type a references directory the tests control,
    and its own walk-up would land outside the repository, so the import path
    is handed over through the environment instead.
    """
    env = dict(os.environ)
    parts = [p for p in (ENGINE, SCRIPTS_DIR, extra) if p]
    existing = env.get("PYTHONPATH")
    if existing:
        parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def make_book_type_tree(files, refs=("book-types",)):
    """A skill-shaped temp tree with script copies and given reference files.

    Used only when the shipped reference file a run needs has not been
    written yet: --book-type and --layout choices are enumerated from
    ../references/<refs> relative to the scripts directory, so a fallback
    file has to sit in that same shape to be selectable at all. Pass
    refs=("layouts",) for layout fixtures. Returns the tree root, which the
    caller owns and removes.
    """
    tree = tempfile.mkdtemp(prefix="rr-bt-")
    scripts_copy = os.path.join(tree, "scripts")
    os.makedirs(scripts_copy)
    os.makedirs(os.path.join(tree, "references", *refs))
    if os.path.isdir(SCRIPTS_DIR):
        for name in sorted(os.listdir(SCRIPTS_DIR)):
            if name.endswith(".py"):
                shutil.copyfile(os.path.join(SCRIPTS_DIR, name),
                                os.path.join(scripts_copy, name))
    for name, text in sorted(files.items()):
        with open(os.path.join(tree, "references", *refs, name), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return tree


def write_tree(directory, files):
    """Write {relative_name: content} under directory, creating parents.

    Returns {name: path}. LF line endings are forced because a fixture that
    inherits the platform ending would make the CRLF normalization test
    assert something different on Windows than on the machine that wrote it.
    """
    paths = {}
    for name, body in files.items():
        path = os.path.join(directory, name)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        paths[name] = path
    return paths


def parse_book_type(text):
    """The spec header of a book-type file as one dict.

    check_notes.py loads its battery from these lines, so the tests build
    their fixtures from the same lines rather than restating the spec and
    drifting from whatever the shipped file declares. A missing or malformed
    line comes back empty (band None) so test_book_types.py can name the gap
    itself instead of the parser guessing a default nobody shipped.
    """
    spec = {"kind_markers": [], "band": None, "sections": [],
            "source_line": None, "free_form": []}
    for line in text.splitlines():
        if not line.startswith("**"):
            continue
        parts = line.split("**")
        if len(parts) < 3:
            continue
        key = parts[1].rstrip(":").strip()
        value = parts[2].strip()
        if key == "Kind markers":
            spec["kind_markers"] = [v.strip() for v in value.split(",")
                                    if v.strip()]
        elif key == "Length band" and "-" in value:
            lo, hi = value.split("-", 1)
            try:
                spec["band"] = (int(lo.strip()), int(hi.strip()))
            except ValueError:
                spec["band"] = None
        elif key == "Template sections":
            spec["sections"] = [v.strip() for v in value.split(",")
                                if v.strip()]
        elif key == "Source line":
            spec["source_line"] = value
        elif key == "Free-form files":
            spec["free_form"] = [v.strip() for v in value.split(",")
                                 if v.strip()]
    return spec
