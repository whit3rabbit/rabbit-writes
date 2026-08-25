# Changelog

## Unreleased

Six passes. The first was architecture and evidence and changed nothing about
what the engine flags. The second changes it in six places, the third resolves
eight reported defects, and the fourth adds a fifth skill and the first thing
in this plugin that talks to a model, gated by the checks that were already
here.

The fifth adds an opt-in ASD-STE100 layer and the transcript-mined tier
phrases that bump the lexicon to version 5. The sixth turns the counted half
of that layer on by default and gives the registers their tolerances for it.
The seventh puts a voice in force between invocations, through the two host
features that reach every turn rather than only the ones somebody asked for.
The 100-repo corpus regression, the calibration fixtures, and every published
self-scan number were re-run after all seven.

### A voice that holds between invocations

A profile applied when somebody ran a skill, and the pre-commit hooks applied
one at commit. In between, the model wrote in its own register and the writer
asked again every turn. Two Claude Code features close that gap and the plugin
now ships both, with the install path deciding which half a person gets.

- **`output-styles/rabbit-writes.md` and `hooks/hooks.json` at the plugin
  root.** Auto-discovered when the plugin is enabled, declared in no manifest,
  and they write nothing into anybody's files. The style is the ordering
  contract (verdict in sentence one, no coined shorthand, no chatbot cadence)
  and it is opt-in through `/config`. `force-for-plugin` is deliberately
  absent, because it overrides the user's own choice on every session a plugin
  is enabled and this one is enabled far more often than prose gets written.
  `keep-coding-instructions: true` is deliberately present, because it
  defaults to false and a style shipped without it drops Claude Code's
  software-engineering instructions for anybody who picks it in a code
  repository. `check_output_styles` requires the one and refuses the other.

- **`rwlib/outputstyle.py` renders a voice profile as an output style.** The
  refusals, the mechanics with the profile's own numbers, the swaps, the
  contrastive pairs, and two sections lifted verbatim from the markdown. The
  long-form judgment stays out: it would be thousands of tokens on every
  request in every session, and the skill loads the whole profile at the
  moment somebody is actually writing. `signature_moves` stays out too, for
  the reason the engine already caps `voice-signature-underuse` at P2. A rule
  telling an editor to *add* a move installs a tic, and a system prompt is a
  stronger push than any finding.

- **`skills/rabbit-writes/scripts/claude_hook.py`** answers two events. At
  `SessionStart` it names the active voice, or says none is and which command
  claims one, which is the first time that fact reaches anybody without
  running a scanner. At `PostToolUse` on `Write` and `Edit` it scans the
  markdown that was just written and hands the findings back through
  `additionalContext`, the only channel that reaches the model in the turn
  that wrote the file. It exits 0 by every path, including unparseable stdin
  and a scanner that raised, and it is silent on a clean scan, a non-prose
  extension, and P2-only findings.

- **`skills/voice-setup/scripts/install_host.py`** is for the install paths
  with no plugin, where the only way to reach the same two features is to
  write into the user's own configuration. `--dry-run` prints every write and
  touches nothing, and the skill's instructions require showing that to the
  user before the real thing. It refuses to rewrite a settings file it could
  not parse, backs the file up before its first edit, and records every path
  written with its hash. `--uninstall` reverses it from that record: it
  restores the previous `outputStyle` rather than deleting the key, removes
  only hook entries naming this plugin's runner, and refuses to delete a style
  file edited by hand since it was written.

- **`check_plugin_hooks` holds the two install paths together**, comparing
  the shipped `hooks.json` against `install_host.py`'s `HOOK_SPECS`, so a hook
  in one and not the other fails the build rather than giving a plugin user
  and a loose-skill user different behaviour.

- **Fixed: the command a fresh install was told to run did not work.**
  `voices.resolve` printed `build_voice.py --activate <name>`, and `--activate`
  is a flag on that command's required mode group rather than a mode, so the
  invocation exited 2 on `one of the arguments --scaffold --check is required`.
  It was the single line between a fresh install and an enforced voice, in
  four places, and nothing checked that it parsed. It does now.

- **Fixed: the path in that same note was wrong in every packaged bundle.**
  It was written repo-relative, and a bundle puts `voices.py` at
  `<bundle>/scripts/rwlib/` with no `skills/` above it, so the command named a
  file that was not there. `package_skills.py` rewrites markdown paths per
  bundle layout and never touches a string inside Python, so neither half of
  this was going to be caught upstream. `voices.build_voice_command()` resolves
  the script from `__file__` across both layouts that carry it and prints it
  relative to the working directory when it stays inside it, so a checkout root
  gets the same line it always had. Where the script is genuinely absent, which
  is four of the five bundles, the note names the `voice-setup` skill rather
  than a path that would not resolve.

- **Fixed: `satoshi.md` used an em dash while `satoshi.rules.json` forbids
  them.** One character, in the section the style renderer lifts, so the
  generated style said "never use an em dash" three lines under one.

### OpenClaw, ClawHub, and Hermes

- **The packager now emits one folder per skill for the hosts that install
  folders.** `python3 scripts/package_skills.py --target clawhub` writes
  `dist/clawhub/<skill>/` with the same members as each zip plus three
  declared deltas: a frontmatter rewritten for ClawHub (`license: MIT-0`, a
  `homepage`, and one JSON `metadata` line whose `openclaw` block declares
  `python3` and the three optional `RABBIT_MODEL_*` env vars, keyed off the
  constants in `rwlib/endpoint.py` rather than restated), `{baseDir}/`-spelled
  paths in the rewritten markdown, and a SECURITY.md at each bundle root
  stating what the bundle is, why a scanner may flag it, and the whole
  network surface. `references/injection.md` and `references/patterns.md`
  gain a reviewer preamble at packaging time only, and the source files are
  untouched. The default target is `all`, and a post-build gate holds the
  folder output to every claim above.
- **`scripts/publish_clawhub.py` wraps the ClawHub CLI.** It rebuilds each
  folder through the gate, prints the suggested slug and the changelog, and
  runs `clawhub skill publish <path> --version <version>` with the two flags
  every source agrees on, `--extra` forwarding anything else. It exits 1
  under CI and never runs there.
- **`check_packaging_metadata` fails the build on drift.** An env var
  `rwlib/endpoint.py` reads that the declaration dict does not carry, a
  SKILL.md version off `plugin.json`'s, or a SECURITY template missing its
  pinned phrases. Four tests in `scripts/test_validate_checks.py` drive it
  over fixtures built to break it.

### The counted STE checks run in every scan

