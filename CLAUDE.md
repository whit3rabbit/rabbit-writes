# rabbit-writes

Claude Code / Codex plugin. Three skills (`rabbit-writes`, `voice-setup`, `readme-writing`) over one prose engine in `skills/rabbit-writes/{references,scripts}`.

## Verify before shipping

```bash
python3 scripts/validate.py                              # manifests, skills, voices, cross-refs, tripwires
python3 skills/rabbit-writes/tests/test_scan.py          # engine calibration + preservation validator
python3 skills/readme-writing/tests/test_readme_check.py # structure, voice, 100-repo regression
claude plugin validate .                                 # manifest schema
```

## Gotchas

- `validate.py` fails on any reference to the second prose skill that was merged away before release, and pins the `SKILL.md` mode table, the "a file path tells you where the text lives" line, and where "minimum effective edit" may appear. Rewording those fails the build on purpose. The check exempts only `CHANGELOG.md` and itself.
- `validate.py` string-matches `readme_check.py`'s `SCAN_PATH` literal. Change both together or the check degrades to a note instead of a failure.
- Scripts resolve siblings by walking up from their own path, so a skill directory can move without editing the scripts inside it.

## Conventions

- Repo prose is held to the active voice: no em dashes, no semicolons. Check with
  `python3 skills/rabbit-writes/scripts/scan.py <file> --voice-rules skills/rabbit-writes/voices/whit3rabbit.rules.json`
- Dogfood before shipping doc changes: `readme_check.py` on `README.md`, `scan.py` on any `SKILL.md`. Both have found real bugs in themselves this way.
- `skills/rabbit-writes/PROOF.md` publishes measured self-scan numbers. Regenerate it when files move or change; never just move it.
- Corpus data regenerates: `cd scripts/readme-research && python3 03_analyze_readme.py --batch && python3 04_aggregate.py`. Step 03 overwrites `docs/readme-analysis/02_all_stats.json`, so a batch that finds no READMEs empties it.
- Codex reads the `.claude-plugin/` manifests, so one manifest set serves both hosts. No `.codex-plugin/` needed.
