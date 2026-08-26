# rabbit-claude-md

Skill for auditing and restructuring CLAUDE.md and AGENTS.md files: named failure modes and a disposition plan instead of grades, with moves to `.claude/docs/` and per-module memory files.

## Commands

```bash
# Audit one file, or sweep a tree for every CLAUDE.md / AGENTS.md spelling
python3 skills/rabbit-claude-md/scripts/claude_check.py CLAUDE.md
python3 skills/rabbit-claude-md/scripts/claude_check.py . --json

# Gate: exit 1 on any unsuppressed P0 (safety band only, by design)
python3 skills/rabbit-claude-md/scripts/claude_check.py CLAUDE.md --check

# Run the skill test suite
python3 skills/rabbit-claude-md/tests/run.py
```

## Structure

- `SKILL.md`: three modes (`audit`, `improve`, `restructure`), the workflow, and the report-before-edit gate.
- `scripts/claude_check.py`: the mechanical checker. `claudemd-*` structure findings merged with the engine at register `docs`, one suppression pass over both.
- `scripts/_bootstrap.py`: engine lookup, copied from `rabbit-reads`.
- `references/`: `criteria.md` (failure modes, dispositions), `templates.md` (shapes per level), `restructure.md` (move playbook).

## Gotchas

- Every threshold lives in `LIMITS` in `claude_check.py`, imported by the tests. There is no CLAUDE.md corpus, so limits are pinned by fixtures, not calibrated.
- No `claudemd-*` id is P0. Blocking stays reserved for the engine's safety band.
- The judgment checks (derivable, wrong altitude, the removal test) live in `SKILL.md` and `references/criteria.md`, never in the script.
- The Script CLI section in `SKILL.md` restates the argparse definitions by hand. `check_claude_md` in `scripts/validate.py` reads this file's Commands block, not `SKILL.md`, so keep the two and the script's `add_argument` calls in sync when a flag changes.