- **Five checks are measurements, so they no longer wait to be asked for.**
  The two sentence caps, Rule 6.6's paragraph cap, condition-before-command,
  and the semicolon all count something, and a count is a fact about the
  document rather than an opinion about vocabulary. They run in every plain
  scan. The six word-list checks (modals, banned verbs, phrasal verbs, -ing
  openers, passive, `ai_slop`) stay behind `--ste` and drop to P2, because
  the aerospace judgment about a word is not everybody's. `--no-ste`
  silences all of it. Still report-only: every id is P1 or P2 and `--check`
  gates on P0 alone.
- **Rule 6.6 is implemented, `ste-paragraph-sentences`.** Six sentences to a
  prose paragraph, counted over prose blocks only, since a ten-item bullet
  list is Rule 6.6's own answer to a long paragraph rather than an instance
  of the problem.
- **`registers.json` is version 4, with five new rows.** Every allowance is a
  per-document count from a sweep rather than a number from the standard:
  100 trending READMEs under `docs`, this repository's prose under `blog`,
  and the 19 open-access papers under `academic`. `chat`, `informal` and
  `linkedin` skip the band, `formal` and `academic` skip the semicolon rule
  because a semicolon is standard punctuation in both, and `academic` skips
  the descriptive cap on the same evidence that made `uniformity` a skip
  there: the papers run a median of 52 long sentences each, about one every
  75 words.
- **A voice profile outranks the standard, in three places.** A `semicolon`
  mechanic at either value stands down the STE copy, a
  `max_paragraph_sentences` stands down Rule 6.6, and a new
  `max_sentence_words` replaces the 20 and 25 word caps in both directions,
  with the label printing the number in force. satoshi carries 35, his
  measured p95, which takes his whitepaper from 30 sentence findings to 8
  without silencing the monsters.
- **Fixed: an alphanumeric identifier counted as two words.** The optional
  unit in the number pattern let it match the digit inside `sha256` or `v2`,
  so `count_words` returned 67 for a 37-word sentence. Every sentence cap
  reads that number and they are default-on now, so a technical sentence
  measured half again as long as it reads is a finding nobody can act on.

### A fifth skill, rabbit-rewrites

- **The passages the engine flags can now be rewritten by a small local model.**
  `scan.py --apply-model` sends one passage per finding to any
  OpenAI-compatible endpoint: llama.cpp's `llama-server`, Ollama, LM Studio,
  vLLM, or OpenRouter. One client and no per-vendor branch, because the only
  thing that differs between a Raspberry Pi running a 1.7B and a hosted
  frontier model is the URL, the model name, and whether a key is needed.
- **The document is never sent, so there is no chunking strategy.** A tell sits
  in a sentence. `rwlib/rewrite.py` cuts the file into one unit per finding and
  sends that unit plus the rule it broke, which is roughly 150 tokens whatever
  the file's length. A 10,000-word draft with 40 findings is 40 independent
  150-token calls, and a 4k-context model has room for all of them. Shape
  findings (`uniformity`, the tier clusters) take the paragraph instead, and a
  paragraph that does not fit the configured context is reported as such rather
  than truncated: a truncated rewrite verifies clean, because both sides of the
  comparison lost the same tail.
- **A small model is not trusted, it is gated.** Every reply has to survive
  `verify.py`, the same check that decides whether `--apply-safe` writes at all,
  plus a rescan proving the phrase it was sent to remove is gone and the total
  finding count came down. Both halves are needed: checking only the finding id
  accepts swapping `delve into` for `robust`, and checking only the phrase
  accepts that same swap from the other direction. A rejected reply is retried
  with the reason attached, then abandoned, and the original stays.
- **A document carrying a concealed instruction is refused before the first
  request.** One step earlier than `--apply-safe` refuses, because a rewriter is
  exactly what that text is addressed to. Nothing in the safety band is sent to
  any model.
- **Which model is a measurement.** `skills/rabbit-rewrites/scripts/bench.py`
  runs a fixed twelve-passage battery through whatever endpoint is configured
  and reports the pass rate, the first-attempt rate, seconds per passage, and a
  histogram of why replies were rejected. Every passage carries a number, a
  path, a version or a quotation, so a model that rewrites fluently and drops a
  detail fails rather than scores.
- **Three refusals in `rwlib/endpoint.py`, each a real failure.** A
  `.rabbit-model` carrying a literal `api_key` is rejected with the reason (the
  file gets committed, so it names an environment variable instead), plain
  `http` reaches loopback and nothing else without an explicit opt-in, and a key
  echoed back by a server that rejected it is scrubbed out of the error message.
  There is no localhost auto-discovery: a tool that silently finds a server on
  port 11434 silently ships somebody's draft to whatever is listening there.
- **`--model-plan` sends nothing.** It prints what would be sent and how big
  each request is, which is the flag to run first on a document that is not
  yours and the one that works before any server exists.
- **Every request asks the model not to think out loud, and that is worth 0%
  against 51%.** Most current small models are hybrid reasoning models.
  Qwen3.5-0.8B-Q4_K_M on `llama-server` scored 0 accepted out of 15 passages
  with thinking on, all fifteen dying at `max_tokens` because the model spent
  its whole output budget on a reasoning block and returned empty content, at
  8.6 seconds a passage. The same model and battery with thinking off: 10 of 15
  on one pass, 23 of 45 over three, at 0.47 seconds. Two spellings go out
  (`chat_template_kwargs` for llama.cpp, `reasoning_effort` for hosted
  OpenAI-compatible endpoints), and a server that rejects both is downgraded
  once and remembered, so the discovery costs one request and not one per
  passage. A reply that carried a reasoning block and no rewrite says so by
  name, because "empty response" sends somebody to the wrong problem entirely.
- **`scripts/model-bench/run.py` compares several models and writes the
  evidence.** It starts a server only if one is not already up, stops only what
  it started, and warms each model before timing it, since an unwarmed run
  charges the weight load to the first passage. Results land in
  `docs/model-bench/`.

### An STE layer, and a lexicon measured off real transcripts

- **`scan.py --ste` adds the ASD-STE100 Issue 9 structural checks.** Sentence
  limits (20 words procedural, 25 descriptive), the modal ladder, banned
  verbs, condition-before-command ordering, gerund clauses, phrasal verbs
  with one-word replacements, passive voice, and semicolons. Report-only by
  design: every `ste-*` id is P1 or P2, so `--check` still gates on P0 alone,
  and nothing here is mechanically fixed. `--ste-mode procedural|descriptive`
  forces the sentence limit, and each paragraph classifies itself otherwise.
- **STE runs inside the engine, not beside it.** The checks read the same
  exempted copy every other band reads, so a semicolon in a code fence is not
  a finding, and they run ahead of the suppression pass, so a `rabbit-allow`
  comment reaches them like anything else. The vocabulary lives in
  `scripts/ste_lexicon.json` and the prose rules in `references/ste.md`.
- **`lexicon.json` is version 5.** The new `clarity_phrases` tier entries
  ("let me check", "now let me", and friends) were counted out of 914 of this
  author's own assistant transcripts rather than guessed at, and they score
  zero hits over the 100-README corpus.

