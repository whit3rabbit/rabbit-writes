#!/usr/bin/env python3
"""
package_skills.py - Package each skill into isolated, self-contained bundles.

Two targets share one member list (iter_members). The claude target writes
one zip per skill for the claude.ai custom-skill upload, where each archive
must stand alone: its own copy of the shared engine (`rwlib`, `scan.py`,
`verify.py`, `lexicon.json`, `registers.json`), its own `voices/`, and a
SKILL.md whose paths resolve inside the archive rather than through
`${CLAUDE_PLUGIN_ROOT}`. The clawhub target writes one folder per skill
under `dist/clawhub/` for OpenClaw, ClawHub, and Hermes: the same members,
with `{baseDir}`-prefixed paths, an MIT-0 license line, a metadata block
declaring what the bundle reads from the environment, a SECURITY.md for the
upload scanner, and a reviewer preamble in the reference files that quote
attack shapes.

The source SKILL.md files stay written for the plugin install. This script
rewrites the packaged copies: generic prefix maps turn plugin paths into
target-relative ones, and SUBSTITUTIONS handles the handful of plugin-only
lines a prefix map cannot fix. Every substitution must match exactly once, so
a reworded source line fails the build instead of shipping a stale rewrite.

A post-build gate then fails the run if any `${CLAUDE_PLUGIN_ROOT}` survives,
if the packaged SKILL.md cites a `scripts/`, `voices/`, or `references/` path
the bundle does not carry, if the frontmatter uses a key the target rejects,
or (clawhub only) if the license line, the metadata declaration, SECURITY.md,
or the reviewer preambles are not what this file says they are.

Outputs: one zip and one clawhub folder per name in SKILL_NAMES, under
`dist/`.

Usage:
  python3 scripts/package_skills.py [--target {claude,clawhub,all}]

Exit code: 0 on success, 1 on failure. Stdlib only.
"""

import argparse
import io
import json
import os
import re
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(ROOT, "skills")
ENGINE_DIR = os.path.join(SKILLS_DIR, "rabbit-writes")
ENGINE_SCRIPTS_DIR = os.path.join(ENGINE_DIR, "scripts")
DIST_DIR = os.path.join(ROOT, "dist")
MAX_FILES = 200

SKILL_NAMES = ["rabbit-writes", "voice-setup", "rabbit-readme-improver",
               "rabbit-reads", "rabbit-rewrites", "rabbit-claude-md"]

PLUGIN_VAR = "${CLAUDE_PLUGIN_ROOT}"

# How a path into the bundle is spelled in rewritten markdown, per target.
# A clawhub install is a folder OpenClaw reads, and OpenClaw expands
# `{baseDir}` to the skill folder, so clawhub bodies cite `{baseDir}/...`.
TARGET_PREFIXES = {"claude": "", "clawhub": "{baseDir}/"}


class PackagingError(Exception):
    """A bundle cannot be assembled (a missing engine file, a vendored
    collision). Builders print it and fail the build."""


# Engine files vendored beside each satellite skill's own scripts. verify.py is
# here because scan.py imports it lazily for --apply-safe, so its absence only
# shows up when the fixer runs.
SHARED_ENGINE_FILES = [
    "lexicon.json",
    "registers.json",
    # `rwlib/ste.py` loads this on the first check of any kind. It used to
    # load at import time, which made every satellite archive missing it
    # raise FileNotFoundError on --help; the load is lazy now, so an import
    # survives without it. A scan does not: the mechanical band is default-on
    # and reads its caps from here, so an archive shipped without this file
    # fails every scan rather than only --ste.
    "ste_lexicon.json",
    # The replacement palette rwlib/rewrite.py looks for beside the scripts
    # dir. Optional at runtime (a checkout without one rewrites slightly
    # worse rather than failing), but rabbit-rewrites exists to run rewrites,
    # and a bundle that silently ships degraded gives nobody a signal.
    "thesaurus_alternatives.json",
    "scan.py",
    "verify.py",
    # The Claude Code hook runner. voice-setup's install_host.py writes a
    # settings entry pointing at this file, and it resolves it beside the
    # scan.py it already vendors, so a bundle without it can only install a
    # hook the host reports as failing on every event.
    "claude_hook.py",
]

