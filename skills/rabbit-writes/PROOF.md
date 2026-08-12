# Self-scan

A tool that flags "delve" in your draft should survive its own pass. This is the result of running `scripts/scan.py` on this plugin's own files, including the unflattering rows.

Reproduce in one command, no dependencies:

```bash
for f in SKILL.md PROOF.md references/*.md voices/whit3rabbit.md \
         ../voice-setup/SKILL.md ../readme-writing/SKILL.md; do
  echo "== $f"; python3 scripts/scan.py "$f"
done
```

Run it from `skills/rabbit-writes/`. It covers every row in the table below, including the three in other skills, which an earlier version of this command left out.

Every number below was measured against a particular pattern catalogue, and the heading says which one. `scan.py --json` reports `lexicon_version` and `registers_version` alongside the findings, and `scripts/validate.py` fails when this heading and `lexicon.json` disagree. A table of scores with no version on it is archaeology: somebody has to guess which catalogue produced it, and the guess is usually wrong.

## Result (v0.1.0, lexicon 2, registers 1, measured 11 August 2026, fifth pass)

| File | Words | P0 | P1 | P2 | Burstiness | MATTR | Em dash / 1k |
|---|---:|---:|---:|---:|---:|---:|---:|
| `SKILL.md` | 2,692 | 0 | 0 | 0 | 0.70 | 0.73 | 0.0 |
| `PROOF.md` | 4,764 | 0 | 0 | 0 | 0.58 | 0.73 | 0.0 |
| `references/patterns.md` | 3,942 | **5** | **15** | **4** | 0.86 | 0.77 | 1.8 |
| `references/false-positives.md` | 786 | 0 | 0 | 0 | 0.70 | 0.82 | 0.0 |
| `references/context.md` | 567 | 0 | 0 | 0 | 0.75 | 0.81 | 0.0 |
| `references/voice.md` | 1,047 | 0 | 0 | 0 | 0.77 | 0.73 | 0.0 |
| `references/craft.md` | 1,069 | 0 | 0 | **7** | 0.70 | 0.77 | 0.0 |
| `references/checklist.md` | 640 | 0 | 0 | 0 | 0.46 | 0.74 | 0.0 |
| `voices/whit3rabbit.md` | 1,518 | 0 | 0 | **10** | 0.69 | 0.79 | 0.0 |
| `../voice-setup/SKILL.md` | 1,582 | 0 | 0 | 0 | 0.61 | 0.75 | 1.3 |
| `../readme-writing/SKILL.md` | 2,378 | 0 | 0 | **7** | 0.63 | 0.73 | 0.0 |

Scores are with the self-reference exemption applied, the rule this skill states in prose: quoted examples, code, tables, and block quotes are exempt from flagging. `apply_exemptions()` in `scan.py` is that rule's executable form. Run with `--no-exempt` to see the raw numbers.

Two patterns opt out of it, `curly-quote` and `citation-leak`, and each says why in a `_scan_raw_note` in `lexicon.json`. Both are facts about how a file was produced rather than about what it says, and the exemption is about content. A chat citation marker pasted into a block quote is the likeliest place one appears and was the one place nothing looked.

Every word count in this table dropped between the second review and the third, and no prose was cut. Item 32 below is why: heading text and block quotes used to be measured as this document's own sentences. The findings columns did not move with them, because flagging already exempted both.

The counts moved again in the fourth pass, this time because the documents changed: the engine was extracted into `scripts/rwlib/`, the tolerance matrix became a data file, and three skill files gained sections. `voices/whit3rabbit.md` fell from 9 P2 hits to 7 by dropping two paraphrases of rules that are defined elsewhere, which is the same drift the one-definition tripwire in `scripts/validate.py` now fails the build over.

The fifth pass moved them for the same reason and not because the engine changed its mind about anything above. `voices/whit3rabbit.md` gained the Quick reference card and Anti-overfitting sections that `TEMPLATE.md` has always had and the worked example did not, which is 335 more words and three more list-label advisories. `references/voice.md`, `SKILL.md`, and `../voice-setup/SKILL.md` grew where blending, per-register mechanics, and `measure_voice.py` are now documented. Every P0 and P1 column is where it was.

## What it found in our own writing

