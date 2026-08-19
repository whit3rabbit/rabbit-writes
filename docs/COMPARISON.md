# Seven humanizer skills, compared

**Bottom line: no one repo does the whole job, and no one repo is redundant.** Each owns a layer the others do badly or skip: orwell the override that stops a rule engine making prose worse, blader the false-positive discipline, conor the catalog and the research honesty, brandonwise the measurement, ghostwriter the voice-as-artifact model, petergyang the judgment, hardik the sharpest individual rules. The thing worth building stacks all seven instead of picking one. The layer map is at the end, and the evidence for every claim is in that repo's section.

Cloned 2026-08-10 into a scratch folder. Every line count and feature note below comes from the checked-out tree, not from the READMEs.

| Repo | Last commit | Skill size | Total repo | Executable code |
|---|---|---|---|---|
| petergyang/no-ai-slop | 2026-08-05 | 97 + 44 (eval) | 1,372 | build_plugin.py (packaging only) |
| conorbronsdon/avoid-ai-writing | 2026-08-07 | 806 | 13,343 | 47-type JS detector, validator, corpus harness |
| blader/humanizer | 2026-07-21 | 412 | 819 | validate-package.py (packaging only) |
| hardikpandya/stop-slop | 2026-03-18 | 68 + 321 (refs) | 496 | none |
| brandonwise/humanizer | 2026-08-09 | 156 | 9,478 | 5,128 lines JS: CLI, MCP, API, vitest |
| angelarose210/ghostwriter | 2026-04-07 | 4 skills, 911 | 3,744 | none (3 harness copies of same files) |
| tamdogood/orwell-writing | 2026-08-09 | 66 | (1 of 14 skills) | none |

---

## One-by-one

### 1. petergyang/no-ai-slop

**Shape.** A 97-line SKILL.md plus a separate `eval.md` the model grades its own output against. Ships as a Codex plugin. `scripts/build_plugin.py` validates the manifest and zips a dist archive. No detection code.

**What it does that nobody else does:**

- **The portability test:** "If a sentence could move unchanged to another person, company, country, or product, it is probably filler." One sentence that replaces about forty banned-phrase entries, because it generalizes instead of enumerating.
- **Detect mode refuses to score:** "AI detectors guess. Named patterns are evidence the user can check." It names the pattern, quotes the line, gives the fix, and declines to guess authorship. Every other repo that detects also scores.
- **Minimum effective edit:** "A rough draft with a real voice should still sound like the same person after editing." Cutting is bounded to the actual slop.
- **eval.md as a self-check loop**, with a check that reads "Was the edit checked directly against this file without requiring separate editor and evaluator agents?" It knows the failure mode of its own architecture.
- "Open it up, don't dumb it down." Strip only what impedes reading: jargon, long sentences, abstract nouns, tangled structure. Keep the substance.
- "Protect the specific fact." Don't smooth a useful detail into generic importance.

**Weakness.** Thin catalog. No stylometrics, no false-positive discipline, no context awareness, no voice capture. It trusts the model's judgment almost entirely.

**Verdict: the best judgment layer of the seven.** Borrow the portability test, minimum-effective-edit, detect-without-scoring, and the self-check-file pattern.

---

### 2. conorbronsdon/avoid-ai-writing

**Shape.** 806-line SKILL.md at v3.23.1, and the only repo where the prose rules and the code are held in sync by a contract (`detector/CATEGORIES.md` maps each rule to a detector `type` or marks it judgment-only, and `categories.test.js` enforces the map).

**Scripts and features:**

