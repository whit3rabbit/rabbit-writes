# rabbit-writes

Claude Code / Codex plugin. Six skills (`rabbit-writes`, `voice-setup`, `rabbit-readme-improver`, `rabbit-reads`, `rabbit-rewrites`, `rabbit-claude-md`) over one prose engine in `skills/rabbit-writes/{references,scripts}`, with `rabbit-reads` verifying the notes it writes through the engine's scanner, `rabbit-rewrites` driving a small local model through the engine's own gate, and `rabbit-claude-md` auditing CLAUDE.md and AGENTS.md memory files through the same engine.

## Verify before shipping

```bash
python3 scripts/validate.py                          # manifests, skills, voices, cross-refs, tripwires
python3 scripts/test_validate_checks.py              # the validator's own checks, driven over fixtures built to break them
python3 skills/rabbit-writes/tests/run.py            # engine, voice, verifier, fixer, invariants
python3 skills/rabbit-readme-improver/tests/run.py           # structure, links, voice, 100-repo regression
python3 skills/voice-setup/tests/run.py              # scaffolding, thesaurus, edit-learning
python3 skills/rabbit-reads/tests/run.py             # extraction, structure mapping, notes battery
python3 skills/rabbit-rewrites/tests/run.py          # the model battery, and the bench that scores against it
python3 skills/rabbit-claude-md/tests/run.py         # CLAUDE.md and AGENTS.md structure checks, discovery, thresholds, engine merge
python3 scripts/detector-corpus/test_corpus_harness.py   # the corpus harness, network stubbed
python3 scripts/academic-research/test_academic_harness.py   # the academic corpus pipeline, over synthetic JATS
python3 scripts/thesaurus-research/test_thesaurus_harness.py   # the thesaurus pipeline, over synthetic datasets
python3 scripts/ste-research/test_ste_harness.py          # the STE dictionary-vocabulary pipeline, over synthetic entries
python3 scripts/claude-vocab-research/test_claude_vocab_harness.py   # the Claude-vocabulary pipeline over the PR-description dataset, synthetic snapshot
python3 scripts/voice-eval/test_eval_harness.py          # the reconstruction scorer, over stubbed triples
python3 scripts/package_skills.py                        # package 6 isolated skill zips into dist/ for Claude custom skills upload, and one clawhub skill folder each under dist/clawhub/
python3 scripts/test_package_skills.py                   # extract each zip outside the repo and run what it ships, the same battery over a loose plugin-layout copy, and the clawhub folders against the zips
python3 scripts/publish_clawhub.py --dry-run             # human-run only, never in CI (the script exits 1 under CI): rebuild each clawhub folder through its gate and print the clawhub argv
claude plugin validate .                             # marketplace manifest only, and it never reads $schema
```

The engine suite runs about 2:20 now, past a 120-second command timeout, so background it or raise the limit rather than watching it get killed. `run.py -k <substring>` while iterating: the corpus-wide tests in `test_verify.py` and `test_stylometry.py` are most of the wall clock, and everything else finishes in seconds.

`run.py` is a stdlib runner so the suite works on a checkout with nothing installed. `pytest` collects the same files and is nicer: run it from inside the tests directory, or from anywhere, since each directory has a `conftest.py` that puts `helpers.py` on the path. `run.py -k <substring>` selects by test or file name.

Tests take zero arguments. `run.py` prints `SKIP` for a test with parameters and then counts it as an error, so a pytest fixture or `parametrize` fails the run rather than degrading to pytest-only. Table-driven cases go in a list inside the test body.

## Architecture pointers

One home per fact. Each skill under `skills/<name>/` carries its own `CLAUDE.md` with that skill's structure, gotchas, and regeneration commands, loaded automatically when Claude works in that directory. Nothing here repeats it.

- `skills/rabbit-writes/`: the prose engine (`scripts/rwlib/`) every other skill imports. Owns the lexicon, registers, the STE layer, voice and fingerprint machinery, the safety band, and the model-rewrite pair.
- `skills/rabbit-rewrites/`: benchmarks the model-rewrite path against `skills/rabbit-writes/scripts/rwlib/{endpoint,rewrite}.py`.
- `skills/rabbit-reads/`: turns a book or paper into a cheatsheet doc set, verified through the engine.
- `skills/rabbit-readme-improver/`: README auditing and drafting from the 100-repo corpus.
- `skills/voice-setup/`: builds and audits the voice profiles the engine enforces.
- `skills/rabbit-claude-md/`: this audit tooling, applied to CLAUDE.md and AGENTS.md files.

Deeper cross-skill detail lives under `.claude/docs/`, imported below so it is always in context. Which one governs which area:

- Packaging and publishing, meaning `scripts/package_skills.py`, `scripts/publish_clawhub.py`, or any bundle's shipped metadata: @.claude/docs/packaging.md
- Adding a check to `scripts/validate.py`, debugging why one did not fire, or a tripwire tripped: @.claude/docs/validate-internals.md
- Host integration, meaning `hooks/hooks.json`, `output-styles/`, `install_host.py`, or `.pre-commit-hooks.yaml`: @.claude/docs/hooks.md

## Conventions

- Repo prose is held to the active voice: no em dashes, no semicolons. Check with `python3 skills/rabbit-writes/scripts/scan.py <file> --voice-rules skills/rabbit-writes/voices/whit3rabbit.rules.json`. Two carve-outs, both measured in `skills/rabbit-writes/PROOF.md`: `references/patterns.md` is a catalog of the marks it bans and quotes them in before/after examples, so it scores 25 voice hits on purpose, and an attributed quotation is never rewritten anywhere. Everything else is at zero and should stay there. `oxford_comma` findings are P2 advisories, not defects, and no regex can settle them. The check has a blind spot: an em dash on a list line that also carries an inline code span is not reported, while the same dash on a plain line is a P0, which is how `voice-setup/SKILL.md` shipped three of them against a voice that forbids them. Sweep for codepoints above 127 as well as running the scan, the same habit the invisible-character gotcha asks for.
- Dogfood before shipping doc changes: `readme_check.py` on `README.md`, `scan.py` on any `SKILL.md`. Both have found real bugs in themselves this way.
- Writing samples for voice work never live in tracked paths. They go under `scratch/` at the repo root, which `.gitignore` already covers, and a profile built from them carries counts, patterns, and synthetic examples rather than passages from the samples. A sample is somebody's prose, and committing it publishes it.
- Codex reads the `.claude-plugin/` manifests, so one manifest set serves both hosts. No `.codex-plugin/` needed.
- **Python 3.9 is the floor, and it is a support claim rather than a technical one.** No script uses syntax past 3.8. The floor moved off 3.8 because 3.8 has been end of life since October 2024 and the 24.04 runner image does not offer it, so testing the claim cost a pinned `ubuntu-22.04` entry. Lower it again only if somebody actually has an old host, and expect to pay that runner back.
- CI runs `python`, not `python3`, and sets `shell: bash` by default. `setup-python` guarantees `python` on all three platforms and does not guarantee `python3` on Windows, and Windows defaults to pwsh, where the trailing `\` in the dogfood block is not a line continuation. The scripts and the docs still say `python3`, which is right everywhere a human runs them.
- The Windows and macOS matrix entries are one apiece and exist for the CRLF write-back path in `--apply-safe --write` and for the platform the plugin is developed on. Before them, that code was tested only by constructing CRLF bytes on Linux, which exercises the branch and not the platform.
