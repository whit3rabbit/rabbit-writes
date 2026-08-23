# Self-scan

A tool that flags "delve" in your draft should survive its own pass. This is the result of running `scripts/scan.py` on this plugin's own files, including the unflattering rows.

Reproduce in one command, no dependencies:

```bash
for f in SKILL.md PROOF.md references/*.md references/forms/*.md \
         references/citations/*.md voices/whit3rabbit.md \
         ../voice-setup/SKILL.md ../readme-writing/SKILL.md \
         ../rabbit-reads/SKILL.md ../rabbit-rewrites/SKILL.md; do
  echo "== $f"; python3 scripts/scan.py "$f"
done
```

Run it from `skills/rabbit-writes/`. It covers every row in the table below, including the four in other skills, which an earlier version of this command left out.

Every number below was measured against a particular pattern catalogue, and the heading says which one. `scan.py --json` reports `lexicon_version` and `registers_version` alongside the findings, and `scripts/validate.py` fails when this heading and `lexicon.json` disagree. A table of scores with no version on it is archaeology: somebody has to guess which catalogue produced it, and the guess is usually wrong.

## Result (v0.1.0, lexicon 5, registers 3, measured 23 August 2026, sixteenth pass)

| File | Words | P0 | P1 | P2 | Burstiness | MATTR | Em dash / 1k |
|---|---:|---:|---:|---:|---:|---:|---:|
| `SKILL.md` | 4,891 | 0 | 0 | 0 | 0.71 | 0.71 | 0.0 |
| `PROOF.md` | 9,066 | 0 | 0 | **1** | 0.59 | 0.72 | 0.0 |
| `references/patterns.md` | 3,942 | **5** | **15** | **4** | 0.87 | 0.77 | 1.8 |
| `references/false-positives.md` | 892 | 0 | 0 | 0 | 0.73 | 0.79 | 0.0 |
| `references/injection.md` | 883 | 0 | 0 | **9** | 0.65 | 0.71 | 0.0 |
| `references/context.md` | 720 | 0 | 0 | 0 | 0.68 | 0.78 | 0.0 |
| `references/voice.md` | 1,799 | 0 | 0 | 0 | 0.76 | 0.71 | 0.0 |
| `references/craft.md` | 1,069 | 0 | 0 | **7** | 0.70 | 0.77 | 0.0 |
| `references/checklist.md` | 748 | 0 | 0 | 0 | 0.49 | 0.73 | 0.0 |
| `references/ste.md` | 904 | 0 | 0 | 0 | 0.56 | 0.72 | 0.0 |
| `references/forms/abstract.md` | 571 | 0 | 0 | **5** | 0.70 | 0.71 | 0.0 |
| `references/forms/blog.md` | 400 | 0 | 0 | **4** | 0.81 | 0.71 | 0.0 |
| `references/forms/case-study.md` | 498 | 0 | 0 | **8** | 0.70 | 0.70 | 0.0 |
| `references/forms/chat.md` | 489 | 0 | 0 | **4** | 0.82 | 0.70 | 0.0 |
| `references/forms/docs.md` | 547 | 0 | 0 | **6** | 0.66 | 0.70 | 0.0 |
| `references/forms/email.md` | 590 | 0 | 0 | **5** | 0.76 | 0.69 | 0.0 |
| `references/forms/essay.md` | 520 | 0 | 0 | **5** | 0.86 | 0.67 | 0.0 |
| `references/forms/executive-summary.md` | 465 | 0 | 0 | **5** | 0.57 | 0.64 | 0.0 |
| `references/forms/incident-report.md` | 619 | 0 | 0 | **9** | 0.74 | 0.75 | 0.0 |
| `references/forms/letter.md` | 521 | 0 | 0 | **8** | 0.91 | 0.71 | 0.0 |
| `references/forms/linkedin.md` | 570 | 0 | 0 | **7** | 0.75 | 0.71 | 0.0 |
| `references/forms/literature-review.md` | 680 | 0 | 0 | **9** | 0.70 | 0.70 | 0.0 |
| `references/forms/memo.md` | 477 | 0 | 0 | **5** | 0.63 | 0.69 | 0.0 |
| `references/forms/pentest-report.md` | 677 | 0 | 0 | **8** | 0.65 | 0.74 | 0.0 |
| `references/forms/proposal.md` | 553 | 0 | 0 | **8** | 0.70 | 0.70 | 0.0 |
| `references/forms/research-paper.md` | 781 | 0 | 0 | **9** | 0.73 | 0.71 | 0.0 |
| `references/forms/security-advisory.md` | 613 | 0 | 0 | **10** | 0.78 | 0.74 | 0.0 |
| `references/forms/substack.md` | 601 | 0 | 0 | **6** | 0.75 | 0.69 | 0.0 |
| `references/forms/technical-blog.md` | 461 | 0 | 0 | **6** | 0.71 | 0.72 | 0.0 |
| `references/forms/technical-report.md` | 567 | 0 | 0 | **9** | 0.77 | 0.69 | 0.0 |
| `references/forms/thesis-chapter.md` | 620 | 0 | 0 | **7** | 0.74 | 0.69 | 0.0 |
| `references/forms/whitepaper.md` | 508 | 0 | 0 | **8** | 0.82 | 0.73 | 0.0 |
| `references/citations/apa7.md` | 719 | 0 | 0 | 0 | 0.65 | 0.67 | 0.0 |
| `references/citations/chicago17.md` | 690 | 0 | 0 | 0 | 0.69 | 0.67 | 0.0 |
| `references/citations/ieee.md` | 671 | 0 | 0 | 0 | 0.66 | 0.70 | 0.0 |
| `references/citations/mla9.md` | 685 | 0 | 0 | 0 | 0.63 | 0.69 | 0.0 |
| `voices/whit3rabbit.md` | 1,558 | 0 | 0 | **10** | 0.69 | 0.78 | 0.0 |
| `../voice-setup/SKILL.md` | 3,686 | 0 | 0 | 0 | 0.65 | 0.72 | 0.0 |
| `../readme-writing/SKILL.md` | 2,432 | 0 | 0 | 0 | 0.63 | 0.73 | 0.0 |
| `../rabbit-reads/SKILL.md` | 1,134 | 0 | 0 | **1** | 0.64 | 0.68 | 0.0 |
| `../rabbit-rewrites/SKILL.md` | 866 | 0 | 0 | 0 | 0.62 | 0.70 | 0.0 |