| File | What it does |
|---|---|
| `detector/patterns.js` | 47 issue types, 0-100 score, trinary HUMAN/MIXED/AI classification, sentence-span highlighting, `contextMode` general/technical |
| `detector/validate.js` | Preservation validator: exits non-zero if a rewrite altered a code fence, frontmatter, blockquote, table cell, inline code, URL, file path, or heading structure, or if it added more tells than it removed |
| `corpus/` + `scripts/fp-measure.js` | Hash-only human-control corpus (public domain 1788-1907, archived pre-2023 blog posts, RAID human rows). Ground truth is provenance, not a judge. Reports FPR/TPR by threshold with Wilson intervals, ROC-AUC, split by register and generating model |
| `scripts/self-scan.js` | Runs the detector on the repo's own docs, publishes raw and exemption-applied scores, gates CI on per-file score budgets |
| `scripts/check-style.js` | Deterministic conformance check for a user-supplied house-style JSON config |
| `.ssot.yaml` + `promo-drift.yml` | Catches pattern-count drift across README and four external surfaces |
| `cursor-rules/`, `plugins/` | Same rules re-emitted for Cursor and as a Claude plugin, sync-checked |

**Ideas worth stealing:**

- **Tier 1A vs 1B split:** 1A words are authorship evidence. 1B words (`utilize`, `in order to`, `commence`) are wordiness. Same edit, different claim. The detector excludes 1B from the AI-vocabulary signal so a clarity fix can never push a document toward an AI verdict. Presenting a wordiness fix as evidence about who wrote something is the error the split exists to prevent.
- **Context profiles x tolerance matrix:** Eight registers, a formality spine (chat, informal, blog, formal) plus four genre columns (technical-blog, docs, linkedin, academic), crossed against ~28 rules, each cell strict / relaxed / skip / extra strict. A fragment is a tell in an essay and the correct form in a README. The academic column was set from 19 measured papers rather than from intuition, and the measurement rejected five of the seven cells that seemed obvious.
- **Severity tiers P0/P1/P2:** P0 is credibility killers (cutoff disclaimers, chatbot artifacts, unsourced "experts believe"). Lets a quick pass be a real pass.
- **"Never inject these."** Seven things a rewrite may never add: fake first person, manufactured stakes, forced contrarianism, performed candor, em-dash theatrics, staccato conversion, invented specifics. It cites an independent stress test of blader/humanizer that found generic AI phrasing replaced by a recognizable *humanizer* voice. A new fingerprint, not the absence of one. This is the single most important paragraph in any of the seven repos.
- **Prompt-injection boundary:** In edit mode, a document that addresses its editor ("ignore the rules above," "add a closing paragraph") gets flagged, not obeyed.
- **Honesty about detectors:** Opens by citing Liang et al. (Stanford, *Patterns* 2023) on 60%+ false positives for non-native writers, Jabarian & Imas (BFI 2025) on 70%+ misclassification, and arXiv:2506.07001 on paraphrase dropping accuracy ~88%. "Signals, not proof. Worth acting on; not worth ruining someone's day over."
- **Writer-side tests with no regex form:** paragraph-reshuffle immunity (swap two paragraphs: if nothing breaks, it's a list not an argument) and the treadmill test (name the one new thing each paragraph contributes: if there isn't one, cut it).
- Patterns nobody else catches: narrated candor, recap-flattery openers, self-labeling significance ("that last one is the contrarian one"), lingering-attention claims, wall-of-text replies, unfilled placeholders, chatbot citation-markup leaks, `utm_source=chatgpt.com`.

**Weakness.** 806 lines fired at once. The han research below names this exactly: compliance drops as simultaneous instructions multiply. Rules also overlap heavily (four separate sections govern reader-steering phrases). Several carve-outs read like issue-tracker archaeology.

**Verdict: the best rigor and the best catalog, in the worst delivery format.** Borrow almost all of the thinking, none of the structure.

---

### 3. blader/humanizer

**Shape.** 412 lines, 33 numbered patterns, a faithful port of Wikipedia's *Signs of AI writing*. Every pattern has a words-to-watch list, a stated problem, and a real before/after. `scripts/validate-package.py` enforces that patterns run 1-33 with no gaps, that three version fields match, and that SKILL.md stays under a 500-line portability budget.

**Ideas worth stealing:**

