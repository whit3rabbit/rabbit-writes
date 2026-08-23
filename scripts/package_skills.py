#!/usr/bin/env python3
"""
package_skills.py - Package each skill into an isolated, self-contained ZIP archive.

Claude custom-skill uploads take one skill per zip, so each archive must stand
alone: its own copy of the shared engine (`rwlib`, `scan.py`, `verify.py`,
`lexicon.json`, `registers.json`), its own `voices/`, and a SKILL.md whose paths
resolve inside the archive rather than through `${CLAUDE_PLUGIN_ROOT}`.

The source SKILL.md files stay written for the plugin install. This script
rewrites the packaged copies: generic prefix maps turn plugin paths into
archive-relative ones, and SUBSTITUTIONS handles the handful of plugin-only
lines a prefix map cannot fix. Every substitution must match exactly once, so
a reworded source line fails the build instead of shipping a stale rewrite.

A post-build gate then fails the run if any `${CLAUDE_PLUGIN_ROOT}` survives,
if the packaged SKILL.md cites a `scripts/`, `voices/`, or `references/` path
the archive does not carry, or if the frontmatter uses a key the upload
endpoint rejects.

Outputs: one zip per name in SKILL_NAMES, under `dist/`.

Usage:
  python3 scripts/package_skills.py

Exit code: 0 on success, 1 on failure. Stdlib only.
"""

import io
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(ROOT, "skills")
ENGINE_DIR = os.path.join(SKILLS_DIR, "rabbit-writes")
ENGINE_SCRIPTS_DIR = os.path.join(ENGINE_DIR, "scripts")
DIST_DIR = os.path.join(ROOT, "dist")
MAX_FILES = 200

SKILL_NAMES = ["rabbit-writes", "voice-setup", "readme-writing",
               "rabbit-reads", "rabbit-rewrites"]

PLUGIN_VAR = "${CLAUDE_PLUGIN_ROOT}"

# Engine files vendored beside each satellite skill's own scripts. verify.py is
# here because scan.py imports it lazily for --apply-safe, so its absence only
# shows up when the fixer runs.
SHARED_ENGINE_FILES = [
    "lexicon.json",
    "registers.json",
    # `rwlib/ste.py` loads this on the first --ste check. It used to load at
    # import time, which made every satellite archive missing it raise
    # FileNotFoundError on --help; the load is lazy now, and the file ships
    # so --ste works in a bundle at all.
    "ste_lexicon.json",
    # The replacement palette rwlib/rewrite.py looks for beside the scripts
    # dir. Optional at runtime (a checkout without one rewrites slightly
    # worse rather than failing), but rabbit-rewrites exists to run rewrites,
    # and a bundle that silently ships degraded gives nobody a signal.
    "thesaurus_alternatives.json",
    "scan.py",
    "verify.py",
]

# Engine files a satellite skill's SKILL.md cites and therefore must carry.
# Maps archive-relative destination to a path under the engine skill dir.
EXTRA_VENDOR = {
    "readme-writing": [
        (os.path.join("references", "craft.md"), os.path.join("references", "craft.md")),
    ],
    "voice-setup": [
        (os.path.join("references", "voice.md"), os.path.join("references", "voice.md")),
    ],
}

# Frontmatter keys the claude.ai upload endpoint accepts. Anything else fails
# the upload with "Unexpected key(s) in SKILL.md frontmatter".
ALLOWED_FRONTMATTER_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}

IGNORE_DIRS = {
    ".git",
    ".github",
    ".pytest_cache",
    "__pycache__",
    "tests",
}

IGNORE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".zip",
}

# CLAUDE.md and PROOF.md are contributor docs: repo-relative paths, measured
# self-scan numbers, none of it true inside an isolated archive.
IGNORE_FILES = {
    ".DS_Store",
    "CLAUDE.md",
    "PROOF.md",
}

# The shared "Paths." paragraph, present in all four SKILL.md files with one
# wording difference ("below means" in rabbit-writes, "means" elsewhere).
_PATHS_OLD_TAIL = (
    "the directory holding this skill and its siblings (`rabbit-writes`, "
    "`voice-setup`, `readme-writing`, `rabbit-reads`, `rabbit-rewrites`). "
    "Claude Code expands "
    "the variable. On a host that doesn't, such as Codex, resolve it that "
    "way by hand."
)
_PATHS_NEW = (
    "**Paths.** Every path below is relative to this skill's own directory, "
    "the one holding this file."
)

