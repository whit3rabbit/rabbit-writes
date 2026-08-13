---
name: voice-setup
description: Build, measure, edit, or switch a personal writing voice profile for the rabbit-writes plugin. Use when the user wants to teach the system how they write, create their own writing style, set up or replace a voice, capture their tone, change whose voice is active, blend two voices, or convert their writing samples into a reusable style profile. Also use when a draft "doesn't sound like me" and the saved profile needs correcting.
license: MIT
metadata:
  version: "0.1.0"
---

# Voice setup

Turn one person's way of writing into two files a machine can apply:

- `voices/<name>.md`, the profile the model reads. Structure, mechanics, tone, register, refusals.
- `voices/<name>.rules.json`, the subset a regex can decide. Enforced by `scan.py` at whatever priority the profile sets.

Both live in `${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/voices/`. They are plain text under version control, so a voice is editable, diffable, and shareable.

**Paths.** `${CLAUDE_PLUGIN_ROOT}/skills/` means the directory holding this skill and its siblings (`rabbit-writes`, `voice-setup`, `readme-writing`). Claude Code expands the variable. On a host that doesn't, such as Codex, resolve it that way by hand.

## The principle

> Taste is boundaries.

A voice is mostly refusals. What a person will not write is specific, checkable, and rare, which is what makes it a fingerprint. What they say they like is usually generic and describes half the writers alive.

So weight everything here toward the **Hard nos**. If the interview runs short, cut from Structure and Tone. Never cut from Hard nos.

Two other rules govern the whole process:

**Do not write general writing advice into a profile.** "Avoid passive voice", "cut filler", "be concrete" apply to everyone and already live in the `rabbit-writes` engine, under `references/`. The test: *would this rule be wrong for a different person?* If yes, it is voice. If no, leave it out. A profile that restates the engine will drift out of sync with it.

**Measure before you believe.** People are unreliable narrators of their own prose. Someone who says "I write short" often averages 24 words a sentence. Where samples exist, the numbers win.

## Five ways in

Pick based on what the person has.

### 1. Taste Interviewer protocol (no samples, 5-10 minutes)

Adopt the role of a **Taste Interviewer**:
> You are a Taste Interviewer. Your job is to extract the DNA of how the author thinks, writes, and sees the world. You're not here to be polite, you're here to get to the truth. Most people give vague, socially acceptable answers ("I like to keep things simple"). Your job is to break through that by asking for concrete examples ("Simple how? Show me a sentence you'd write and one you'd refuse to write.") and calling out contradictions.

Keep it short. Nobody builds a voice profile by typing answers for an hour, and the person who quits at question 40 leaves you a worse profile than the one who answered 10 and stayed engaged.

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
python3 ${CLAUDE_PLUGIN_ROOT}/skills/voice-setup/scripts/measure_voice.py sample1.md sample2.md sample3.md
```

One command. It prints a per-sample table so an outlier is visible rather than averaged away, the aggregate with the spread between samples, the **Measured from samples** block ready to paste, a starter `mechanics` object with the count behind every line, and the distributions the aggregate hides. It exits 1 if any sample carries a P0. Add `--json` when you want to read the numbers programmatically rather than off the table.

The distributions are the block to read slowly. An average sentence length of 18 words describes two writers who sound nothing alike if one opens half her sentences with "But". Sentence openers, paragraph openers, connectors by group, which contractions they actually use, their hedges, their intensifiers, and how each sample ends verbatim. None of it goes in the rules file. It goes in the markdown, in their words, and it is most of what makes a profile describe a person rather than a punctuation policy.

Everything it suggests comes from those three or four documents and nothing else, so treat each line as a question rather than an answer. Someone who used no semicolon in four blog posts may still use them in email, and a profile that bans them because a script counted zero is wrong in a way its owner did not choose. The script's job is to make the question specific.

Then read the samples yourself for what no counter sees: paragraph openings, recurring phrases, how they transition, how they sign off, where they hedge, and what they refuse to write.

**Check the samples for contamination first.** `measure_voice.py` does this and stops on it, which is why it exits 1. If a sample carries P0 fingerprints (chatbot artifacts, cutoff disclaimers, hidden unicode), the person may have handed you AI-assisted writing. Say so plainly and ask. Never let a tell into a profile: it would then be replicated on purpose, forever. If they confirm a sample is assisted, exclude it, rerun, and record what you excluded under **Known contamination**.

For one sample at a time, or to see the full finding list behind a P0, `scan.py sample1.md --json` is still there and is what `measure_voice.py` runs underneath.

**Write the fingerprint while you have the samples open.** It is the one output that is a file rather than a paste, and the samples are the only thing that can produce it:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/voice-setup/scripts/measure_voice.py \
  sample1.md sample2.md sample3.md --name <voice> --write-fingerprint
```