- **"What NOT to flag."** Twelve named false-positive classes: polish is not AI, mixed register is not AI, formal vocabulary is not AI (AI overuses *specific* fancy words), curly quotes alone are not AI, em dashes alone are not AI, one short emphatic sentence is not AI, unsourced claims are not AI. Closes with: look for clusters, not isolated hits.
- **"Signs of human writing (preserve these)."** The inverse list, and the rarest thing in the seven repos. Specific hard-to-fabricate detail. Mixed feelings and unresolved tension. Dated, era-bound references. Genuine asides and self-corrections. Variety in sentence length. Anything edited before 2022-11-30. This converts the tool from a subtractive scrubber into something that can recognize what to protect.
- **A writing sample outranks the skill's own rules,** including the hard em-dash ban. "Matching the author beats scrubbing the tell."
- **PERSONALITY AND SOUL, with a genre gate:** Sterile writing is as obvious as slop. But: apply this only to essays, posts, opinion. For encyclopedic, technical, and legal text, neutral and plain *is* the correct human voice.
- **Never invent facts,** stated with unusual precision: swapping a vague claim for a specific one is allowed only when the specific comes from the source or the user. Opinions are voice. Facts are not.
- **Invocation modes:** pasted text (show the work), file (edit in place, report a summary), embedded (another agent is calling you, so output prose and no ceremony).
- Draft, then ask two questions ("What makes the below so obviously AI generated?" and "Does the rewrite state any fact not in the source?"), then final.

**Weakness.** The em-dash ban is absolute and wrong as written for many good writers, which the repo half-admits with the sample override. No context awareness, no stylometrics, no code.

**Verdict: the best pattern catalog and the only serious false-positive discipline.** Borrow the two detection-guidance lists nearly verbatim, the sample-override rule, and the genre gate on personality.

---

### 4. hardikpandya/stop-slop

**Shape.** 68-line SKILL.md that delegates to three references. No code. Tuned for essays and posts by someone with a strong personal style.

**Ideas worth stealing:**

- **The false agency table:** The best single table in any of the seven. "Complaints don't become fixes. Bets don't live or die. Decisions don't emerge. Cultures don't shift. Data doesn't tell us. Markets don't reward." AI reaches for these because they avoid naming the actor. Fix: name the human, or use "you" to put the reader in the seat.
- **Vague declaratives:** "The reasons are structural." "The implications are significant." "The stakes are high." A sentence that announces importance without naming the thing. Cut it or replace it with the thing.
- **Meta-joiners:** "The rest of this essay explains..." Delete. Let the essay move.
- **"Two items beat three."** A better instruction than "avoid the rule of three," because it says what to do.
- **"Cut quotables."** If it reads like a pull-quote, rewrite it.
- **A 5-dimension 1-10 rubric** (directness, rhythm, trust, authenticity, density) with a 35/50 revise threshold.
- "Put the reader in the room." No narrator-from-a-distance.

**Weakness.** "Kill all adverbs. No -ly words" and "No em dashes" are absolutes that will damage good prose, and the skill has no carve-outs at all. Zero false-positive discipline. It is a style manifesto, which is fine, but it is not safe to apply to someone else's writing unattended.

**Verdict: the sharpest individual rules, the least safe defaults.** Borrow the false-agency table, vague declaratives, meta-joiners, "two beats three," and the rubric. Discard the absolutism.

---

### 5. brandonwise/humanizer

**Shape.** The only repo that is mostly software. 5,128 lines of JS across a CLI, an MCP server, an HTTP API with an OpenAPI spec, and a vitest suite with calibration fixtures asserting that known-AI samples score above 55 and known-human samples score low.

**Scripts and features:**

| Module | What it does |
|---|---|
| `src/stats.js` | Burstiness, type-token ratio, sentence-length coefficient of variation, function-word ratio, n-gram repetition, Flesch-Kincaid, paragraph stats. Sentence splitter handles abbreviations and initials |
| `src/analyzer.js` | Composite score: 70% weighted pattern density (log scale), 30% statistical uniformity. Emits a separate **reliability score** driven by word count and tells you when the sample is too short to trust |
| `src/humanizer.js` | `autoFix` for transforms with no judgment involved, plus a prioritized suggestion report |
| `src/workflows.js` | `scanPath` across a repo, `compareTexts` for before/after drafts |
| `src/vocabulary.js` | 560+ terms in three tiers, plus a function-word list for stylometry |
| `mcp-server/`, `api-server/` | The analyzer as an MCP tool and as an HTTP service |