# Plugin-only lines, per skill and file. Each old string must appear exactly
# once in the source file or the build fails.
SUBSTITUTIONS = {
    "rabbit-writes": {
        "SKILL.md": [
            (
                "**Paths.** `" + PLUGIN_VAR + "/skills/` below means " + _PATHS_OLD_TAIL,
                _PATHS_NEW,
            ),
            (
                "Outside a plugin install `" + PLUGIN_VAR + "` is unset, which "
                "turns every path above into an absolute path that does not "
                "exist. If that happens, resolve `scripts/scan.py` relative to "
                "this file's own directory instead.",
                "Every path above resolves relative to this file's own directory.",
            ),
        ],
    },
    "voice-setup": {
        "SKILL.md": [
            (
                "Both live in `" + PLUGIN_VAR + "/skills/rabbit-writes/voices/`. "
                "They are plain text under version control, so a voice is "
                "editable, diffable, and shareable.",
                "Both live in this skill's `voices/` directory. They are plain "
                "text, so a voice is editable, diffable, and shareable.",
            ),
            (
                "**Paths.** `" + PLUGIN_VAR + "/skills/` means " + _PATHS_OLD_TAIL,
                _PATHS_NEW,
            ),
            (
                "   - Inside the plugin, `" + PLUGIN_VAR + "/skills/rabbit-writes/voices/`, "
                "is the only place `voices/ACTIVE` and a repo's `.rabbit-voice` "
                "resolve a name. A plugin update overwrites that directory.",
                "   - This skill's own `voices/` directory is the only place "
                "`voices/ACTIVE` and a repo's `.rabbit-voice` resolve a name. "
                "A skill update overwrites that directory.",
            ),
            (
                "and `references/voice.md` in the `rabbit-writes` skill has the reading.",
                "and `references/voice.md` has the reading.",
            ),
            (
                "**Validate the whole install,** when there is one:\n\n"
                "```bash\n"
                "python3 " + PLUGIN_VAR + "/scripts/validate.py\n"
                "```\n\n"
                "Same structural checks over every installed profile, plus "
                "active-voice alignment and file pairing. Note the path: it sits "
                "at the repository root rather than under `" + PLUGIN_VAR + "/skills/`, "
                "so it only exists in a full-repo install and is absent when the "
                "skills were copied in loose. `build_voice.py --check` is "
                "the one that ships with the skill, which is why it is the step "
                "above and not this one.",
                "**Validate the whole install,** when there is one: the plugin "
                "repository's `validate.py` runs the same structural checks over "
                "every installed profile, plus active-voice alignment and file "
                "pairing. It only exists in a full-repo install. "
                "`build_voice.py --check` is the one that ships with this skill, "
                "which is why it is the step above and not this one.",
            ),
        ],
    },
    "readme-writing": {
        "SKILL.md": [
            (
                "The full study (methodology, the 100-repo table, every stat "
                "cited below) lives in `" + PLUGIN_VAR + "/docs/README_WRITEUP.md`.",
                "The full study (methodology, the 100-repo table, every stat "
                "cited below) lives in `docs/README_WRITEUP.md` in the plugin "
                "repository, and `references/patterns.md` here carries the same "
                "numbers.",
            ),
            (
                "**Paths.** `" + PLUGIN_VAR + "/skills/` means " + _PATHS_OLD_TAIL + " "
                "`" + PLUGIN_VAR + "/docs/` only exists in a full-repo install. "
                "When it's missing, `references/patterns.md` carries the same "
                "numbers and `scripts/readme_check.py` still runs, since it "
                "resolves its siblings from its own location.",
                _PATHS_NEW + " `references/patterns.md` carries the corpus "
                "numbers and `scripts/readme_check.py` resolves its own "
                "libraries from its location.",
            ),
            (
                "offer `voice-setup` to create or activate a profile "
                "(`python3 skills/voice-setup/scripts/build_voice.py --activate <name>`).",
                "offer the `voice-setup` skill to create or activate a profile.",
            ),
            (
                "| `" + PLUGIN_VAR + "/docs/README_WRITEUP.md` | When the user "
                "asks *why* a rule exists, wants the underlying data, or "
                "disputes a recommendation. This is the full study with the "
                "100-repo table and methodology |",
                "| `docs/README_WRITEUP.md` in the plugin repository | When the "
                "user asks *why* a rule exists, wants the underlying data, or "
                "disputes a recommendation. This is the full study with the "
                "100-repo table and methodology. It is not bundled with this "
                "skill, and `references/patterns.md` carries the same numbers |",
            ),
        ],
        os.path.join("references", "patterns.md"): [
            (
                "Every number here is from `" + PLUGIN_VAR + "/docs/README_WRITEUP.md`, "
                "computed across 100 real READMEs from currently-trending GitHub "
                "repos (methodology and the full 100-repo table are there).",
                "Every number here is from the full study, `docs/README_WRITEUP.md` "
                "in the plugin repository, computed across 100 real READMEs from "
                "currently-trending GitHub repos (methodology and the full "
                "100-repo table are there).",
            ),
        ],
    },
    "rabbit-reads": {
        "SKILL.md": [
            (
                "**Paths.** `" + PLUGIN_VAR + "/skills/` means " + _PATHS_OLD_TAIL,
                _PATHS_NEW,
            ),
        ],
    },
    "rabbit-rewrites": {
        "SKILL.md": [
            (
                "**Paths.** `" + PLUGIN_VAR + "/skills/` means " + _PATHS_OLD_TAIL,
                _PATHS_NEW,
            ),
        ],
    },
}

