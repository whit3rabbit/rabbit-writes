---
name: rabbit-writes
description: Draft or edit prose in the user's own writing voice, using their saved voice profile plus AI-pattern removal. Use whenever the user will send or publish the text as themselves — emails, Slack and chat messages, reports, incident writeups, reviews, proposals, documentation, or personal correspondence. Also use when the user asks to write in their voice, match their style, sound like themselves, swap or change the active voice, or check whether a draft sounds like them. Do not use for third-party content the user is not authoring in their own voice.
license: MIT
metadata:
  version: "1.0.0"
---

# Rabbit writes

Draft and edit in a specific person's voice. Two layers, and the order matters:

1. **The voice profile** is the person. It decides how the prose sounds and which rules are absolute.
2. **The `human-writing` engine** is everything true of good writing regardless of who is writing. It fills every gap the profile leaves.

The profile wins every conflict. The engine's guardrails are the one exception, and they run the other way. See Precedence below.

## Load the active voice first

Before drafting or editing anything, do this:

1. Read `voices/ACTIVE`. It contains one line: the name of the active voice.
2. Read `voices/<name>.md`. That is the voice profile, and it is now the authority on style.
3. Note that `voices/<name>.rules.json` exists. It holds the mechanically checkable subset for `scan.py`.

If `voices/ACTIVE` is missing or names a profile that does not exist, say so and offer to run the `voice-setup` skill. Do not silently fall back to a different person's voice. Writing in the wrong person's register is worse than asking.

Shipped with `whit3rabbit` as the active voice. Anyone can replace it. See Swapping voices below.

## Precedence

| Layer | Beats | Example |
|---|---|---|
| Engine **guardrails** | everything | A profile cannot authorize inventing a fact, adding an opinion the source lacked, or rewriting inside a code block |
| **Voice profile** | engine style rules | A profile that uses em dashes keeps them at its own rate, whatever `patterns.md` §49 says |
| Engine **register profile** | nothing above it | `--profile casual` relaxes general rules; it never relaxes a voice rule |
| Engine **pattern catalog** | nothing above it | The default when the profile is silent |

The guardrails constrain the editor, not the voice, which is why a voice preference cannot override them. They are in `${CLAUDE_PLUGIN_ROOT}/skills/human-writing/SKILL.md` under "Guardrails on you, the editor."

The single most important one: **you may subtract and sharpen, you may not add.** If the source has no first person, the rewrite has no first person. Matching a voice means matching what the writer does, not installing what a "human voice" is supposed to look like.

## Workflow

**1. Load the voice.** As above. Hold the profile's Hard nos in mind. They are the part a reader would notice first.

**2. Set the register.** Infer it, or take it from the user: `blog`, `linkedin`, `technical-blog`, `investor-email`, `docs`, `casual`. Most profiles also define their own register axis (on the clock versus off, formal versus casual). The profile's version wins when both apply.

**3. Draft or edit.** Apply the profile. For anything it does not cover, use `${CLAUDE_PLUGIN_ROOT}/skills/human-writing/references/patterns.md` and `references/craft.md`.

**4. Scan.**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/human-writing/scripts/scan.py draft.md \
    --voice-rules ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/voices/<name>.rules.json
```

Findings come back in three bands, reported separately:

- **voice** — this person's rules. A hit is a defect, not a suggestion.
- **fingerprint** — evidence the text came out of a chat tool.
- **craft** — general writing problems. Real, but never evidence about who wrote something.

**5. Check.** Run `${CLAUDE_PLUGIN_ROOT}/skills/human-writing/references/checklist.md`, then the profile's own final check. Every item is yes or no. Fix every no once, re-check once, stop.

**6. Verify a file edit.**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/human-writing/scripts/verify.py original.md rewritten.md
```

## Swapping voices

The voice is data, not code. Nothing in this skill or in `human-writing` knows anything about a particular person.

**Switch to a voice already in the folder:**

```bash
echo "dana" > ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/voices/ACTIVE
```

**Create a new voice.** Invoke the `voice-setup` skill. It runs a refusal-first interview, writes `voices/<name>.md` and `voices/<name>.rules.json`, and offers to make it active. Roughly 80% of a working profile is what the person refuses to do, so that is where the interview spends its time.

**Derive a voice from writing samples.** Ask for three or four pieces the person wrote themselves, then invoke `voice-setup` in sample mode. It measures sentence-length distribution, burstiness, contraction rate, and punctuation habits from the real text rather than from what the person believes about their writing. Those two answers differ more often than not.

**Blend two voices.** "70% whit3rabbit, 30% dana." Interpolate the numeric dimensions, take the union of both `Never` lists, and use the higher-weighted profile's structural defaults. Refusals are the load-bearing part, so the stricter refusal always wins. Record the lineage in the new file.

**Edit a voice by hand.** The profiles are markdown and JSON. Change them and commit. That is the whole update mechanism.

### One voice, several people

A team can keep several profiles in `voices/` and switch per task. A per-project override works too: if the working directory contains `.rabbit-voice`, read the voice name from there instead of from `voices/ACTIVE`. That lets a repo pin its own house voice without touching the plugin.

### What belongs in a profile, and what does not

**In the profile:** the person's structure habits, mechanics, punctuation, tone, register rules, hard nos, humor, openers and closers, and their own final check.

**Not in the profile:** anything true of good writing generally. Do not copy "avoid passive voice" or "cut filler" into a voice file. Those live in the engine and apply to everyone. A profile that restates the engine is a profile that will drift out of sync with it.

The test: would this rule be wrong for a different person? If yes, it is voice. If no, it belongs in `human-writing`.

## When there is no profile

Infer the register from the draft and impose nothing. Apply the engine and its guardrails, keep the writer's existing habits, and offer to build a profile. A generic "human voice" is its own detectable register, and installing one is the failure this skill exists to prevent.
