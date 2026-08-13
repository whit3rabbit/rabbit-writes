# Changelog

## Unreleased

Two passes. The first was architecture and evidence and changed nothing about
what the engine flags. The second, below, changes it in six places and says so.
The 100-repo corpus regression, the calibration fixtures, and every published
self-scan number were re-run after both.

### What the engine flags, changed on purpose

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
