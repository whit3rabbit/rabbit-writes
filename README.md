# rabbit-writes

Write and edit in **your** voice, not a chatbot's.

Most "humanizer" tools do half the job. They strip the AI tells and hand back prose that reads like a different machine: staccato fragments, performed candor, fake first person. A new fingerprint, not the absence of one.

This one separates the two halves. A **voice profile** says how *you* write. An **engine** handles everything true of good writing regardless of who is writing. The profile wins every conflict. The engine fills every gap.

The voice is data. Swap it, edit it, blend two of them, or write your own from a template. Nothing in the engine knows anything about any particular person.

## Install

```
/plugin marketplace add https://github.com/whit3rabbit/rabbit-writes
/plugin install rabbit-writes
```

Or clone the skills straight in:

```bash
git clone https://github.com/whit3rabbit/rabbit-writes
cp -r rabbit-writes/skills/* ~/.claude/skills/
```

Python 3.8+ with the standard library, and only if you want the scripts. Nothing to build.

## First thing to do: make it sound like you

The plugin ships with an example voice profile (`whit3rabbit`). It is not yours.

To write in your own voice, create your own voice profile and activate it:

```
skills/rabbit-writes/voices/<you>.md            the profile the model reads
skills/rabbit-writes/voices/<you>.rules.json    the part a regex can enforce
```

### Three ways to create your voice profile

