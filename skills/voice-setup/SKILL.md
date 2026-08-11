---
name: voice-setup
description: Build, measure, edit, or switch a personal writing voice profile for the rabbit-writes plugin. Use when the user wants to teach the system how they write, create their own writing style, set up or replace a voice, capture their tone, change whose voice is active, blend two voices, or convert their writing samples into a reusable style profile. Also use when a draft "doesn't sound like me" and the saved profile needs correcting.
license: MIT
metadata:
  version: "0.1.0"
---

# Voice setup

Turn one person's way of writing into two files a machine can apply:

- `voices/<name>.md` — the profile the model reads. Structure, mechanics, tone, register, refusals.
- `voices/<name>.rules.json` — the subset a regex can decide. Enforced by `scan.py` at whatever priority the profile sets.

Both live in `${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/voices/`. They are plain text under version control, so a voice is editable, diffable, and shareable.

**Paths.** `${CLAUDE_PLUGIN_ROOT}/skills/` means the directory holding this skill and its siblings (`rabbit-writes`, `voice-setup`, `readme-writing`). Claude Code expands the variable. On a host that doesn't, such as Codex, resolve it that way by hand.

## The principle

> Taste is boundaries.

A voice is mostly refusals. What a person will not write is specific, checkable, and rare, which is what makes it a fingerprint. What they say they like is usually generic and describes half the writers alive.

So weight everything here toward the **Hard nos**. If the interview runs short, cut from Structure and Tone. Never cut from Hard nos.

Two other rules govern the whole process:

**Do not write general writing advice into a profile.** "Avoid passive voice", "cut filler", "be concrete" apply to everyone and already live in the `rabbit-writes` engine, under `references/`. The test: *would this rule be wrong for a different person?* If yes, it is voice. If no, leave it out. A profile that restates the engine will drift out of sync with it.

**Measure before you believe.** People are unreliable narrators of their own prose. Someone who says "I write short" often averages 24 words a sentence. Where samples exist, the numbers win.

## Four ways in

Pick based on what the person has.

### 1. Taste Interviewer protocol (no samples, 5-10 minutes)

Adopt the role of a **Taste Interviewer**:
> You are a Taste Interviewer — your job is to extract the DNA of how the author thinks, writes, and sees the world. You’re not here to be polite; you’re here to get to the truth. Most people give vague, socially acceptable answers ("I like to keep things simple"). Your job is to break through that by asking for concrete examples ("Simple how? Show me a sentence you'd write and one you'd refuse to write.") and calling out contradictions.

**CRITICAL RULE: Never conduct a lengthy 100-question interview.** Users should never have to spend hours typing answers by keyboard.

Keep the interview to **10 high-signal questions max** covering the 7 core categories, asked in 2 quick batches of 5:

**Batch 1: Mechanics, Aesthetics & JSON Rules**
1. **Beliefs & Contrarian Takes**: What do you believe about your subject that most people in your field do not? What conventional wisdom do you reject?
2. **Punctuation Mechanics**: Do you ban em dashes, semicolons, emojis, or one-word period sentences ("No.")? (`mechanics`)
3. **Openers & Closers**: What are your exact signature sign-offs for informal emails vs official correspondence? (e.g., `"Thanks," + "-Name"` vs `"v/r"`) (`required_when`)
4. **Aesthetic Crimes (Banned Words)**: What specific words make you cringe or close a tab? (`banned_words`)
5. **Aesthetic Crimes (Banned Phrases)**: What cliché phrases or corporate filler (e.g. "circle back", "thought leader", "wild west") feel like nails on a chalkboard? (`banned_phrases`)

**Batch 2: Voice, Structure, Hard Nos & Anti-Overfitting**
6. **Voice & Personality**: What is your ratio of substance to warmth (e.g. 80/20)? How do you use humor or handle disagreement?
7. **Structural Preferences**: Do you lead with the conclusion (BLUF) or build to it? Max sentences per paragraph, and how do you handle lists/headers?
8. **Hard Nos**: What claims, tone, or formatting would embarrass you to publish under your name? What lines will you never cross?
9. **Red Flags**: What makes you immediately spot an AI imitation of your writing or distrust a piece of content?
10. **What Matters Most**: If you could keep only three rules, what are your #1 belief, #1 signature pattern, and #1 absolute refusal?

**Interview Rules:**
- Ask in 2 concise batches (or 1 question at a time if the user prefers).
- Push back on vague answers: *"Simple how? Give me a sentence you've written that captures this."*
- Call out contradictions when earlier and later answers clash.

### 2. From samples (recommended & fastest)

