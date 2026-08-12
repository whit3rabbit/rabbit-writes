# rabbit-writes

Claude Code / Codex plugin. Three skills (`rabbit-writes`, `voice-setup`, `readme-writing`) over one prose engine in `skills/rabbit-writes/{references,scripts}`.

## Verify before shipping

```bash
python3 scripts/validate.py                          # manifests, skills, voices, cross-refs, tripwires
python3 skills/rabbit-writes/tests/run.py            # engine, voice, verifier, fixer, invariants
python3 skills/readme-writing/tests/run.py           # structure, links, voice, 100-repo regression
python3 scripts/detector-corpus/test_corpus_harness.py   # the corpus harness, network stubbed
claude plugin validate .                             # manifest schema
```

`run.py` is a stdlib runner so the suite works on a checkout with nothing installed. `pytest` collects the same files and is nicer: run it from inside the tests directory, or from anywhere, since each directory has a `conftest.py` that puts `helpers.py` on the path. `run.py -k <substring>` selects by test or file name.

## Where a fact lives

One home per fact. These four moved there and the old copies are gone, so adding a second copy is a regression rather than a style question.

- **Markdown spans, sentence splitting, the lexicon, badge hosts, section keywords, the finding schema.** `skills/rabbit-writes/scripts/rwlib/`. Imported by `scan.py`, `verify.py`, `readme_check.py`, and the corpus research scripts, all of which bootstrap it by inserting the engine's `scripts/` directory into `sys.path`.
- **The tolerance matrix.** `skills/rabbit-writes/scripts/registers.json`. `scan.py` derives `PROFILE_SKIP`, `PROFILE_RELAX`, `VOCAB_EXEMPT_PROFILES`, and `REGISTERS` from it, and the markdown table in `references/context.md` is rendered from it by `python3 skills/rabbit-writes/scripts/rwlib/registers.py --write`. `validate.py` fails if the doc has drifted.
- **The README corpus figures.** `skills/readme-writing/scripts/corpus_summary.json`, produced from the research aggregate by `scripts/readme-research/05_export_corpus_summary.py`. `validate.py` compares the two whenever `docs/readme-analysis/` is present. It carries `measured_at`, which `04_aggregate.py` derives from the latest `pushed_at` in the sample rather than from the clock, so rerunning the aggregation over the same committed data does not move it. The checker quotes it: "corpus comparison (100 trending repos, 2026-08-10)".
- **Versions.** `lexicon.json` and `registers.json` each carry a `version`. `scan.py --json` echoes both, `PROOF.md`'s heading quotes the lexicon one, and `validate.py` fails if they disagree.
- **How many of an invisible character are in a document.** `rwlib.artifacts.occurrences`. `scan.py` reports off it and `rwlib/fixes.py` thresholds off it, and it is where the emoji-joiner carve-out lives. The two used to count differently, so a document could be reported and then neither fixed nor explained.
- **Which voice profile applies, and why.** `rwlib.voices.resolve`: `.rabbit-voice` beside the document or in the working directory, then `voices/ACTIVE`, then a lone installed profile, each with the note that says which. It lived in `readme_check.py` and `scan.py` had none of it, so the two checkers in one plugin could disagree about whose rules were in force. `scan.py --voice auto` and `readme_check.py`'s default both go through it. Resolution is never the default in `scan.py`: that is what the `rabbit-scan` hook runs in somebody else's repository.
- **An HTML character reference.** `rwlib.markdown`. `PROSE_DASH_RX` matches `&mdash;` and `&#8212;` as well as the character, so a find-and-replace cannot walk a document past `verify.py`'s gate or a voice that forbids em dashes. `blank_entities` goes the other way for the semicolon ban, because the `;` closing `&nbsp;` is markup. Both directions are in `tests/test_entities.py`.
- **What priority a synthetic finding is.** `SYNTHETIC_PRIORITIES` in `rwlib/lexicon.py`, beside `SYNTHETIC_FINDING_IDS`. `scan.py` reads it at each call site through `SYNTH = lexicon_mod.synthetic_priority`, so there is no hand-sync left, and an id that is only in one of the two sets raises there rather than drifting. Two tests hold it: `test_every_synthetic_finding_declares_a_priority` on the id sets, `test_scan_raises_each_synthetic_finding_at_its_declared_priority` on the engine agreeing. The one carve-out is `hidden-unicode`, where the table names the P0 ceiling and the space-like half is raised at P2 at the call site.

## Gotchas