**Every P2 in the `references/forms/` rows is the same finding:** a bold list label ending in a period, which is how `references/craft.md` has always written its own bullets and why it carries seven. The rule is skipped in the `docs` register and these rows are measured with no register at all, which is what the reproduce command above does.

**The sixteenth pass added one row and cleaned another.** `references/ste.md`
documents the STE layer, rewritten here against the code and lexicon that
shipped after its first version described rules and an API that did not
exist, and it enters at zero across all three priorities. `SKILL.md` gained
one word and lost four voice-band semicolons: its `--ste-mode` reference row
listed five option values the flag never had, and the corrected line needed
none of the punctuation the fictional one carried. Nothing else moved, the
right shape for an edit that only touched documentation.

**Two skill rows arrived in the fifteenth,** `../rabbit-rewrites/SKILL.md` for the new skill, and `../rabbit-reads/SKILL.md`, which was missing from a table claiming to cover this plugin's own files. Both land at 0 P0 and 0 P1. The one P2 on `rabbit-reads` is the bold-list-label rule that every `references/forms/` row carries, described above. One older row moved without anybody editing it for style: `SKILL.md` gained 146 words when its mode section grew a thesaurus step.

**Thirteen forms were added two passes before,** nine business and security ones (`memo`, `executive-summary`, `technical-report`, `proposal`, `whitepaper`, `case-study`, `incident-report`, `security-advisory`, `pentest-report`) and four academic ones (`research-paper`, `abstract`, `literature-review`, `thesis-chapter`). All thirteen land at 0 P0 and 0 P1 on the first measurement. Three older rows moved without anybody editing them for style, which is what a stale table looks like: the two satellite `SKILL.md` word counts and `references/patterns.md`'s burstiness had drifted since the twelfth pass.

**The four `references/citations/` rows score zero across all three priorities,** which is worth a sentence because they are the only files in this plugin that ship literal strings on purpose. A reference-entry pattern is a mechanical format with no voice in it, and every one of them is a fenced code span, so `apply_exemptions` blanks it before any rule runs. That is the correct outcome and it is also the reason these rows prove less than the others: the engine is scoring the prose around the formats, not the formats.

Nothing in this engine validates a citation. There is no check that a DOI resolves or that a cited work exists, and a green scan on a fabricated reference means the scan did not look. `scripts/test_validate_checks.py` covers the part that is checkable: that a style file cannot ship an example sentence, and that all four styles carry a row for the same eleven source types, so picking a style is never also picking which sources a writer may cite.

Two findings in those files were real and were fixed rather than published. `forms/docs.md` raised a significance-inflation P0 on a phrase it was naming to describe a tolerance, and it now names it in a code span, which is what the quoted-example exemption is for. `forms/substack.md` raised a self-labeling P1 on a sentence announcing that the point it had just made was the important one.

Scores are with the self-reference exemption applied, the rule this skill states in prose: quoted examples, code, tables, and block quotes are exempt from flagging. `apply_exemptions()` in `scan.py` is that rule's executable form. Run with `--no-exempt` to see the raw numbers.

Two patterns opt out of it, `curly-quote` and `citation-leak`, and each says why in a `_scan_raw_note` in `lexicon.json`. Both are facts about how a file was produced rather than about what it says, and the exemption is about content. A chat citation marker pasted into a block quote is the likeliest place one appears and was the one place nothing looked.

Every word count in this table dropped between the second review and the third, and no prose was cut. Item 32 below is why: heading text and block quotes used to be measured as this document's own sentences. The findings columns did not move with them, because flagging already exempted both.

The counts moved again in the fourth pass, this time because the documents changed: the engine was extracted into `scripts/rwlib/`, the tolerance matrix became a data file, and three skill files gained sections. `voices/whit3rabbit.md` fell from 9 P2 hits to 7 by dropping two paraphrases of rules that are defined elsewhere, which is the same drift the one-definition tripwire in `scripts/validate.py` now fails the build over.

