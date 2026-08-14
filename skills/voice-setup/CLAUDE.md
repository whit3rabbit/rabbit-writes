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

# Learn rules from a before/after editing diff pair
python3 skills/voice-setup/scripts/learn_edits.py before.md after.md
```

## Structure & Architecture

- **`SKILL.md`**: Frontmatter and workflows for voice creation (Taste Interviewer protocol, sample measurement, profile editing/blending).
- **`scripts/`**:
  - `measure_voice.py`: Analyzes sample text files for stylometric markers, distributions, sentence lengths, and checks samples for AI contamination (P0 fingerprints). Generates starter JSON mechanics and fingerprint files.
  - `build_voice.py`: Scaffolds voice templates, validates profile syntax and mechanical completeness via `rwlib.voice_check`, and activates specified voices in `skills/rabbit-writes/voices/ACTIVE`.
  - `learn_edits.py`: Extracts style diffs and banned phrases from before/after text revisions.
- **Target Profiles (`skills/rabbit-writes/voices/`)**:
  - `<name>.md`: Human-readable profile describing voice, structure, tone, and hard refusals.
  - `<name>.rules.json`: Machine-enforceable regex rules, banned words/phrases, and mechanics.
  - `<name>.fingerprint.json`: Stylometric baseline data for measuring distance.

## Conventions & Gotchas

- **P0 Contamination Check**: `measure_voice.py` checks input samples for P0 contamination (chatbot artifacts, cutoff disclaimers, hidden unicode). If detected, it exits with code 1 to prevent writing AI artifacts into a human voice profile.
- **Profile Pair Integrity**: A voice profile consists of both `.md` and `.rules.json` in `skills/rabbit-writes/voices/`. `build_voice.py --check` ensures no scaffold prompts (`<angle brackets>`) remain before allowing activation.
- **Voice Validation**: `build_voice.py --check` uses `rwlib.voice_check` from `skills/rabbit-writes/scripts`, sharing rule validation logic with `scripts/validate.py`.
