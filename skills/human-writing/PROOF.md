# Self-scan

A tool that flags "delve" in your draft should survive its own pass. This is the result of running `scripts/scan.py` on this plugin's own files, including the unflattering rows.

Reproduce in one command, no dependencies:

```bash
for f in SKILL.md references/*.md; do echo "== $f"; python3 scripts/scan.py "$f"; done
```

## Result (v1.0.0, measured 10 August 2026)

| File | Words | P0 | P1 | P2 | Burstiness | MATTR | Em dash / 1k |
|---|---:|---:|---:|---:|---:|---:|---:|
| `SKILL.md` | 1,233 | 0 | 0 | 0 | 0.66 | 0.76 | 4.1 |
| `references/patterns.md` | 4,596 | 0 | **14** | **4** | 0.89 | 0.76 | 2.6 |
| `references/false-positives.md` | 811 | 0 | 0 | 0 | 0.69 | 0.81 | 1.2 |
| `references/context.md` | 417 | 0 | 0 | 0 | 0.67 | 0.85 | 0.0 |
| `references/voice.md` | 858 | 0 | 0 | 0 | 0.74 | 0.74 | 2.3 |
| `references/craft.md` | 1,050 | 0 | 0 | **7** | 0.67 | 0.77 | 0.0 |
| `references/checklist.md` | 624 | 0 | 0 | 0 | 0.47 | 0.74 | 4.8 |
| `../rabbit-writes/SKILL.md` | 769 | 0 | 0 | 0 | 0.62 | 0.74 | 3.9 |
| `../voice-setup/SKILL.md` | 1,210 | 0 | 0 | 0 | 0.58 | 0.76 | 1.6 |
| `../rabbit-writes/voices/whit3rabbit.md` | 1,219 | 0 | 0 | **9** | 0.60 | 0.75 | 0.0 |

Scores are with the self-reference exemption applied, the rule this skill states in prose: quoted examples, code, tables, and block quotes are exempt from flagging. `apply_exemptions()` in `scan.py` is that rule's executable form. Run with `--no-exempt` to see the raw numbers.

## What it found in our own writing

**`patterns.md` scores worst, and that is structural.** A catalog listing the words it catalogs will hit its own lexicon. Three Tier-1 words, nine `-ing` analyses, and a 36-word Tier-2 cluster all come from the vocabulary tables: the comma-separated lists of the words each rule exists to catch. Those are unquoted by design, because quoting a 36-item list would make it unreadable.

Two options were available. Quote every list entry so the exemption swallows it, or leave the number visible and explain it. The number is left visible. A tool that suppresses its own findings to look clean is doing the thing this plugin exists to criticize.

**`craft.md` has 7 P2 hits.** The boilerplate detector firing on "the intersection of" and the transition detector firing on paragraph-initial "Additionally" inside rule text. Real hits on prose that is quoting rules rather than following them.

**`checklist.md` has the lowest burstiness at 0.47**, right at the human floor. A numbered checklist is supposed to be metronomic. This is the detector correctly measuring a shape that is correct for its genre and wrong for prose, which is why `context.md` exists and why a number never renders a verdict on its own.

## The voice band, applied to ourselves

The active voice is `whit3rabbit`, whose rules ban em dashes, semicolons, emojis, one-word sentences for emphasis, US date order, paragraphs over five sentences, and a specific buzzword list. Running the whole plugin against those rules:

| File | Voice hits |
|---|---:|
| `../rabbit-writes/voices/whit3rabbit.md` | 0 |
| `../rabbit-writes/SKILL.md` | 0 |
| `../voice-setup/SKILL.md` | 0 |
| `SKILL.md` | 0 |
| `references/patterns.md` | 19 |

**`patterns.md` is the deliberate exception, and it should stay that way.** The engine is voice-agnostic. Forcing a general reference file to conform to whichever person happens to be active would be the wrong direction: the engine serves every voice, so it follows none of them. Its em dashes and semicolons are mostly inside quoted before/after examples of the patterns themselves.

**The first run found nine semicolons in `whit3rabbit.md`, in a profile that bans semicolons.** They came from the source style guide, which used them while forbidding them. Fixed by splitting the sentences, which is what the rule asks for. This is the case the voice band exists to catch: a person's stated rules and their actual habits disagreeing, in the document that is supposed to define them.

**Six more were found in the skill documentation.** Two semicolons and four instances of `**Bold lead** — full sentence` at the start of a paragraph, which this catalog names as a tell in §50. Fixed.

## Bugs found by dogfooding

Four, all in the scanner, all found by pointing it at this repo rather than at a fixture.

1. **Stylometrics counted markdown table rows.** `context.md` reported 9.5% trigram repetition, which was the tolerance matrix repeating the word "strict", not the writing. `strip_for_stats()` now drops table rows.
2. **The voice paragraph-length check counted lists as paragraphs.** A twelve-item numbered list reported as "a paragraph of 12 sentences." `is_prose_block()` now excludes lists, tables, headings, and fences.
3. **The voice em-dash ban ignored list typography.** `- **Term** — description` is typography, not a prose splice, and the general rule already carves it out. The voice rule now agrees.
4. **The list-typography check ran against the exemption-blanked text,** so a list item leading with an inline-code term (`` - `voices/x.md` — the profile ``) lost its lead term to blanking and flagged anyway. It now checks the raw text; blanking preserves length, so offsets line up.
5. **`required_when` had no gate,** so "missing closer" fired on every document that was not a letter. Entries now take a `when_rx` that scopes the check to text of the right shape.

## Calibration

`tests/test_scan.py` asserts the separation holds and fails if it drifts.

| Fixture | Findings | P0 | Burstiness |
|---|---:|---:|---:|
| `tests/samples/ai-sample.md` | 33 | 7 | 0.66 |
| `tests/samples/human-sample.md` | 0 | 0 | 0.62 |
| `tests/samples/metronomic-sample.md` | 1 (uniformity) | 0 | 0.36 |

The third fixture matters most. It contains no flagged vocabulary, no chatbot artifacts, and no negation runways. It still reads as machine output because every sentence is the same length. Vocabulary and rhythm are independent axes, and a draft can pass every word check and fail the read-aloud test.

The voice tests additionally assert that a register profile never relaxes a voice rule, that the shipped profile's own register passes its own rules, and that `TEMPLATE.rules.json` flags nothing on clean prose.

## What this does not prove

The fixtures are hand-written, not drawn from a provenance-labeled corpus. Two samples establish that the detector separates an obvious case from an obvious case, which is the weakest form of evidence a detector can offer.

`conorbronsdon/avoid-ai-writing` does this properly: a hash-only corpus of public-domain works, archived pre-2023 blog posts, and RAID human baseline rows, where ground truth is provenance rather than a judge, reporting false-positive rates by register with Wilson intervals. That is the right shape for this measurement and it is not implemented here.

Until it is, treat these numbers as a regression guard, not an accuracy claim.