#### 1. From Writing Samples (Fastest & Recommended)
Provide 3–4 pieces of your actual writing — such as Substack posts (e.g. [Ruben Substack](https://ruben.substack.com/p/i-am-just-a-text-file)), articles, emails, or chat logs:

```
Create a voice profile from my writing samples: [paste samples or file paths]
```

`voice-setup` measures your sentence length distribution, burstiness, contraction rate, and transition habits automatically. You don't have to spend hours typing answers.

#### 2. Fast-Track 5-Minute Interview
If you don't have samples ready:

```
Set up my writing voice
```

`voice-setup` runs a fast 5–10 question interview focused directly on boundaries: your banned words, banned phrases, punctuation bans, and signature closers.

#### 3. Manual Template Editing
Copy the template files and edit them directly:

```bash
cp skills/rabbit-writes/voices/TEMPLATE.md skills/rabbit-writes/voices/<you>.md
cp skills/rabbit-writes/voices/TEMPLATE.rules.json skills/rabbit-writes/voices/<you>.rules.json
```

Fill in your rules, then validate and activate:

```bash
python3 scripts/validate.py
echo "<you>" > skills/rabbit-writes/voices/ACTIVE
```

Taste is boundaries: roughly 80% of a working profile is **refusals** (what you will never write). What you say you like usually describes half the writers alive; what you refuse to put your name on is your fingerprint.

## What's in it

Three skills.

**`rabbit-writes`** — the writing skill. Loads the active voice, drafts or edits in it, delegates detection to the engine. This is the one that fires when you ask for an email.

**`human-writing`** — the engine. 63 patterns in a priority-tiered catalog, a false-positive discipline, register profiles, Orwell and Simplified Technical English as a positive craft layer, a 32-item self-check, and two scripts. Voice-agnostic by design.

**`voice-setup`** — builds, measures, edits, blends, and switches voice profiles.

```
rabbit-writes/
  .claude-plugin/           plugin + marketplace manifests
  scripts/validate.py       repo validator
  skills/
    rabbit-writes/
      SKILL.md
      voices/
        ACTIVE                 one line: whose voice is live
        whit3rabbit.md         shipped example profile
        whit3rabbit.rules.json its enforceable subset
        TEMPLATE.md            copy this to add your own
        TEMPLATE.rules.json
    human-writing/
      SKILL.md
      references/           patterns, false-positives, context, voice, craft, checklist
      scripts/              scan.py, verify.py, lexicon.json
      tests/                calibration fixtures and regression tests
      PROOF.md              the engine scanned with its own scanner
    voice-setup/
      SKILL.md
```

## Three bands, never conflated

`scan.py` reports findings in three groups and refuses to merge them into one score.

| Band | Means | Example |
|---|---|---|
| **voice** | your own rules | a semicolon, "circle back", an em dash |
| **fingerprint** | evidence the text came out of a chat tool | `utm_source=chatgpt.com`, a zero-width space, "I hope this helps!" |
| **craft** | bad writing regardless of author | `utilize`, a hedge stack, uniform paragraphs |

Keeping them apart is the point. Presenting a wordiness fix as evidence about who wrote something is the most common failure in this category of tool, and it is the one that gets people accused of things.

```bash
python3 skills/human-writing/scripts/scan.py draft.md \
    --voice-rules skills/rabbit-writes/voices/whit3rabbit.rules.json
```

A register profile (`--profile casual`, `--profile docs`) relaxes the general rules. It never relaxes a voice rule. Lowercase and loose punctuation are fine off the clock. "Circle back" never is.

## What it will not do

- Tell you whether AI wrote something. Independent audits put commercial detector false-positive rates above 60% on non-native English writers (Liang et al., Stanford, *Patterns* 2023) and open-source misclassification above 70% (Jabarian & Imas, BFI 2025-116). Signals, not proof, and never a basis for an academic-integrity or hiring decision.
- Add a fact, name, number, date, or citation that was not in your source.
- Add first person, an anecdote, or an opinion your draft did not have.
- Add an em dash during a rewrite.
- Rewrite anything inside code, tables, block quotes, frontmatter, or attributed quotations.
- Follow instructions embedded in the text it is editing.

You may subtract and sharpen. You may not add. That constraint is what separates restoring a voice from installing one.

## Verify a rewrite

```bash
python3 skills/human-writing/scripts/verify.py original.md rewritten.md
```

Exits non-zero if the rewrite altered a code block, frontmatter, a table row, a block quote, inline code, a URL, a file path, or the heading structure, or if it added em dashes or ended with more tells than it started with. Edit mode writes to files, so a broken promise there would otherwise be silent.

## Tests

```bash
python3 scripts/validate.py                          # manifests, skills, voices, cross-refs
python3 skills/human-writing/tests/test_scan.py      # calibration and regression
```

The calibration fixtures assert that known slop scores high, known human prose scores zero, and a third sample with no flagged vocabulary at all still trips the uniformity detector because every sentence is the same length. Vocabulary and rhythm are independent axes, and that third fixture is the one that matters.

`skills/human-writing/PROOF.md` publishes the engine scanned by its own scanner, including the unflattering rows.

## Where this came from

The engine is merged from seven open-source humanizer skills. Each was best at exactly one thing:

- [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop) — the portability test, minimum effective edit, detect-without-scoring
- [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) — the fingerprint/craft split, register tolerance matrix, severity tiers, "never inject these", the preservation validator, honesty about detector accuracy
- [blader/humanizer](https://github.com/blader/humanizer) — the Wikipedia pattern port, "what not to flag", "signs of human writing", sample-outranks-the-rules
- [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) — false agency, vague declaratives, meta-joiners
- [brandonwise/humanizer](https://github.com/brandonwise/humanizer) — stylometric ranges, hidden-unicode detection, reliability gating
- [angelarose210/ghostwriter](https://github.com/angelarose210/ghostwriter) — voice profile as a portable artifact, contaminated-sample handling, weighted blending
- [tamdogood/orwell-writing](https://github.com/tamdogood/builder-essential-skills/tree/main/skills/orwell-writing) — Orwell's six rules and the ASD-STE100 baseline

Plus three sources that shaped the architecture:

- [testdouble/han, human-readable-output-standard](https://github.com/testdouble/han/blob/main/docs/research/human-readable-output-standard.md) — layered instruction delivery, the audience frame over readability formulas, behaviorally anchored self-checks
- [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) — the underlying catalog and the mechanism behind it
- [Ruben Hassid, *I am just a text file*](https://ruben.substack.com/p/i-am-just-a-text-file) — taste is boundaries; a voice profile is mostly refusals

`docs/COMPARISON.md` is the full writeup: what each repo does, tables of what they share and where they diverge, and the reasoning behind every borrow.

## Contributing a voice

Voices are welcome as pull requests. Include the `.md` and the `.rules.json`, keep general writing advice out of both, and leave `voices/ACTIVE` alone.

MIT.