Point to 3 or 4 pieces written by the author (e.g. Substack posts like [Ruben Substack](https://ruben.substack.com/p/i-am-just-a-text-file), articles, past emails, or chat logs). This is the fastest method because it extracts mechanics automatically without manual typing:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/scripts/scan.py sample1.md --json
```

Read off `avg_sentence_words`, `sentence_sd`, `burstiness`, `mattr`, and `em_dashes_per_1k`, and write them into the profile's **Measured from samples** block. Then read the samples yourself for what the numbers miss: paragraph openings, contraction rate, recurring phrases, how they transition, how they sign off, where they hedge.

**Check the samples for contamination first.** If a sample carries P0 fingerprints (chatbot artifacts, cutoff disclaimers, hidden unicode), the person may have handed you AI-assisted writing. Say so plainly and ask. Never let a tell into a profile: it would then be replicated on purpose, forever. If they confirm a sample is assisted, exclude it and record what you excluded under **Known contamination**.

Combine sample extraction with 3 quick questions about **Hard refusals** (what they refuse to write), since samples show what was written, not what was rejected.

### 3. Adjust an existing profile

When a draft "doesn't sound like me," the profile is what missed, not the engine. Ask what specifically read wrong, find the rule that produced it, and change that rule. Then add the correction to the profile so the same miss does not repeat. Show the diff.

Do not re-run the full interview. A working profile plus one correction beats a fresh profile every time.

### 4. Blend

"70% whit3rabbit, 30% dana." Interpolate the numeric dimensions. Take the **union** of both Never lists, because the stricter refusal wins and refusals are load-bearing. Take structural defaults from the higher-weighted profile. Write the lineage into the new file so it can be traced later.

### 5. Extend

Blending mixes two whole people. The commoner ask is smaller: my voice, plus what this repo or this client does differently. That is `extends`, and it belongs in the rules file rather than in a new profile.

```json
{
  "voice": "whit3rabbit-acme",
  "extends": "whit3rabbit",
  "banned_words": ["synergy"],
  "mechanics": {"oxford_comma": "require"}
}
```

Bans union with the parent's. Mechanics merge key by key with the child winning, so a key the child never mentions keeps the parent's value and an override file stays four lines long. `scan.py` reports the lineage, so a report never claims a voice that is mostly somebody else's rules without saying so.

A child cannot quietly drop an inherited ban. That is deliberate: a house style that silently unbans a word is a house style nobody can rely on. To soften an inherited rule, give the child a `banned_regex` entry with the **same id**. Entries merge by id and the child's wins outright, so it can lower a priority, widen a `max_allowed`, or point the pattern somewhere narrower.

Reach for `extends` when a person's voice is unchanged and the context is not. Reach for a new profile when the person is.

---

## Writing the files

**Start from the templates.** `voices/TEMPLATE.md` and `voices/TEMPLATE.rules.json` carry the expected shape and inline guidance. Copy, fill, delete the guidance.

**Use their words.** A profile written in your prose describes a person who does not exist. Quote their answers where they were specific. If they said "no motivational-poster cadence," write that, not "vary paragraph length."

**Move what a regex can decide into the JSON.** A banned word list belongs in `banned_words`. "Never attack the person" cannot be a regex and stays in the markdown. Rules of thumb:

| Goes in the JSON | Stays in the markdown |
|---|---|
| Banned words and phrases | Judgment about tone |
| Punctuation bans (em dash, semicolon, emoji) | When humor is appropriate |
| Paragraph and sentence length caps | How to deliver hard news |
| Date format | How much evidence to show |
| Named phrasings they refuse | What counts as a true warm-up |

**Set the priority deliberately.** `default_priority` is `P0` by default, meaning a hit is a defect on the same tier as a chatbot artifact. Some people want their preferences at `P1` instead. Ask, and say which you set.

**Test the rules before saving.** Write a short paragraph that deliberately breaks four or five of them, run the scan, and confirm each one fires:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/scripts/scan.py /tmp/violations.md \
    --voice-rules ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/voices/<name>.rules.json
```

A rule that does not fire is worse than no rule, because it reads as coverage.

**Then test the inverse.** Run the scan on one of the person's real samples. If their own writing trips their own rules, one of the two is wrong. Usually the rule is too broad. Fix it and note what you changed.

**Validate the voice setup:**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py
```

Confirms JSON syntax, regex compilation, active voice alignment, and file pairing.

**Activate it:**

```bash
echo "<name>" > ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/voices/ACTIVE
```

Confirm what is now active and what it replaced. Never switch the active voice without saying so.

## Deliver the result

Show the person their profile and say plainly what you inferred versus what they told you. Inferred rules are the ones most likely to be wrong, and they are the ones worth correcting on day one.

Then offer a live test: have them give you something real to draft, run it through the new profile, and adjust from what they push back on. One round of that is worth more than another twenty interview questions.
