# Host integration: hooks, output styles, and pre-commit

Cross-cutting detail spanning `hooks/hooks.json` and `output-styles/` at the repo root, `skills/voice-setup/scripts/install_host.py`, and `.pre-commit-hooks.yaml`. Moved out of the root `CLAUDE.md`. Needed only when touching one of those surfaces.

## Where the host integration lives, and which install path gets which half

Two surfaces for one feature, and the split is decided by how the plugin was installed. `output-styles/` and `hooks/hooks.json` at the repository root are auto-discovered by Claude Code when the plugin is enabled, declared in no manifest, and they write nothing into anybody's files. `skills/voice-setup/scripts/install_host.py` is for the install paths with no plugin (a symlink into `~/.claude/skills/`, loose skills), where the only way to reach the same two features is to write into the user's own configuration. `check_plugin_hooks` in `scripts/validate.py` holds the two ends together by comparing the shipped `hooks.json` against `install_host.py`'s `HOOK_SPECS`, so a hook in one and not the other fails the build rather than giving a plugin user and a loose-skill user different behavior.

The uninstall story is entirely `~/.claude/rabbit-writes-host.json`: every path written with the hash it had, every hook command added, and the previous `outputStyle`, which is restored rather than deleted. A second `--install` reads that record forward, because recording the style the first install set as "what was there before" makes the uninstall a no-op that looks like it worked.

## Pre-commit hooks are tested from a stranger's working directory

`check_precommit_hooks` in `scripts/validate.py` runs `.pre-commit-hooks.yaml` from a directory that is not this repository, and nothing else in the tree is tested that way. Both suites run from this repository's root with this repository's files by default, which is why two hooks shipped broken: `readme-check` blocked a stranger's commit over this author's semicolon, and `rabbit-scan-voice` handed a plugin-relative `--voice-rules` path to a directory where it does not exist. The check parses `.pre-commit-hooks.yaml` with a regex, so a change to that file's shape makes it fail loudly rather than pass on an empty list.

`check_precommit_hooks` decides whether a hook applies somebody's style rules by reading its own `args` for a `--voice` prefix, which covers `--voice-rules` too. The `args:` guard above it pins that `parse_hooks` read the arguments at all, written against the `args:` key rather than a flag name because the flag has already changed once.

The default hooks apply no voice profile. `readme-check-voice` and `rabbit-scan-voice` are the opt-ins. `rabbit-scan-voice` says `--voice auto` rather than naming a path, so a committer's `.rabbit-voice` wins over the cloned plugin's `ACTIVE`. `resolve_plugin_paths` in `scripts/precommit.py` is no longer load-bearing for anything shipped, and stays for a hand-written `--voice-rules` pointing at a bundled profile. `--no-voice` on `readme_check.py` means "no style profile," not "no prose scan": structure, fingerprints, and craft all still run, because a pasted citation marker is evidence rather than taste.
