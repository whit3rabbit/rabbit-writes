# Packaging: what a clawhub bundle declares, and the note its scanner reads

Deep, cross-skill packaging detail moved out of the root `CLAUDE.md`. Needed only when touching `scripts/package_skills.py`, `scripts/publish_clawhub.py`, or a bundle's shipped metadata.

`OPENCLAW_ENV_DESCRIPTIONS` in `scripts/package_skills.py` is keyed by the env var constants imported from `rwlib.endpoint` and never restated, so the frontmatter of all six clawhub folders cannot drift from what the vendored code reads. A clawhub upload scan cross-checks declared metadata against the code, and an undeclared read is the flag. `check_packaging_metadata` in `scripts/validate.py` holds the two ends together against the source, and the folder gate compares the built `SKILL.md` against the endpoint module itself rather than against the dict, which would be comparing the build against itself.

The scanner-facing prose lives in `scripts/packaging/SECURITY_CLAWHUB.md`, emitted as every bundle's `SECURITY.md` with pinned phrases the gate requires. The reviewer preamble lands in `references/injection.md` and `references/patterns.md` at packaging time only, so the source files stay untouched.

`install_host.py` and `claude_hook.py` are neither one reachable from a scan, which is what `SECURITY_CLAWHUB.md` says to the clawhub scanner that will flag the write, and `check_packaging_metadata` pins `install_host.py` by name in that file.

Regenerate and verify with:

```bash
python3 scripts/package_skills.py       # package 6 isolated skill zips, and one clawhub folder each under dist/clawhub/
python3 scripts/test_package_skills.py  # extract each zip outside the repo and run what it ships
python3 scripts/publish_clawhub.py --dry-run   # human-run only, never in CI: rebuild each clawhub folder through its gate
```
