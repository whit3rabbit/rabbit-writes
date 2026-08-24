#!/usr/bin/env python3
"""
The licence cross-check: the README against the tree it sits in.

Checklist item 15 has said "check for a LICENSE file rather than guessing" since
this skill shipped, and until now nothing did. The script read the README and
only the README, so both halves of the mismatch were invisible to it: a project
with a LICENSE the README never mentions, and, worse, a README asserting a
licence over an empty directory. The second is this skill's own named top
failure mode, asserting something false, in its purest form.

The scaffolding here is heavier than the assertions because the check walks the
filesystem, and every test has to own the tree it is asserting about. A test that
inherits the developer's repository root is a test that passes here and nowhere
else.

Stdlib only, 3.9+.
"""

import os
import shutil
import tempfile

from helpers import Repo, check_module, ids, run, written

LICENSED = """# widget

widget resizes images in bulk. It reads a directory and writes thumbnails
beside each original.

## Install

```sh
npm install -g widget
```

## Usage

```sh
widget ./photos --size 240
```

## License

MIT. See LICENSE.
"""

UNLICENSED = LICENSED.replace("\n## License\n\nMIT. See LICENSE.\n", "")



def test_a_license_section_with_no_file_anywhere_is_a_p1():
    """A licence a project does not carry is the most expensive thing a README
    can get wrong, and it is the one thing reading the README cannot catch."""
    repo = Repo(LICENSED)
    try:
        result = run(repo.readme)
        assert "license-file-missing" in ids(result), ids(result)
        entry = [f for f in result["findings"]
                 if f["id"] == "license-file-missing"][0]
        assert entry["priority"] == "P1", entry
    finally:
        repo.close()


def test_a_license_file_beside_the_readme_clears_it():
    repo = Repo(LICENSED, "LICENSE")
    try:
        assert "license-file-missing" not in ids(run(repo.readme))
    finally:
        repo.close()


def test_every_spelling_of_the_file_counts():
    """`LICENCE`, `COPYING`, and `LICENSE.md` are all in the wild and none of
    them is wrong. Reporting one of them as absent is the false assertion."""
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE",
                 "COPYING", "license", "LICENSE-MIT"):
        repo = Repo(LICENSED, name)
        try:
            assert "license-file-missing" not in ids(run(repo.readme)), name
        finally:
            repo.close()


def test_a_readme_in_a_subdirectory_is_covered_by_the_root_license():
    """`docs/README.md` is governed by the LICENSE at the repository root.
    Calling that project unlicensed is the false positive that would have made
    the whole check not worth shipping."""
    repo = Repo(LICENSED, "LICENSE")
    try:
        nested = repo.sub("docs", LICENSED)
        assert "license-file-missing" not in ids(run(nested))
    finally:
        repo.close()


def test_the_walk_stops_at_the_repository_root():
    """A nested repository does not inherit its parent's licence. The `.git`
    marker is where the project ends."""
    outer = Repo(LICENSED, "LICENSE")
    try:
        inner = os.path.join(outer.path, "vendor")
        os.makedirs(os.path.join(inner, ".git"))
        readme = os.path.join(inner, "README.md")
        with open(readme, "w", encoding="utf-8") as fh:
            fh.write(LICENSED)
        assert "license-file-missing" in ids(run(readme))
    finally:
        outer.close()


def test_a_file_with_no_section_sharpens_the_existing_finding():
    """`no-license` hedged because the script could not see the tree. Now that
    it can, and the file is right there, it is a fact rather than a prompt."""
    repo = Repo(UNLICENSED, "LICENSE")
    try:
        result = run(repo.readme)
        entry = [f for f in result["findings"] if f["id"] == "no-license"]
        assert entry, ids(result)
        assert entry[0]["priority"] == "P1", entry[0]
        assert "LICENSE" in entry[0]["excerpt"], entry[0]
    finally:
        repo.close()


def test_neither_a_section_nor_a_file_keeps_the_original_hedge():
    repo = Repo(UNLICENSED)
    try:
        entry = [f for f in run(repo.readme)["findings"]
                 if f["id"] == "no-license"]
        assert entry and entry[0]["priority"] == "P2", entry
        assert "rather than guessing" in entry[0]["excerpt"], entry[0]
    finally:
        repo.close()


def test_a_walk_that_never_finds_a_root_says_nothing():
    """Silence rather than a guess. A README with no repository around it, which
    is what every test fixture written to a bare temp directory looks like, is a
    project whose boundary this check does not know. It cannot call a file
    absent from a tree it never finished walking."""
    rc = check_module()
    tmp = tempfile.mkdtemp(prefix="rabbit-noroot-")
    try:
        deep = os.path.join(tmp, *["d"] * 12)
        os.makedirs(deep)
        readme = os.path.join(deep, "README.md")
        with open(readme, "w", encoding="utf-8") as fh:
            fh.write(LICENSED)
        path, saw_root = rc.find_license_file(readme)
        assert path is None and saw_root is False, (path, saw_root)
        findings, stats = [], {"sections": ["license"]}
        rc.check_license_file(readme, findings, stats)
        assert not findings, findings
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_a_document_that_is_not_on_disk_is_left_alone():
    """Scanning a string through a temporary path has no tree around it."""
    rc = check_module()
    findings, stats = [], {"sections": ["license"]}
    rc.check_license_file("/nonexistent/path/README.md", findings, stats)
    assert not findings, findings
    assert "license_file" not in stats, stats


def test_licenses_directory_and_variants_count_as_license_file():
    """UNLICENSE, MIT-LICENSE.txt, and a LICENSES/ directory should satisfy the license file check."""
    for name in ("UNLICENSE", "MIT-LICENSE.txt", "LICENSE.MIT"):
        repo = Repo(LICENSED, name)
        try:
            assert "license-file-missing" not in ids(run(repo.readme)), name
        finally:
            repo.close()

    # LICENSES directory
    repo = Repo(LICENSED)
    try:
        lic_dir = os.path.join(repo.path, "LICENSES")
        os.makedirs(lic_dir)
        with open(os.path.join(lic_dir, "MIT.txt"), "w") as fh:
            fh.write("MIT License terms")
        assert "license-file-missing" not in ids(run(repo.readme))
    finally:
        repo.close()


def test_license_badge_and_trailing_mention_prevent_no_license():
    """A license badge or a license mention in the last 10 lines prevents no-license."""
    # 1. Badge only
    badge_readme = "# Widget\n\nWidget does things.\n\n[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)\n\n## Install\n\n```sh\npip install x\n```\n"
    scratch = tempfile.mkdtemp()
    try:
        res1 = run(written(scratch, "README.md", badge_readme), "--no-voice")
        assert "no-license" not in ids(res1), ids(res1)
        assert res1["stats"]["has_license_mention"] is True
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    # 2. Mention in final 10 lines
    trailing_readme = "# Widget\n\nWidget does things.\n\n## Install\n\n```sh\npip install x\n```\n\nReleased under the MIT license.\n"
    scratch = tempfile.mkdtemp()
    try:
        res2 = run(written(scratch, "README.md", trailing_readme), "--no-voice")
        assert "no-license" not in ids(res2), ids(res2)
        assert res2["stats"]["has_license_mention"] is True
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