The sixth pass added the `safety` band, and the only column it moved is its own. `references/injection.md` is new and scores 9 P2 hits on itself, which is the same story `patterns.md` tells one rule further on: a file that lists the directive shapes it catches will match them. Every one is visible in running prose or a list, which is exactly the finding the band raises at P2 and calls quotable rather than concealed. Zero P0s anywhere in this table, including on the file that documents the attack.

This file carries one of its own now, for the same reason: the `forget` paragraph below quotes an attack shape to say what the rule matches, and the band reads raw text, so a fence would not have hidden it and hiding it was never the point.

That number is left visible for the reason the `patterns.md` paragraph above gives. The alternative was to fence every example so the exemption swallows it, and the band deliberately does not honour the exemption, so fencing them would have proved nothing except that the author knew where the blind spot was.

**Measured against somebody else's writing, not just ours.** The band was run over the 100-README corpus in `docs/readme-analysis/repos/` before it was wired into anything, because a P0 here fails `--check`, and `--check` is what the `rabbit-scan` pre-commit hook runs in a stranger's repository.

| Finding | 100 trending READMEs |
|---|---:|
| `injection-hidden-directive` (P0) | 0 |
| `injection-tag-smuggling` (P0) | 0 |
| `injection-hidden-text` (P1) | 4 |
| `injection-visible-directive` (P2) | 0 |

Zero P0s is what makes the hook gating defensible, and `test_no_corpus_readme_raises_a_safety_p0` asserts it rather than reporting it: a tightening that puts a P0 on ordinary documentation has to be argued before it ships, not after somebody's commit is blocked.

The 4 P1s are the honest cost. All four are maintainer notes in HTML comments, two of them the same "Keep these links. Translations will automatically update with the README." A build-marker allowlist cut the raw count from 8 to 4, and the remaining four are prose somebody wrote rather than a marker a tool emits, which is exactly what the P1 says. Tuning them away would mean either dropping the rule or special-casing four repositories, and the number is published instead.

The concealment tables that landed beside the band were held to the same bar. Directional formatting, variation selectors, Hangul fillers, braille blanks, tag-character residue below the smuggling threshold, entity spellings of the invisibles, and the category sweep for unlisted format and control characters were each run over the same 100 READMEs after wiring: zero findings from all of them, at every priority. The only `hidden-unicode` hit in the corpus is one README's 1,134 non-breaking spaces, which the space-like rule already reported before any of this existed. The tolerances (three direction marks, three braille blanks, the emoji carve-outs for the joiner and the presentation selectors) are what that zero cost, and each one is pinned in `tests/test_hidden_text.py`.

Three directive families were cut or narrowed against that corpus before anything shipped. `instead of editing` is ordinary English. An unanchored agent-noun rule read `state model, output formats` and `In your agent, run it once per repo` as instructions. A bare `forget everything` matched "the three essentials (if you forget everything else)" in two of this plugin's own voice profiles. Each was measured, not guessed.

The `forget` family took a second pass, in review rather than against the corpus, because the corpus never showed it: requiring one pronoun after the verb left `forget you|your|what`, which is `don't forget your API key` and `I'll never forget what happened`. In visible prose that is a P2 nuisance. In an HTML comment it is concealment plus a directive, so it is a P0 that halts `--apply-safe` on somebody's own maintainer note, and the safety band takes no suppression by design. It now matches the whole instruction shape, which also picked up `forget the above instructions`, an attack the pronoun version never saw. Corpus counts are unchanged: 0 P0, 4 P1, 0 P2.

**One design decision came out of review rather than measurement.** The safety band cannot be suppressed. Every other band answers to `rabbit-allow`, and that comment lives inside the document being scanned: whoever can plant a concealed instruction can plant the comment excusing it, and both arrive in the same file from the same hand. A suppression naming a safety id is refused and reported at P1 rather than silently ignored. `test_a_safety_p0_cannot_be_suppressed` holds it.

The twelfth pass moved one row and no findings column. `../voice-setup/SKILL.md` grew to 3,379 words where the measured thesaurus is now documented: the words-to-reach-for table, the proposals it prints, and the families file beside the script. Its burstiness and MATTR moved with the words, and the voice table below still carries its six serial-comma advisories.

The eleventh pass moved four word counts and no findings column, and one of the four had been wrong before any document changed. `SKILL.md` published 3,806 against 3,860 measured at the time, a transposition nobody caught, and it has since grown to 3,987 where opt-in register auto-detection is documented. `references/injection.md` gained the sentence saying a quoted span in a report is data rather than an instruction, and it is the only row whose burstiness moved with its words. `../voice-setup/SKILL.md` gained the `--out` flag and the note that `--scaffold --activate` is refused until a profile passes its own check, and `../readme-writing/SKILL.md` lost ten words tightening the table-of-contents threshold. Every P0, P1, and P2 column is where it was.

The ninth pass moved one row, this file's, and it moved a findings column. A bug-fix pass narrowed the `forget` rule and the paragraph explaining it quotes an attack shape, which the safety band reads and reports at P2 the way it reports the nine in `references/injection.md`. Two other fixes could have moved a column here and did not: tier-1 words no longer double-count a tier-1 phrase they sit inside, which cost nothing in this table because both hits were in exempted spans, and `verify.py` stopped reporting a path inside a table row twice, which nothing in this table measures.