# Engine files a satellite skill's SKILL.md cites and therefore must carry.
# Maps archive-relative destination to a path under the engine skill dir.
EXTRA_VENDOR = {
    "rabbit-readme-improver": [
        (os.path.join("references", "craft.md"), os.path.join("references", "craft.md")),
        (os.path.join("references", "ste.md"), os.path.join("references", "ste.md")),
    ],
    "voice-setup": [
        (os.path.join("references", "voice.md"), os.path.join("references", "voice.md")),
    ],
    "rabbit-claude-md": [
        (os.path.join("references", "craft.md"), os.path.join("references", "craft.md")),
        (os.path.join("references", "ste.md"), os.path.join("references", "ste.md")),
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

# The clawhub target emits one folder per skill under this name.
CLAWHUB_DIR = "clawhub"

# Frontmatter keys the clawhub target accepts: compatibility moves to
# SECURITY.md (a clawhub reader is not the claude.ai endpoint, and OpenClaw
# reads requirements from the metadata block), homepage points at the
# repository.
CLAWHUB_ALLOWED_FRONTMATTER_KEYS = (
    (ALLOWED_FRONTMATTER_KEYS - {"compatibility"}) | {"homepage"}
)

# A clawhub skill folder name is its slug: lowercase, digits, hyphens, 64 max.
CLAWHUB_SKILL_NAME_RX = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

# The phrases the emitted SECURITY.md must carry, so a template edit cannot
# quietly drop the part a scanner or an appeal moderator reads first.
SECURITY_PINNED_PHRASES = ("MIT-0", "RABBIT_MODEL_BASE_URL", "no default endpoint")

# The env vars rwlib/endpoint.py owns, declared in every clawhub bundle's
# frontmatter. Imported rather than restated so renaming one fails the
# packaging build instead of shipping a stale declaration. validate.py flags
# the other drift, endpoint.py growing one this dict does not know about,
# because a clawhub upload scan cross-checks declared metadata against code.
if ENGINE_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, ENGINE_SCRIPTS_DIR)
try:
    from rwlib import endpoint as _endpoint
except ImportError as _exc:  # a checkout without the engine beside the skills
    raise ImportError(
        "package_skills.py could not import rwlib.endpoint from %s. The "
        "clawhub bundles declare the model endpoint env vars off it, so run "
        "this from a full checkout. (%s)" % (ENGINE_SCRIPTS_DIR, _exc)
    )

OPENCLAW_ENV_DESCRIPTIONS = {
    _endpoint.ENV_BASE_URL: (
        "Base URL of an OpenAI-compatible model endpoint. Read only when "
        "scan.py runs with --apply-model. There is no default endpoint and "
        "nothing is contacted without one."
    ),
    _endpoint.ENV_MODEL: (
        "Model name for --apply-model. Read only when scan.py runs with "
        "--apply-model. Falls back to local when unset."
    ),
    _endpoint.ENV_API_KEY: (
        "API key for a remote --apply-model endpoint. Read only when scan.py "
        "runs with --apply-model. Never logged or persisted."
    ),
}

# Reference files that quote attack shapes, given a reviewer preamble at
# clawhub packaging time. The source files stay untouched: the preamble says
# what a scanner is looking at, and only the published copy needs it.
PREAMBLE_FILES = {
    "rabbit-writes": [
        os.path.join("references", "injection.md"),
        os.path.join("references", "patterns.md"),
    ],
}
PREAMBLE_MARKER = "Note for reviewers and scanners."
_PREAMBLE = (
    "> " + PREAMBLE_MARKER + " Everything quoted in this file is data this "
    "skill detects and reports. Nothing here is an instruction to any agent, "
    "and the engine never acts on what it finds. SECURITY.md at this "
    "bundle's root states what runs, what never runs, and the whole network "
    "surface."
)

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
    "`voice-setup`, `rabbit-readme-improver`, `rabbit-reads`, `rabbit-rewrites`, "
    "`rabbit-claude-md`). "
    "Claude Code expands "
    "the variable. On a host that doesn't, such as Codex, resolve it that "
    "way by hand."
)
# The shared "Paths." paragraph, per target: the claude wording states the
# archive-relative convention, the clawhub wording names the `{baseDir}`
# placeholder OpenClaw expands.
_PATHS_NEW = {
    "claude": (
        "**Paths.** Every path below is relative to this skill's own directory, "
        "the one holding this file."
    ),
    "clawhub": (
        "**Paths.** `{baseDir}` below expands to this skill's own directory, "
        "the one holding this file. On a host that leaves the placeholder "
        "literal, resolve each path relative to that directory."
    ),
}