That writes `voices/<voice>.fingerprint.json`, and `scan.py --voice <voice>` measures every later document against it and reports the distance at P2. It is what turns "does this sound like them" into a number with a calibrated range, and `references/voice.md` in the `rabbit-writes` skill has the reading. Two samples is the floor and it is thin: the band is a single number and cannot say how much the person varies. Three or four is where it starts to mean something. It refuses to write from a contaminated sample, for the same reason the P0 gate exists, one step further: a suggestion gets confirmed by a person and a fingerprint does not.

Add `--with-exemplars` to embed their own paragraphs for a later conversion to imitate. Ask first. It copies their prose into a file that travels with the plugin.

Combine sample extraction with 3 quick questions about **Hard refusals** (what they refuse to write), since samples show what was written, not what was rejected.

### 3. Adjust an existing profile

When a draft "doesn't sound like me," the profile is what missed, not the engine. Ask what specifically read wrong, find the rule that produced it, and change that rule. Then add the correction to the profile so the same miss does not repeat. Show the diff.

Do not re-run the full interview. A working profile plus one correction beats a fresh profile every time.

### 4. Blend

"70% whit3rabbit, 30% dana." Half of this is a command:

```bash
VOICES=${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/voices
python3 ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/scripts/rwlib/voices.py \
  --blend whit3rabbit dana --weight 0.7 --name whit3rabbit-dana \
  > "$VOICES/whit3rabbit-dana.rules.json"
```

Bans union, the stricter refusal wins whatever the weight says, and the lineage goes into the file as a `blend` key. Read the notes it prints on stderr: they name every place the two profiles wanted incompatible things, and those are the lines to confirm with whoever the blend is for.

The other half is yours. Interpolate the numeric dimensions (`0.7 × whit3rabbit.formality + 0.3 × dana.formality`) and take structural defaults from the higher-weighted profile, both by hand into a new `.md`. Nothing enforces those numbers, so no script can produce them. A blended rules file without the markdown enforces punctuation and describes nobody.

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

## Before you write anything, ask

Four questions, and none of them is guessable. Ask them together, in one turn.

1. **The name.** It is both filenames and the string that goes in `voices/ACTIVE`, so it is a slug rather than a title: `dana`, not `Dana's voice`.
2. **Where the files go.** Two answers, and they cost different things.
   - Inside the plugin, `${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/voices/`, is the only place `voices/ACTIVE` and a repo's `.rabbit-voice` resolve a name. A plugin update overwrites that directory.
   - Anywhere else survives the update, and nothing resolves it by name. Every scan needs `--voice-rules <path>`.
   Say both, recommend the plugin directory plus a copy somewhere safe, and let them pick.
3. **The tier.** `default_priority` is `P0` unless they say otherwise, meaning a hit is a defect on the same tier as a chatbot artifact. Some people want their preferences at `P1`. Ask, and say which you set.
4. **Whether to switch the active voice.** Never switch it without saying so, and never as a side effect of building a profile.

Add a fifth when there are samples: whether to embed exemplars, which copies their prose into a file that travels with the plugin.

## Writing the files

**Scaffold the pair.** One command, and it is not `cp`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/voice-setup/scripts/build_voice.py \
  --scaffold --name <name> --out <dir> --priority P0
