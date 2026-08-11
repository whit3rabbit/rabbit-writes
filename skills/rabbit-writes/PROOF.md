# Self-scan

A tool that flags "delve" in your draft should survive its own pass. This is the result of running `scripts/scan.py` on this plugin's own files, including the unflattering rows.

Reproduce in one command, no dependencies:

```bash
for f in SKILL.md PROOF.md references/*.md; do echo "== $f"; python3 scripts/scan.py "$f"; done
```

## Result (v0.1.0, measured 10 August 2026)

| File | Words | P0 | P1 | P2 | Burstiness | MATTR | Em dash / 1k |
|---|---:|---:|---:|---:|---:|---:|---:|
| `SKILL.md` | 2,186 | 0 | 0 | 0 | 0.69 | 0.74 | 0.0 |
| `PROOF.md` | 829 | 0 | 0 | 0 | 0.59 | 0.72 | 0.0 |
| `references/patterns.md` | 4,650 | 0 | **14** | **4** | 0.88 | 0.76 | 2.6 |
| `references/false-positives.md` | 811 | 0 | 0 | 0 | 0.69 | 0.81 | 1.2 |
| `references/context.md` | 417 | 0 | 0 | 0 | 0.67 | 0.84 | 0.0 |
| `references/voice.md` | 914 | 0 | 0 | 0 | 0.72 | 0.74 | 2.2 |
| `references/craft.md` | 1,102 | 0 | 0 | **7** | 0.67 | 0.77 | 0.0 |
| `references/checklist.md` | 666 | 0 | 0 | 0 | 0.51 | 0.75 | 3.0 |
| `voices/whit3rabbit.md` | 1,223 | 0 | 0 | **9** | 0.60 | 0.80 | 0.0 |
| `../voice-setup/SKILL.md` | 1,223 | 0 | 0 | 0 | 0.58 | 0.76 | 2.5 |
| `../readme-writing/SKILL.md` | 2,386 | 0 | **1** | **7** | 0.60 | 0.74 | 8.0 |

Scores are with the self-reference exemption applied, the rule this skill states in prose: quoted examples, code, tables, and block quotes are exempt from flagging. `apply_exemptions()` in `scan.py` is that rule's executable form. Run with `--no-exempt` to see the raw numbers.

## What it found in our own writing

**`patterns.md` scores worst, and that is structural.** A catalog listing the words it catalogs will hit its own lexicon. Three Tier-1 words, nine `-ing` analyses, and a 36-word Tier-2 cluster all come from the vocabulary tables: the comma-separated lists of the words each rule exists to catch. Those are unquoted by design, because quoting a 36-item list would make it unreadable.

Two options were available. Quote every list entry so the exemption swallows it, or leave the number visible and explain it. The number is left visible. A tool that suppresses its own findings to look clean is doing the thing this plugin exists to criticize.

**`craft.md` has 7 P2 hits.** The boilerplate detector firing on "the intersection of" and the transition detector firing on paragraph-initial "Additionally" inside rule text. Real hits on prose that is quoting rules rather than following them.

**`readme-writing/SKILL.md` carries 8 em dashes per 1,000 words,** the highest rate in the plugin and above the 6.0 human-range ceiling. It is the newest file here and the least edited against this scanner. Left visible rather than quietly fixed.

**`checklist.md` has the lowest burstiness at 0.51.** A numbered checklist is supposed to be metronomic. This is the detector correctly measuring a shape that is correct for its genre and wrong for prose, which is why `context.md` exists and why a number never renders a verdict on its own.

## The voice band, applied to ourselves

The active voice is `whit3rabbit`, whose rules ban em dashes, semicolons, emojis, one-word sentences for emphasis, US date order, paragraphs over five sentences, and a specific buzzword list. Running the plugin against those rules:

| File | Voice hits |
|---|---:|
| `voices/whit3rabbit.md` | 0 |
| `SKILL.md` | 0 |
| `../voice-setup/SKILL.md` | 0 |
| `references/patterns.md` | 19 |
| `../readme-writing/SKILL.md` | 28 |

