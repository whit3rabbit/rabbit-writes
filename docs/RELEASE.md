# Release

What a release of this plugin touches, in order: the changelog, the version
in three places, CI, the ClawHub publishes, and the tag. Everything here is
a maintainer concern. Installing the skills is covered in the README and in
`docs/OPENCLAW.md`.

## 1. Finish the changelog first

The top of `CHANGELOG.md` is `## Unreleased`, and one thing reads it
mechanically: `scripts/publish_clawhub.py` derives its per-skill changelog
note from the first paragraph under that heading. Publish with the section
still in place. Once it is retitled to a version the wrapper falls back to
"See CHANGELOG.md in the plugin repository.", and the note ClawHub prints
next to the skill stops saying what changed. `--changelog` overrides the
derivation by hand when the section has already moved on.

So the order is: finish `## Unreleased`, publish, then retitle it to
`## <version> (YYYY-MM-DD)` in the tagging commit.

## 2. Bump the version in three places

- `.claude-plugin/plugin.json` is the source of truth. Its `version` is what
  `publish_clawhub.py` passes as `--version`, and ClawHub requires semver.
- Every `skills/*/SKILL.md` repeats it under `metadata.version`.
  `check_packaging_metadata` in `scripts/validate.py` fails the build when
  any of the six disagrees with plugin.json, so a missed edit is a caught
  error rather than a published mismatch.
- `CHANGELOG.md` carries the human version heading.

`lexicon.json` and `registers.json` carry their own versions. They version
the engine's data rather than the release, and `validate.py` holds them to
`PROOF.md` on its own schedule. Do not bump them as part of a release.

## 3. CI, and what it cannot run

`.github/workflows/ci.yml` runs on every push to `main` and every pull
request, across Python 3.9 through 3.13 on Linux, plus one Windows and one
macOS entry. It runs the repo validator, the engine, rabbit-readme-improver,
voice-setup, and rabbit-reads suites, three stubbed research harnesses
(detector-corpus, thesaurus-research, voice-eval), the dogfood scans over
the repo's own prose, and an informational labeled-corpus score that never
gates.

Three things a release needs that CI does not run:

- `claude plugin validate .`, which needs an authenticated CLI a runner has
  no way to provide. The workflow's own header comment says so. Run it by
  hand before tagging.
- The packaging battery (`scripts/test_package_skills.py`), the mutation
  tests for the validator itself (`scripts/test_validate_checks.py`), the
  `rabbit-rewrites` suite, and the `academic-research` harness are hand-run
  today. The full local battery is the "Verify before shipping" block in
  `CLAUDE.md`, and a release runs all of it.
- `scripts/publish_clawhub.py --dry-run`, which exits 1 under `CI` on
  purpose. Publishing is a human act with a logged-in account.

## 4. Publish to ClawHub

```bash
npm i -g clawhub
clawhub login
python3 scripts/publish_clawhub.py --dry-run   # prints what it will run, per skill
python3 scripts/publish_clawhub.py             # the real publish
```

`--skill <name>` narrows the run. `--extra=--flag` forwards anything the CLI
supports that the wrapper does not model. The wrapper:

- Rebuilds each folder through `build_skill_folder` before touching the CLI,
  so what ships is what the gate saw. `dist/` is gitignored and regenerated
  on every run, and a stale folder cannot be published.
- Passes only `clawhub skill publish <path> --version <version>`, plus
  `--dry-run` and `--json` when asked. `--slug`, `--name`, and `--changelog`
  are not documented on `skill publish` in the official CLI docs (checked
  August 2026), so the wrapper prints the suggested slug and the changelog
  for the human instead, and the printed argv at `--dry-run` is where any
  flag drift shows up.
- Exits 1 under CI and never runs there.

Expect the scan. ClawHub relicenses everything it publishes as MIT-0 and
rejects conflicting license text, which is why each bundle's SKILL.md says
`license: MIT-0` while the repository stays MIT. Every upload also passes a
hash check and a code review that cross-check declared metadata against the
code. These bundles quote attack patterns as detection documentation, so a
warning label on `rabbit-writes` is possible and is an accepted outcome, not
a build failure.