# Plugin-only lines, per skill and file. Each old string must appear exactly
# once in the source file or the build fails.
SUBSTITUTIONS = {
    "rabbit-writes": {
        "SKILL.md": [
            (
                "**Paths.** `" + PLUGIN_VAR + "/skills/` below means " + _PATHS_OLD_TAIL,
                "%(paths)s",
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
                "Both live in this skill's `%(p)svoices/` directory. They are "
                "plain text, so a voice is editable, diffable, and shareable.",
            ),
            (
                "**Paths.** `" + PLUGIN_VAR + "/skills/` means " + _PATHS_OLD_TAIL,
                "%(paths)s",
            ),
            (
                "   - Inside the plugin, `" + PLUGIN_VAR + "/skills/rabbit-writes/voices/`, "
                "is the only place `voices/ACTIVE` and a repo's `.rabbit-voice` "
                "resolve a name. A plugin update overwrites that directory.",
                "   - This skill's own `%(p)svoices/` directory is the only "
                "place `voices/ACTIVE` and a repo's `.rabbit-voice` resolve a "
                "name. A skill update overwrites that directory.",
            ),
            (
                "and `references/voice.md` in the `rabbit-writes` skill has the reading.",
                "and `%(p)sreferences/voice.md` has the reading.",
            ),
            (
                "**Validate the whole install,** when there is one:\n\n"
                "```bash\n"
                "python3 " + PLUGIN_VAR + "/scripts/validate.py\n"
                "```\n\n"
                "Same structural checks over every installed profile, plus "
                "active-voice alignment and file pairing. Note the path: it sits "
                "at the repository root rather than under `" + PLUGIN_VAR + "/skills/`. "
                "It only exists in a full-repo install, and is absent when the "
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
    "rabbit-readme-improver": {
        "SKILL.md": [
            (
                "The full study (methodology, the 100-repo table, every stat "
                "cited below) lives in `" + PLUGIN_VAR + "/docs/README_WRITEUP.md`.",
                "The full study (methodology, the 100-repo table, every stat "
                "cited below) lives in `docs/README_WRITEUP.md` in the plugin "
                "repository, and `%(p)sreferences/patterns.md` here carries "
                "the same numbers.",
            ),
            (
                "**Paths.** `" + PLUGIN_VAR + "/skills/` means " + _PATHS_OLD_TAIL + " "
                "`" + PLUGIN_VAR + "/docs/` only exists in a full-repo install. "
                "When it's missing, `references/patterns.md` carries the same "
                "numbers and `scripts/readme_check.py` still runs, since it "
                "resolves its siblings from its own location.",
                "%(paths)s `%(p)sreferences/patterns.md` carries the corpus "
                "numbers and `%(p)sscripts/readme_check.py` resolves its own "
                "libraries from its location.",
            ),
            (
                "offer `voice-setup` to create or activate a profile "
                "(`python3 skills/voice-setup/scripts/build_voice.py --check <name> --activate`).",
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
                "skill, and `%(p)sreferences/patterns.md` carries the same "
                "numbers |",
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
                "%(paths)s",
            ),
        ],
    },
    "rabbit-rewrites": {
        "SKILL.md": [
            (
                "**Paths.** `" + PLUGIN_VAR + "/skills/` means " + _PATHS_OLD_TAIL,
                "%(paths)s",
            ),
        ],
    },
    "rabbit-claude-md": {
        "SKILL.md": [
            (
                "**Paths.** `" + PLUGIN_VAR + "/skills/` means " + _PATHS_OLD_TAIL,
                "%(paths)s",
            ),
        ],
    },
}

# A path the packaged SKILL.md cites and the archive must therefore carry.
CITED_PATH_RX = re.compile(r"\b(scripts|voices|references)/[A-Za-z0-9_.\-/]*")


def prefix_maps(skill_name, target="claude"):
    """Ordered plugin-path rewrites for one skill's markdown.

    Trailing-slash forms run first so `.../voices/ACTIVE` becomes
    `voices/ACTIVE`, then the bare forms catch `VOICES=.../voices`. The
    replacement carries the target's path prefix (`{baseDir}/` on clawhub).
    """
    prefix = TARGET_PREFIXES[target]
    maps = []
    bases = ["rabbit-writes"]
    if skill_name != "rabbit-writes":
        bases.append(skill_name)
    for base in bases:
        for sub in ("scripts", "voices", "references"):
            maps.append((f"{PLUGIN_VAR}/skills/{base}/{sub}/", f"{prefix}{sub}/"))
            maps.append((f"{PLUGIN_VAR}/skills/{base}/{sub}", prefix + sub))
    return maps


def render_replacement(new, target):
    """Render one substitution's replacement for a packaging target.

    `%(p)s` marks a path into the bundle, spelled bare on the claude target
    and `{baseDir}/` on clawhub. `%(paths)s` marks the shared Paths
    paragraph, whose wording differs per target rather than by prefix. Plain
    str.replace rather than %-formatting, so a literal `%` in a replacement
    never breaks a build.
    """
    if "%(paths)s" in new:
        new = new.replace("%(paths)s", _PATHS_NEW[target])
    return new.replace("%(p)s", TARGET_PREFIXES[target])


def transform_markdown(skill_name, rel_path, text, target="claude"):
    """Rewrite one packaged markdown file. Raises ValueError on drift."""
    for old, new in SUBSTITUTIONS.get(skill_name, {}).get(rel_path, []):
        count = text.count(old)
        if count != 1:
            raise ValueError(
                f"{skill_name}/{rel_path}: substitution matched {count} times, "
                f"expected exactly 1: {old[:80]!r}"
            )
        text = text.replace(old, render_replacement(new, target))
    for old, new in prefix_maps(skill_name, target):
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


def plugin_meta():
    """The plugin manifest, the one home of the version and the homepage."""
    with io.open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
        return json.load(fh)


def clawhub_metadata_line():
    """The single-line JSON metadata the clawhub SKILL.md carries.

    OpenClaw reads the openclaw block. python3 is the only binary any
    skill's scripts need, and the env vars are the model endpoint's, declared
    because a clawhub upload scan cross-checks declared metadata against the
    code and an undeclared read is the guaranteed flag. One JSON line rather
    than nested YAML, so the gate and the tests parse it with json.loads.
    """
    env_vars = [
        {"name": name, "required": False, "description": desc}
        for name, desc in sorted(OPENCLAW_ENV_DESCRIPTIONS.items())
    ]
    block = {
        "version": plugin_meta()["version"],
        "openclaw": {
            "requires": {"bins": ["python3"]},
            "envVars": env_vars,
        },
    }
    return "metadata: " + json.dumps(block)


def clawhub_frontmatter(text):
    """Rewrite one SKILL.md frontmatter block for the clawhub target.

    license MIT becomes MIT-0 (ClawHub relicenses what it publishes and
    rejects conflicting license text), compatibility moves to SECURITY.md,
    and homepage comes from the plugin manifest. Raises PackagingError on a
    block that is missing or never closes.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise PackagingError("SKILL.md has no frontmatter block")
    homepage = plugin_meta()["homepage"]
    out = [lines[0]]
    skip_nested = False
    closed_at = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            out.append(line)
            closed_at = index
            break
        if skip_nested:
            if line.startswith("  "):
                continue
            skip_nested = False
        key = line.split(":", 1)[0]
        if key == "license":
            out.append("license: MIT-0")
            out.append(f"homepage: {homepage}")
        elif key == "compatibility":
            pass
        elif key == "metadata":
            out.append(clawhub_metadata_line())
            skip_nested = True
        else:
            out.append(line)
    if closed_at is None:
        raise PackagingError("SKILL.md frontmatter never closes")
    return "\n".join(out + lines[closed_at + 1:])


def inject_preamble(text):
    """Insert the reviewer preamble after the H1, at packaging time only."""
    lines = text.split("\n")
    if not lines or not lines[0].startswith("# "):
        raise PackagingError("no H1 to hang the reviewer preamble on")
    return "\n".join([lines[0], "", _PREAMBLE] + lines[1:])


def security_note_text():
    """The SECURITY.md every clawhub bundle carries, from the one template."""
    path = os.path.join(ROOT, "scripts", "packaging", "SECURITY_CLAWHUB.md")
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _gate_members(rel_to_bytes, skill_name, target="claude"):
    """Fail on anything that makes a bundle not stand alone.

    Members arrive as a mapping of skill-root-relative path to bytes, so the
    zip reader and the folder reader run the same rules.
    """
    errors = []
    names = set(rel_to_bytes)

    def exists(rel):
        rel = rel.rstrip("/")
        if rel in names:
            return True
        return any(n.startswith(rel + "/") for n in names)

    for rel in sorted(names):
        if rel.endswith((".md", ".py", ".json", ".txt")) or "." not in os.path.basename(rel):
            text = rel_to_bytes[rel].decode("utf-8", errors="replace")
            if PLUGIN_VAR in text:
                errors.append(f"{rel}: contains {PLUGIN_VAR} after rewrite")

    if "SKILL.md" not in names:
        errors.append("missing SKILL.md")
        return errors
    skill_md_text = rel_to_bytes["SKILL.md"].decode("utf-8")
    keys = frontmatter_keys(skill_md_text)
    if keys is None:
        errors.append("SKILL.md: no frontmatter block")
    else:
        allowed = (CLAWHUB_ALLOWED_FRONTMATTER_KEYS if target == "clawhub"
                   else ALLOWED_FRONTMATTER_KEYS)
        for key in keys:
            if key not in allowed:
                errors.append(f"SKILL.md: frontmatter key {key!r} rejected by the "
                              f"{target} target")
    for match in CITED_PATH_RX.finditer(skill_md_text):
        cited = match.group(0).rstrip(".")
        if not exists(cited):
            errors.append(f"SKILL.md: cites {cited} but the bundle has no such member")
    if target == "clawhub":
        errors.extend(_clawhub_gate_rules(rel_to_bytes, skill_name, skill_md_text))
    return errors


def _clawhub_gate_rules(rel_to_bytes, skill_name, skill_text):
    """The clawhub-only rules: license, declared metadata, the scanner note,
    the preambles, and the slug shape of the name."""
    errors = []
    names = set(rel_to_bytes)

    if "license: MIT-0" not in skill_text:
        errors.append("SKILL.md: license is not MIT-0")
    if "homepage:" not in skill_text:
        errors.append("SKILL.md: no homepage")
    metadata = None
    for line in skill_text.split("\n"):
        if line.startswith("metadata: "):
            try:
                metadata = json.loads(line[len("metadata: "):])
            except ValueError:
                errors.append("SKILL.md: metadata line is not JSON")
            break
    if metadata is None and "SKILL.md: metadata line is not JSON" not in errors:
        errors.append("SKILL.md: no metadata line")
    openclaw = metadata.get("openclaw") if isinstance(metadata, dict) else None
    if isinstance(openclaw, dict):
        bins = (openclaw.get("requires") or {}).get("bins")
        if bins != ["python3"]:
            errors.append('SKILL.md: metadata requires.bins is not ["python3"]')
        declared = set()
        for entry in openclaw.get("envVars") or []:
            if isinstance(entry, dict) and entry.get("name"):
                declared.add(entry["name"])
            elif isinstance(entry, str):
                declared.add(entry)
        # Expected straight off the endpoint module, not off
        # OPENCLAW_ENV_DESCRIPTIONS: the dict builds the metadata line, so
        # comparing the metadata against it would compare the build against
        # itself and a dropped declaration would silence both sides.
        expected = {value for attr, value in vars(_endpoint).items()
                    if attr.startswith("ENV_") and isinstance(value, str)}
        missing = sorted(expected - declared)
        if missing:
            errors.append("SKILL.md: metadata does not declare env vars %s"
                          % ", ".join(missing))
        unexpected = sorted(declared - expected)
        if unexpected:
            errors.append("SKILL.md: metadata declares env vars nothing reads: %s"
                          % ", ".join(unexpected))

    security = rel_to_bytes.get("SECURITY.md")
    if security is None:
        errors.append("missing SECURITY.md")
    else:
        text = security.decode("utf-8", errors="replace")
        for phrase in SECURITY_PINNED_PHRASES:
            if phrase not in text:
                errors.append("SECURITY.md: missing the phrase %r" % phrase)

    for rel in sorted(names):
        if os.path.basename(rel).upper().startswith(("LICENSE", "COPYING")):
            errors.append(f"{rel}: a clawhub bundle carries no license file")
    for rel in PREAMBLE_FILES.get(skill_name, []):
        if rel not in names:
            errors.append(f"missing {rel}, expected with the reviewer preamble")
        elif PREAMBLE_MARKER not in rel_to_bytes[rel].decode("utf-8", errors="replace"):
            errors.append(f"{rel}: reviewer preamble missing")

    if not CLAWHUB_SKILL_NAME_RX.match(skill_name):
        errors.append(f"skill name {skill_name!r} is not a valid clawhub slug shape")
    return errors


def gate(zip_path, skill_name):
    """Fail on anything that makes the archive not stand alone."""
    with zipfile.ZipFile(zip_path) as zf:
        prefix = f"{skill_name}/"
        rel_to_bytes = {}
        for name in zf.namelist():
            rel = name[len(prefix):] if name.startswith(prefix) else name
            rel_to_bytes[rel] = zf.read(name)
    return _gate_members(rel_to_bytes, skill_name)


def iter_members(skill_name):
    """Yield (abs_source, rel_dest, rewrite_rel) for one skill's bundle.

    The order is load-bearing: the skill's own tree first, then the vendored
    engine, voices/, and EXTRA_VENDOR, so a duplicate rel_dest later in the
    order is silently skipped the way add_file's zf.getinfo lookup was, and
    an EXTRA_VENDOR entry naming a shipped file raises rather than skipping
    (a silent skip would drop the file the SKILL.md cites it for). rel_dest
    is relative to the skill root; rewrite_rel is set only for files from
    the skill's own tree, the ones whose markdown gets rewritten.
    """
    skill_source = os.path.join(SKILLS_DIR, skill_name)
    if not os.path.isdir(skill_source):
        raise PackagingError(f"skill directory not found: {skill_source}")
    seen = set()

    def fresh(rel_dest):
        if rel_dest in seen:
            return False
        seen.add(rel_dest)
        return True

    # 1. The skill's own tree, markdown rewritten for the bundle layout.
    for root_dir, dirs, files in os.walk(skill_source):
        dirs[:] = [d for d in dirs if not should_ignore(os.path.relpath(os.path.join(root_dir, d), skill_source))]
        for file in sorted(files):
            abs_file = os.path.join(root_dir, file)
            rel_from_skill = os.path.relpath(abs_file, skill_source)
            if should_ignore(rel_from_skill):
                continue
            if not fresh(rel_from_skill):
                continue
            yield abs_file, rel_from_skill, rel_from_skill

    if skill_name == "rabbit-writes":
        return

    # 2. The engine: rwlib plus the files scan.py needs beside it.
    rwlib_source = os.path.join(ENGINE_SCRIPTS_DIR, "rwlib")
    for root_dir, dirs, files in os.walk(rwlib_source):
        dirs[:] = [d for d in dirs if not should_ignore(d)]
        for file in sorted(files):
            abs_file = os.path.join(root_dir, file)
            rel_from_engine = os.path.relpath(abs_file, ENGINE_SCRIPTS_DIR)
            if should_ignore(rel_from_engine):
                continue
            dest = os.path.join("scripts", rel_from_engine)
            if not fresh(dest):
                continue
            yield abs_file, dest, None
    for shared_file in SHARED_ENGINE_FILES:
        abs_file = os.path.join(ENGINE_SCRIPTS_DIR, shared_file)
        if not os.path.isfile(abs_file):
            raise PackagingError(f"engine file missing: {abs_file}")
        dest = os.path.join("scripts", shared_file)
        if not fresh(dest):
            continue
        yield abs_file, dest, None

    # 3. voices/, so rwlib.voices.VOICES_DIR (two up from rwlib, then
    # voices/) resolves inside the bundle.
    voices_source = os.path.join(ENGINE_DIR, "voices")
    for root_dir, dirs, files in os.walk(voices_source):
        dirs[:] = [d for d in dirs if not should_ignore(d)]
        for file in sorted(files):
            abs_file = os.path.join(root_dir, file)
            rel_from_voices = os.path.relpath(abs_file, voices_source)
            if should_ignore(rel_from_voices):
                continue
            dest = os.path.join("voices", rel_from_voices)
            if not fresh(dest):
                continue
            yield abs_file, dest, None

    # 4. Engine files this skill's SKILL.md cites by name.
    for dest_rel, engine_rel in EXTRA_VENDOR.get(skill_name, []):
        if dest_rel in seen:
            raise PackagingError(
                f"vendored {dest_rel} collides with a file {skill_name} already ships"
            )
        seen.add(dest_rel)
        yield os.path.join(ENGINE_DIR, engine_rel), dest_rel, None


def build_skill_zip(skill_name):
    dist_zip_path = os.path.join(DIST_DIR, f"{skill_name}.zip")
    if os.path.exists(dist_zip_path):
        os.unlink(dist_zip_path)

    files_added = 0
    skill_md_count = 0

    try:
        with zipfile.ZipFile(dist_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for abs_file, rel_dest, rewrite_rel in iter_members(skill_name):
                archive_path = os.path.join(skill_name, rel_dest)
                if rewrite_rel is not None and abs_file.endswith(".md"):
                    with io.open(abs_file, encoding="utf-8") as fh:
                        text = fh.read()
                    zf.writestr(archive_path, transform_markdown(skill_name, rewrite_rel, text))
                else:
                    zf.write(abs_file, archive_path)
                files_added += 1
                if rel_dest == "SKILL.md":
                    skill_md_count += 1
    except (PackagingError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if os.path.exists(dist_zip_path):
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


def build_skill_folder(skill_name):
    """Write dist/clawhub/<skill>/ as one self-contained skill folder.

    Same members in the same order as the zip, plus the clawhub-only deltas:
    the SKILL.md frontmatter rewritten for clawhub, the reviewer preamble
    injected into PREAMBLE_FILES, and SECURITY.md at the root.
    """
    folder = os.path.join(DIST_DIR, CLAWHUB_DIR, skill_name)
    if os.path.isdir(folder):
        shutil.rmtree(folder)

    files_added = 0
    skill_md_count = 0
    try:
        for abs_file, rel_dest, rewrite_rel in iter_members(skill_name):
            dest = os.path.join(folder, rel_dest)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if rewrite_rel is not None and abs_file.endswith(".md"):
                with io.open(abs_file, encoding="utf-8") as fh:
                    text = fh.read()
                data = transform_markdown(skill_name, rewrite_rel, text, target="clawhub")
                if rel_dest == "SKILL.md":
                    data = clawhub_frontmatter(data)
                if rel_dest in PREAMBLE_FILES.get(skill_name, []):
                    data = inject_preamble(data)
                with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(data)
            else:
                shutil.copyfile(abs_file, dest)
            files_added += 1
            if rel_dest == "SKILL.md":
                skill_md_count += 1
        with io.open(os.path.join(folder, "SECURITY.md"), "w",
                     encoding="utf-8", newline="\n") as fh:
            fh.write(security_note_text())
    except (PackagingError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if os.path.isdir(folder):
            shutil.rmtree(folder)
        return False

    rel_to_bytes = {}
    for root_dir, dirs, files in os.walk(folder):
        for file in files:
            abs_path = os.path.join(root_dir, file)
            with io.open(abs_path, "rb") as fh:
                rel_to_bytes[os.path.relpath(abs_path, folder)] = fh.read()
    errors = _gate_members(rel_to_bytes, skill_name, target="clawhub")
    if skill_md_count != 1:
        errors.append(f"contains {skill_md_count} SKILL.md files, expected exactly 1")
    if files_added > MAX_FILES:
        errors.append(f"contains {files_added} files, exceeding limit of {MAX_FILES}")

    size_kb = sum(len(data) for data in rel_to_bytes.values()) / 1024
    print(f"Created {CLAWHUB_DIR}/{skill_name}: {len(rel_to_bytes)} files, "
          f"{size_kb:.1f} KB, at {folder}")
    if errors:
        for err in errors:
            print(f"ERROR: {CLAWHUB_DIR}/{skill_name}: {err}", file=sys.stderr)
        shutil.rmtree(folder)
        return False
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Package each skill into isolated, self-contained bundles.")
    parser.add_argument(
        "--target", choices=("claude", "clawhub", "all"), default="all",
        help="claude: one zip per skill under dist/ for the claude.ai "
             "custom-skill upload. clawhub: one folder per skill under "
             "dist/clawhub/ for OpenClaw, ClawHub, and Hermes. "
             "all (default): both.")
    args = parser.parse_args(argv)
    os.makedirs(DIST_DIR, exist_ok=True)
    success = True
    for skill in SKILL_NAMES:
        if args.target in ("claude", "all") and not build_skill_zip(skill):
            success = False
        if args.target in ("clawhub", "all") and not build_skill_folder(skill):
            success = False
    if success:
        print("All %d skills packaged under dist/: zips for the claude.ai "
              "upload, folders under dist/%s for OpenClaw, ClawHub, and "
              "Hermes." % (len(SKILL_NAMES), CLAWHUB_DIR))
        return 0
    print("Packaging failed for one or more skills.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