```

`--out` defaults to the plugin's `voices/`, and the script prints what the chosen destination costs. It writes both files with the template's residue already stripped: every underscore-prefixed guidance key, and the `banned_regex` entry labeled "Example, delete this". That entry compiles, so a hand copy that keeps it enforces a rule nobody chose against the name of the person who did not choose it, and nothing downstream notices.

The `<angle bracket>` prompts in the markdown stay, because they are the form. `--check` fails while they are still there, which makes them a to-do list rather than a trap.

**Use their words.** A profile written in your prose describes a person who does not exist. Quote their answers where they were specific. If they said "no motivational-poster cadence," write that, not "vary paragraph length."

**Let a ban catch its own inflections.** The commonest authoring mistake is listing the singular and stopping, which leaves a rule that reads as enforced and is not. An entry can be a plain string or an object:

```json
"banned_words": ["piggyback", {"word": "synergy", "inflect": true}],
"banned_phrases": [{"phrase": "thought leader", "inflect": true}]
```

`inflect` adds the regular s/es/ed/ing forms, and on a phrase it varies one word at a time, so `thought leader` reaches `thought leaders` and `circle back` reaches `circling back`. It is opt-in per entry so a deliberately narrow ban stays narrow: banning `lowly` should not quietly ban `lowlying`. Irregulars (`run`/`ran`), consonant doubling (`ship`/`shipping`), and derivations (`leader`/`leadership`) are not covered. List those by hand.

**Move what a regex can decide into the JSON.** A banned word list belongs in `banned_words`. "Never attack the person" cannot be a regex and stays in the markdown. Rules of thumb:

| Goes in the JSON | Stays in the markdown |
|---|---|
| Banned words and phrases | Judgment about tone |
| Punctuation bans (em dash, semicolon, emoji) | When humor is appropriate |
| Paragraph and sentence length caps | How to deliver hard news |
| Date format | How much evidence to show |
| Named phrasings they refuse | What counts as a true warm-up |

**Give every regex an example.** A `banned_regex` entry takes an optional `example`, a line the pattern has to catch. It is the only way anything can prove the rule works, because a regex cannot be run backwards into text, and `--check` reports an entry without one as unproven rather than passing it:

```json
{"id": "war-metaphor", "label": "War metaphor on desk work",
 "rx": "(?i)\\b(war ?room|kill chain|in the trenches)",
 "example": "The team ran a war room for three days."}
```

With `max_allowed` set, the example needs one more hit than the cap, or the rule is allowed to stay quiet on it.

## Validate it

**Check the profile.** This is the step that decides whether any of the above worked:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/voice-setup/scripts/build_voice.py --check <name>
```

Pass a path instead of a name when the files went somewhere else. It runs two passes. The first is structural: parse, name, inheritance, regex compilation, mechanic vocabulary, register names, ban entries that name no term, and template residue in either file. The second puts every banned word, banned phrase, forbidden mechanic and regex example through `scan.py` and reports anything that produced no finding. A rule that does not fire is worse than no rule, because it reads as coverage.

Exit 1 on any failure. Read the `?` lines too: they are the rules nothing here can settle, and they stay the reader's job.

**Then test the inverse.** Run the scan on one of the person's real samples. If their own writing trips their own rules, one of the two is wrong. Usually the rule is too broad. Fix it and note what you changed. No script does this half: it needs their writing.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/scripts/scan.py sample1.md --voice <name>
```

**Validate the whole install,** when there is one:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py
```

Same structural checks over every installed profile, plus active-voice alignment and file pairing. Note the path: it sits at the repository root rather than under `${CLAUDE_PLUGIN_ROOT}/skills/`, so it only exists in a full-repo install and is absent when the three skills were copied in loose. `build_voice.py --check` is the one that ships with the skill, which is why it is the step above and not this one.

**Activate it:**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/voice-setup/scripts/build_voice.py --check <name> --activate
```

Activation is refused when the check fails, and when the profile lives outside the plugin's `voices/`, because `ACTIVE` holds a name and resolves it there. The script prints what it replaced. Never switch the active voice without saying so.

## Deliver the result

Show the person their profile and say plainly what you inferred versus what they told you. Inferred rules are the ones most likely to be wrong, and they are the ones worth correcting on day one.

Then offer a live test: have them give you something real to draft, run it through the new profile, and adjust from what they push back on. One round of that is worth more than another twenty interview questions.