**`patterns.md` scores worst, and that is structural.** A catalog listing the words it catalogs will hit its own lexicon. Three Tier-1 words, nine `-ing` analyses, and three Tier-2 clusters all come from the vocabulary tables: the comma-separated lists of the words each rule exists to catch. Those are unquoted by design, because quoting a 36-item list would make it unreadable.

**The 5 P0s on `patterns.md` are the same story, one rule further on.** Line 46 lists the five chat citation markers in backticks, and `citation-leak` stopped honouring the exemption in lexicon 2, so each one now scores. That is the cost of catching a marker pasted into a block quote, which is where a real one usually lands. This file pays it in full and publishes the number.

Two options were available in both cases. Quote every list entry so the exemption swallows it, or leave the number visible and explain it. The number is left visible. A tool that suppresses its own findings to look clean is doing the thing this plugin exists to criticize.

Anyone enabling the `rabbit-scan` pre-commit hook on a repository that writes about slop detection inherits this, so the hooks file says so and points at `files`.

**`craft.md` has 7 P2 hits.** The boilerplate detector firing on "the intersection of" and the transition detector firing on paragraph-initial "Additionally" inside rule text. Real hits on prose that is quoting rules rather than following them.

**`readme-writing/SKILL.md` used to carry 8 em dashes per 1,000 words,** the highest rate in the plugin and above the 6.0 human-range ceiling. An earlier version of this file left that visible rather than fixing it, on the grounds that publishing the number was the honest move.

That was half right. `CLAUDE.md` states the repo's prose convention as no em dashes and no semicolons, so leaving them made the convention untrue rather than making the report honest. The prose was rewritten instead. The file now reads 0.0 per 1,000 words and 0 voice hits, and the P1 it used to carry is gone with them.

**`checklist.md` has the lowest burstiness at 0.46.** A numbered checklist is supposed to be metronomic. This is the detector correctly measuring a shape that is correct for its genre and wrong for prose, which is why `context.md` exists and why a number never renders a verdict on its own.

## The voice band, applied to ourselves

The active voice is `whit3rabbit`, whose rules ban em dashes, semicolons, emojis, one-word sentences for emphasis, US date order, paragraphs over five sentences, and a specific buzzword list. Running the plugin against those rules:

Every file is listed this time. An earlier version of this table showed five, which flattered the result: the reference files were carrying em dashes and semicolons that nobody had counted in public.

| File | Voice hits | What they are |
|---|---:|---|
| `references/checklist.md` | 0 | |
| `references/craft.md` | 0 | |
| `../readme-writing/SKILL.md` | 0 | |
| `PROOF.md` | 1 | serial-comma advisory |
| `references/false-positives.md` | 1 | serial-comma advisory |
| `references/voice.md` | 2 | one one-word sentence, one serial-comma advisory |
| `voices/whit3rabbit.md` | 4 | serial-comma advisories |
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
14. **The Tier-1 table and the lexicon disagreed.** `patterns.md` listed `leverage`, `landscape`, and `unpack` as replace-on-sight, and the lexicon had the first two as cluster-only and the third not at all. `seamlessly` was in both Tier 1 and Tier 3, so one word produced a P1 and inflated the density that produced a P2. The sense-dependent words moved to Tier 2 with the reason stated, and `tests/test_engine.py` now fails if a word in the Tier-1 table does not resolve in the lexicon.
15. **A non-breaking space was a P0.** It is correct French typography, correct before a unit, and correct in a name that must not wrap. Reporting it as a credibility killer failed documents that had been typeset properly. Space-like characters now report at P2 and only past three of them. The zero-width characters are unchanged.
16. **`Dr.` read as a one-word sentence.** "The meeting ran late. Dr. Smith arrived" flagged the honorific as emphasis. Guarded with a narrower abbreviation list than the sentence splitter uses, deliberately leaving out `No.`, which in prose is almost always the sentence this rule exists to catch.
17. **Three `here` links reported the same line.** The vague-link-text check searched for the link text and always found the first occurrence. It iterates matches now.
18. **One caveat anywhere laundered every headline number.** A README with five stats and one "results vary" in the FAQ passed. A caveat now has to sit in the claim's own section.

## Bugs the fixes introduced