The eighth pass moved four rows and no findings column. `SKILL.md`, `references/voice.md`, `references/checklist.md`, and `../voice-setup/SKILL.md` grew where the attainment gate, the caricature guard, the fact check, the plan-then-execute rule, and the samples-plus-interview route are documented. Every one of them still scores zero at every priority.

It caught this document once on the way, which is the only reason worth publishing a self-scan at all. The paragraph introducing the reconstruction eval used "harness" twice and the engine reported a Tier-2 cluster, and the section on the fact-check carve-outs ran to six sentences against a five-sentence cap in the active voice. The prose was changed, not the rules.

The fifth pass moved them for the same reason and not because the engine changed its mind about anything above. `voices/whit3rabbit.md` gained the Quick reference card and Anti-overfitting sections that `TEMPLATE.md` has always had and the worked example did not, which is 335 more words and three more list-label advisories. `references/voice.md`, `SKILL.md`, and `../voice-setup/SKILL.md` grew where blending, per-register mechanics, and `measure_voice.py` are now documented. Every P0 and P1 column is where it was.

The seventh pass moved three rows, and two of them are the plugin failing its own rules in public. `../readme-writing/SKILL.md` dropped from 7 P2 hits to 0: every one was `list-label-period`, its own craft band firing on its own bolded list labels. `../voice-setup/SKILL.md` went from 1.3 em dashes per 1,000 words to 0.0, which matters because the active voice forbids em dashes outright and `CLAUDE.md` states that as the repo's convention. `SKILL.md` grew where `--voice auto` and the `PROOF.md` reference row are now documented. No P0 or P1 column moved anywhere.

One of those em dashes is worth naming, because the scan did not find it and a reader has to. An em dash on a list line that also carries an inline code span is not reported, while the same dash on a plain list line is. Two of the three in `../voice-setup/SKILL.md` sat behind a code span in exactly that shape. They were found by sweeping the file for codepoints above 127, which is the habit `CLAUDE.md` already prescribes for invisible characters, and the same habit turns out to catch a visible one the counters miss.

Those same three rows moved once more when the voice fingerprint landed, and for the same reason: `SKILL.md`, `references/voice.md`, and `../voice-setup/SKILL.md` are where it is documented. `references/voice.md` picked up a second serial-comma advisory with the words. No P0 or P1 column moved.

`../voice-setup/SKILL.md` grew again with `build_voice.py`, which is where scaffolding a profile and proving its rules fire are now documented, and picked up a fifth serial-comma advisory with the words. Same story as every row above it: the document changed, the engine did not, and no P0 or P1 column moved.

## What it found in our own writing

**`patterns.md` scores worst, and that is structural.** A catalog listing the words it catalogs will hit its own lexicon. Three Tier-1 words, nine `-ing` analyses, and three Tier-2 clusters all come from the vocabulary tables: the comma-separated lists of the words each rule exists to catch. Those are unquoted by design, because quoting a 36-item list would make it unreadable.

**The 5 P0s on `patterns.md` are the same story, one rule further on.** Line 46 lists the five chat citation markers in backticks, and `citation-leak` stopped honouring the exemption in lexicon 2, so each one now scores. That is the cost of catching a marker pasted into a block quote, which is where a real one usually lands. This file pays it in full and publishes the number.

Two options were available in both cases. Quote every list entry so the exemption swallows it, or leave the number visible and explain it. The number is left visible. A tool that suppresses its own findings to look clean is doing the thing this plugin exists to criticize.

Anyone enabling the `rabbit-scan` pre-commit hook on a repository that writes about slop detection inherits this, so the hooks file says so and points at `files`.

**`craft.md` has 7 P2 hits.** The boilerplate detector firing on "the intersection of" and the transition detector firing on paragraph-initial "Additionally" inside rule text. Real hits on prose that is quoting rules rather than following them.

**`readme-writing/SKILL.md` used to carry 8 em dashes per 1,000 words,** the highest rate in the plugin and above the 6.0 human-range ceiling. An earlier version of this file left that visible rather than fixing it, on the grounds that publishing the number was the honest move.

That was half right. `CLAUDE.md` states the repo's prose convention as no em dashes and no semicolons, so leaving them made the convention untrue rather than making the report honest. The prose was rewritten instead. The file now reads 0.0 per 1,000 words and 0 voice hits, and the P1 it used to carry is gone with them.

**`checklist.md` has the lowest burstiness at 0.46.** A numbered checklist is supposed to be metronomic. This is the detector correctly measuring a shape that is correct for its genre and wrong for prose, which is why `context.md` exists and why a number never renders a verdict on its own.

## The new register, measured on somebody else's documents

`informal` is the one column the forms work added rather than renamed, and a column that quietly reports nothing is the failure mode `curly-quote` already demonstrated once. Run over the same 100 trending READMEs in `docs/readme-analysis/repos/`:

| Priority | 100 trending READMEs, `--profile informal` |
|---|---:|
| P0 | 0 |
| P1 | 249 |
| P2 | 1,077 |

Zero P0s is the number that matters, for the same reason it matters in the safety table above: `--check` is what the `rabbit-scan` pre-commit hook runs in a stranger's repository. A README is a `docs` document and nobody would scan one under `informal` on purpose, so this measures the column against ordinary prose rather than against its own genre.