**Ideas worth stealing:**

- **The stylometric table with target ranges:** Burstiness: human 0.5-1.0, AI 0.1-0.3. TTR: human 0.5-0.7, AI 0.3-0.5. Trigram repetition: human <0.05, AI >0.10. Numbers a script can check and a model cannot eyeball.
- **`autoFix` as a category:** Some fixes need no judgment: curly quotes, non-breaking spaces, filler substitutions. Separating those from the judgment calls is the right architecture.
- **Hidden-unicode detection:** Zero-width space, ZWNJ, ZWJ, word joiner, BOM, soft hyphen, narrow no-break space. Nobody else looks for these, and they are near-proof of a copy-paste from a chat UI.
- **Reliability gating:** "Treat this score as directional. Re-run on N+ words before making high-stakes calls."
- **Calibration tests:** Fixtures that fail CI if scoring drifts.
- The before/after example in the SKILL.md is the best one in the set: it replaces vague uplift with "Solar panel costs dropped 90% between 2010 and 2023, according to IRENA data."

**Weakness.** The skill file itself is thin on judgment and has no false-positive guidance. Its ground truth is a handful of hand-written fixtures, not a provenance-based corpus. "Add personality" is instruction without guardrails, which is the failure conor documented.

**Verdict: the best measurement layer.** Borrow the stylometric thresholds, the autoFix/judgment split, hidden-unicode detection, and reliability gating by word count.

---

### 6. angelarose210/ghostwriter

**Shape.** Four composable skills (`voice-analyze`, `voice-create`, `voice-apply`, `voice-blend`) shipped in triplicate for `.claude/`, `.hermes/`, and `.openclaw/`. Shared `references/ai-tells.md` is the enforcement core.

**Ideas worth stealing:**

- **Voice as a persistent artifact, not a prompt:** A YAML profile with five 0-1 dimensions (formality, confidence, warmth, energy, complexity) plus prefer/avoid vocabulary, structure preferences, and authenticity markers. It survives the session.
- **Reverse-engineer a profile from samples,** and while doing it, scan the sample for AI tells so the extracted profile doesn't inherit them. If the sample has tells, they go into the profile's `avoid` list and get documented in an `ai_tells_report`. That is the only place in the seven repos that handles a contaminated sample.
- **Weighted blending:** "70% technical-authority, 30% friendly-explainer" interpolates the numeric dimensions and merges vocabulary (union of prefer, intersection of avoid).
- **Authenticity markers** as a checklist: acknowledges uncertainty, shows tradeoffs, uses specific numbers, references constraints.
- A structured output report showing dimension deltas and what the tells pass removed.
- The AI-tells reference is exhaustively categorized by part of speech, which makes it easy to machine-read.

**Weakness.** The ban lists are the broadest and least defensible here: 50 banned verbs, 49 banned adjectives, plus "never use semicolons" and "never use Oxford commas." Applied literally, this produces its own recognizable dialect, which is exactly conor's stress-test finding. The three harness copies triple maintenance for no benefit.

**Verdict: the best voice architecture, the worst banlist.** Borrow the profile-as-artifact model, the contaminated-sample handling, the dimension scales, and the authenticity markers. Do not borrow the lists.

---

### 7. tamdogood/orwell-writing

**Shape.** 66 lines. Orwell's six rules from *Politics and the English Language*, plus an ASD-STE100 Simplified Technical English baseline. The only skill in the set that is a positive discipline rather than a banlist.

**Ideas worth stealing:**

