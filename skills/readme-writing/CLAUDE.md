# readme-writing

README auditing, drafting, restructuring, and section writing skill based on empirical analysis of 100 trending GitHub repositories.

## Commands

```bash
# Run unit tests
python3 skills/readme-writing/tests/run.py

# Pytest equivalent
pytest skills/readme-writing/tests/

# Audit or check a README.md file
python3 skills/readme-writing/scripts/readme_check.py path/to/README.md

# Audit with JSON payload
python3 skills/readme-writing/scripts/readme_check.py path/to/README.md --json

# Run as a gate (exit 1 on P0/P1 issues)
python3 skills/readme-writing/scripts/readme_check.py path/to/README.md --check

# Check README with explicit voice rules
python3 skills/readme-writing/scripts/readme_check.py path/to/README.md --voice-rules skills/rabbit-writes/voices/whit3rabbit.rules.json
```

## Structure & Architecture

- **`SKILL.md`**: Frontmatter and operational guidelines. Defines section structure rules and modes (`draft`, `audit`, `restructure`, `section`).
- **`scripts/`**:
  - `readme_check.py`: Main checker script. Evaluates section order, badges, claim caveats, link formatting, table of contents rules, and active voice profile rules. Dynamically imports `rwlib` from `skills/rabbit-writes/scripts`.
  - `corpus_summary.json`: Aggregated metrics measured from 100 trending GitHub repositories (checked against `docs/readme-analysis/` by `scripts/validate.py`).
- **`references/`**:
  - `patterns.md`: Statistical findings and catalog of measured README patterns.
  - `checklist.md`: Step-by-step checklist for auditing README files.
- **`tests/`**: Unit test suite verifying structural ordering, link/claim verification, license checks, corpus summary consistency, and voice profile integration.

## Conventions & Gotchas

- **Structural Section Order**: Pitch (first 2 sentences) → Fastest path to running it (Installation) → Depth → Community mechanics → License.
- **Corpus Summary Invariant**: `corpus_summary.json` carries a `measured_at` date derived from the latest `pushed_at` timestamp in the sample. `scripts/validate.py` verifies `corpus_summary.json` against `docs/readme-analysis/` when present.
- **`rwlib` Integration**: `readme_check.py` resolves `rwlib` relative to its file path (`skills/rabbit-writes/scripts`), running craft and voice checks without requiring `scan.py` directly.
- **Link Conventions**: Inline Markdown `[text](url)` is used (96.8% corpus usage). Avoid reference-style links or raw bare URLs.