It is a published number rather than a test, deliberately. A corpus sweep costs about a second per document per register in process, so asserting this for every register would add several minutes to a suite that already runs about 2:20 for weaker coverage than the per-cell tests give. `tests/test_registers.py` exercises every cell in the matrix instead: every skip cell has to silence a document that fires without it, and every relaxed cell has to stay silent at its allowance and report past it. That is the property `curly-quote` violated, checked on every cell rather than sampled.

## The academic register, and the five cells the corpus rejected

`academic` is the second column added rather than renamed, and it is the first one calibrated against a corpus assembled for the purpose: 19 open-access PLOS papers, 72,704 words, six subject facets, all CC BY 4.0. `docs/academic-corpus/README.md` has the method and `docs/academic-corpus/summary.json` has the full table. Every number here is per document rather than per hit, because that distinction is what set the exemption list.

| Finding | `formal` | `academic` |
|---|---:|---:|
| `tier1` | 17/19 | 9/19 |
| `trigram-repetition` | 17/19 | 0/19 |
| `confidence-calibration` | 14/19 | 2/19 |
| `uniformity` | 13/19 | 0/19 |
| `tier2-cluster` | 11/19 | 7/19 |
| `clarity` | 14/19 | 14/19 |
| `vague-attribution` | 3/19 | 3/19 |

**The cells that are not in the matrix are the interesting half.** Five were expected to need tolerances and were dropped because the corpus said they fire on at most one paper in nineteen: `uniform-paragraphs`, `em-dash-rate`, `rhetorical-question`, `signposting`, and `hedge-stack`. `tier3-density` is the sharpest case. A synthetic paper written to test the register fired it on `significant` and `effective`, which is why both words were on the draft exemption list, and no real paper fires that rule at all: it needs 2% of every word in the document and nothing reaches it. Two words were exempted on the strength of a sample that did not exist.

**The exemption list is three words because a document count disagreed with a hit count.** `holistic` raised 11 tier-1 hits and appears in fewer than two of the nineteen papers, which is one author's habit and not a fact about the register. `crucial` is in six papers and was still rejected, because it means the same thing in every register and is an intensifier rather than a term. What survived is `paradigm`, `paradigms`, and `transformation`, each carrying a sense in a paper that it does not carry in a blog post.

**`clarity` is unchanged on purpose.** `utilize`, `in terms of`, and `it is important to note that` fire on 14 of the 19 papers, and academic writing being full of them is a fact about academic writing rather than a reason to stop reporting it. Academic style guides say the same.

**Detection, and the measurement that was circular the first time.** `--profile auto` now returns `academic` when a document's headings cover three distinct IMRaD categories. Threshold and vocabulary both come from the corpus.

| Threshold | README false positives | Papers detected |
|---|---:|---:|
| 2 categories | 1/100 | 18/19 |
| 3 categories | 0/100 | 17/19 |

Three, because zero false positives is the bar every other entry in `DETECTABLE_REGISTERS` cleared and the one document at two is a README with `Test Results` and `Limitations` in it. The two papers missed at three are a computer-science paper using Method and Experiments and a humanities paper whose middle sections are named after its argument. Both fall through to the default register, which is what an unclassified document has always done.

The first version of the recall column read 19 of 19, and it was measuring nothing: it ran against `docs/academic-corpus/texts/`, whose headings this repository's own extractor writes. The numbers above are against the papers' real JATS section titles, refetched for the purpose. That is also where the heading vocabulary came from, which is why `methods` matches methodology and materials and methodology, and why a leading section number is stripped before anything is matched.

**The false positive that was fixed in the rule rather than in the matrix.** `vague-attribution` is a fingerprint P0 and fired on `research suggests` and `studies show` in 6 of the 19 papers, 13 hits. In a paper those phrases usually carry a citation the engine could not see. A relaxed academic cell was the wrong fix and the suite said so: a fingerprint P0 is never skipped or relaxed in any register, and `test_no_p0_fingerprint_is_skipped_or_relaxed_anywhere` rejected the cell immediately. Narrowing the rule is the fix that is allowed, so in lexicon 4 the pattern stands down when a citation marker arrives before the sentence ends.

| | Papers | Hits |
|---|---:|---:|
| lexicon 3 | 6/19 | 13 |
| lexicon 4 | 3/19 | 4 |

**The window is the sentence, and a character count would not have worked.** Over the corpus the marker sits 55 to 170 characters past the phrase and never inside 40, so the obvious narrowing (a short fixed window) suppresses none of the 13. Both marker shapes are matched (a numeric bracket and an author-year parenthesis) because the plugin ships citation styles of both kinds. The author-year half requires a capitalised surname, or `(Q1 2024 data)` reads as a source.

**The 4 that remain are correct, and they are why this is not a mute.** Three papers use one of these phrases with nothing cited anywhere in the sentence, which is the thing the rule exists to catch. `scan.py --check` still fails on those three, and the 100-README corpus is unmoved at 0 P0 before and after: the one raw hit there is a table cell quoting the pattern as an example, and the quoted-example exemption was already blanking it.

## The voice band, applied to ourselves