### A fourth skill, rabbit-reads

- **`rabbit-reads` distills a book, paper, or thesis into per-concept
  cheatsheets.** A run writes a `<book-slug>-notes/` folder of 40-70 line
  markdown documents plus a README index. The source's structure is mapped to
  section line ranges first, the concept set comes from that map, and the
  writing fans out to subagents.
- **Three scripts, and the book types are data.** `extract_text.py` normalizes
  the source to plain text, `map_structure.py` maps that text to section line
  ranges, and `check_notes.py` verifies the finished notes mechanically and can
  run the `rabbit-writes` scanner over them. The book types (non-fiction,
  fiction, arxiv paper, thesis) are data files in `references/book-types/`, one
  per type, parsed by both `check_notes.py` and `scripts/validate.py`, so a new
  type is a new file there and not a code change.
- **The formats it accepts: pdf, docx, doc, rtf, html, odt, epub, md, and
  txt.** pdf through poppler's `pdftotext`, docx through the plugin's own docx
  reader, doc/rtf/html/odt through macOS `textutil`, and the rest read
  directly. Every route writes its plain text under `scratch/`, and the
  intermediates stay there.
- **The notes paraphrase the source and never quote it.** A committed note
  that reproduces passages of somebody's book republishes them, and a
  normalized copy of the whole text is the same problem larger, so nothing
  derived from the source lands in a tracked path.

### A corpus audit for finished profiles