# A path the packaged SKILL.md cites and the archive must therefore carry.
CITED_PATH_RX = re.compile(r"\b(scripts|voices|references)/[A-Za-z0-9_.\-/]*")


def prefix_maps(skill_name):
    """Ordered plugin-path rewrites for one skill's markdown.

    Trailing-slash forms run first so `.../voices/ACTIVE` becomes
    `voices/ACTIVE`, then the bare forms catch `VOICES=.../voices`.
    """
    maps = []
    bases = ["rabbit-writes"]
    if skill_name != "rabbit-writes":
        bases.append(skill_name)
    for base in bases:
        for sub in ("scripts", "voices", "references"):
            maps.append((f"{PLUGIN_VAR}/skills/{base}/{sub}/", f"{sub}/"))
            maps.append((f"{PLUGIN_VAR}/skills/{base}/{sub}", sub))
    return maps


def transform_markdown(skill_name, rel_path, text):
    """Rewrite one packaged markdown file. Raises ValueError on drift."""
    for old, new in SUBSTITUTIONS.get(skill_name, {}).get(rel_path, []):
        count = text.count(old)
        if count != 1:
            raise ValueError(
                f"{skill_name}/{rel_path}: substitution matched {count} times, "
                f"expected exactly 1: {old[:80]!r}"
            )
        text = text.replace(old, new)
    for old, new in prefix_maps(skill_name):
        text = text.replace(old, new)
    return text


def should_ignore(path):
    parts = path.split(os.sep)
    for part in parts:
        if part in IGNORE_DIRS or part.startswith(".tmp"):
            return True
    filename = parts[-1]
    if filename in IGNORE_FILES or filename.startswith(".tmp"):
        return True
    _, ext = os.path.splitext(filename)
    if ext.lower() in IGNORE_EXTENSIONS:
        return True
    return False


def frontmatter_keys(skill_md_text):
    """Top-level YAML keys of the frontmatter block, without a YAML parser."""
    lines = skill_md_text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    keys = []
    for line in lines[1:]:
        if line.strip() == "---":
            return keys
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):", line)
        if m:
            keys.append(m.group(1))
    return None


def gate(zip_path, skill_name):
    """Fail on anything that makes the archive not stand alone."""
    errors = []
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())

        def exists(rel):
            member = f"{skill_name}/{rel}".rstrip("/")
            if member in names:
                return True
            return any(n.startswith(member + "/") for n in names)

        for name in sorted(names):
            if name.endswith((".md", ".py", ".json", ".txt")) or "." not in os.path.basename(name):
                text = zf.read(name).decode("utf-8", errors="replace")
                if PLUGIN_VAR in text:
                    errors.append(f"{name}: contains {PLUGIN_VAR} after rewrite")

        skill_md = f"{skill_name}/SKILL.md"
        if skill_md not in names:
            errors.append(f"missing {skill_md}")
        else:
            text = zf.read(skill_md).decode("utf-8")
            keys = frontmatter_keys(text)
            if keys is None:
                errors.append(f"{skill_md}: no frontmatter block")
            else:
                for key in keys:
                    if key not in ALLOWED_FRONTMATTER_KEYS:
                        errors.append(f"{skill_md}: frontmatter key {key!r} rejected by upload")
            for match in CITED_PATH_RX.finditer(text):
                cited = match.group(0).rstrip(".")
                if not exists(cited):
                    errors.append(f"{skill_md}: cites {cited} but the archive has no such member")
    return errors