The active voice is `whit3rabbit`, whose rules ban em dashes, semicolons, emojis, one-word sentences for emphasis, US date order, paragraphs over five sentences, and a specific buzzword list. Running the plugin against those rules:

Every file is listed this time. An earlier version of this table showed five, which flattered the result: the reference files were carrying em dashes and semicolons that nobody had counted in public.

| File | Voice hits | What they are |
|---|---:|---|
| `../rabbit-rewrites/SKILL.md` | 0 |  |
| `../readme-writing/SKILL.md` | 0 |  |
| `references/craft.md` | 0 |  |
| `references/forms/case-study.md` | 0 |  |
| `references/forms/docs.md` | 0 |  |
| `references/forms/essay.md` | 0 |  |
| `references/forms/incident-report.md` | 0 |  |
| `references/forms/memo.md` | 0 |  |
| `references/forms/proposal.md` | 0 |  |
| `references/forms/research-paper.md` | 0 |  |
| `references/forms/security-advisory.md` | 0 |  |
| `references/forms/substack.md` | 0 |  |
| `references/forms/technical-report.md` | 0 |  |
| `references/forms/thesis-chapter.md` | 0 |  |
| `references/forms/whitepaper.md` | 0 |  |
| `references/injection.md` | 0 |  |
| `references/checklist.md` | 1 | serial-comma advisory |
| `references/citations/apa7.md` | 1 | serial-comma advisory |
| `references/citations/chicago17.md` | 1 | serial-comma advisory |
| `references/false-positives.md` | 1 | serial-comma advisory |
| `references/forms/blog.md` | 1 | serial-comma advisory |
| `references/forms/chat.md` | 1 | serial-comma advisory |
| `references/forms/email.md` | 1 | serial-comma advisory |
| `references/forms/executive-summary.md` | 1 | serial-comma advisory |
| `references/forms/letter.md` | 1 | serial-comma advisory |
| `references/forms/linkedin.md` | 1 | serial-comma advisory |
| `references/forms/literature-review.md` | 1 | serial-comma advisory |
| `references/forms/technical-blog.md` | 1 | serial-comma advisory |
| `references/ste.md` | 1 | serial-comma advisory |
| `references/citations/ieee.md` | 2 | serial-comma advisories |
| `references/citations/mla9.md` | 2 | serial-comma advisories |
| `references/forms/abstract.md` | 2 | serial-comma advisories |
| `references/forms/pentest-report.md` | 2 | serial-comma advisories |
| `references/voice.md` | 2 | serial-comma advisories |
| `../rabbit-reads/SKILL.md` | 3 | serial-comma advisories |
| `references/context.md` | 3 | serial-comma advisories |
| `voices/whit3rabbit.md` | 4 | serial-comma advisories |
| `../voice-setup/SKILL.md` | 6 | serial-comma advisories |
| `PROOF.md` | 6 | serial-comma advisories |
| `SKILL.md` | 6 | serial-comma advisories |
| `references/patterns.md` | 25 | 10 em dashes, 7 semicolons, 2 one-word sentences, 6 advisories |

The serial-comma rows are the `oxford_comma` mechanic, which reports at P2 and never at the voice default. It cannot tell a three-item list from a compound sentence, so it advises and says so in the finding. Counting advisories as defects would be the same error in the other direction.

**`patterns.md` is the deliberate exception.** The engine is voice-agnostic. Forcing a general reference file to conform to whichever person happens to be active would be the wrong direction, because the engine serves every voice and so follows none of them. Its em dashes and semicolons sit in before and after examples of the patterns themselves, in a form the quoted-example exemption does not recognize. That is a fair thing to hold against the file and it is left visible.

**`context.md` used to carry six, and four of them were the voice persona block,** where each persona is one dense line of targets. A definition list is not a paragraph, and the paragraph-length rule reads it as one. Those four were parked for two releases on the grounds that rewriting a reference table into prose to satisfy a prose rule is the tail wagging the dog, which is still true and is not what unparked them. Each persona ended its line with the registers it suits, a trailing italic sentence that is a label rather than a claim, and moving it into the persona's own label takes all five under the cap without cutting a target or adding filler. The rule still reads a definition list as a paragraph, and that half is still parked at the end of this file.

**An early run found nine semicolons in `whit3rabbit.md`, in a profile that bans semicolons.** They came from the source style guide, which used them while forbidding them. Fixed by splitting the sentences, which is what the rule asks for. This is the case the voice band exists to catch: a person's stated rules and their actual habits disagreeing, in the document that is supposed to define them.

**Merging the two prose skills introduced one of its own.** The "Paths." paragraph, added to every `SKILL.md` so Codex users can resolve `${CLAUDE_PLUGIN_ROOT}` by hand, used a semicolon. Three files, one sentence, caught by this scan and split.

### The voice distance is not calibrated on anybody real yet

`voice-distance` is new, and this table cannot exercise it: no profile in this repository ships a fingerprint, because a fingerprint is built from a person's writing samples and this repository has none of the author's. Nothing in the table above moved, and nothing in a stranger's repository moves either, since the finding only exists where a `voices/<name>.fingerprint.json` does.

What the measure has been tested against is two synthetic voices in `tests/test_stylometry.py`: four samples on four unrelated subjects in one register, a fifth held-out sample by the same writer, and a formal committee report. The held-out sample lands inside the band, the report lands at roughly 1.6x it, and the markers the report is charged with are `furthermore`, `therefore`, and `however`. That is the property the module claims and it is the property a test can own without a real person's prose in the repository.