Found on a second read of the fixes themselves, which is the pass that usually gets skipped.

19. **Rebuilding the tell counter from the lexicon swept in `curly-quote`.** Fixing the frozen-copy bug in item 11 pulled in every fingerprint pattern, and curly quotes are one. Paste a paragraph through Word, Google Docs, or macOS and the typography curls by itself, so a correct rewrite gained tells it did not write and `verify.py` hard-failed it. That is the false positive `references/false-positives.md` warns about, produced by the tool whose job is catching silent breakage. P2 fingerprints are excluded from the counter now, and a test pins a straight-to-curly rewrite as passing.
20. **Three relaxed matrix cells still had no allowance** after `PROFILE_RELAX` was added: hedging, boilerplate clusters, and Tier-1 vocabulary in `docs`. They sat in exactly the gap `curly-quote` had just been lifted out of. The suite then parsed the tolerance matrix and failed on any cell without an implementation in either direction, which `scripts/registers.json` has since made structural rather than parsed. It found two more the moment it was written, `docs` against future-narrative closers and social endorsement closers, plus one policy the matrix and the engine disagreed on.
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

The image half of that carve-out was measured later and split. Over the same
100-README corpus there are 341 markdown images: 300 with an absolute src, which
`URL_RX` already covered, 41 relative with an extension, which `PATH_RX` already
covered, and **0** in the gap. The HTML `<img>` half held **3**. A check that
costs nothing and closes a real hole is worth making whatever its yield, so
image sources are in the extract set now, scoped to exactly the leftovers so a
retargeted absolute src is still one violation rather than two.

Alt text stayed out, and this is the measurement it stayed out on: **337** of
those images carry alt text, **7,282** characters of it, containing **0**
lexicon tells and **18** prose dashes. The 18 cost nothing, because both
counters compare a before to an after and an editor that leaves alt text alone
moves neither. What protecting it verbatim would cost is the legitimate edit.
Alt text in this corpus is overwhelmingly badge labels, `PyPI` becoming
`PyPI version` is a fix rather than a violation, and `SKILL.md`'s guardrails
never promised alt text was untouchable. Requiring it here would have been the
verifier inventing a promise the skill does not make.

## Bugs found by a third review

A read of the same six surfaces again, this time looking at the places the first
two passes did not reach: the seams between tools, and the measurement layer that
produces the numbers on this page. One finding had consequences outside the repo.

