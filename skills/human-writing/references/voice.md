# Voice

> "Taste is boundaries." — Ruben Hassid, *I am just a text file*

Models do not lack taste. They lack *specific* taste. Given no constraints, they produce the statistical average, which is the same mechanism that generates every pattern in `patterns.md`. The fix is not a better adjective in a prompt. It is a durable file describing one person's refusals.

**Roughly 80% of a good voice profile is what the writer will not do.** Preferences are easy to state and weak in effect. Refusals are specific, checkable, and rare, which is what makes them a fingerprint.

---

## The precedence rule

A user-supplied writing sample or voice profile **outranks every style rule in this skill**, including the em-dash guidance in `patterns.md` §49.

If the sample uses em dashes, keep them at roughly the sample's frequency. If the writer says "stuff" and "things", keep that register; do not upgrade their vocabulary. If they open three paragraphs with "So," and it is characteristic, leave it.

Matching the author beats scrubbing the tell. Always.

---

## Using a sample

When the user pastes their own previous writing:

1. **Read the sample before touching the draft.** Note sentence-length pattern, contraction rate, paragraph openings, punctuation habits, recurring phrases, transitions, and level of polish.
2. **Check the sample for contamination.** If the sample itself carries P0 fingerprints, the writer may have pasted AI-assisted work. Say so, ask, and exclude those patterns from what you replicate. Never inherit a tell into a profile.
3. **Match the habits, do not just delete tells.** Regularizing a deliberate quirk is a failure even when it scores clean.
4. Run `python3 scripts/scan.py sample.md --json` to get the writer's actual burstiness, type-token ratio, sentence-length distribution, and em-dash rate. Those become the targets for the rewrite, replacing this skill's defaults.

---

## Building a profile

Ask the questions below and write the answers to a markdown file the user owns, outside this skill. One file, read first, portable across tools.

Inside the `rabbit-writes` plugin this is already built: profiles live in `../rabbit-writes/voices/`, `voices/ACTIVE` names the current one, and the `voice-setup` skill runs the interview and writes both files. Use that instead of hand-rolling. The rest of this section is the underlying method, and it applies wherever the profile ends up.

Weight the interview toward sections 3, 5, and 6. Those carry the signal.

### 1. Beliefs
- What do you believe about your subject that most people in your field do not?
- What argument do you find yourself making repeatedly?
- What do you refuse to pretend to be uncertain about?

### 2. Mechanics
- Contractions: always, never, or by register?
- Sentence length: what does your natural range look like?
- Do you use em dashes, semicolons, parentheses, the Oxford comma? Answer honestly rather than correctly.
- Paragraph length. Do you write one-sentence paragraphs?
- Headings: sentence case, title case, or none?
- First person: I, we, you, or absent?

### 3. Aesthetic crimes *(weight this heavily)*
- What words make you close a tab?
- What openings do you refuse to write?
- What endings? (Kickers? Summaries? Calls to action?)
- What formatting do you consider a tell of a bad writer?
- Name three phrases you would never use even if they were accurate.

### 4. Voice
- Who do you sound like when you are writing well?
- Who do you sound like when you are writing badly?
- How much do you hedge? What does hedging look like when you do it on purpose?
- Do you use humor? What kind, and where does it go?
- Profanity: yes, no, sparingly?

### 5. Structure
- Do you lead with the conclusion or build to it?
- Do you use examples, analogies, data, or anecdote as your default evidence?
- How do you transition? (Explicit connectives, white space, or nothing?)
- How long is a piece before you split it?

### 6. Hard nos *(weight this heavily)*
- What claims will you not make?
- What tone will you not adopt, even for a client?
- What would embarrass you to publish under your name?
- What would a reader who knows you notice immediately as not-you?

### 7. Red flags
- When a draft of yours goes wrong, how does it go wrong?
- What is your most common self-edit?
- What do you always cut on a second pass?

### Profile shape

```markdown
# Voice: <name>

## Dimensions
formality: 0.3        # 0 casual, 1 formal
confidence: 0.8       # 0 hedging, 1 assertive
warmth: 0.5           # 0 clinical, 1 friendly
energy: 0.4           # 0 measured, 1 enthusiastic
complexity: 0.6       # 0 simple, 1 sophisticated

## Measured from samples
avg_sentence_words: 17
sentence_length_sd: 9
burstiness: 0.68
type_token_ratio: 0.58
em_dashes_per_1000w: 4
contraction_rate: high

## Never
- <the aesthetic crimes, verbatim>
- <the hard nos>

## Always
- <the mechanics and structural defaults>

## Signature moves
- <the two or three things a reader would recognize>

## Authenticity markers
- acknowledges uncertainty: yes/no
- shows tradeoffs: yes/no
- uses specific numbers: yes/no
- names constraints: yes/no

## Known contamination
- <tells found in the source samples, excluded from replication>
```

---

## Blending

"70% technical, 30% casual" interpolates the numeric dimensions: `0.7 × technical.formality + 0.3 × casual.formality`. Vocabulary merges as the union of `Always` and the union of `Never` — the stricter refusal wins, because refusals are the load-bearing part. Structural defaults come from the highest-weighted profile. Record the lineage in the blended file.

---

## Authenticity markers

Sterile is as detectable as slop. But personality is genre-gated: apply this to essays, posts, opinion, and personal writing. For encyclopedic, technical, legal, or reference text, **neutral and plain is the correct human voice.** Do not inject opinions or first person there.

Where voice belongs, the marks of a real writer are:

- acknowledged uncertainty and unresolved tension
- stated tradeoffs, including ones that cut against the argument
- specific numbers, dates, and names
- named constraints ("we had two weeks and one engineer")
- an aside the writer could defend
- one thought left unfinished

**And the hard limit:** none of these may be *added* to text that did not have them. If the source has no `I`, the rewrite has no `I`. If the source has no anecdote, do not write one. You may subtract and sharpen. You may not add stance, personality, or fact.

That constraint is what separates restoring a voice from installing one.