It is not evidence that the band separates two real writers of similar register, that a person's own samples cluster as tightly as these fixtures do, or that the three verdict thresholds are set at the right places. Those need real profiles, and the honest reading until then is that the number is a signal to look at rather than a measurement to trust. This is why it is P2, why it never fails `--check`, and why the finding text says the measure cannot tell a deliberate change of register from a conversion that did not land.

Two known limits are structural rather than uncalibrated. The marker list is English, like every other calibration in this engine. And a document shorter than 250 words is measured and reported with the number, with no finding raised off it, because below that the marker rates are sampling noise.

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
| `tests/samples/ai-sample.md` | 41 | 7 | 0.66 |
| `tests/samples/human-sample.md` | 0 | 0 | 0.62 |
| `tests/samples/metronomic-sample.md` | 1 (uniformity) | 0 | 0.07 |
| `tests/samples/needs-conversion.md` | 14 | 10 | 0.21 |
| `tests/samples/already-in-voice.md` | 0 | 0 | 0.54 |

`ai-sample.md` reads 41 now rather than the 44 an earlier pass published, and the three findings it lost came from two engine fixes this table was never regenerated for. Two were `formulaic-challenges` hits on "the team faces challenges next quarter", which item 36 narrowed to the formula section 45 actually describes. The third was `pivotal` counted a second time inside `marking a pivotal moment`, the double-count the ninth pass above already names, where it cost this table one finding and the self-scan table none. The fixture has not been edited since it was written, and `tests/test_calibration.py` asserts a floor of 20 findings rather than the published figure, which is why nothing failed while that figure aged.

The metronomic fixture matters most for the craft bands. It contains no flagged vocabulary, no chatbot artifacts, and no negation runways. It still reads as machine output because every sentence is the same length. Vocabulary and rhythm are independent axes, and a draft can pass every word check and fail the read-aloud test.

The last two fixtures measure a different thing: whether the inputs to a conversion offer actually fire. `needs-conversion.md` is a report in a neutral register, structurally wrong for the active profile, and it reports 6 over-cap paragraphs, 4 banned words, a numeric date, and burstiness of 0.21 against a human floor of 0.45. `already-in-voice.md` says the same things in the profile's shape and reports nothing at all.

`needs-conversion.md` gained a section in the third review pass, for a reason worth naming. Fixing the heading measurement in item 32 took the fixture from 620 measured words to 596, four short of the 600-word floor where this engine calls a sample reliable, and a fixture whose whole job is to be long enough for the numbers to mean something failed that assertion on a rounding error. The prose was extended rather than the assertion relaxed.

Neither fixture proves the skill chose a deep rewrite when it should have. Mode selection is prompt behaviour and no script in this repo can assert it. What they protect is the measurement the offer is built from, so the numbers a user sees before deciding are real.

## The two detectors that came with the attainment gate

Both were calibrated before they were wired to anything, which is this repository's rule for a new detector, and both zeros are asserted in a test rather than reported here.

**`voice-caricature`, the overshoot check.** The obvious form of this rule does not work, and the number is the reason the four qualifications exist. Leave-one-out over 13 documents by this repository's writer that clear the reliability floor, rule "any of the six measures outside the sample min-max":

| samples | fires on a held-out document by the same writer |
|---|---:|
| 3 | 95.5% of 2,860 pairs |
| 4 | 90.7% of 6,435 pairs |

That is a constant, not a detector. Min and max over three samples are two order statistics with enormous variance, and with three samples two of them define the envelope. With direction, a magnitude floor in sample sd, an envelope pad, and a two-measure minimum:

| population | fires |
|---|---:|
| same-author leave-one-out, 3 samples | 2 of 2,860 (0.1%) |
| same-author leave-one-out, 4 samples | 0 of 6,435 |
| same-author leave-one-out, 6 samples | 0 of 12,012 |
| 100 trending READMEs against a 4-sample profile | 0 of 80 measurable, 20 skipped |

**Read that last row twice, because it is weaker than it looks.** As a false-positive rate it is zero. As exposure it is close to meaningless, because the guard only runs when a fingerprint resolved and a stranger's repository has none. What it answers is "if somebody pointed a profile at these, would it be a wall of findings", and the answer is no. The 20 skipped are documents under 25 prose sentences, where burstiness is noise, and they are reported as skipped rather than counted as clean.

The base is 13 documents by one writer in one genre. That is thinner than the 100-README corpus and it should be read as thinner. What keeps the rule honest in the other direction is that it still fires: a document in this writer's register with the register turned up, sentences chopped to a quarter of their own shortest and contractions at twenty times their own rate, is reported, and `test_the_guard_still_fires_on_a_document_that_is_actually_a_caricature` pins that. A rule that never fires passes every restraint test ever written and is indistinguishable from no rule.

**Fact preservation in `verify.py`.** Numbers, dates and quotations, compared as multisets after canonicalization. The corpus is 100 single documents and this check needs pairs, so it measures exposure and reformat-tolerance rather than a paired false-positive rate, and it says so.

