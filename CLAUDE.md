# rabbit-writes

Claude Code / Codex plugin. Three skills (`rabbit-writes`, `voice-setup`, `readme-writing`) over one prose engine in `skills/rabbit-writes/{references,scripts}`.

## Verify before shipping

```bash
python3 scripts/validate.py                          # manifests, skills, voices, cross-refs, tripwires
python3 skills/rabbit-writes/tests/run.py            # engine, voice, verifier, fixer, invariants
python3 skills/readme-writing/tests/run.py           # structure, links, voice, 100-repo regression
claude plugin validate .                             # manifest schema
```

`run.py` is a stdlib runner so the suite works on a checkout with nothing installed. `pytest` collects the same files and is nicer: run it from inside the tests directory, or from anywhere, since each directory has a `conftest.py` that puts `helpers.py` on the path. `run.py -k <substring>` selects by test or file name.

## Where a fact lives

One home per fact. These four moved there and the old copies are gone, so adding a second copy is a regression rather than a style question.

- **Markdown spans, sentence splitting, the lexicon, badge hosts, section keywords, the finding schema.** `skills/rabbit-writes/scripts/rwlib/`. Imported by `scan.py`, `verify.py`, `readme_check.py`, and the corpus research scripts, all of which bootstrap it by inserting the engine's `scripts/` directory into `sys.path`.
- **The tolerance matrix.** `skills/rabbit-writes/scripts/registers.json`. `scan.py` derives `PROFILE_SKIP`, `PROFILE_RELAX`, `VOCAB_EXEMPT_PROFILES`, and `REGISTERS` from it, and the markdown table in `references/context.md` is rendered from it by `python3 skills/rabbit-writes/scripts/rwlib/registers.py --write`. `validate.py` fails if the doc has drifted.
- **The README corpus figures.** `skills/readme-writing/scripts/corpus_summary.json`, produced from the research aggregate by `scripts/readme-research/05_export_corpus_summary.py`. `validate.py` compares the two whenever `docs/readme-analysis/` is present.
- **Versions.** `lexicon.json` and `registers.json` each carry a `version`. `scan.py --json` echoes both, `PROOF.md`'s heading quotes the lexicon one, and `validate.py` fails if they disagree.

## Gotchas

- `validate.py` runs two separate tripwires, and they have different reach. `check_no_stale_skill_name` searches the whole repo for the second prose skill that was merged away before release, exempting only `CHANGELOG.md` and itself. `check_mode_contract` reads one file, `skills/rabbit-writes/SKILL.md`, and pins its mode table, its "a file path tells you where the text lives" line, and the absence of "minimum effective edit" from the guardrail section above `## Modes`. It says nothing about the phrase anywhere else, which is why `README.md` carries it in the attribution list and passes. Rewording either pinned line fails the build on purpose.
- `validate.py` string-matches `readme_check.py`'s `SCAN_PATH` literal. Change both together or the check degrades to a note instead of a failure. `readme_check.py` also resolves `rwlib` from that same literal, so the two cannot end up pointing at different checkouts.
- Invisible characters are written as escapes everywhere, never as literals. Any tool that normalizes whitespace turns a literal U+00A0 into a plain space, and the check or fixture that depended on it stops working without changing anything a reader can see. This has already happened once to a test fixture.
- The corpus research scripts keep their own table patterns and sentence splitter, deliberately. Every committed `stats.json` was measured with those, so swapping in the engine's copies would silently move a published number. The comments at `TABLE_ROW_RE` in `03_analyze_readme.py` say so.
- Scripts resolve siblings by walking up from their own path, so a skill directory can move without editing the scripts inside it.

## Conventions

- Repo prose is held to the active voice: no em dashes, no semicolons. Check with
  `python3 skills/rabbit-writes/scripts/scan.py <file> --voice-rules skills/rabbit-writes/voices/whit3rabbit.rules.json`
  Two carve-outs, both measured in `skills/rabbit-writes/PROOF.md`. `references/patterns.md`
  is a catalog of the marks it bans and quotes them in before/after examples, so it scores
  25 voice hits on purpose. An attributed quotation is never rewritten anywhere. Everything
  else is at zero and should stay there. `oxford_comma` findings are P2 advisories, not
  defects, and no regex can settle them.
- Dogfood before shipping doc changes: `readme_check.py` on `README.md`, `scan.py` on any `SKILL.md`. Both have found real bugs in themselves this way.
- `skills/rabbit-writes/PROOF.md` publishes measured self-scan numbers. Regenerate it when files move or change; never just move it.
- Corpus data regenerates: `cd scripts/readme-research && python3 03_analyze_readme.py --batch && python3 04_aggregate.py && python3 05_export_corpus_summary.py`. Step 03 overwrites `docs/readme-analysis/02_all_stats.json`, so a batch that finds no READMEs empties it. Step 05 is not optional: without it the checker keeps comparing against the old numbers.
- The labeled corpus in `docs/detector-corpus/` is empty and the harness around it is not. `scripts/detector-corpus/score.py` publishes a per-register false-positive rate with a Wilson interval the moment somebody populates it, and `PROOF.md` says plainly that until then the calibration rests on two hand-written samples.
- Codex reads the `.claude-plugin/` manifests, so one manifest set serves both hosts. No `.codex-plugin/` needed.
