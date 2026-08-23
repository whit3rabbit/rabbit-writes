# OpenClaw, ClawHub, and Hermes

The plugin's five skills run on the hosts that install AgentSkills folders.
This page covers installing them on OpenClaw, publishing them to ClawHub, and
installing them on Hermes. The Claude Code and Codex plugin installs and the
claude.ai zip uploads are covered in the README.

## The short version

One packager builds both shapes:

```bash
python3 scripts/package_skills.py                    # zips for claude.ai and folders for OpenClaw
python3 scripts/package_skills.py --target clawhub   # folders only
```

Every folder lands under `dist/clawhub/<skill>/` and carries everything the
skill needs: the engine (`scan.py`, `verify.py`, `rwlib/` and its data
files), a `voices/` snapshot, the references, and a SKILL.md whose paths are
spelled `{baseDir}/...`, the placeholder OpenClaw expands to the skill
folder. A host that leaves the placeholder literal still works: resolve the
paths relative to the folder.

## OpenClaw

Copy the folders you want into your workspace skills directory and restart
the gateway:

```bash
git clone https://github.com/whit3rabbit/rabbit-writes
cd rabbit-writes
python3 scripts/package_skills.py --target clawhub
cp -r dist/clawhub/* <your workspace skills dir>/
```

Each skill stands alone, so install one or all five. The satellites carry
their own engine copy, the same tradeoff the claude.ai zips make: profiles
built inside one skill's `voices/` do not reach another.

The frontmatter declares `python3` under `requires.bins` and the three
optional `RABBIT_MODEL_*` variables under `envVars`. Nothing is required.
The variables matter only to `scan.py --apply-model`, and there is no
default endpoint, so nothing contacts any server without a person naming
one.

## ClawHub

Publishing is a logged-in, human-run act, so the wrapper never runs in CI
(it exits 1 there) and rebuilds every bundle through the packaging gate
before touching the CLI:

```bash
npm i -g clawhub
clawhub login
python3 scripts/publish_clawhub.py --dry-run   # prints what it will run, per skill
python3 scripts/publish_clawhub.py             # the real publish
```

`--skill <name>` narrows the run, `--changelog` overrides the derived
changelog text, and `--extra=--flag` forwards anything the CLI supports that
the wrapper does not model. The wrapper passes `clawhub skill publish <path>
--version <version>` plus `--dry-run` and `--json` when asked. It
deliberately passes no `--slug`, `--name`, or `--changelog`: the official
CLI docs do not document them on `skill publish` (checked August 2026),
third-party guides disagree, and the printed argv at `--dry-run` makes any
drift a one-flag fix. The suggested slug and the changelog text print for
the human instead.

Two things to know before the first publish.

**ClawHub relicenses everything it publishes as MIT-0.** The repository
stays MIT. The bundle's SKILL.md says `license: MIT-0` and carries no
license file, which is what the platform requires rather than a statement
about the source.

**The upload scan may flag these bundles, and that is expected.** Every
upload passes a hash check and a code review, and declared metadata is
cross-checked against the code. These bundles quote attack patterns as
detection documentation and carry regexes that match directive phrases,
which is exactly what a scan for injection tooling looks for. The mitigation
is honesty rather than obfuscation:

- Every bundle root carries a SECURITY.md stating what the bundle is (a
  detector, not an actor), why a scanner may flag it, the verifiable
  guarantees (injection findings are unfixable and unsuppressible by
  design), and the whole network surface.
- `references/injection.md` and `references/patterns.md` open with a
  reviewer preamble saying the quotations are data. The source files are
  untouched, the preamble is injected at packaging time.
- The SKILL.md metadata declares every env var the vendored code reads, so
  the declaration and the code cannot disagree.

If a bundle still lands a warning label, SECURITY.md is the appeal evidence,
and daily rescans can change a skill's status after publishing. A label is
an accepted outcome, not a build failure.

## Hermes

Hermes reads the same folders. Install by copying:

```bash
python3 scripts/package_skills.py --target clawhub
mkdir -p ~/.hermes/skills
cp -r dist/clawhub/* ~/.hermes/skills/
```

`hermes claw migrate` imports an existing OpenClaw install instead, for a
host that already has one.

## What the folders are

`dist/clawhub/<skill>/` is the zip's member list plus the clawhub deltas:

| Delta | Why |
|---|---|
| `license: MIT-0`, a `homepage`, and one JSON `metadata` line | What ClawHub and OpenClaw read. The metadata's `openclaw` block declares `requires.bins: [python3]` and the three `RABBIT_MODEL_*` env vars. |
| `{baseDir}/`-spelled paths | The placeholder OpenClaw expands. The claude zips keep bare relative paths. |
| SECURITY.md at the root | The scanner's and a human moderator's first read. |
| A reviewer preamble in two reference files | Says the quoted attack shapes are data, without touching the sources. |

The gate `build_skill_folder` runs after every build and fails the folder if
any of that is missing: an undeclared env var, a dropped pinned phrase in
SECURITY.md, a license file, a surviving `${CLAUDE_PLUGIN_ROOT}`, a metadata
line that is not JSON, or a cited path the folder does not carry.
`python3 scripts/test_package_skills.py` covers both outputs, and
`check_packaging_metadata` in `scripts/validate.py` holds the declarations
to the code between builds.