| measurement | result |
|---|---|
| raw numeric tokens in the corpus | 13,098 |
| after blanking code, tables, quotes, URLs, paths and entities | 6,028 prose facts, median 26 per document |
| plus 278 dates and 300 quotations | |
| identity: `validate(text, text)` | 0 of 100 lose a fact |
| null edit through `fixes.apply` | 0 of 100 |
| eight benign reformats, applied outside quotations | 0 of 100 each |
| one prose number corrupted | caught in 65 of 65 applicable documents |

The eight reformats are the carve-outs stated as tests: strip thousands commas, percent sign to the spelled word, dash range to "10 to 20", add a `v` to a version, ISO date to spelled and back, straight quotes to curly, rewrap paragraphs, collapse runs of spaces. Each one is a rewrite this skill actually instructs, and each is one carve-out's regression test.

Five of those carve-outs exist because the corpus produced a false positive nobody would have guessed:

- a percent-encoded anchor link read `97%` out of `%AD%97%E5`
- `$1,000` matched only its tail and reported a 0
- a sentence-final number was dropped entirely, by a lookahead that refused a following full stop
- a spaced em dash between two numbers read as a range and fragmented `1,237` on the way
- an HTML attribute value read as somebody's quotation, in 55 of the 100 documents, which is the one that would have been noticed last

Two limits, stated rather than papered over. Spelled numbers are not tracked at all, because "three" against "3" is a style edit a profile can legitimately require in either direction. And a paired corpus does not exist: `docs/voice-eval/` is where one would go, and it is empty.

## The reconstruction eval

`scripts/voice-eval/` scores the whole pipeline end to end with labels nobody had to write: take a piece the writer actually wrote, deslop it into a neutral register, convert it back, and measure how much of the distance the round trip closed. The original is the answer key, so no human judgement enters the metric.

**The corpus is empty, and the harness is not**, which is the same arrangement `docs/detector-corpus/` has and for the same reason. Gathering real writing from a real person with their consent is the expensive half, and a scorer written afterwards gets written to fit whatever data turned up. `scripts/voice-eval/test_eval_harness.py` runs it over synthetic triples with known answers, in CI, so the day somebody populates the corpus the arithmetic is already known to work: a round trip that landed scores above 0.9, one that moved nothing scores near 0, and one that went backwards scores negative.

Until then, the pipeline's end-to-end behaviour rests on the fixtures in `tests/`, which own their ground truth and are not real writing. That is the same disclaimer the section below makes about the detector corpus, and it is not a smaller one.

## Which models clear the rewrite gate

`skills/rabbit-rewrites/scripts/bench.py` sends the twelve-passage battery through a configured endpoint and scores every reply against the same gate `--apply-model` uses: `verify.py` on the passage, the phrase gone, the finding count down. Three passes each, 45 units per model, on one laptop. The raw JSON is in `docs/model-bench/`.

```bash
python3 scripts/model-bench/run.py --model qwen2.5:7b --model gemma2:latest --repeat 3
```

| Model | Served by | Accepted | First try | Findings | Sec / passage | Facts dropped |
|---|---|---:|---:|---|---:|---:|
| `Qwen3.5-0.8B` Q4_K_M | llama-server | 23 / 45 (51%) | 19 | 66 -> 31 | 0.50 | 2 |
| `qwen2.5:7b` | ollama | 27 / 45 (60%) | 27 | 66 -> 9 | 1.45 | 4 |
| `gemma2` 9B | ollama | 33 / 45 (73%) | 30 | 66 -> 3 | 2.34 | 22 |

**The last column is the reason the gate exists.** `gemma2` has the best pass rate in the table and dropped a number, a date or a quotation on 22 of its 45 passages, roughly one attempt in two. `qwen2.5:7b` did it 4 times. Ranked on pass rate alone, `gemma2` wins and is the worse tool. Every one of those 22 was caught and none reached a document. A rewriter with no preservation check would have shipped all of them, and the only symptom would have been a number quietly changing in somebody's draft.

**An 0.8B is a usable engine for this, which is the claim the design rests on.** It clears half the passages, three times faster than the 7B, and its rejections are mostly harmless (`the model returned` the passage unchanged, x32). It leaves more findings behind, so the honest description is a first pass rather than a finish. On a Raspberry Pi the seconds-per-passage will be worse and the pass rate will not move, because the pass rate is a property of the weights.

**Thinking on is a 0% pass rate.** Measured before the client learned to turn it off: `Qwen3.5-0.8B` scored 0 of 15, every rejection `stopped at max_tokens`, because it spent all 640 output tokens on a reasoning block and returned empty content, at 8.58 seconds a passage. Off, the same model and battery scored 10 of 15 at 0.47. Most current small models are hybrid reasoning models, so this is not a footnote about one file.

**One pass over twelve cases is not a rate.** The same 0.8B scored 67% on a single pass and 51% over three. `--repeat` exists because of that gap, and the table above is the three-pass number in every row.

**What this does not measure.** Grammar, and whether the result sounds like anybody. The gate proves a rewrite kept every number, date, path and quotation and lost the tell it was sent to remove. `qwen2.5:7b` produced "lets teams to use" in an early run and it passed every check here, because it is a fluency problem and nothing in this engine reads for fluency. Read the diff.

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