def build_skill_zip(skill_name):
    skill_source = os.path.join(SKILLS_DIR, skill_name)
    if not os.path.isdir(skill_source):
        print(f"Error: skill directory not found: {skill_source}", file=sys.stderr)
        return False

    dist_zip_path = os.path.join(DIST_DIR, f"{skill_name}.zip")
    if os.path.exists(dist_zip_path):
        os.unlink(dist_zip_path)

    files_added = 0
    skill_md_count = 0

    def add_file(zf, abs_file, archive_path, rewrite_rel=None):
        nonlocal files_added
        try:
            zf.getinfo(archive_path)
            return
        except KeyError:
            pass
        if rewrite_rel is not None and abs_file.endswith(".md"):
            with io.open(abs_file, encoding="utf-8") as fh:
                text = fh.read()
            zf.writestr(archive_path, transform_markdown(skill_name, rewrite_rel, text))
        else:
            zf.write(abs_file, archive_path)
        files_added += 1

    try:
        with zipfile.ZipFile(dist_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. The skill's own tree, markdown rewritten for the archive layout.
            for root_dir, dirs, files in os.walk(skill_source):
                dirs[:] = [d for d in dirs if not should_ignore(os.path.relpath(os.path.join(root_dir, d), skill_source))]
                for file in sorted(files):
                    abs_file = os.path.join(root_dir, file)
                    rel_from_skill = os.path.relpath(abs_file, skill_source)
                    if should_ignore(rel_from_skill):
                        continue
                    add_file(zf, abs_file, os.path.join(skill_name, rel_from_skill), rewrite_rel=rel_from_skill)
                    if rel_from_skill == "SKILL.md":
                        skill_md_count += 1

            if skill_name != "rabbit-writes":
                # 2. The engine: rwlib plus the files scan.py needs beside it.
                rwlib_source = os.path.join(ENGINE_SCRIPTS_DIR, "rwlib")
                for root_dir, dirs, files in os.walk(rwlib_source):
                    dirs[:] = [d for d in dirs if not should_ignore(d)]
                    for file in sorted(files):
                        abs_file = os.path.join(root_dir, file)
                        rel_from_engine = os.path.relpath(abs_file, ENGINE_SCRIPTS_DIR)
                        if should_ignore(rel_from_engine):
                            continue
                        add_file(zf, abs_file, os.path.join(skill_name, "scripts", rel_from_engine))
                for shared_file in SHARED_ENGINE_FILES:
                    abs_file = os.path.join(ENGINE_SCRIPTS_DIR, shared_file)
                    if not os.path.isfile(abs_file):
                        print(f"ERROR: engine file missing: {abs_file}", file=sys.stderr)
                        return False
                    add_file(zf, abs_file, os.path.join(skill_name, "scripts", shared_file))

                # 3. voices/, so rwlib.voices.VOICES_DIR (two up from rwlib,
                # then voices/) resolves inside the archive.
                voices_source = os.path.join(ENGINE_DIR, "voices")
                for root_dir, dirs, files in os.walk(voices_source):
                    dirs[:] = [d for d in dirs if not should_ignore(d)]
                    for file in sorted(files):
                        abs_file = os.path.join(root_dir, file)
                        rel_from_voices = os.path.relpath(abs_file, voices_source)
                        if should_ignore(rel_from_voices):
                            continue
                        add_file(zf, abs_file, os.path.join(skill_name, "voices", rel_from_voices))

                # 4. Engine files this skill's SKILL.md cites by name.
                for dest_rel, engine_rel in EXTRA_VENDOR.get(skill_name, []):
                    archive_path = os.path.join(skill_name, dest_rel)
                    try:
                        zf.getinfo(archive_path)
                        print(f"ERROR: vendored {dest_rel} collides with a file {skill_name} already ships", file=sys.stderr)
                        return False
                    except KeyError:
                        pass
                    add_file(zf, os.path.join(ENGINE_DIR, engine_rel), archive_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        os.unlink(dist_zip_path)
        return False

    errors = gate(dist_zip_path, skill_name)
    if skill_md_count != 1:
        errors.append(f"contains {skill_md_count} SKILL.md files, expected exactly 1")
    if files_added > MAX_FILES:
        errors.append(f"contains {files_added} files, exceeding limit of {MAX_FILES}")

    file_size_kb = os.path.getsize(dist_zip_path) / 1024
    print(f"Created {skill_name}.zip: {files_added} files, {file_size_kb:.1f} KB, at {dist_zip_path}")
    if errors:
        for err in errors:
            print(f"ERROR: {skill_name}.zip: {err}", file=sys.stderr)
        os.unlink(dist_zip_path)
        return False
    return True


def main():
    os.makedirs(DIST_DIR, exist_ok=True)
    success = True
    for skill in SKILL_NAMES:
        if not build_skill_zip(skill):
            success = False
    if success:
        print("All %d skills packaged as isolated, self-contained archives in "
              "dist/." % len(SKILL_NAMES))
        return 0
    print("Packaging failed for one or more skills.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