- `validate.py` runs two separate tripwires, and they have different reach. `check_no_stale_skill_name` searches the whole repo for the second prose skill that was merged away before release, exempting only `CHANGELOG.md` and itself. `check_mode_contract` reads one file, `skills/rabbit-writes/SKILL.md`, and pins its mode table, its "a file path tells you where the text lives" line, and the absence of "minimum effective edit" from the guardrail section above `## Modes`. It says nothing about the phrase anywhere else, which is why `README.md` carries it in the attribution list and passes. Rewording either pinned line fails the build on purpose.
- `validate.py` string-matches `readme_check.py`'s `SCAN_PATH` literal. Change both together or the check degrades to a note instead of a failure. `readme_check.py` also resolves `rwlib` from that same literal, so the two cannot end up pointing at different checkouts.
- Invisible characters are written as escapes everywhere, never as literals. Any tool that normalizes whitespace turns a literal U+00A0 into a plain space, and the check or fixture that depended on it stops working without changing anything a reader can see. This has already happened once to a test fixture.
- The corpus research scripts keep their own table patterns and sentence splitter, deliberately. Every committed `stats.json` was measured with those, so swapping in the engine's copies would silently move a published number. The comments at `TABLE_ROW_RE` in `03_analyze_readme.py` say so.
- Scripts resolve siblings by walking up from their own path, so a skill directory can move without editing the scripts inside it.
- The hooks are tested from somebody else's working directory, by `check_precommit_hooks` in `validate.py`, and nothing else in the tree is. Both suites run from this repository root with this repository's files, which is why two hooks shipped broken: `readme-check` blocked a stranger's commit over this author's semicolon, and `rabbit-scan-voice` handed a plugin-relative `--voice-rules` path to a directory where it does not exist. The check parses `.pre-commit-hooks.yaml` with a regex, so a change to that file's shape makes it fail loudly rather than pass on an empty list.
- `check_precommit_hooks` in `validate.py` decides whether a hook applies somebody's style rules by reading its own `args` for a `--voice` prefix, which covers `--voice-rules` too. The `args:` guard above it pins that `parse_hooks` read the arguments at all, and it is written against the `args:` key rather than a flag name because the flag has already changed once.
- The default hooks apply no voice profile, and `readme-check-voice` and `rabbit-scan-voice` are the opt-ins. `rabbit-scan-voice` says `--voice auto` rather than naming a path, so a committer's `.rabbit-voice` wins over the cloned plugin's `ACTIVE`. `resolve_plugin_paths` in `precommit.py` is no longer load-bearing for anything shipped and stays for a hand-written `--voice-rules` pointing at a bundled profile. `--no-voice` on `readme_check.py` means "no style profile", not "no prose scan": structure, fingerprints and craft all still run, because a pasted citation marker is evidence rather than taste. A profile that only fails to *resolve* is a note and the run continues, but a profile named by hand with `--voice-rules` and not readable exits 2, the way `scan.py` does. The alternative was a clean report on a document nobody checked.
- Suppressions live in `rwlib/suppress.py` and are marked, never dropped: a suppressed finding keeps its place in the list with a `suppressed` key, comes out of the priority counts, and is printed under its own heading. `findings.counts` skips it and adds a `suppressed` tally, and both `--check` paths test `"suppressed" not in f`. `scan.scan(..., suppressions=False)` exists for `readme_check.py`, which merges the two halves and runs one pass over the whole list: run in both, the audit would fire twice and call a suppression naming a structure id unused. The repo does not use the mechanism on `references/patterns.md`, on purpose, and `SKILL.md` says why.
- `citation-leak` and `curly-quote` carry `scan_raw`, so the quoted-example exemption does not reach them. That is why `references/patterns.md` publishes 5 P0s in `PROOF.md`, and why any document that quotes a chat citation marker in backticks fails `--check`. `placeholder` deliberately does not, and its `_scan_raw_note` says why.

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
- **Python 3.9 is the floor, and it is a support claim rather than a technical one.** No script uses syntax past 3.8. The floor moved off 3.8 because 3.8 has been end of life since October 2024 and the 24.04 runner image does not offer it, so testing the claim cost a pinned `ubuntu-22.04` entry. Lower it again only if somebody actually has an old host, and expect to pay that runner back.
- CI runs `python`, not `python3`, and sets `shell: bash` by default. `setup-python` guarantees `python` on all three platforms and does not guarantee `python3` on Windows, and Windows defaults to pwsh, where the trailing `\` in the dogfood block is not a line continuation. The scripts and the docs still say `python3`, which is right everywhere a human runs them.
- The Windows and macOS matrix entries are one apiece and exist for the CRLF write-back path in `--apply-safe --write` and for the platform the plugin is developed on. Before them, that code was tested only by constructing CRLF bytes on Linux, which exercises the branch and not the platform.