30. **The research pipeline sent a GitHub token to a third party.** `01_fetch_candidates.py` attached `Authorization: Bearer $GITHUB_TOKEN` to every request its helper made, and one of those requests goes to `api.ossinsight.io`, which never asked for a GitHub credential and cannot use one. The header is now attached only when the host is exactly `api.github.com`, compared as a whole hostname rather than a suffix, because `api.github.com.example.net` belongs to somebody else. This is the only finding in the pass with an effect beyond this repository, and it was fixed on its own.
31. **The two engines disagreed about a date range.** `verify.py` deliberately exempts a spaceless en dash between digits, because `2010–2023` is correct typography and the one en dash a rewrite legitimately produces, and a test pinned it. `scan.py` had no such carve-out, so under a voice that forbids em dashes the same file passed verification and failed the scan with a P0, and `em_dashes_per_1k` counted the range as a splice. Both now use one pattern, and a test asserts the two files declare it identically, because two copies of one rule drift quietly: the scan keeps reporting and the verifier keeps passing.
32. **Heading text was measured as the sentence below it.** `strip_for_stats()` removed the `##` and left the words. A heading carries no terminal punctuation, so `split_sentences` glued it onto the first sentence of its section, and every section opener in every markdown document measured two or three words long. Block quotes were worse: they are exempt from flagging and were counted in full, so a document that is half quotation reported the rhythm of whoever it was quoting. Both are dropped now, which is the same rule `03_analyze_readme.py` applies to the corpus, and every word count in the table above moved.
33. **Nested badge links were parsed as links to the badge.** `[![PyPI](shields.io/...)](pypi.org/...)` is one of the most common shapes in this corpus. The link regex refuses a leading `!` and then matches the outer bracket, which stops at the `]` closing the alt text, so it captured `![PyPI` as the link text and the *badge image* URL as the destination. Both link counters had it, which means the study measured link style over pseudo-links. Images are blanked before links are counted now, in both the checker and the corpus script. Regenerating moved less than expected, because a badge wrapper was counted once either way: the destinations were wrong rather than the totals, and `avg_link_text_words` went from 2.16 to 2.18.
34. **One unclosed `<table>` could fail CI.** `find_pitch` skips `<details>` and `<table>` blocks, and the depth counter has no way to know a block was never closed. A hand-written sponsor grid missing a `</table>`, which GitHub renders anyway, kept the counter positive to the end of the file, skipped every line after it, and reported `no-pitch`: a P0, and an exit 1 under `--check`, on a README whose second paragraph says exactly what the project is. A markdown heading now closes any block still open, and a second pass that ignores the blocks entirely runs only when the first found nothing.
35. **`classify_heading` could not classify `## API`.** The keyword was written `" api"` with a leading space, to stop it matching "apiary" and "rapid", and a leading space has nothing to sit against at the start of the string. The single most obvious API heading there is fell through to `other` in both the checker and the study. Headings are padded before the test now, so a keyword can ask for a whole word by writing its own spaces, and the plural is spelled out so `Required APIs` keeps the classification it always had. `"getting started"` was also listed under both `installation` and `usage`, and installation is tested first, so the usage copy could never win a heading. It is gone.
36. **Smaller drift, again.** `verify.py` ran its path check over inline code, so one edit to `` `scripts/scan.py` `` reported two broken promises where there was one. `--profile` took its choices from `PROFILE_SKIP`, so a register whose skip set emptied out would vanish from the CLI and from the coverage the tests get by iterating registers: there is an explicit `REGISTERS` tuple now, pinned against the tolerance matrix's own columns. `formulaic-challenges` fired on "the team faces challenges next quarter", which is a sentence rather than a tell, and now matches the formula patterns.md section 45 actually describes. The sentence splitter protected abbreviations with U+2024 ONE DOT LEADER and replaced every one of them with a period at the end, quietly rewriting any document that legitimately contained one. `check_structure` checked the position of the *first* license heading, so a README with an early licence mention and a real License section at the end was told its license is not last. `[a][b]` in prose, `matrix[i][j]` outside a code span, was reported as a reference-style link, and a reference now has to resolve against a definition before it is named. Both scanners documented exit codes they do not use.

## Calibration

`tests/test_calibration.py` asserts the separation holds and fails if it drifts.

| Fixture | Findings | P0 | Burstiness |
|---|---:|---:|---:|
| `tests/samples/ai-sample.md` | 44 | 7 | 0.66 |
| `tests/samples/human-sample.md` | 0 | 0 | 0.62 |
| `tests/samples/metronomic-sample.md` | 1 (uniformity) | 0 | 0.07 |
| `tests/samples/needs-conversion.md` | 14 | 10 | 0.21 |
| `tests/samples/already-in-voice.md` | 0 | 0 | 0.54 |

The metronomic fixture matters most for the craft bands. It contains no flagged vocabulary, no chatbot artifacts, and no negation runways. It still reads as machine output because every sentence is the same length. Vocabulary and rhythm are independent axes, and a draft can pass every word check and fail the read-aloud test.

The last two fixtures measure a different thing: whether the inputs to a conversion offer actually fire. `needs-conversion.md` is a report in a neutral register, structurally wrong for the active profile, and it reports 6 over-cap paragraphs, 4 banned words, a numeric date, and burstiness of 0.21 against a human floor of 0.45. `already-in-voice.md` says the same things in the profile's shape and reports nothing at all.

`needs-conversion.md` gained a section in the third review pass, for a reason worth naming. Fixing the heading measurement in item 32 took the fixture from 620 measured words to 596, four short of the 600-word floor where this engine calls a sample reliable, and a fixture whose whole job is to be long enough for the numbers to mean something failed that assertion on a rounding error. The prose was extended rather than the assertion relaxed.

Neither fixture proves the skill chose a deep rewrite when it should have. Mode selection is prompt behaviour and no script in this repo can assert it. What they protect is the measurement the offer is built from, so the numbers a user sees before deciding are real.

## What this does not prove

