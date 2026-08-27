# voice-setup

Skill for building, measuring, editing, and switching personal writing voice profiles used by the `rabbit-writes` engine.

## Commands

```bash
# Measure writing samples & generate steganographic/stylometric distributions
python3 skills/voice-setup/scripts/measure_voice.py sample1.md sample2.md sample3.md

# Measure samples and output JSON
python3 skills/voice-setup/scripts/measure_voice.py sample1.md sample2.md --json

# Measure samples, then print the interview they could not answer (route 3)
python3 skills/voice-setup/scripts/measure_voice.py sample1.md sample2.md --questions

# Measure samples and write a fingerprint file
python3 skills/voice-setup/scripts/measure_voice.py sample1.md sample2.md --name <voice> --write-fingerprint

# Scaffold a new voice profile
python3 skills/voice-setup/scripts/build_voice.py --scaffold --name <name>

# Check validity of a voice profile
python3 skills/voice-setup/scripts/build_voice.py --check <name>

# Activate a voice profile (sets skills/rabbit-writes/voices/ACTIVE)
python3 skills/voice-setup/scripts/build_voice.py --check <name> --activate

# Learn rules from a converted/edited diff pair
python3 skills/voice-setup/scripts/learn_edits.py converted.md edited.md

# Audit a finished profile against the writer's own corpus
python3 skills/voice-setup/scripts/audit_voice.py <voice> sample1.md sample2.md
```

## Structure & Architecture

- **`SKILL.md`**: Frontmatter and workflows for voice creation (Taste Interviewer protocol, sample measurement, profile editing/blending).
- **`scripts/`**:
  - `measure_voice.py`: Analyzes sample text files for stylometric markers, distributions, sentence lengths, and checks samples for AI contamination (P0 fingerprints). Generates starter JSON mechanics and fingerprint files.
  - `build_voice.py`: Scaffolds voice templates, validates profile syntax and mechanical completeness via `rwlib.voice_check`, and activates specified voices in `skills/rabbit-writes/voices/ACTIVE`.
  - `learn_edits.py`: Extracts style diffs and banned phrases from before/after text revisions.
  - `audit_voice.py`: Runs a finished profile over the writer's own corpus and reports which rules fire on the prose they came from (fire-backs, exit 1), per-sample fingerprint distance with a scale-vs-register reading, the one-register-or-two shape receipt (which needs no fingerprint and is printed without one), engine P0 tells as Known contamination candidates (the `safety` band excluded, since it is unsuppressible by design), and cap suggestions measured with the engine's own yardstick. Nothing is written. An out-of-range distance is read against the fingerprint's stored sample sizes first, because a corpus half the calibration size reads far whatever register it is in, and scale and register call for different fixes. It resolves the register before `stylometry.path_for`, off `registers.default_register()`, the same default `scan.py` passes: asking `path_for` with `None` skips the register-scoped file, so a profile carrying only `<name>.blog.fingerprint.json` used to report no fingerprint here while `scan.py` measured the same document against it. Every number a suggestion carries is measured with the engine's own yardstick, over the exempted copy `scan()` already built: `is_prose_block` for the paragraph cap (a six-item bullet list otherwise reads as one 24-sentence paragraph) and `stats["word_count"]` for a signature rate.
  - `thesaurus.json`: Versioned reach/overreach word families behind the measured thesaurus in `measure_voice.py`. Each family pairs a plain word with the dressed-up synonyms a sample set may reach past, and a family where the samples attest the plain word only becomes a `preferred_substitutions` proposal. Shape rules live in `thesaurus_check.py` beside it, with three consumers that must not disagree: `scripts/validate.py`, the research pipeline's `04_merge_accepted.py`, and this skill's own `tests/test_thesaurus.py`. A family edit requires a `version` bump. Families grow through `scripts/thesaurus-research/` at the repo root, not by hand-pasting generated entries. The dataset URLs, pinned hashes, and every generation threshold live in `scripts/thesaurus-research/thesaurus_io.py`, one home each.
- **Target Profiles (`skills/rabbit-writes/voices/`)**:
  - `<name>.md`: Human-readable profile describing voice, structure, tone, and hard refusals.
  - `<name>.rules.json`: Machine-enforceable regex rules, banned words/phrases, and mechanics.
  - `<name>.fingerprint.json`: Stylometric baseline data for measuring distance.

## Conventions & Gotchas

- **P0 Contamination Check**: `measure_voice.py` checks input samples for P0 contamination (chatbot artifacts, cutoff disclaimers, hidden unicode). If detected, it exits with code 1 to prevent writing AI artifacts into a human voice profile.
- **Profile Pair Integrity**: A voice profile consists of both `.md` and `.rules.json` in `skills/rabbit-writes/voices/`. `build_voice.py --check` ensures no scaffold prompts (`<angle brackets>`) remain before allowing activation.
- **Voice Validation**: `build_voice.py --check` uses `rwlib.voice_check` from `skills/rabbit-writes/scripts`, sharing rule validation logic with `scripts/validate.py`.
- **Tests**: `tests/run.py` is a zero-dependency runner over `tests/test_voice_setup.py`, `tests/test_thesaurus.py`, and `tests/test_audit_voice.py`. CI runs it, so a thesaurus family that breaks a proposal fails the build rather than a hand-run.
- **Audit exit semantics**: `audit_voice.py` exits 1 when a profile rule fires on the writer's own prose. `voice-distance` and `voice-oxford-comma` are exempt (a measurement, and an advisory no regex settles), and everything else counts whatever its priority: a stated rule the writer's own prose breaks is a disagreement even when it enforces at P2. Pass whole documents, not chunks, because per-document caps and the reliability floor dilute over split files.
- **A ban list entry is escaped whole**, so `word_regex` matches a multi-word `banned_words` entry fine. The only real difference between the two lists is that `phrase_regex` lets whitespace flex across a line break. The entry that never fires is one pasted in with its markdown still on it (`` `synergy` ``), because `apply_exemptions` blanks the code span before any ban is applied. That is the case `build_voice.py --check` reports as DEAD, and it is most of why the live-fire probe earns its cost.
- **A fresh scaffold fails its own `--check`, on purpose.** `build_voice.py --scaffold` strips the template's guidance keys and its `example-rule` entry, and deliberately leaves the `<angle bracket>` prompts in the markdown, because they are the form. The failing check is the to-do list, and `--activate` refuses until somebody fills it in.
- **Thesaurus candidates regenerate**: `python3 scripts/thesaurus-research/01_fetch_datasets.py` (network, one-shot), then `python3 scripts/thesaurus-research/02_generate_candidates.py` and `python3 scripts/thesaurus-research/03_corpus_evidence.py`. A human edits `status` fields in `docs/thesaurus-research/candidates.json`, and `python3 scripts/thesaurus-research/04_merge_accepted.py` writes the shipped file and bumps its version. Regeneration carries review forward, so rerunning 02 never loses an accepted or rejected mark.