- **`audit_voice.py` scripts the inverse test.** `SKILL.md` used to say "no
  script does this half: it needs their writing", and the half in question is
  running a finished profile over the writer's own corpus to see which rules
  fire on the prose they came from. One `scan()` call per sample supplies the
  fire-backs, the engine's own P0 tells, the fingerprint distance, and the
  numbers the suggestions are measured from. Exit 1 names every rule that fired,
  attributed back to its entry (inherited entries say so, and say that a child
  cannot drop a parent's ban), with the count and the fix on the line.
- **Everything else it reports is deliberately not a judgment.** Per-sample
  distance from the band, with the out-of-range reading checked against the
  fingerprint's stored sample sizes first, because a corpus half the
  calibration size reads far whatever register it is in and scale and register
  suggest different fixes. A one-register-or-two receipt over per-sample
  sentence medians, which needs no fingerprint and is printed without one.
  Engine P0 patterns as candidates for `## Known contamination` at three hits
  across two samples, cross-noted when the phrase is also a signature-move
  subject, with the safety band excluded outright: that band is unsuppressible
  by design, so a concealed injection is never a tell to record as somebody's
  habit. And `stylometry.caricature`, calibrated in `PROOF.md` and previously
  wired to nothing, gains its first caller.
- **Two exemptions, both documented.** `voice-distance` is a measurement, not a
  rule, and `voice-oxford-comma` is held at hard P2 by the engine on the ground
  that no regex settles a serial comma: without the exemption the house profile
  would fail its own audit on an advisory nobody can act on. Everything else
  counts whatever its priority, because a stated rule the writer's own prose
  breaks is a disagreement even when it enforces at P2.
- **Every number a suggestion carries is measured with the engine's own
  yardstick.** Over the exempted copy `scan()` already built, with
  `is_prose_block` gating the paragraph cap and `stats["word_count"]` as the
  denominator for a signature rate. Measured any other way a six-item bullet
  list reads as one 24-sentence paragraph, and "raise the cap to 24" over a
  document where the engine counted four is the rule turned off. The register
  resolves before `stylometry.path_for` for the same reason: asked with
  `None` it skips the register-scoped file, so a profile carrying only
  `<name>.blog.fingerprint.json` reported no fingerprint here while `scan.py`
  measured the same document against it.
- **`test_audit_voice.py` joins the suite `run.py` already collects**,
  seventeen zero-argument tests over synthetic corpora where the profile is
  wrong in exactly one way. The repo validator compiles the new script and
  checks its CLI error handling, and the root `CLAUDE.md` records where the
  fact lives.

### A measured thesaurus in measure_voice.py

- **`measure_voice.py` now measures vocabulary reach.** A versioned families
  file, `skills/voice-setup/scripts/thesaurus.json`, pairs each plain word with
  the dressed-up synonyms a draft might reach past ("get" beside "obtain",
  "acquire", "procure"). The report counts both halves over the samples and
  proposes a `preferred_substitutions` entry only where the plain word is
  attested and the synonym never appears. A family the samples use both halves
  of prints as a non-rule and becomes one interview question, and a family the
  writer runs the formal direction of prints as inverted. `--json` carries the
  totals, the proposals, and the thesaurus version.
- **The proposals are edits, not documentation.** `fixes.py` already applied
  `preferred_substitutions` entries whose value is a mechanical replacement,
  whole-word and case-insensitive, and `TEMPLATE.rules.json` still said the key
  was "Not enforced". The note now says what actually happens, including the
  part that matters when choosing keys: no part-of-speech awareness, so a
  polysemous key rewrites every sense it matches. A round-trip test pins a
  proposed block landing through `fixes.apply` and passing `verify.validate`.
- **The family file has a shape check and a suite CI actually runs.**
  `check_thesaurus` in `scripts/validate.py` holds the reach words to the same
  mechanical-substitution bar as the fixer, refuses duplicate and cross-family
  terms, and requires the integer `version` a report quotes.
  `skills/voice-setup/tests/run.py` covers the proposal branches and had never
  run in CI, which now runs it on every push.

### Eight defects, found in review

- **`attain.py` called two different things a regression, and disagreed with
  itself about both.** The per-measure comparison applied a noise epsilon and
  the document verdict applied none, so a conversion that landed all six
  measures and drifted the Delta from 0.912 to 0.914 reported `regressed` and
  failed `--check`. And `measure_verdict` tested movement before tolerance, so a
  measure that went from 0.1 to 0.5 sample sd off the profile mean, well inside
  the band, was `regressed` and could fail the document on its own. Both halves
  now say the same thing: a regression has to end up outside the tolerance it is
  measured against, and the Delta gets an epsilon scaled to the profile's own
  self-distance band, because the band is what makes a Delta readable at all.
- **The lone-profile voice fallback is gone, and `voices/ACTIVE` ships empty.**
  `resolve()` fell back to "the only profile installed", and this plugin ships
  exactly one, an example. On a fresh install `--voice auto` therefore enforced
  a stranger's `default_priority: P0` bans on somebody's prose, announced in a
  note that under a pre-commit hook goes nowhere anybody reads. `SKILL.md` had
  said not to do that in prose for three releases. Resolution now ends in
  nothing, and the note names the one command that claims a profile. This
  repository keeps its own house voice through a root `.rabbit-voice`, which is
  the same mechanism a consumer uses.
- **`verify.py` reported one edit as two broken promises, one span type further
  on.** Inline code and URLs were already blanked before the path pass. Tables,
  block quotes and frontmatter were not, so an edited path inside a table row
  came back as "table row altered" and "file path altered". Over the 100-README
  corpus that is 658 of 2,275 path tokens sitting inside a span the checker
  already compares verbatim.
- **The `forget` branch of the injection detector read ordinary English as an
  attack.** `forget` plus a pronoun matches `don't forget your API key` and
  `I'll never forget what happened`. In visible prose that is a P2 nuisance.
  Inside an HTML comment it is concealment plus a directive, so it is a P0 that
  halts `--apply-safe` on somebody's own maintainer note, and the safety band
  takes no suppression by design. It now matches the instruction shape, and
  picked up `forget the above instructions` on the way, which the pronoun
  version never saw. Corpus counts are unchanged at 0 P0, 4 P1, 0 P2.
- **Tier-1 words and tier-1 phrases counted the same token twice.** `delve into`
  matched both lists and produced two P1 findings about one word. The phrase
  takes its span first now, the way `facts.numbers()` orders its takes.
- **Four small ones.** `--stdout` and `--write` without `--apply-safe` were
  accepted and silently did nothing, which on the `--stdout` path means a caller
  redirecting into a file got the report where it expected the document. Both
  are refused now. `voices.blend` filtered the template's guidance keys out of
  `mechanics` and not out of `mechanics_by_register`. `attain.py` built the
  `measure_voice.py` path in its error message relative to nothing, so the
  suggested command only worked from the repository root. And the one-word
  sentence rule's lookbehind wanted exactly one space after the period, so
  anybody who types two was never checked by it at all.
- **`stylometry.fingerprint`'s docstring described a version that never
  shipped**, promising a stderr warning eight lines above the comment explaining
  why it deliberately says nothing. The code was right.
- **`CLAUDE.md` drifted from the data it describes, and now something fails when
  it does.** One file named six registers, four of which do not exist, and
  documented `verify.py <file>` for a script that takes two paths and exits 2
  without them. `check_claude_md` in `scripts/validate.py` reads the register
  names out of `registers.json` and the required argument counts out of each
  script's own `add_argument` calls, which is the same argument `check_matrix_doc`
  already makes for the tolerance table: a documented fact the code never had is
  worse than no documentation.

### The conversion is checkable now, and the rewrite is a plan

- **`attain.py`: did the conversion land?** `verify.py` proves a rewrite broke
  nothing and cannot tell a real conversion from eleven punctuation fixes,
  because both pass every rule it has. That failure has a name now. Given the
  two documents and a profile, this reports the distance both ways and each of
  the six measures with its gap in the writer's own sample sd, signed, because
  "10 sd under" and "10 sd over" call for opposite edits. Five verdicts, and
  `flat` is the one it exists for: the distance barely moved and no measure
  moved a full sd, which is the shallow conversion `SKILL.md` has named in prose
  three times with nothing behind it. The exit contract is the new rule in one
  line: **a number about a document never blocks, a number about an edit may.**
  `voice-distance` still cannot fail `scan.py --check`, because that is what a
  pre-commit hook runs in a stranger's repository. `attain.py --check` exits 1
  on `flat` and `regressed`, never on `missed`, because a document that cannot
  reach the target without inventing content is guardrail 1 working. No hook
  ships for it and `validate.py` fails one that appears without being opt-in.
- **A fingerprint carries the writer's envelope, not only their average.**
  Schema 2 adds a `measures` block with min and max as well as mean and sd, and
  the sentence-length distribution as deciles. `measure_voice.py` fills both
  from the same samples, and its own table gained the range column, which is the
  one to read: a mean with a wide envelope under it is a writer with two
  registers, and the mean is nobody. The arithmetic lives in `stylometry.py` and
  the measuring does not, because `scan.py` imports that module and a second
  copy of `compute_stats` is the drift `rwlib` exists to end.
- **`voice-caricature`: more characteristic than the writer's own samples.**
  The overshoot `references/false-positives.md` warns about, wearing this
  writer's clothes instead of a generic humanizer's. The obvious rule does not
  work and the number is published: "any measure outside the sample min-max"
  fires on 95.5% of held-out documents by the same writer at three samples. With
  direction, magnitude in sample sd, an envelope pad and a two-measure minimum
  it fires on 0.1% at three samples, 0.0% at four, and none of the 80 measurable
  documents in the 100-README corpus. P2 forever, never fixable, and it still
  fires on a document that actually is one.
- **`signature_moves`, which is `banned_regex` pointed the other way.** A move
  the writer makes on purpose, with a ceiling and optionally a floor, so "BLUF"
  does not get installed on every paragraph. Capped at P2 whatever
  `default_priority` says, and that is not negotiable: `voice-signature-underuse`
  is the first finding in this engine that tells an editor to *add* something,
  and an editor made to satisfy a P0 would insert the move until the check
  passed, which is the tic `references/voice.md` warns about. Opt-in, P2, never
  fixable are its three guards.
- **`contrastive_pairs`.** The Taste Interviewer has always asked for a sentence
  the writer would write and one they would refuse, and had nowhere to put the
  answer, so both halves evaporated into adjectives. They go in the rules file
  now, unenforced, beside `preferred_substitutions`, and a conversion is shown
  them at the point it has to choose a sentence.
- **`learn_edits.py` reads a correction instead of a memory.** Adjust mode ran
  on recall, which is worst exactly when it matters. Given what the skill
  produced and what the author turned it into, this proposes substitutions,
  removals, opener shifts, mechanics answers and measure moves, each with its
  count. Nothing is written, and nothing appears that did not repeat at least
  twice: a word replaced once was wrong in that sentence rather than wrong in
  general.
- **The rewrite is a plan and then an execution.** `SKILL.md` splits a
  conversion in two, because compliance drops as the number of simultaneous
  instructions rises and deciding while writing is how a conversion quietly
  becomes a word swap. `attain.py --plan` turns the stored sentence
  distribution into a per-paragraph target: "five sentences, at least one under
  9 words, at least one over 29, median around 16". A band, deliberately not a
  sampled per-sentence script, which nobody hits and which manufactures a
  cadence rather than restoring one. In `deslop` the counterpart is span
  scoping: edit the flagged span plus one sentence of context and leave the rest
  alone, because the model cannot smooth what it never touches. Both loops cap
  at two passes.
- **The reconstruction eval.** `scripts/voice-eval/` scores the whole pipeline
  end to end with labels nobody had to write: deslop a piece the writer actually
  wrote, convert it back, and measure how much of the distance the round trip
  closed, with the original as the answer key. The corpus is empty and the
  scorer runs in CI over synthetic triples with known answers, which is the same
  bargain `scripts/detector-corpus/` already made.

### What the engine flags, changed on purpose

- **Guardrail 1 has something behind it now.** `verify.py` compares numbers,
  dates and quotations as multisets, so a paraphrase that turns 3,200 into 3,000
  fails. Reformatting does not: a date compares as its ISO form so a
  `date_format` conversion passes, a range is one token, a version is an
  identifier, and `1,200` and `1200` are one number. Only the loss fails, and
  the asymmetry is a decision: a rewrite that turns "the last two years" into
  "2024 and 2025" is deriving a number the source carried. Entities are listed
  and never fail, for every reason `false-positives.md` gives about a crude
  signal. Calibrated over the 100-README corpus before it was wired in: 0 of 100
  on identity, 0 of 100 through the mechanical fixer, 0 of 100 on each of eight
  benign reformats, and caught in 65 of 65 when a prose number was corrupted.
  Five of its carve-outs exist because that corpus produced a false positive
  nobody would have guessed, and `PROOF.md` lists them.
- **`contraction_rate` is one of the engine's stats.** It was computed in
  `measure_voice.py` off a private regex, which was a second counter for a fact
  `scan.py` needed, and the two spellings disagreed about whether a contraction
  starts with a word character or a letter.

- **A voice is a measurable target now, not only a list of refusals.**
  `measure_voice.py --name <voice> --write-fingerprint` writes
  `voices/<name>.fingerprint.json` from the same samples the profile came from,
  and `scan.py --voice` finds it beside the rules file and reports the distance
  to it. The measure is Burrows' Delta over 190 function words, calibrated
  against the writer's own samples, so the number reads as "0.97, where their
  own pieces sit within 0.61 of each other" rather than as a bare score.
  Everything the voice band enforced before this was a refusal, and a document
  could clear every one of them and still sound like nobody. `voice-distance`
  is P2 forever, never fails `--check`, and is not reported under 250 words: a
  writer is allowed to sound unlike themselves on purpose, and a number that
  blocked a commit over register would be the humanizer-shaped failure this
  plugin exists to avoid. Every reported distance names the markers responsible
  with the direction and both rates, because "further from the profile" tells a
  rewrite pass nothing and "furthermore at +16 sd, so at -2.4" tells it what to
  trade. Profiles without a fingerprint are unaffected, and a stranger's
  repository has none, so the pre-commit hooks do not move.
- **`measure_voice.py` reports the distributions the averages hide.** Sentence
  and paragraph openers, connectors by group, which contractions this person
  actually uses, their hedges and intensifiers, and how each sample ends
  verbatim. Two writers with the same 18-word average sound nothing alike if one
  opens half her sentences with "But", and none of that reached the old table.
  It also refuses to write a fingerprint from a contaminated sample: every other
  output of that script is a suggestion a person confirms, and this one is a
  file a later scan measures against without asking.
- **An HTML character reference is the character it renders as.** `&mdash;` and
  `&#8212;` count as em dashes now, so a find-and-replace no longer walks a
  document past `verify.py`'s "no em dashes added" gate or a voice that forbids
  them. The mirror case is fixed with it: the `;` closing `&amp;` or `&nbsp;` is
  markup, and a profile that forbids semicolons was reporting one finding per
  entity in a README header.
- **A wrapped bullet list is a list.** `is_prose_block` decided by ratio alone,
  so a list whose items wrap over several lines each scored as one long
  paragraph. `CHANGELOG.md` reported five of these under a voice profile and
  every one was false. `long-paragraph` in the README checker drops from 406 to
  390 across the corpus for the same reason. This was parked in `PROOF.md` for a
  release with its fix already written down, and this is that release.
- **Image sources are preserved by `verify.py`.** A relative extensionless
  `src` fell through both the URL and path checks. Measured before the change:
  0 of 341 markdown images in the corpus were in the gap, and 3 HTML ones. Alt
  text stays editable, with the measurement behind that decision in `PROOF.md`.
- **The README checker reads the LICENSE file.** Given a real path it walks up
  to the repository root for `LICENSE`, `LICENCE`, or `COPYING`. A file with no
  License section sharpens the existing `no-license` finding to P1. A License
  section over a tree with no file is a new P1. A walk that never finds a root
  says nothing rather than guessing.
- **Suppressions, with the reason mandatory.**
  `<!-- rabbit-allow: citation-leak (why) -->` stops a known finding failing the
  run. Without a reason it does not apply and raises a P1 of its own. The
  finding is still printed, with the reason and the line that allowed it, and
  one covering nothing is reported at P2 so stale ones do not accumulate. This
  repo does not use it on `references/patterns.md`, whose five P0s `PROOF.md`
  publishes on purpose.
- **Voice profiles can say more.** `"inflect": true` on a ban expands the
  regular s/es/ed/ing forms, opt-in per entry so a narrow ban stays narrow.
  `mechanics_by_register` and `applies_to_registers` on a `banned_regex` let a
  profile scope its own rule to a register, which is the on-the-clock and
  off-the-clock distinction the profile markdown has always drawn and the rules
  file could not express. A register still cannot relax a voice rule.

### Hidden text, measured against the corpus before it shipped

- **The concealment tables.** `artifacts.py` now names the channels somebody
  uses on purpose, beside the paste residue it always named: directional
  formatting (the Trojan Source characters), variation selectors, Hangul
  fillers, braille blanks, interlinear annotation, and the invisible math
  operators. Everything report-only raises at P1 with the reason it is never
  auto-removed, the tolerated few (direction marks, braille blanks) at P2 past
  an allowance, and a category sweep backstops the tables: any format or
  control character nothing names reports as unlisted, which covers ANSI
  terminal escapes. Zero findings from all of it over the 100-README corpus,
  and `PROOF.md` publishes the measurement.
- **The Unicode Tags block is tiled by two detectors with no gap.** Runs that
  decode to readable words are the safety band's `injection-tag-smuggling` P0
  and are never edited, even by a caller reaching `fixes.apply` directly. The
  residue below that threshold reports as `hidden-unicode` P0 and strips like
  a zero-width space, because unreadable noise has no honest use at any count.
- **An entity spelling of an invisible is the invisible.** `&#8203;` renders a
  zero-width space, so it reports as one, at P1 because the reference is at
  least visible in the source. `&nbsp;` stays exempt: it is ubiquitous,
  visible, and the reason `blank_entities` exists. The deletable ones strip
  with `--apply-safe`, and the report-only ones keep their entity forms too.
- **White text and the `hidden` attribute joined the safety band's
  concealment axis.** `color:#fff` with no declared background, the `<font
  color="white">` spelling, and `hidden`/`hidden="until-found"` all count as
  concealment now, and a hidden element or white span carrying prose is the
  same P1 a hidden comment carries. A style that declares any background stays
  silent, because that author is managing contrast, not hiding.
- **`scan.py` reads Word documents.** A `.docx` routes through
  `rwlib/docx_text.py`: the visible text gets the ordinary prose scan, and the
  runs the file itself declares hidden (`w:vanish`, `w:webHidden`, white
  `w:color`, a `w:sz` of two points or less) are judged the way the safety
  band judges a concealed span, with the paragraph number for a line. Word
  splits runs mid-sentence, so adjacent hidden runs are judged as one stretch.
  `--apply-safe` refuses the format rather than pretending a zip is text.

### New tools

- **`measure_voice.py --questions`, and the route it belongs to.** `voice-setup`
  had two ways to build a profile from nothing and one sentence about doing
  both, which is the one worth doing: a counter sees what somebody wrote and
  never what they refused to write, and a person is an unreliable narrator of
  their own prose who knows exactly what they will not publish. The two are
  route 3 in `SKILL.md` now, and the mode is what makes the second half know
  what the first half found. It prints an interview instead of the report, at
  most ten questions, and asks only what the samples could not settle. Every
  `forbid` it would have proposed is a silence rather than a refusal, so it
  comes back as a question, and a writer who used em dashes in four pieces is
  not asked about em dashes. **The questions and the counts print as two
  blocks, in that order, and that is the whole design.** A count read out first
  has told the author the answer, and what comes back is agreement rather than
  evidence. `test_no_question_carries_its_own_count` pins it, the reserved
  refusal questions survive the budget because this skill's own rule is to cut
  from Structure and Tone and never from Hard nos, and every question trimmed to
  hold the cap is named rather than dropped quietly. It refuses to interview
  over a contaminated sample set, for one step past the reason the P0 gate
  exists: ten answers about somebody else's prose are ten answers about
  somebody else.
- **`scan.py --voice auto`**, which resolves `.rabbit-voice`, then
  `voices/ACTIVE`, then a lone installed profile. The order lived only in
  `readme_check.py`, so the two checkers in one plugin could disagree about
  whose rules were in force. It is in `rwlib.voices.resolve` now. No profile is
  applied unless asked for, because that is what the `rabbit-scan` hook runs in
  somebody else's repository.
- **`voice-setup/scripts/measure_voice.py`**, which turns the sample workflow
  into one command: a per-sample table, the aggregate with the spread, the
  `Measured from samples` block ready to paste, and a starter `mechanics` object
  with the count behind every line. Exits 1 if any sample carries a P0.
- **`voice-setup/scripts/build_voice.py`**, which builds a profile and then
  proves it. `--scaffold --name <voice> --out <dir>` writes the pair from the
  templates with the template's own residue already gone: the underscore-prefixed
  guidance keys, and the `banned_regex` entry labeled "Example, delete this".
  That entry compiles, so a hand copy that kept it enforced a rule nobody chose,
  at the profile's priority, against the name of the person who did not choose
  it, and nothing in the repository noticed. `--check` runs the structure pass
  and then puts every banned word, banned phrase, forbidden mechanic and regex
  example through `scan.py`, reporting anything that produces no finding: a rule
  that does not fire is worse than no rule, because it reads as coverage. It is
  the validator that ships with the skill, which matters because
  `scripts/validate.py` sits at the repository root and a plugin install has no
  such file. `--activate` writes `voices/ACTIVE`, and refuses when the check
  failed or the profile lives outside `voices/`, where `ACTIVE` cannot resolve
  a name at all.
- **`banned_regex` entries take an optional `example`**, a line the pattern has
  to catch. It is the only way anything can prove a regex works, because a
  pattern cannot be run backwards into text, and an entry without one is
  reported as unproven rather than passed. The ten regexes in
  `voices/whit3rabbit.rules.json` each carry one now.
- **`rwlib/voices.py --blend a b --weight 0.7`**, for the half of blending a
  script can do. Bans union, the stricter side wins whatever the weight says,
  genuine conflicts are reported by name, and the lineage goes into the file.
  `references/voice.md` now says plainly that the numeric dimensions are not
  blended by anything, because nothing reads them.

### The detector corpus, still empty, no longer unreachable

- **`scripts/detector-corpus/fetch_samples.py`.** `score.py` has always ended
  its report with "refetch from the archive URLs" and nothing did it, so
  reproducing a published rate on a fresh clone was a manual afternoon. It is
  the one script here that makes network requests: only http and https are
  followed, a mismatch never overwrites a good local copy, and a text that was
  extracted by hand is reported as manual rather than as a failure, because it
  never claimed to round-trip.
- **A second kind of provenance.** A `human` sample can now prove its date with
  a published research corpus instead of a web archive capture, recording the
  dataset, the pinned revision, the split, the row, the collection date, and the
  licence. Rows are refetched through the Hugging Face datasets viewer, which is
  JSON over HTTPS and so does not put `datasets` and `pyarrow` into a stdlib-only
  repository.
- **`test_corpus_harness.py`**, with the network stubbed, now runs in CI. The
  code that will publish a false-positive rate the day somebody populates this
  had never run over a populated corpus.
- **An informational `score.py` step in CI**, which never gates. The corpus is
  empty, `PROOF.md` says so, and a number nobody sees is a number nobody notices
  has stayed at zero.
- **Candidate datasets checked and written up**, in `docs/detector-corpus/README.md`.
  Nothing was added. RAID is the trap worth naming: MIT-licensed, the obvious
  choice, and widely summarised as pre-2022 Wayback-sourced human text, while the
  paper says its abstracts are filtered to 2023 or later. Three other corpora
  clear the date bar and are written in registers this engine does not measure.
  The gap is a sourcing problem, not a tooling one.
- Two Wilson figures quoted in `corpus_io.py` and `PROOF.md` were rounded the
  wrong way. Zero flags over fifty samples is an upper bound of 7.1%, not "under
  7%", and 52 is where it crosses. Recomputed and pinned by a test.

### One home per fact

Four facts were stated in two or three places each, with comments asking the
next reader to keep the copies in sync. They drifted anyway, which is where the
last two review passes spent themselves.

- **`skills/rabbit-writes/scripts/rwlib/`** holds the markdown spans, sentence
  splitting, the lexicon, badge hosts, section keywords, the finding schema, and
  the register tables. `scan.py`, `verify.py`, `readme_check.py`, and the corpus
  research scripts all import it. The test that pinned two regex literals against
  each other is gone, replaced by an identity check: two modules importing one
  object cannot drift. Verified byte-identical over all 100 corpus READMEs.
- **`scripts/registers.json`** is the tolerance matrix. `scan.py` derives
  `PROFILE_SKIP`, `PROFILE_RELAX`, and `VOCAB_EXEMPT_PROFILES` from it, and the
  table in `references/context.md` is rendered from it. The test that parsed the
  markdown table to check the two agreed is gone with the second copy.
- **`skills/readme-writing/scripts/corpus_summary.json`** is the corpus extract
  the README checker compares against, produced by a new step 05 in the research
  pipeline. It used to be a literal dict with a comment promising it mirrored the
  aggregate and nothing checking the promise.
- **`lexicon.json` and `registers.json` carry a `version`**, echoed in
  `scan.py --json` and in `PROOF.md`'s heading. `validate.py` fails when they
  disagree, so a published measurement names the catalogue that produced it.
- **`rwlib/voice_check.py`** decides whether a rules file is a profile.
  `scripts/validate.py` and `voice-setup/scripts/build_voice.py --check` are
  both callers, so the repository validator and the one a person runs on their
  own machine cannot disagree about what valid means. `validate.py` lost its own
  copy of the regex-compilation, register-name and ban-entry checks in the
  trade, and gained the ones it never had: template residue in either file, the
  mechanic vocabulary, and a rules file with no markdown beside it.
- **`rwlib/voices.MECHANIC_VALUES`** is the mechanics vocabulary, assembled from
  the `STRICTNESS` and `NUMERIC_MECHANICS` tables that were already there rather
  than restated. An unknown key and a misspelled value both failed silently
  before: `mech.get("semicolons")` is None, the comparison is False, and the rule
  the author believes they wrote never runs. A test holds the template's
  `_options` block against it.

### New

- **`scan.py --apply-safe`** applies only the edits with exactly one correct
  answer (hidden characters, AI tracking parameters, and a voice's own
  single-word substitutions), then runs `verify.py` on its own output. Dry run
  without `--write`. Nothing inside code, a table, a quote, or a fence is
  touched: it is reported and left alone. Converting a typed `--` into an em dash
  was in the set until the property tests pointed out that this plugin never adds
  an em dash, so every fix failed its own gate.
- **`--sarif` on both checkers**, so findings land inline on a pull request diff
  instead of in a CI log. P0 maps to `error`, P1 to `warning`, P2 to `note`.
- **`extends` in a voice rules file.** Bans union with the parent, mechanics
  merge key by key with the child winning. Cycles and missing parents are errors,
  because a profile that inherits from nothing enforces nothing.
- **`.pre-commit-hooks.yaml`**, four hooks, all gating on P0 only. Two defaults
  that apply no voice profile, and `readme-check-voice` and `rabbit-scan-voice`
  as the opt-ins: pre-commit clones this repository, so a shipped default that
  enforced a voice would enforce this author's, and a stranger's em dash is not
  a defect in a stranger's README.
- **An English-only scope, stated.** Every band and tier list here is calibrated
  on English. A document whose letters are mostly non-ASCII now gets a note at
  the top of the report. A note, never a failure: a bilingual README with an
  English quickstart deserves an answer for the English half.
- **`docs/detector-corpus/`**, the harness `PROOF.md` has been admitting it needs.
  Provenance-labeled samples, hash-only storage, a human label refused after the
  2022-11-30 cutoff, and a per-register false-positive rate with a Wilson
  interval. The corpus is empty, and both `PROOF.md` and that directory's README
  say so plainly rather than implying otherwise.

### Tests

- **Both suites split** from one ordered 900-line function into named test files
  with memoized fixtures. `run.py` drives them with nothing installed, and
  `pytest` collects the same files. `run.py -k <substring>` selects by name.
- **`tests/test_invariants.py`** makes the blanking invariant a property instead
  of a comment repeated in six places. It found two live bugs in its first hour:
  the `--apply-safe` em-dash conversion above, and a tracking-parameter fix that
  reached into a code fence.
- **`validate.py` gained five checks**: the register matrix against the docs, the
  corpus extract against the aggregate, the finding schema over real findings
  from both checkers, the version stamps, and a one-definition tripwire. The last
  one caught a rule spelled out in three files whose copies had already stopped
  agreeing about whether "country" was on a list.

### Fixed

- `readme_check.py` emitted a `detail` key that `scan.py` never did, so its own
  reporter branched on the band to find its text and no consumer could parse both
  with one reader. One schema now, versioned.

## 0.1.0 (unreleased)

First release. Everything below was built before anything was published, so this
is a description rather than a migration note.

### What ships

- **`rabbit-writes`**: the prose skill and the engine it runs on. Four modes:
  `detect` (audit only), `deslop` (strip machine tells, no profile needed),
  `voice` (convert an existing document into the active voice), `draft` (new
  prose in that voice). Underneath: a 63-pattern catalog in P0/P1/P2 tiers, a
  false-positive discipline, six register profiles with a tolerance matrix, an
  Orwell and ASD-STE100 craft layer, and a 33-item behaviourally anchored
  self-check.
- **`voice-setup`**: interview, sample measurement, editing, and blending for
  voice profiles. Owns everything about building a profile.
- **`readme-writing`**: drafts or audits a `README.md` against patterns measured
  from 100 real trending GitHub repos, in the user's own voice. Ships
  `readme_check.py`.
- **`scan.py`**: fingerprint detection (hidden unicode, AI tracking parameters,
  chat citation leaks, unfilled placeholders), tiered vocabulary with density and
  cluster rules, stylometrics (burstiness, MATTR, trigram repetition, sentence
  and paragraph variation), self-reference exemption, reliability gating by word
  count. Named findings in three bands, and deliberately no single AI score.
- **`verify.py`**: preservation validator for rewrites, with `--allow-structure`
  for conversions that reorder sections on purpose.
- **`docs/README_WRITEUP.md`** and **`docs/readme-analysis/`**: the 100-repo
  study behind `readme-writing`, plus the pipeline in `scripts/readme-research/`
  that reproduces it.
- Runs under Claude Code and OpenAI Codex from one set of `.claude-plugin/`
  manifests. Codex reads that format directly.

### Design decisions worth keeping

These were arrived at the hard way and are easy to undo by accident.

- **Modes route on intent, never on how the text arrived.** An earlier draft of
  this plugin split the work across two skills and keyed its edit mode on "user
  names a file", with a contract of "minimal in-place edits". Pointing it at a
  document therefore selected the most conservative behaviour by construction,
  and a request to convert a document into somebody's voice came back with a
  heading and one fixed sentence. `scripts/validate.py` now pins the mode table
  and the rule that a file path is not a mode.
- **"You may not add" governs content, not form.** It bars facts, stance, and
  installed personality. It does not bar reordering, splitting, merging, or
  rewriting sentences, and reading it that way is what produced the shallow
  edits above. `voice` mode restructures by design, because a profile is mostly
  structural and a word swap cannot apply "lead with the conclusion".
- **"Make the minimum effective edit" belongs to `deslop`, not to the
  guardrails.** As a guardrail it outranked the voice profile and capped every
  conversion. `validate.py` fails if it reappears in the guardrail section.
- **`verify.py` must not fail a conversion for changing headings.** The tooling
  contradicting the instruction is worse than either being wrong alone.
  `--allow-structure` scopes that carve-out to headings and nothing else.
- **Pointed at an existing document with no mode word in the request, ask.**
  Measure the gap, say what a full conversion would change with real numbers from
  `scan.py`, and let the user pick. Silence in either direction is the bug.
- **`references/craft.md` loads for `voice`, not just `draft`.** It holds nearly
  all the structural guidance, and gating it to drafting meant no edit pass ever
  saw it.
- **The engine stays voice-agnostic.** It knows a profile can exist and always
  defers to one. It knows nothing about any particular person, and
  `voices/whit3rabbit.md` is an example, not a default.

### Corrections made during development

- **Two numbers in the README study were wrong.** The analysis script understood
  Markdown and ignored HTML, in a corpus where 76% of READMEs use an HTML header
  block. Bare URLs were counted inside `href`/`src` attributes and inline code
  (2,009 of 2,357 "bare" URLs were attribute values), and badges in HTML `<img>`
  tags were not counted at all. Corrected: bare URLs are 3.0% of links, not
  29.3%, and the median badge count is 5, not zero. Section order, length, and
  sentence statistics were never affected. `docs/README_WRITEUP.md` carries the
  correction note.
- **The research scripts read an absolute path from the machine that fetched the
  corpus**, so the study did not reproduce anywhere else, and the badge-type
  counter had been failing silently and shipping an empty result.
- **`readme_check.py` bugs found by running it on this repo's own README:**
  `long-paragraph` line numbers pointed into a stripped copy of the file rather
  than the file, and link syntax inside backticks counted as a real link, so a
  document explaining `[text][ref]` was flagged for using one.
- **Scanner bugs found by pointing it at this repo** rather than at fixtures are
  listed in `skills/rabbit-writes/PROOF.md`, along with the self-scan numbers
  including the unflattering rows.

### Corrections made during pre-release review

A read-through by someone who had not written any of it. The full list with the
reasoning is in `skills/rabbit-writes/PROOF.md` under "Bugs found by review".
The parts that change behaviour:

- **Two shipped features did nothing.** `curly-quote` was listed in every
  register's skip set, so the pattern could not fire anywhere, and the
  `oxford_comma` mechanic was documented in both rules files and read by no line
  of code. Both work now. `PROFILE_RELAX` gives the tolerance matrix's "relaxed"
  cells an executable form as hit allowances, since skipping had been standing
  in for relaxing throughout, and `validate.py` fails on a register that names a
  rule id that does not exist.
- **`verify.py` had its own silent failure modes**, which matters more than
  usual for the script whose job is catching silent breakage. It read headings
  and table rows out of code fences, so moving a fenced block that contained
  shell comments failed a rewrite that touched no headings. It matched file
  paths inside URLs, double-reporting every edited link. It counted tells from a
  frozen fifteen-word copy of the lexicon. It dropped a trailing bare `#` from a
  URL and then reported the mismatch it had just created.
- **Lexicon and catalog disagreed on Tier 1**, and `seamlessly` sat in both
  Tier 1 and Tier 3, so one word produced a P1 and inflated the density behind a
  P2. `key` was a Tier-3 word, which put one of the commonest words in English
  in charge of the density count. A test now fails if a word in the section 12
  table does not resolve in the lexicon.
- **False positives that cost trust:** a non-breaking space was a P0 (it is
  correct French typography, now P2 past three), `Dr.` read as a one-word
  sentence, one stray quote exempted the following 200 characters from scoring,
  three `here` links all reported the same line, and one caveat anywhere in a
  README excused every headline number in it.
- **The tolerance matrix is now checked, not just written.** `test_scan.py`
  parses the table in `references/context.md` and fails on any cell with no
  implementation, in either direction. It caught five gaps on its first run,
  including three the `PROFILE_RELAX` work had left behind. A missing entry is
  invisible to `validate.py`, which can only see an id that does not exist, so
  this is the guard for the class of bug `curly-quote` belonged to.
- **One fix introduced a bug of its own.** Rebuilding `verify.py`'s tell counter
  from the lexicon swept in `curly-quote`, so a rewrite that passed through an
  auto-curling editor gained tells from typography and failed verification. P2
  fingerprints are excluded from that counter now.
- **CI.** `.github/workflows/ci.yml` runs the validator and both suites across
  Python 3.8 through 3.13, and scans this repo's own prose with `--check`.
- **`.claude/settings.local.json` is ignored.** It was never committed here,
  only because a contributor's global excludes happened to cover it. The repo
  now ignores it itself.
- **Reproduction.** `README.rst` and `README.txt` no longer vanish from the
  research pipeline, which looked only for `README.md` and then fell back to an
  absolute path on the machine that fetched the corpus.

### Corrections made during a second pre-release review

A read of both scanners, the verifier, the research pipeline, the validators, and
the tests together. The full list is in `skills/rabbit-writes/PROOF.md` under
"Bugs found by a second review". The parts that change behaviour:

- **The invisible-character tables were stored as invisible characters.** A save
  that normalized whitespace would have turned the U+00A0 key into a plain space,
  at which point `scan.py` reports every space in every document as a paste
  artifact. They are `\uXXXX` escapes now, in the test fixtures too, and a test
  asserts the codepoints rather than the keys.
- **`verify.py` compared headings by membership, not as a multiset,** unlike
  every other preservation check. Two identical headings, one dropped and one
  different one added, passed both the membership test and the count test.
- **Two hard gates in `verify.py` ran on the raw text,** so a correctly written
  date range failed "em dashes added" and a quoted example of a flagged phrase
  failed "more tells after rewrite". Both now run on the same exempted copy
  `scan.py` uses, an en dash between digits is not a splice, and both name the
  span that moved the counter.
- **`oxford_comma: "forbid"` had no guard and no test,** so it reported the comma
  in every compound sentence as a serial comma. Both sides of the mechanic carry
  the same guards now, and every previously untested branch of `apply_voice_rules`
  has a case: `em_dash: "limit"`, `date_format: "mdy"` and `"iso"`,
  `curly_quotes: "forbid"`, and `required_when` firing as well as staying quiet.
- **`readme_check.py` counted badges out of the raw file,** so a fenced example
  showing badge markdown could trip `badge-wall` on a README with no badges. It
  also saw markdown links only, missing `<a href>click here</a>` in the HTML
  header blocks that 76% of the corpus uses.
- **Two findings were answered by documenting rather than by changing code,**
  because measuring showed the change would cost more than it bought: the one
  deliberate divergence between the checker's badge host list and the corpus
  scripts', and the fact that `verify.py` tracks a file path only when it has an
  extension. Both are written down at both ends now, and `SKILL.md` says which
  half of its own path promise is mechanically enforced.
