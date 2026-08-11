# Self-scan

A tool that flags "delve" in your draft should survive its own pass. This is the result of running `scripts/scan.py` on this plugin's own files, including the unflattering rows.

Reproduce in one command, no dependencies:

```bash
for f in SKILL.md PROOF.md references/*.md; do echo "== $f"; python3 scripts/scan.py "$f"; done
```

## Result (v0.1.0, measured 10 August 2026)

| File | Words | P0 | P1 | P2 | Burstiness | MATTR | Em dash / 1k |
|---|---:|---:|---:|---:|---:|---:|---:|
| `SKILL.md` | 2,234 | 0 | 0 | 0 | 0.69 | 0.74 | 0.0 |
| `PROOF.md` | 2,985 | 0 | 0 | 0 | 0.57 | 0.73 | 0.0 |
| `references/patterns.md` | 4,776 | 0 | **15** | **4** | 0.87 | 0.76 | 2.5 |
| `references/false-positives.md` | 812 | 0 | 0 | 0 | 0.69 | 0.81 | 0.0 |
| `references/context.md` | 571 | 0 | 0 | 0 | 0.75 | 0.81 | 0.0 |
| `references/voice.md` | 915 | 0 | 0 | 0 | 0.73 | 0.74 | 1.1 |
| `references/craft.md` | 1,102 | 0 | 0 | **7** | 0.68 | 0.77 | 0.0 |
| `references/checklist.md` | 666 | 0 | 0 | 0 | 0.49 | 0.75 | 0.0 |
| `voices/whit3rabbit.md` | 1,223 | 0 | 0 | **9** | 0.60 | 0.80 | 0.0 |
| `../voice-setup/SKILL.md` | 1,223 | 0 | 0 | 0 | 0.58 | 0.76 | 2.5 |
| `../readme-writing/SKILL.md` | 2,403 | 0 | 0 | **7** | 0.63 | 0.73 | 0.0 |

Scores are with the self-reference exemption applied, the rule this skill states in prose: quoted examples, code, tables, and block quotes are exempt from flagging. `apply_exemptions()` in `scan.py` is that rule's executable form. Run with `--no-exempt` to see the raw numbers.

## What it found in our own writing

**`patterns.md` scores worst, and that is structural.** A catalog listing the words it catalogs will hit its own lexicon. Three Tier-1 words, nine `-ing` analyses, and a 36-word Tier-2 cluster all come from the vocabulary tables: the comma-separated lists of the words each rule exists to catch. Those are unquoted by design, because quoting a 36-item list would make it unreadable.

Two options were available. Quote every list entry so the exemption swallows it, or leave the number visible and explain it. The number is left visible. A tool that suppresses its own findings to look clean is doing the thing this plugin exists to criticize.

**`craft.md` has 7 P2 hits.** The boilerplate detector firing on "the intersection of" and the transition detector firing on paragraph-initial "Additionally" inside rule text. Real hits on prose that is quoting rules rather than following them.

**`readme-writing/SKILL.md` used to carry 8 em dashes per 1,000 words,** the highest rate in the plugin and above the 6.0 human-range ceiling. An earlier version of this file left that visible rather than fixing it, on the grounds that publishing the number was the honest move.

That was half right. `CLAUDE.md` states the repo's prose convention as no em dashes and no semicolons, so leaving them made the convention untrue rather than making the report honest. The prose was rewritten instead. The file now reads 0.0 per 1,000 words and 0 voice hits, and the P1 it used to carry is gone with them.

**`checklist.md` has the lowest burstiness at 0.49.** A numbered checklist is supposed to be metronomic. This is the detector correctly measuring a shape that is correct for its genre and wrong for prose, which is why `context.md` exists and why a number never renders a verdict on its own.

## The voice band, applied to ourselves

The active voice is `whit3rabbit`, whose rules ban em dashes, semicolons, emojis, one-word sentences for emphasis, US date order, paragraphs over five sentences, and a specific buzzword list. Running the plugin against those rules:

Every file is listed this time. An earlier version of this table showed five, which flattered the result: the reference files were carrying em dashes and semicolons that nobody had counted in public.

| File | Voice hits | What they are |
|---|---:|---|
| `PROOF.md` | 1 | serial-comma advisory |
| `references/checklist.md` | 0 | |
| `references/craft.md` | 0 | |
| `../readme-writing/SKILL.md` | 0 | |
| `references/false-positives.md` | 1 | serial-comma advisory |
| `references/voice.md` | 2 | one attributed quotation, one serial-comma advisory |
| `voices/whit3rabbit.md` | 3 | serial-comma advisories |
| `../voice-setup/SKILL.md` | 3 | serial-comma advisories |
| `SKILL.md` | 6 | serial-comma advisories |
| `references/context.md` | 6 | 4 over-cap paragraphs, 1 one-word sentence, 1 advisory |
| `references/patterns.md` | 25 | 10 em dashes, 7 semicolons, 2 one-word sentences, 6 advisories |

The serial-comma rows are the `oxford_comma` mechanic, which reports at P2 and never at the voice default. It cannot tell a three-item list from a compound sentence, so it advises and says so in the finding. Counting advisories as defects would be the same error in the other direction.

**`patterns.md` is the deliberate exception.** The engine is voice-agnostic. Forcing a general reference file to conform to whichever person happens to be active would be the wrong direction, because the engine serves every voice and so follows none of them. Its em dashes and semicolons sit in before and after examples of the patterns themselves, in a form the quoted-example exemption does not recognize. That is a fair thing to hold against the file and it is left visible.

**Four of `context.md`'s six are the register profile block,** where each profile is one dense line of targets. A definition list is not a paragraph, and the paragraph-length rule reads it as one. Left as is, because rewriting a reference table into prose to satisfy a prose rule is the tail wagging the dog. See the parked false positive at the end of this file, which is the same rule reading the same shape wrong.

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

## Bugs found by review

A second pass, this one by a reader rather than by the tool. Two of these were shipped features that did nothing.

7. **`curly-quote` could never fire.** Every register listed it in the skip set, and `--profile` only accepts those registers, so the pattern and its lexicon entry were dead code. `context.md` said `technical-blog` and `docs` should relax it rather than skip it. Skipping had been standing in for relaxing everywhere, so `PROFILE_RELAX` now carries the tolerance matrix's relaxed cells as hit allowances and the pattern reports past them. It also scores against the raw text, because the quoted-example exemption blanks a curly-quoted span including the quote marks that are the thing being checked.
8. **The `oxford_comma` mechanic was documented and never read.** `TEMPLATE.rules.json` described it and `whit3rabbit.rules.json` set it to `require`, and no line of `scan.py` looked at the key. It is implemented now, at P2, with two guards that keep it from firing on every compound sentence in the file.
9. **`verify.py` read structure out of code blocks.** A bash fence containing `# install it` counted as a heading, so moving a code block changed the heading count and failed a rewrite that touched no headings. Fences are blanked before headings, tables, and block quotes are extracted.
10. **`verify.py` double-reported every edited URL.** The path regex matches inside `https://raw.githubusercontent.com/user/repo/main/README.md`, and the carve-out that lets a URL lose an AI tracking parameter did not reach the second report. URLs are blanked before the path check.
11. **`verify.py` counted tells from a hardcoded copy of the lexicon.** Fifteen words, frozen. It now builds the counter from `lexicon.json` and falls back to the frozen list only when the engine is not beside it.
12. **A stray quote exempted the next 200 characters.** `QUOTED_RX` accepted a straight quote closed by a curly one, so one unpaired mark could blank a whole paragraph out of scoring. Each pair now has to close with its own kind.
13. **`key` was a Tier-3 word.** One of the most common words in English, sitting in the list that fires on density. It dominated the count. Removed, and the phrase worth catching (`key turning point`) was already a pattern regex.
14. **The Tier-1 table and the lexicon disagreed.** `patterns.md` listed `leverage`, `landscape`, and `unpack` as replace-on-sight, and the lexicon had the first two as cluster-only and the third not at all. `seamlessly` was in both Tier 1 and Tier 3, so one word produced a P1 and inflated the density that produced a P2. The sense-dependent words moved to Tier 2 with the reason stated, and `tests/test_scan.py` now fails if a word in the Tier-1 table does not resolve in the lexicon.
15. **A non-breaking space was a P0.** It is correct French typography, correct before a unit, and correct in a name that must not wrap. Reporting it as a credibility killer failed documents that had been typeset properly. Space-like characters now report at P2 and only past three of them. The zero-width characters are unchanged.
16. **`Dr.` read as a one-word sentence.** "The meeting ran late. Dr. Smith arrived" flagged the honorific as emphasis. Guarded with a narrower abbreviation list than the sentence splitter uses, deliberately leaving out `No.`, which in prose is almost always the sentence this rule exists to catch.
17. **Three `here` links reported the same line.** The vague-link-text check searched for the link text and always found the first occurrence. It iterates matches now.
18. **One caveat anywhere laundered every headline number.** A README with five stats and one "results vary" in the FAQ passed. A caveat now has to sit in the claim's own section.