The fixtures are hand-written, not drawn from a provenance-labeled corpus. Two samples establish that the detector separates an obvious case from an obvious case, which is the weakest form of evidence a detector can offer.

`conorbronsdon/avoid-ai-writing` does this properly: a hash-only corpus of public-domain works, archived pre-2023 blog posts, and RAID human baseline rows, where ground truth is provenance rather than a judge, reporting false-positive rates by register with Wilson intervals. That is the right shape for this measurement.

The harness for it now exists, in `docs/detector-corpus/` and `scripts/detector-corpus/`. It takes samples with an archive capture proving they predate 2022-11-30, stores a SHA-256 rather than the prose, refuses a human label dated after the cutoff, excludes any sample whose text no longer matches its hash, and reports the P0 false-positive rate per register with a Wilson interval. Run `python3 scripts/detector-corpus/score.py` to see it.

**The corpus is empty.** The machinery works and nobody has gathered the texts, which needs network access, a few hours, and a copyright judgment about redistributing other people's writing that the hash-only design answers but does not make for anybody. `docs/detector-corpus/README.md` is the procedure.

Two numbers are worth stating in the meantime, because they are what the current fixtures are actually worth. Zero false positives over two human samples is a rate somewhere between 0% and 66%. Zero over fifty would be somewhere under 7.2%, and 52 samples is where the upper bound crosses 7%. That gap is the whole argument for building this, and it is why the sentence below has not changed. The round numbers an earlier draft of this paragraph used were checked against `corpus_io.wilson` and two of them were wrong, which is the same lesson one paragraph up: a figure nobody recomputes is a figure that drifts.

Until the corpus is populated, treat these numbers as a regression guard, not an accuracy claim.

## Known false positives

### The wrapped list, fixed

`is_prose_block()` decided a block was a list when at least half its lines started with a bullet. A list whose items wrap over several lines each failed that ratio and got scored as one long paragraph, so the voice paragraph-length cap fired on it. `CHANGELOG.md` reported five of these and every one was a bullet list.

It sat parked for one release because the fix would have moved the numbers published above, and a calibration table that changed in the same pass that published it is worth less than one that did not. That objection expires once the table has been published and stood, which it has. The fix is the one the parked note specified: a block whose first non-blank line is a list item is a list, whatever the ratio says. Nothing that opens with a bullet is a paragraph, so the ratio never needed a vote there, and the majority rule still governs everything past the first line.

`CHANGELOG.md` goes from 5 `voice-paragraph-length` findings to 0, all five of them false. The self-scan table above did not move with it, which is worth saying plainly rather than leaving as a surprise: the reproduce command runs `scan.py` with no voice profile, and `max_paragraph_sentences` is a voice mechanic. Nothing in the published table was ever affected. The stylometric columns were never at risk either, because paragraph statistics are deliberately not filtered through `is_prose_block()`, for the reason in the next section.

`readme_check.py` shares the rule, so the same fix reaches `long-paragraph` there. Across the 100-README corpus it drops 406 findings to 390: **16 fewer**, every one of them a wrapped bullet list read as a paragraph. The corpus P0 band in `tests/test_corpus.py` does not move, because `long-paragraph` is a P2.

### Still parked, and measured

A second one was parked in the third review, with the measurement written down this time. List items are counted as sentences by `strip_for_stats()`, and they distort rhythm the way heading text did: a one-word bullet is a one-word sentence. Dropping them was measured and rejected. It takes `checklist.md` from 640 measured words to 91, under the 120-word floor where the stylometric flags switch off, so the change would silence the uniformity detector on exactly the list-heavy documents most worth measuring.

Filtering the paragraph statistics through `is_prose_block()` was measured too, and rejected for the opposite reason: what survives in a list-heavy file is the one-sentence lead-ins, whose length is uniform by nature, so `checklist.md` drops to a paragraph sd of 0.53 and newly trips `uniform-paragraphs` for having short paragraphs that are correct. A bullet is also prose a reader reads, which a `##` is not.

The readme-writing skill had the same rule reading the same shape wrong, from the other direction: a block whose first line was prose and whose remaining lines were bullets scored as one long paragraph. That one was not parked, because nothing published depends on it. It is item 28 above.
