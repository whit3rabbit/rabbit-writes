# Restructure: moving content out of a CLAUDE.md

The playbook for the two moving dispositions, `move-to-docs` and `move-to-module`. Everything here happens after the audit report and after the user approves the plan, never before.

## Choose the target

- **Depth with a topic name** goes to `.claude/docs/<topic>.md`. Name by topic, never by date or session. The repository's own `docs/` is the project's documentation, written for its users, and agent context filed there litters it: `.claude/docs/` keeps the two audiences apart. Use the repo's `docs/` only when the content genuinely is project documentation, or when the user says that is where they keep this kind of context.
- **A fact scoped to one directory** goes to a CLAUDE.md inside that directory. Create the file if the module has none, and give it only what belongs to it (see `templates.md`).
- When several root gotchas share a topic, they move together into one docs file rather than one file each. A docs folder of six-line fragments is the bloat problem relocated.

## Move mechanics

1. **Move whole, then tighten in place.** Copy the content to the target first, verify nothing was dropped, then tighten the copy at the target. Tightening during the move is how facts silently disappear.
2. **Delete the source copy in the same change.** One home per fact. A move that leaves the original behind is a duplication, and the two copies start drifting immediately.
3. **Leave a one-line pointer** in the file the content left: what moved and a plain markdown link to where. The root file stays a map, and a map shows where the depth lives.
4. **Link, do not import, by default.** An `@path` import loads the target into every session, which re-spends the context the move just saved. Import only content that genuinely must always be loaded, and say why in the report when you do.
5. **Never move a safety-critical rule out of an always-loaded file.** A rule that prevents a destructive action protects nothing from inside a file nobody opened. If it is load-bearing every session, it stays in the root, tightened rather than moved.
6. **Preserve attribution and truth.** Moving is not rewriting: a claim stays a claim, a number stays its number. Rewording happens under the tighten disposition, where the diff shows it.

## Verify after moving

- Re-run `scripts/claude_check.py` on every CLAUDE.md touched. The moved content should no longer fire where it was, and the target module file should come back clean.
- Run every file that received moved content through the engine at register `docs`, the same scan the checker applies, so moved prose meets the same bar it was held to before the move.
- Confirm every fenced command still resolves from its new file's directory. A command that worked from the root can name a path that no longer resolves relative to a module file.
- Report the move map: each source line range, its target, and before-and-after non-blank line counts for every touched CLAUDE.md.
