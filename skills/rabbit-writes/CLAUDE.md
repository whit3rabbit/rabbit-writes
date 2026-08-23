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

# Scan with auto-detected register profile
python3 skills/rabbit-writes/scripts/scan.py <file> --profile auto

# Apply mechanical safe fixes in-place
python3 skills/rabbit-writes/scripts/scan.py <file> --apply-safe --write

# Show what a model would be sent, one passage per finding, and send nothing
python3 skills/rabbit-writes/scripts/scan.py <file> --apply-model --model-plan

# Rewrite those passages through a small OpenAI-compatible model, gating each reply
python3 skills/rabbit-writes/scripts/scan.py <file> --apply-model --model-endpoint http://127.0.0.1:8080/v1 --model-name qwen3-1.7b --write

# Output findings in SARIF 2.1.0 format
python3 skills/rabbit-writes/scripts/scan.py <file> --sarif

# Post-edit integrity check (facts, dates, quotes, numbers). Two files: it
# compares a rewrite against what it was rewritten from.
python3 skills/rabbit-writes/scripts/verify.py <original> <rewritten>

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
  - `registers.json`: The tolerance matrix, and the only home for the register names. `references/context.md` renders its table from this file, `scan.py` derives its skip and relax sets from it, and restating the list here is how this line came to name four registers that do not exist.
  - `rwlib/`: Shared engine library containing stylometry, injection checks, fixes, suppression, fact checking, voice resolution, SARIF export, docx text extraction, and the model-backed rewriting pair (`endpoint.py`, `rewrite.py`).
- **`voices/`**: Holds active voice marker (`ACTIVE`), voice markdown profiles (`<name>.md`), rule definitions (`<name>.rules.json`), and fingerprints (`<name>.fingerprint.json`). Includes `TEMPLATE` files.
- **`references/`**: Technical and craft reference documentation (`craft.md`, `false-positives.md`, `injection.md`, `patterns.md`, `context.md`, `voice.md`, `checklist.md`).
- **`references/forms/`**: One file per document form. Each names the register it routes to and gives that form's slots, length bands, and tells. A form file supplies slots and never fills them: `check_form_files` in `scripts/validate.py` enforces that by requiring every quoted phrase to sit under `## Tells`, where the heading already says the phrases in it are the ones to avoid.
- **`tests/`**: Suite of 20+ test files verifying engine logic, fixes, stylometry, injection rules, and invariants.

## Conventions & Gotchas

- **Importing `rwlib`**: Scripts insert `skills/rabbit-writes/scripts` into `sys.path`. Import via `from rwlib import ...`.
- **ASCII Only for Engine Source**: `test_every_invisible_logic_source_is_escape_only` enforces pure ASCII in engine `.py` files (except `markdown.py`). Write invisible unicode characters as hex/unicode escapes (`\u00a0`), never raw literals.
- **`verify.py` Blast Radius**: `verify.validate(...)["ok"]` determines whether `scan.py --apply-safe --write` writes output to disk. False positives silently disable the fixer.
- **Safety Band**: `safety` band findings (concealed text, prompt injection) are never fixable or suppressible. A P0 halts rewrites, and `rewrite.run` refuses *before the first request* rather than after planning, because a rewriter is exactly what a concealed instruction is written for.
- **`rwlib` never imports `scan.py` or `verify.py`**: `scan.py` imports `verify` lazily and `verify` imports `rwlib.facts`, so a module down here reaching back up closes the loop. `rewrite.run` takes `scan_fn`, `validate_fn`, and the burstiness floor as arguments for this reason.
- **Mode Contract Integrity**: `validate.py` pins `SKILL.md` wording. Editing pinned lines in `SKILL.md` will fail `scripts/validate.py`.