## Bugs the fixes introduced

Found on a second read of the fixes themselves, which is the pass that usually gets skipped.

19. **Rebuilding the tell counter from the lexicon swept in `curly-quote`.** Fixing the frozen-copy bug in item 11 pulled in every fingerprint pattern, and curly quotes are one. Paste a paragraph through Word, Google Docs, or macOS and the typography curls by itself, so a correct rewrite gained tells it did not write and `verify.py` hard-failed it. That is the false positive `references/false-positives.md` warns about, produced by the tool whose job is catching silent breakage. P2 fingerprints are excluded from the counter now, and a test pins a straight-to-curly rewrite as passing.
20. **Three relaxed matrix cells still had no allowance** after `PROFILE_RELAX` was added: hedging, boilerplate clusters, and Tier-1 vocabulary in `docs`. They sat in exactly the gap `curly-quote` had just been lifted out of. `tests/test_scan.py` now parses the tolerance matrix and fails on any cell without an implementation in either direction. It found two more the moment it was written, `docs` against future-narrative closers and social endorsement closers, plus one policy the matrix and the engine disagreed on.
21. **The no-P0-relaxation rule was invented rather than inherited.** The engine's actual promise is that P0 *fingerprints* are never suppressed, because those are evidence about how a document was produced. `significance-inflation` is a craft P0, and one "plays a key role" in a reference page is the register rather than a tell. The matrix always said so. A test now asserts the real promise, that no P0 fingerprint appears in any skip or relax set, instead of the broader one that was quietly overriding the matrix.

## Bugs found by a second review

A read of both scanners, the verifier, the research pipeline, the validators, and
the tests together, looking for logic errors and doc/code drift rather than for
prose. The first four are cases where a user got a wrong answer rather than an
ugly one.

