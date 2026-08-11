# Changelog

## Unreleased

Architecture and evidence. Nothing here changes what the engine flags, and the
100-repo corpus regression, the calibration fixtures, and every published
self-scan number were re-run to prove it.

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
- **`.pre-commit-hooks.yaml`**, three hooks, all gating on P0 only.
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
  with memoized fixtures. `run.py` drives them with nothing installed; `pytest`
  collects the same files. `run.py -k <substring>` selects by name.
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
