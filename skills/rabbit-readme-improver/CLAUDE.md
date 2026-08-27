# rabbit-readme-improver

README auditing, drafting, restructuring, and section writing skill based on empirical analysis of 100 trending GitHub repositories.

## Commands

```bash
# Run unit tests
python3 skills/rabbit-readme-improver/tests/run.py

# Pytest equivalent
pytest skills/rabbit-readme-improver/tests/

# Audit or check a README.md file
python3 skills/rabbit-readme-improver/scripts/readme_check.py path/to/README.md

# Audit with JSON payload
python3 skills/rabbit-readme-improver/scripts/readme_check.py path/to/README.md --json

# Run as a gate (exit 1 on P0 issues)
python3 skills/rabbit-readme-improver/scripts/readme_check.py path/to/README.md --check

# Check README with explicit voice rules
python3 skills/rabbit-readme-improver/scripts/readme_check.py path/to/README.md --voice-rules skills/rabbit-writes/voices/whit3rabbit.rules.json
```

## Structure & Architecture

- **`SKILL.md`**: Frontmatter and operational guidelines. Defines section structure rules and modes (`draft`, `audit`, `restructure`, `section`).
- **`scripts/`**:
  - `readme_check.py`: Main checker script. Evaluates section order, badges, claim caveats, link formatting, table of contents rules, and active voice profile rules. Dynamically imports `rwlib` from `skills/rabbit-writes/scripts`.
  - `corpus_summary.json`: Aggregated metrics measured from 100 trending GitHub repositories (checked against `docs/readme-analysis/` by `${CLAUDE_PLUGIN_ROOT}/scripts/validate.py`).
- **`references/`**:
  - `patterns.md`: Statistical findings and catalog of measured README patterns.
  - `checklist.md`: Step-by-step checklist for auditing README files.
- **`tests/`**: Unit test suite verifying structural ordering, link/claim verification, license checks, corpus summary consistency, and voice profile integration.

## Conventions & Gotchas

- **Structural Section Order**: Pitch (first 2 sentences) → Fastest path to running it (Installation) → Depth → Community mechanics → License.
- **Corpus Summary Invariant**: `corpus_summary.json`, produced from the research aggregate by `scripts/readme-research/05_export_corpus_summary.py`, carries a `measured_at` date derived from the latest `pushed_at` timestamp in the sample rather than from the clock, so rerunning the aggregation over the same committed data does not move it. `${CLAUDE_PLUGIN_ROOT}/scripts/validate.py` verifies `corpus_summary.json` against `docs/readme-analysis/` when present, and `readme_check.py` quotes it: "corpus comparison (100 trending repos, 2026-08-10)".
- **`rwlib` Integration**: `readme_check.py` resolves `rwlib` relative to its file path (`skills/rabbit-writes/scripts`), running craft and voice checks without requiring `scan.py` directly.
- **Link Conventions**: Inline Markdown `[text](url)` is used (96.8% corpus usage). Avoid reference-style links or raw bare URLs.
- **`SCAN_PATH` drift**: `validate.py` string-matches `readme_check.py`'s `SCAN_PATH` literal. Change both together, or the check degrades to a note instead of a failure. `readme_check.py` also resolves `rwlib` from that same literal, so the two cannot end up pointing at different checkouts.
- **The corpus research scripts keep their own table patterns and sentence splitter, deliberately.** Every committed `stats.json` was measured with those, so swapping in the engine's copies would silently move a published number. The comments at `TABLE_ROW_RE` in `03_analyze_readme.py` say so.
- **Corpus data regenerates**: `cd scripts/readme-research && python3 03_analyze_readme.py --batch && python3 04_aggregate.py && python3 05_export_corpus_summary.py`. Step 03 overwrites `docs/readme-analysis/02_all_stats.json`, so a batch that finds no READMEs empties it. Step 05 is not optional: without it the checker keeps comparing against the old numbers.