22. **The invisible-character tables were stored as invisible characters.** The keys of `HIDDEN_UNICODE`, the two entries of `SPACE_LIKE_UNICODE`, and a bare variation selector inside `EMOJI_RX` were the characters themselves. The file's own comment warned that two identical-looking keys merge silently, and nothing defended against it. The worst case was not a merge: a save that normalized whitespace would turn the U+00A0 key into a plain space, and `raw_text.count(" ")` would then report every space in every document as a paste artifact. All of them are `\uXXXX` escapes now, in the fixtures too, and a test asserts the exact codepoints rather than the keys.
23. **`verify.py` compared headings by membership while every other preservation check used a multiset.** A document with two `## Notes` that lost one of them and gained a different heading passed both the membership test and the count test, and a section disappeared with nothing reported. Headings are compared the same way as code, tables, quotes, and paths now.
24. **Two hard gates in `verify.py` ran on the raw text.** A rewrite that correctly wrote a date range as `2010–2023` failed "em dashes added", and a draft that quoted a flagged phrase to warn about it failed "more tells after rewrite", which is the exemption `scan.py` grants and this script did not. Both counters run on the same exempted copy now, an en dash between digits is not counted, and both name the offending span so a false positive can be read rather than guessed at.
25. **`oxford_comma: "forbid"` had no guard at all.** The require side carried two, and the forbid side was a bare `,\s+(?:and|or)\s+\w`, which matches every compound sentence in the language: "She left the room, and he stayed" is required punctuation, not a serial comma. The branch was also untested, so an entire mechanic shipped reporting on correct writing. Both sides carry the same guards now and both are tested.
26. **`readme_check.py` counted badges out of the raw file,** so a README showing badge markdown inside a fenced example was counted as wearing those badges, and fifteen of them in a code block tripped `badge-wall` on a file with no badge in it.
27. **`vague-link-text` saw markdown links only.** The study counts HTML as the third link style and 76% of the corpus centers its header in HTML, so `<a href="...">click here</a>` in a header block was exactly the case being missed. Extending the check to anchor text found 34 more across the corpus, all of them real: 31 `this link`, plus `here`, `Click here`, and `Learn more`.
28. **The mixed-block twin of the parked false positive, in the other skill.** `check_prose_shape` decided a block was a list by looking at its first line only, so a lead-in sentence followed by eight bullets scored as one 90-word paragraph. It uses the same majority rule as `is_prose_block` now, which drops 8 `long-paragraph` findings across the corpus. The `scan.py` twin is still parked, for the reason at the end of this file.
29. **Smaller drift, fixed without ceremony.** `voice-curly-quote` matched on the raw text and built its excerpt from the blanked copy, so a quote inside an exempted span reported a line of spaces. `find_pitch` returned a line count no caller used and that disagreed by one with the count `check_structure` computed for itself. `moving_ttr` rebuilt a set per window position. The `efficiency-overuse` note was off by one about its own threshold. `04_aggregate.py` had re-declared the image regex without the title clause `03_analyze_readme.py` uses, so the two steps of one pipeline disagreed about the same corpus, and `03`'s badge host list carried a regex in a list of substrings, where it could never match.

Two of the review's findings were answered by documenting rather than by
changing code, because measuring showed the change would cost more than it
bought. `readme_check.py`'s badge host list carries one entry the corpus scripts
do not, `/badge`, which catches 625 badges against 568 over the committed
snapshot with no non-badge image caught either way. It is the broader of the two
on purpose and the divergence is now written down at both ends. `verify.py`'s
path check ignores an extensionless path like `voices/ACTIVE`, and dropping the
extension requirement makes it match "and/or", "TCP/IP", "human/AI", and every
`owner/repo` slug in this repo's own prose. On a gate that blocks file writes,
under-matching is the safe direction, so `SKILL.md` now says which half of its
own promise is mechanically enforced.

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

## Known false positive, parked on purpose

`is_prose_block()` decides a block is a list when at least half its lines start with a bullet. A list whose items wrap over several lines each fails that ratio and gets scored as one long paragraph, so the voice paragraph-length cap fires on it. `CHANGELOG.md` reports five of these and every one is a bullet list.

It is left alone for now because the fix moves the numbers published above, and a calibration table that changed in the same pass that published it is worth less than one that did not. The fix is to treat a block whose first non-blank line is a list item as a list regardless of the ratio. Whoever takes it should expect the self-scan table and `tests/samples/needs-conversion.md` counts to move with it, and should regenerate this file rather than editing the numbers by hand.

The readme-writing skill had the same rule reading the same shape wrong, from the other direction: a block whose first line was prose and whose remaining lines were bullets scored as one long paragraph. That one was not parked, because nothing published depends on it. It is item 28 above.