- **Orwell's rule six: "Break any of these rules sooner than say anything outright barbarous."** Every other skill in this set needs this line and none of them have it. It is the master override that keeps a rule engine from producing worse writing than it found.
- **The STE baseline for technical prose:** one action per sentence, same term for the same thing (explicitly *don't* vary to avoid repetition), short noun groups, procedures as condition-action-result, positive instructions, and a hard preserve list for code, commands, identifiers, product names, legal text, and quotations.
- **Explicit creative-writing carve-out:** For fiction and lyrical prose, STE is a clarity aid and never overrides the form. Keep intentional ambiguity, cadence, dialogue style, imagery, character voice.
- **Intellectual honesty:** "Do not claim strict STE conformance without checking the current ASD-STE100 issue and dictionary."
- "Flag any remaining jargon, passive voice, or ornate phrasing that is necessary rather than silently removing important precision."

**Weakness.** No AI-specific content whatsoever. It predates the problem by 80 years, which is the point, but it will not catch `utm_source=chatgpt.com` or a rule-of-three stack.

**Verdict: the best foundation and the best escape hatch.** Borrow rule six as the top-level override, the STE baseline as the technical-register layer, and the creative carve-out.

---

## Table of similarities

Every repo except orwell-writing converges on this core. The count is out of the six AI-focused repos.

| Rule | Repos | Notes on how they differ |
|---|---|---|
| Ban em dashes | 6/6 | Absolute in blader, hardik, ghostwriter. Rate-limited (1/1,000 words, with a list-item carve-out) in conor. Sample-overridable in blader |
| Kill "delve / tapestry / robust / leverage / seamless" class vocabulary | 6/6 | Flat list in petergyang, hardik, ghostwriter. Tiered in brandonwise (3), conor (3 + a 1A/1B split) |
| Kill "It's not X, it's Y" | 6/6 | Only conor catches the split-sentence form, the multi-negation countdown, and the tailing negation |
| Kill superficial -ing analyses | 6/6 | Only conor also catches the non--ing declarative form ("this represents a broader shift") |
| Kill vague attribution ("experts believe") | 6/6 | conor and blader both add: never invent a source to fix it |
| Kill chatbot artifacts and sycophancy | 6/6 | Identical everywhere |
| Kill filler and hedging | 6/6 | hardik is the outlier: cut *all* adverbs |
| Kill generic uplift conclusions | 6/6 | Identical everywhere |
| Kill significance inflation / importance puffery | 6/6 | Same rule, six names |
| Kill copula avoidance ("serves as", "boasts") | 5/6 | Missing only from hardik |
| Kill rule of three | 5/6 | hardik states it best: "two items beat three" |
| Kill synonym cycling | 5/6 | orwell/STE frames it positively: same term for the same thing |
| Kill formatting slop (emoji headings, bold spray, inline-header bullets, Title Case) | 5/6 | conor adds the list-label period tell (`**Intros.**` where a human writes `**Intros:**`) |
| Vary sentence and paragraph rhythm | 6/6 | Only brandonwise and conor give numeric targets |
| Prefer active voice, name the actor | 6/6 | hardik's false-agency table is the sharpest treatment |
| Be concrete; replace abstraction with numbers, names, dates | 6/6 | petergyang's portability test is the best generalization of it |
| Never invent facts | 3/6 | Explicit in blader, conor, petergyang. Absent from hardik, brandonwise, ghostwriter |
| Sterile is as bad as slop; add voice back | 4/6 | Only blader and conor gate it by genre |
| Read-aloud test | 5/6 | Cheapest good check in the set |
| Some kind of scoring | 4/6 | petergyang deliberately refuses to score |

---

## Table of differences

| Capability | petergyang | conor | blader | hardik | brandonwise | ghostwriter | orwell |
|---|---|---|---|---|---|---|---|
| Detect-only mode | yes | yes | no | no | yes | no | no |
| Edit-file-in-place mode | no | yes | yes | no | yes (CLI) | no | no |
| Embedded / silent mode | no | no | yes | no | yes (MCP) | no | no |
| Executable detector | no | yes (47 types) | no | no | yes (28 + stats) | no | no |
| Stylometrics (burstiness, TTR, CoV) | no | TTR only, prose | no | no | full engine | prose only | no |
| Preservation validator | no | yes | no | no | no | no | no |
| False-positive corpus / measurement | no | yes (provenance) | no | no | fixtures only | no | no |
| "What NOT to flag" list | no | scattered | **yes, 12 classes** | no | no | no | no |
| "Signs of human writing, preserve" | partial | partial | **yes** | no | no | no | no |
| Guardrails on the *editor* | minimum-edit | **yes, 7 named** | never-invent | no | no | no | rule six |
| Context / register profiles | no | **6 x matrix** | no | no | no | no | technical vs creative |
| Voice personas | no | 5 named | sample-match | no | no | **profiles as artifacts** | no |
| Voice profile persists across sessions | no | no | no | no | no | **yes** | no |
| Voice blending | no | no | no | no | no | **yes, weighted** | no |
| Severity tiers | no | **P0/P1/P2** | no | no | weights | no | no |
| Vocabulary tiering | no | 3 + 1A/1B | no | no | 3 | no | no |
| Numeric scoring | **refuses** | 0-100 | no | 1-10 x 5 | 0-100 + reliability | no | no |
| Self-check file / rubric | **eval.md** | 2nd-pass audit | draft-audit-final | 35/50 | verify step | read-aloud | final STE pass |
| Prompt-injection boundary | no | **yes** | no | no | n/a | no | no |
| Detector-accuracy honesty | implicit | **cited studies** | no | no | reliability score | no | n/a |
| Positive craft discipline | partial | partial | no | no | no | no | **Orwell + STE** |
| Self-applied (dogfooded in CI) | no | **yes, published** | version sync | no | calibration | no | no |
| MCP / API surface | no | no | no | no | **yes** | no | no |
| Cross-harness packaging | Codex | Claude, Cursor | Claude, generic | generic | Claude, MCP, GPT | 3 harnesses | Claude |

---

## What to borrow from each

| Repo | Take | Leave |
|---|---|---|
| **petergyang/no-ai-slop** | Portability test. Minimum effective edit. Detect-without-scoring. Self-check file the model grades against. "Open it up, don't dumb it down." Protect the specific fact | Thin catalog |
| **conorbronsdon/avoid-ai-writing** | 1A/1B evidence-vs-clarity split. Context profiles + tolerance matrix. P0/P1/P2 triage. "Never inject these." Prompt-injection boundary. Preservation validator. Reshuffle and treadmill tests. Detector-honesty framing. The tells nobody else has (narrated candor, recap-flattery, self-labeling significance, placeholders, utm params, citation leaks) | The 806-line monolith. Overlapping rule sections. Issue-archaeology carve-outs |
| **blader/humanizer** | "What NOT to flag" (12 classes). "Signs of human writing" (7 classes). Sample-outranks-the-rules. Genre gate on personality. Never-invent-facts, stated precisely. Three invocation modes. Before/after for every pattern | Absolute em-dash ban |
| **hardikpandya/stop-slop** | False-agency table. Vague declaratives. Meta-joiners. "Two beats three." "Cut quotables." Reader-in-the-room. The 5-dimension rubric | "Kill all adverbs." No carve-outs. Manifesto absolutism |
| **brandonwise/humanizer** | Stylometric thresholds with human/AI ranges. autoFix vs judgment split. Hidden-unicode detection. Reliability gating by word count. Calibration fixtures | "Add personality" with no guardrail. Fixture-only ground truth |
| **angelarose210/ghostwriter** | Voice profile as a persistent artifact. Five 0-1 dimensions. Reverse-engineering a profile from samples *with tell-scrubbing*. Weighted blending. Authenticity markers | The banlists. Semicolon and Oxford-comma bans. Triplicate harness copies |
| **tamdogood/orwell-writing** | Rule six as the master override. STE baseline for technical prose. Preserve list (code, identifiers, legal, quotations). Creative-writing carve-out. Refusal to overclaim conformance | Nothing. It is 66 lines and all of it earns its place |

---

## Applying the three resources

### testdouble/han, `human-readable-output-standard.md`

This is the architectural correction the whole set needs.

1. **The curse of instructions.** Compliance drops as simultaneous instructions multiply. The standard's answer is to decompose into three layers that fire at different times: structural rules baked into the output template, do/don't pairs supplied as few-shot examples, testable checks run as a separate pass. Conor's 806 lines all fire at once, which is why the repo needs a second-pass audit section to catch what the first pass missed. **The super skill uses progressive disclosure: a short router, references loaded per mode, a script for the mechanical layer.**
2. **It rejects readability formulas as optimization targets.** Flesch and Gunning Fog are poor proxies, disagree with each other, and reward gaming. Brandonwise computes Flesch-Kincaid. The super skill reports it as a diagnostic only and never optimizes toward it.
3. **The audience frame beats the formula.** "Write this for a smart non-expert who has not seen the code" dropped reading difficulty 2-5 grade levels with no accuracy loss across three clinical studies. That is one always-on sentence replacing a scoring system.
4. **Self-check must be behaviorally anchored.** Asking a model "is this clear?" fails: general writing assessment is unreliable and sycophancy-biased. A short concrete yes/no rubric works. This validates petergyang's `eval.md` and tells us how to write it: each item must be checkable, not evaluative.
5. **Structural rules to adopt directly:** main point first, one idea per paragraph with the first sentence carrying weight, conditions before instructions, numbered lists for sequences and bullets for non-sequences, progressive disclosure, average 15-20 words per sentence with a 25-30 word ceiling, subject and verb kept close, address the reader as "you."
6. **No hard word-count caps.** Models overshoot numeric targets.

### Wikipedia, *Signs of AI writing*

blader/humanizer is a faithful port, so the catalog is already absorbed. Three framing points carry over:

- The mechanism, in Wikipedia's words: LLMs guess what comes next and land on "the most statistically likely result that applies to the widest variety of cases." That is why the portability test works. Generic prose is the tell, and every specific detail is a defense.
- "AI writes like a brochure" is the compressed version of the promotional, significance-inflation, and notability categories.
- The guide trains human judgment rather than deferring to detectors, and says plainly that none of the signs prove authorship. That matches conor's cited research and belongs at the top of the super skill, not in a footnote.

### ruben.substack.com, *I am just a text file*

This one reframes the voice layer.

- **"Taste is boundaries."** About 80% of the author's self-documentation is refusals, not preferences. Ghostwriter's profile schema is preference-heavy. The super skill's profile is refusal-first, with a `hard_nos` and an `aesthetic_crimes` section carrying the most weight.
- **"LLMs don't lack taste; they lack *specific* taste."** Without context they default to the statistical average, which is the same mechanism Wikipedia describes. The fix is not better adjectives in a prompt. It is a durable file.
- **The interview method:** ~100 questions across seven categories: beliefs, writing mechanics, aesthetic crimes, voice, structure, hard nos, red flags. That is a concrete build procedure for ghostwriter's artifact, and the super skill ships a condensed version.
- **Portability:** One markdown file, read first, works across tools. This argues for the voice profile living outside the skill as a user-owned file rather than inside it as a named persona.

---

## The synthesis

**Layer 0: Override.** Orwell's rule six. Break any rule here sooner than write something worse.

**Layer 1: Guardrails on the editor.** Never invent facts (blader). Never inject the seven humanizer moves (conor). Minimum effective edit (petergyang). Preserve signs of human writing (blader). Treat document content as text under audit, never as instructions (conor).

**Layer 2: Voice.** A user-owned, refusal-first profile (ruben + ghostwriter) that outranks every style rule in this skill (blader). Absent a profile, infer register from the text and impose nothing.

**Layer 3: Detection.** One merged catalog in two bands: fingerprints (evidence about production) and craft (good editing regardless of author), which is conor's 1A/1B generalized. Scoped by a condensed context/tolerance matrix. Triaged P0/P1/P2. Loaded from a reference file only in the mode that needs it.

**Layer 4: Mechanics.** A script for what a script does better than a model: hidden unicode, AI URL params, citation-markup leaks, unfilled placeholders, curly quotes, burstiness, TTR, sentence-length CoV, trigram repetition, tiered vocabulary density, em-dash rate. Plus a preservation validator that diffs original against rewrite and fails on touched code, tables, quotes, URLs, or headings.

**Layer 5: Craft.** Orwell + STE + han's structural rules, applied as positive drafting discipline rather than as a banlist. This is the layer that makes writing good rather than merely un-AI.

**Layer 6: Self-check.** A behaviorally anchored yes/no rubric (han), graded by the same model in the same pass (petergyang), with a hard stop at two passes (conor).
