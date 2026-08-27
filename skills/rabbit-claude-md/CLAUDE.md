# rabbit-claude-md

Skill for auditing and restructuring CLAUDE.md and AGENTS.md files: named failure modes and a disposition plan instead of grades, with moves to `.claude/docs/` and per-module memory files.

## Commands

```bash
# Audit one file, or sweep a tree for every CLAUDE.md / AGENTS.md spelling (both families together)
python3 skills/rabbit-claude-md/scripts/claude_check.py CLAUDE.md
python3 skills/rabbit-claude-md/scripts/claude_check.py . --json

# Fold ~/.claude/CLAUDE.md and ~/.codex/AGENTS.md into the duplicate check, read-only
python3 skills/rabbit-claude-md/scripts/claude_check.py . --global

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
- **`check_claude_md` in the repo's own `scripts/validate.py` holds every `CLAUDE.md` file in the tree to the code it describes, and only in two ways.** A line carrying three or more backticked bare words must name registers from `registers.json` (or modes from its `_modes` block), and a `python3 <path>` line inside a fence must supply the positionals that script's own `add_argument` calls require. Both drifts were live once: one file named six registers, four of which did not exist, and another showed a script invocation missing a required path. A command whose script path does not resolve from the repo root is skipped rather than guessed at. It reads required-argument counts out of each script directly rather than from `precommit.py`'s `VALUE_FLAGS`, a hook's runtime allowlist that must not be steerable from a doc. `claude_check.py`'s own `claudemd-dead-path` finding overlaps in spirit (it also flags a fenced path that does not resolve) but is a separate, narrower check: it does not verify positional-argument counts or register names, so the two checkers can still disagree about a positional-count drift that only `scripts/validate.py`'s `check_claude_md` would catch.
- **The size check has two independent axes.** `claudemd-oversize` reads non-blank line count, `claudemd-char-budget` reads raw character count against the ~40,000-character ceiling commonly recommended for a memory file. Neither implies the other: a handful of very long lines can cross the character budget while staying well under the line-count bands, and terse short lines can do the reverse. `claudemd-import-cost` is a third, separate axis again: the file's own size on either measure can pass while what an `@import` pulls in transitively (bounded by `IMPORT_HOP_LIMIT` hops, cycle-safe) does not.
- **`map_coverage_note`, `harness_inventory_note`, and `git_currency_note` only run for the root memory file**, gated on `file_dir == repo_root` and the canonical `CLAUDE.md`/`AGENTS.md` basename, not a local override or a nested module's file. `git_currency_note` also needs a real git repository to say anything. The bare `.git` marker the other checks tolerate is not enough for it, so a Tree test fixture needs an actual `git init` and commit to exercise it.
- **`dual_harness_findings` runs once per sweep, not per file.** It compares every same-directory `CLAUDE.md`/`AGENTS.md` pair. Results get injected into each file's list after `check_claude_file` returns, then re-sorted rather than relying on the internal sort.
- A directory sweep dedupes the discovered file list by realpath before sorting, CLAUDE spellings ahead of AGENTS spellings. A symlinked pair is one report under the CLAUDE.md name, not the same content audited twice under two names.
