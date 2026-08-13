# rabbit-writes

Core prose engine skill for `rabbit-writes`. Provides detector audits, in-place file deslopping, voice conversions, and drafting.

## Commands

```bash
# Run unit & engine tests
python3 skills/rabbit-writes/tests/run.py

# Run specific tests with filter
python3 skills/rabbit-writes/tests/run.py -k <substring>

# Pytest equivalent (from anywhere)
pytest skills/rabbit-writes/tests/

# Scan prose / audit file
python3 skills/rabbit-writes/scripts/scan.py <file>

# Scan with voice profile rules
python3 skills/rabbit-writes/scripts/scan.py <file> --voice-rules skills/rabbit-writes/voices/whit3rabbit.rules.json

# Check mode gate (exit code 1 on errors)
python3 skills/rabbit-writes/scripts/scan.py <file> --check

# Post-edit integrity check (facts, dates, quotes, numbers)
python3 skills/rabbit-writes/scripts/verify.py <file>

# Measure voice conversion delta between two files
python3 skills/rabbit-writes/scripts/attain.py <source> <target> --voice whit3rabbit
```

## Structure & Architecture

- **`SKILL.md`**: Frontmatter definition and operational guidelines. Defines guardrails and four modes (`detect`, `deslop`, `voice`, `draft`). Mode table and guardrails are pinned by repo validator (`scripts/validate.py`).
- **`PROOF.md`**: Measured self-scan numbers and voice-band calibration tables.
- **`scripts/`**:
  - `scan.py`: Main CLI tool and engine scanner.
  - `verify.py`: Integrity and fact-preservation checker.
  - `attain.py`: CLI tool measuring conversion progress and stylometric distance.
  - `lexicon.json`: Machine-writing pattern rules.
  - `registers.json`: Tolerance matrix across registers (`formal`, `docs`, `technical`, `casual`, `narrative`, `internal`).
  - `rwlib/`: Shared engine library containing stylometry, injection checks, fixes, suppression, fact checking, voice resolution, SARIF export, and docx text extraction.
- **`voices/`**: Holds active voice marker (`ACTIVE`), voice markdown profiles (`<name>.md`), rule definitions (`<name>.rules.json`), and fingerprints (`<name>.fingerprint.json`). Includes `TEMPLATE` files.
- **`references/`**: Technical and craft reference documentation (`craft.md`, `false-positives.md`, `injection.md`, `patterns.md`, `context.md`, `voice.md`, `checklist.md`).
- **`tests/`**: Suite of 20+ test files verifying engine logic, fixes, stylometry, injection rules, and invariants.

## Conventions & Gotchas

- **Importing `rwlib`**: Scripts insert `skills/rabbit-writes/scripts` into `sys.path`. Import via `from rwlib import ...`.
- **ASCII Only for Engine Source**: `test_every_invisible_logic_source_is_escape_only` enforces pure ASCII in engine `.py` files (except `markdown.py`). Write invisible unicode characters as hex/unicode escapes (`\u00a0`), never raw literals.
- **`verify.py` Blast Radius**: `verify.validate(...)["ok"]` determines whether `scan.py --apply-safe --write` writes output to disk. False positives silently disable the fixer.
- **Safety Band**: `safety` band findings (concealed text, prompt injection) are never fixable or suppressible. A P0 halts rewrites.
- **Mode Contract Integrity**: `validate.py` pins `SKILL.md` wording. Editing pinned lines in `SKILL.md` will fail `scripts/validate.py`.