SECURITY.md at each bundle root is the appeal evidence, and daily rescans
can change a skill's status after publishing. Check each skill's page on
clawhub.ai after the run.

The claude.ai zips come out of the same packaging run (`--target all` is the
default) and are uploaded by hand on claude.ai. That path is documented in
the README.

## 5. Tag

Commit the changelog retitle (`## Unreleased` becomes
`## <version> (YYYY-MM-DD)`) and tag the commit. `claude plugin validate .`
belongs before this step, not after.

## Why the packaging is shaped the way it is

- **One member list, two outputs.** `iter_members` in
  `scripts/package_skills.py` yields each bundle's files once, and the zip
  writer and the folder writer are both consumers of it. A clawhub folder
  cannot drift from a claude.ai zip because neither has a file list of its
  own. `test_clawhub_folder_is_the_zip_modulo_declared_deltas` pins the
  folder to the zip plus exactly the declared deltas, which transfers the
  whole zip battery to the folder output.
- **Every skill stands alone.** OpenClaw and Hermes install one folder per
  skill with no repository around it, so each folder vendors the engine
  (`scan.py`, `verify.py`, `rwlib/` and its data files) and a `voices/`
  snapshot. The tradeoff is the same one the claude.ai zips make: a profile
  built inside one skill's `voices/` never reaches another.
- **Paths are spelled `{baseDir}/...`** because that is the placeholder
  OpenClaw expands to the skill folder. A host that leaves it literal still
  resolves the paths relative to the folder, and the Paths paragraph in each
  rewritten SKILL.md says so.
- **The frontmatter is rewritten, not authored twice.** The source SKILL.md
  files stay written for the plugin install, and `clawhub_frontmatter`
  rewrites the packaged copy: `license: MIT-0`, a `homepage` from
  `plugin.json`, `compatibility` dropped (it moves to SECURITY.md), and a
  one-line JSON `metadata` whose `openclaw` block declares `python3` and the
  three optional `RABBIT_MODEL_*` env vars. The env names are imported from
  `rwlib/endpoint.py` rather than restated, so the declaration cannot drift
  from what the vendored code reads.
- **SECURITY.md and the reviewer preambles are the scanner mitigation.**
  This plugin detects concealed prompt injection, so parts of it look like
  the thing it detects: directive-matching regexes, and reference files that
  quote attack shapes as documentation. The mitigation is context rather
  than obfuscation. Every bundle root carries a SECURITY.md stating what the
  bundle is (a detector, not an actor), the guarantees a reviewer can check
  (injection findings are unfixable and unsuppressible by design), and the
  whole network surface. The two reference files that quote attack shapes
  open with a preamble saying the quotations are data, injected at packaging
  time so the source files stay untouched.
- **A gate holds every claim.** After each folder is written, the gate fails
  the build on a surviving `${CLAUDE_PLUGIN_ROOT}`, a `scripts/`,
  `voices/`, or `references/` citation the folder does not carry, a metadata
  line that is not JSON or does not declare every env var the vendored
  endpoint module reads, a missing pinned phrase in SECURITY.md, a license
  file, a missing reviewer preamble, or a name that is not a legal slug.
  `check_packaging_metadata` in `validate.py` holds the declarations to the
  source between builds, and four tests in `scripts/test_validate_checks.py`
  prove it fires.

## The checklist

1. Finish `## Unreleased` in `CHANGELOG.md`.
2. Bump `version` in `.claude-plugin/plugin.json` and `metadata.version` in
   all six `skills/*/SKILL.md` (`validate.py` catches a miss).
3. Run the full "Verify before shipping" block in `CLAUDE.md`, plus
   `claude plugin validate .`.
4. `python3 scripts/publish_clawhub.py --dry-run`, read the printed argv,
   then the real run. Check each skill's page on clawhub.ai.
5. Upload `dist/*.zip` on claude.ai if that channel is in the release.
6. Retitle `## Unreleased` to the version heading, commit, and tag.
