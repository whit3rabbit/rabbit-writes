# Changelog

## 0.1.0 (unreleased)

First release. Everything below was built before anything was published, so this
is a description rather than a migration note.

### What ships

- **`rabbit-writes`**: the prose skill and the engine it runs on. Four modes:
  `detect` (audit only), `deslop` (strip machine tells, no profile needed),
  `voice` (convert an existing document into the active voice), `draft` (new
  prose in that voice). Underneath: a 63-pattern catalog in P0/P1/P2 tiers, a
  false-positive discipline, six register profiles with a tolerance matrix, an
  Orwell and ASD-STE100 craft layer, and a 32-item behaviourally anchored
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