**`patterns.md` and `readme-writing/SKILL.md` are the deliberate exceptions.** The engine is voice-agnostic. Forcing a general reference file to conform to whichever person happens to be active would be the wrong direction: the engine serves every voice, so it follows none of them. `patterns.md`'s em dashes and semicolons are mostly inside quoted before/after examples of the patterns themselves. `readme-writing/SKILL.md`'s are prose, and they are a fair thing to hold against it.

**An early run found nine semicolons in `whit3rabbit.md`, in a profile that bans semicolons.** They came from the source style guide, which used them while forbidding them. Fixed by splitting the sentences, which is what the rule asks for. This is the case the voice band exists to catch: a person's stated rules and their actual habits disagreeing, in the document that is supposed to define them.

**Merging the two prose skills introduced one of its own.** The "Paths." paragraph, added to every `SKILL.md` so Codex users can resolve `${CLAUDE_PLUGIN_ROOT}` by hand, used a semicolon. Three files, one sentence, caught by this scan and split.

## Bugs found by dogfooding

All in the scanner, all found by pointing it at this repo rather than at a fixture.

1. **Stylometrics counted markdown table rows.** `context.md` reported 9.5% trigram repetition, which was the tolerance matrix repeating the word "strict", not the writing. `strip_for_stats()` now drops table rows.
2. **The voice paragraph-length check counted lists as paragraphs.** A twelve-item numbered list reported as "a paragraph of 12 sentences." `is_prose_block()` now excludes lists, tables, headings, and fences.
3. **The voice em-dash ban ignored list typography.** `- **Term** — description` is typography, not a prose splice, and the general rule already carves it out. The voice rule now agrees.
4. **The list-typography check ran against the exemption-blanked text,** so a list item leading with an inline-code term lost its lead term to blanking and flagged anyway. It now checks the raw text, and blanking preserves length so the offsets line up.
5. **`required_when` had no gate,** so "missing closer" fired on every document that was not a letter. Entries now take a `when_rx` that scopes the check to text of the right shape.
6. **`verify.py` failed every voice conversion.** It treated any changed or added heading as a violation, so a rewrite that reordered sections to lead with the conclusion, which is exactly what a profile asks for, reported that it had broken a promise. `--allow-structure` now moves those two checks into a reported list. Everything else stays hard.

## Calibration

`tests/test_scan.py` asserts the separation holds and fails if it drifts.

| Fixture | Findings | P0 | Burstiness |
|---|---:|---:|---:|
| `tests/samples/ai-sample.md` | 42 | 7 | 0.66 |
| `tests/samples/human-sample.md` | 0 | 0 | 0.62 |
| `tests/samples/metronomic-sample.md` | 1 (uniformity) | 0 | 0.07 |
| `tests/samples/needs-conversion.md` | 12 | 8 | 0.24 |
| `tests/samples/already-in-voice.md` | 0 | 0 | 0.53 |

The metronomic fixture matters most for the craft bands. It contains no flagged vocabulary, no chatbot artifacts, and no negation runways. It still reads as machine output because every sentence is the same length. Vocabulary and rhythm are independent axes, and a draft can pass every word check and fail the read-aloud test.

The last two fixtures measure a different thing: whether the inputs to a conversion offer actually fire. `needs-conversion.md` is a report in a neutral register, structurally wrong for the active profile, and it reports 5 over-cap paragraphs, 3 banned words, a US-order date, and burstiness of 0.24 against a human floor of 0.45. `already-in-voice.md` says the same things in the profile's shape and reports nothing at all.

Neither fixture proves the skill chose a deep rewrite when it should have. Mode selection is prompt behaviour and no script in this repo can assert it. What they protect is the measurement the offer is built from, so the numbers a user sees before deciding are real.

## What this does not prove

The fixtures are hand-written, not drawn from a provenance-labeled corpus. Two samples establish that the detector separates an obvious case from an obvious case, which is the weakest form of evidence a detector can offer.

`conorbronsdon/avoid-ai-writing` does this properly: a hash-only corpus of public-domain works, archived pre-2023 blog posts, and RAID human baseline rows, where ground truth is provenance rather than a judge, reporting false-positive rates by register with Wilson intervals. That is the right shape for this measurement and it is not implemented here.

Until it is, treat these numbers as a regression guard, not an accuracy claim.
