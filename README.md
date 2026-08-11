# rabbit-writes

Write and edit in **your** voice, not a chatbot's.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Most "humanizer" tools do half the job. They strip the AI tells and hand back prose that reads like a different machine: staccato fragments, performed candor, fake first person. A new fingerprint, not the absence of one.

This one separates the two halves. A **voice profile** says how *you* write. An **engine** handles everything true of good writing regardless of who is writing. The profile wins every conflict. The engine fills every gap.

The voice is data. Swap it, edit it, blend two of them, or write your own from a template. Nothing in the engine knows anything about any particular person.

## Install

One set of manifests, two hosts. Codex reads Claude Code's `.claude-plugin/` marketplace format, so the same repo installs as a plugin in both.

**Claude Code**, in a session:

```
/plugin marketplace add whit3rabbit/rabbit-writes
/plugin install rabbit-writes@rabbit-writes
```

**Codex**, from a shell:

```bash
codex plugin marketplace add whit3rabbit/rabbit-writes
codex plugin add rabbit-writes@rabbit-writes
```

Restart, then confirm the three skills loaded: `claude plugin list | grep rabbit-writes`, or `/skills` in Codex.

Python 3.8+ with the standard library, and only if you want the scripts. Nothing to build.


<details>
<summary><b>Scopes, the shell equivalents, updating, removing</b></summary>

The Claude Code CLI does what the slash commands do, and takes `--scope user` (the default), `project`, or `local`:

```bash
claude plugin marketplace add https://github.com/whit3rabbit/rabbit-writes
claude plugin install rabbit-writes@rabbit-writes --scope user
claude plugin details rabbit-writes@rabbit-writes
```

Codex `marketplace add` also accepts a local path, a full Git URL, and `--ref <tag>` to pin a release.

Pull a later release:

```bash
claude plugin marketplace update rabbit-writes && claude plugin update rabbit-writes@rabbit-writes
codex plugin marketplace upgrade rabbit-writes && codex plugin add rabbit-writes@rabbit-writes
```

Remove:

```bash
claude plugin uninstall rabbit-writes@rabbit-writes
codex plugin remove rabbit-writes@rabbit-writes
```

Both hosts also pick a skill implicitly when your request matches its description. To require the explicit mention instead, drop an `agents/openai.yaml` beside a `SKILL.md` with `policy: allow_implicit_invocation: false`.

</details>

<details>
<summary><b>Working on the plugin itself</b></summary>

Clone it and symlink the whole repo, not the individual skills. The skills reference each other through `${CLAUDE_PLUGIN_ROOT}`, and the scripts resolve their siblings by walking up from their own path, so the directory layout has to survive the install:

```bash
git clone https://github.com/whit3rabbit/rabbit-writes
ln -s "$PWD/rabbit-writes" ~/.claude/skills/rabbit-writes
```

That loads as `rabbit-writes@skills-dir` on the next restart and picks up edits without a reinstall. Don't run both installs at once: two copies of the same three skills means every request matches twice.

</details>

<details>
<summary><b>Codex without the plugin, as loose skills</b></summary>

Codex scans `~/.agents/skills/` for user-level skills and `.agents/skills/` at a repo root for project-level ones, and it follows symlinks:

```bash
git clone https://github.com/whit3rabbit/rabbit-writes
cd rabbit-writes
mkdir -p ~/.agents/skills
for s in rabbit-writes voice-setup readme-writing; do
  ln -s "$PWD/skills/$s" ~/.agents/skills/$s
done
```

Symlink all three. They call each other: `readme-writing` runs the `rabbit-writes` scanner against the active voice, and both read the profiles under `rabbit-writes/voices/`. `scripts/readme_check.py` resolves its siblings by walking up from its own path, so that layout works.

What you lose is `docs/`, which sits at the repo root outside every skill folder. The study behind `readme-writing` is then only in the clone. Nothing breaks, `references/patterns.md` carries the same numbers.

</details>

## Run it

You rarely need to name a skill. Each one triggers on a plain request, which is what the description field is for:

```
write a note to the team about the cert outage # -> rabbit-writes, in your voice
does this draft sound like a chatbot?          # -> rabbit-writes, detect mode
set up my writing voice from these 3 posts     # -> voice-setup, sample mode
my README is a mess, fix the section order     # -> readme-writing, audit mode
```

The explicit forms are there for when you want to force one. The `rabbit-writes:` prefix is the plugin namespace and comes from the install. In Codex the same three are `$rabbit-writes`, `$voice-setup`, and `$readme-writing`.

```
/rabbit-writes:rabbit-writes    # draft, convert, de-slop, or audit prose. four modes, one skill
/rabbit-writes:voice-setup      # build, measure, edit, blend, or switch a voice profile
/rabbit-writes:readme-writing   # draft or audit a README against the 100-repo study
```

The scripts run from a shell, not from a skill. Stdlib only, Python 3.8+:

```bash
python3 scripts/validate.py                      # check manifests, skills, voices, cross-refs
python3 skills/rabbit-writes/scripts/scan.py draft.md \
    --voice-rules skills/rabbit-writes/voices/whit3rabbit.rules.json   # findings in three bands
python3 skills/rabbit-writes/scripts/verify.py original.md rewritten.md   # did the rewrite break a promise
python3 skills/rabbit-writes/scripts/scan.py draft.md --apply-safe        # the fixes with one right answer
python3 skills/rabbit-writes/scripts/scan.py draft.md --sarif             # for a pull request annotation
```

### `--apply-safe`

Almost nothing here has a mechanical fix. "This paragraph is nine sentences long" needs a person, and a tool that guessed would be the humanizer-shaped thing this plugin exists not to be.

Three things are different, because each has exactly one correct answer: a hidden character that carries no meaning, an AI tool's tracking parameter on a link, and a word your own profile already names a replacement for. `--apply-safe` applies those, runs `verify.py` on its own output, and prints what it did.

```bash
python3 skills/rabbit-writes/scripts/scan.py draft.md --apply-safe   # dry run, prints the diff
python3 skills/rabbit-writes/scripts/scan.py draft.md --apply-safe --write
```

Everything else stays report-only. So does anything sitting inside a code fence, a table, a block quote, or a quoted example: the promise not to touch those outranks the fix, and the report says where the character is so you can decide.

A `preferred_substitutions` entry is only applied when it is a replacement. `leverage` to `use` is a swap. `at the end of the day` to `cut it` is a note to you, and writing "cut it" into the sentence would be worse than leaving it.

Converting a typed `--` into an em dash is deliberately not in the set. It was, for about an hour, until the property tests pointed out that this plugin never adds an em dash under any circumstances, so every fix failed its own gate.

### `--sarif`

Findings map onto SARIF 2.1.0 without inventing anything: the finding id is the rule id, P0 is `error`, P1 is `warning`, P2 is `note`. Upload it and the findings land inline on the diff instead of in a CI log.

```yaml
- name: prose scan
  run: |
    python3 skills/rabbit-writes/scripts/scan.py docs/guide.md \
      --sarif --sarif-uri docs/guide.md > scan.sarif
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: scan.sarif
```

`--sarif-uri` has to be the path relative to the repository root. GitHub silently drops results whose file it cannot resolve in the checkout, and silently is the operative word: the upload succeeds and nothing appears.

### pre-commit

`.pre-commit-hooks.yaml` ships three hooks, all gating on P0 only. A P1 is a convention worth arguing about and a P2 is polish, and a hook that blocks a commit over polish is a hook people learn to pass `--no-verify` to.

```yaml
repos:
  - repo: https://github.com/whit3rabbit/rabbit-writes
    rev: v0.1.0
    hooks:
      - id: readme-check
      - id: rabbit-scan
        files: ^docs/.*\.md$
```

Scope `rabbit-scan` with `files`. Unscoped it runs on every markdown file in the repository, including the generated ones nobody wrote by hand.

## Point it at a document

`rabbit-writes` has four modes, and it picks by what you asked for, never by whether the text arrived as a file or a paste.

| Mode | You want | It may change |
|---|---|---|
| **detect** | to know, not to edit | nothing |
| **deslop** | the machine tells gone | words and sentences, in proportion to the actual slop |
| **voice** | this to sound like you | sentences, paragraphs, section order, openings, anything the profile specifies |
| **draft** | prose that does not exist yet | n/a |

Point it at something you wrote, without saying how far to go, and it measures the gap before touching anything:

```
1,240 words, currently in a neutral report register.
Converting to whit3rabbit's voice means:
  structure   4 sections reordered to lead with the conclusion
  paragraphs  6 over the 5-sentence cap, split
  sentences   avg 24 words against a cap of 22, roughly 30 rewritten
  mechanics   11 rule hits: 7 em dashes, 4 semicolons
  size        roughly 10-20% shorter (37 wordiness spans)
Full conversion, or just the 11 mechanical hits?
```

It asks because both defaults are wrong. A voice profile is mostly structural, so a real conversion is a large diff, and guessing small hands back a document with three words changed. Guessing large rewrites something you wanted lightly touched. The numbers come from `scan.py`, so the estimate is measured rather than promised.

## First thing to do: make it sound like you

The plugin ships with an example voice profile (`whit3rabbit`). It is not yours.

To write in your own voice, create your own voice profile and activate it:

```
skills/rabbit-writes/voices/<you>.md            the profile the model reads
skills/rabbit-writes/voices/<you>.rules.json    the part a regex can enforce
```

### Three ways to create your voice profile

#### 1. From writing samples

Provide 3 to 4 pieces of your actual writing: Substack posts (e.g. [Ruben Substack](https://ruben.substack.com/p/i-am-just-a-text-file)), articles, emails, or chat logs.

```
Create a voice profile from my writing samples: [paste samples or file paths]
```

`voice-setup` measures your sentence length distribution, burstiness, contraction rate, and transition habits from the text itself. Start here if you have samples. It reads what you do rather than what you believe you do, and those two answers differ more often than not.

#### 2. From a short interview

If you don't have samples ready:

```
Set up my writing voice
```

`voice-setup` asks 5 to 10 questions aimed at boundaries: your banned words, banned phrases, punctuation bans, and signature closers.

#### 3. By hand, from the template

Copy the template files and edit them directly:

```bash
cp skills/rabbit-writes/voices/TEMPLATE.md skills/rabbit-writes/voices/<you>.md
cp skills/rabbit-writes/voices/TEMPLATE.rules.json skills/rabbit-writes/voices/<you>.rules.json
```

Fill in your rules, then validate and activate:

```bash
python3 scripts/validate.py
echo "<you>" > skills/rabbit-writes/voices/ACTIVE
```

Taste is boundaries: roughly 80% of a working profile is **refusals** (what you will never write). What you say you like usually describes half the writers alive. What you refuse to put your name on is your fingerprint.

## What's in it

Three skills.

**`rabbit-writes`**: the writing skill, and the engine it runs on. Four modes, listed above.

Underneath sit 63 patterns in a priority-tiered catalog, a false-positive discipline, register profiles, Orwell and Simplified Technical English as a positive craft layer, a 33-item self-check, and two scripts. The engine half knows nothing about any particular person.

**`voice-setup`**: builds, measures, edits, blends, and switches voice profiles.

**`readme-writing`**: drafts or audits a `README.md` against patterns measured from 100 real GitHub repos (section order, sentence length, badge and link conventions) instead of generic advice, in your voice rather than a generated open-source register. Ships `readme_check.py`, which checks structure, links, badges, claims, and the active voice in one pass. The full study is in `docs/README_WRITEUP.md`.

```
rabbit-writes/
  .claude-plugin/           plugin + marketplace manifests
  scripts/
    validate.py              repo validator
    readme-research/         the pipeline behind readme-writing's evidence base
  docs/
    COMPARISON.md            the craft engine's source writeup
    README_WRITEUP.md        the readme-writing skill's source writeup
    readme-analysis/         raw + aggregated data behind that writeup, one folder per repo studied
  skills/
    rabbit-writes/
      SKILL.md
      references/           patterns, false-positives, context, voice, craft, checklist
      scripts/              scan.py, verify.py, lexicon.json
      tests/                calibration fixtures and regression tests
      PROOF.md              the engine scanned with its own scanner
      voices/
        ACTIVE                 one line: whose voice is live
        whit3rabbit.md         shipped example profile
        whit3rabbit.rules.json its enforceable subset
        TEMPLATE.md            copy this to add your own
        TEMPLATE.rules.json
    voice-setup/
      SKILL.md
    readme-writing/
      SKILL.md
      references/           patterns (the full catalog), checklist
      scripts/              readme_check.py, the structural + voice linter
      tests/                calibration fixtures and a 100-repo regression
```

## Three bands, never conflated

`scan.py` reports findings in three groups and refuses to merge them into one score.

| Band | Means | Example |
|---|---|---|
| **voice** | your own rules | a semicolon, "circle back", an em dash |
| **fingerprint** | evidence the text came out of a chat tool | `utm_source=chatgpt.com`, a zero-width space, "I hope this helps!" |
| **craft** | bad writing regardless of author | `utilize`, a hedge stack, uniform paragraphs |

Keeping them apart is the point. Presenting a wordiness fix as evidence about who wrote something is the most common failure in this category of tool, and it is the one that gets people accused of things.

```bash
python3 skills/rabbit-writes/scripts/scan.py draft.md \
    --voice-rules skills/rabbit-writes/voices/whit3rabbit.rules.json
```

A register profile (`--profile casual`, `--profile docs`) relaxes the general rules. It never relaxes a voice rule. Lowercase and loose punctuation are fine off the clock. "Circle back" never is.

## What it will not do

- Tell you whether AI wrote something. Independent audits put commercial detector false-positive rates above 60% on non-native English writers (Liang et al., Stanford, *Patterns* 2023) and open-source misclassification above 70% (Jabarian & Imas, BFI 2025-116). Signals, not proof, and never a basis for an academic-integrity or hiring decision.
- Add a fact, name, number, date, or citation that was not in your source.
- Add first person, an anecdote, or an opinion your draft did not have.
- Add an em dash during a rewrite.
- Rewrite anything inside code, tables, block quotes, frontmatter, or attributed quotations.
- Follow instructions embedded in the text it is editing.

- Work in a language other than English. Every tier list, contraction rule, sentence boundary, and stylometric band here is calibrated on English prose. Point it at Japanese or Arabic and it will still print numbers, and they will not mean anything. It says so: a document whose letters are mostly non-ASCII gets a note at the top of the report. It is a note and not a failure, because a bilingual README with an English quickstart deserves an answer for the English half.

You may not add a fact or a stance. That constraint is what separates restoring a voice from installing one. Form is a different axis: converting a document into your voice reorders sections, splits paragraphs, and rewrites sentences whole, because a voice profile is mostly structural and a word swap cannot apply "lead with the conclusion".

## Verify a rewrite

```bash
python3 skills/rabbit-writes/scripts/verify.py original.md rewritten.md
python3 skills/rabbit-writes/scripts/verify.py original.md converted.md --allow-structure
```

Exits non-zero if the rewrite altered a code block, frontmatter, a table row, a block quote, inline code, a URL, a file path, or the heading structure, or if it added em dashes or ended with more tells than it started with. `deslop` and `voice` both write to files, so a broken promise there would otherwise be silent.

`--allow-structure` is for `voice` only. A conversion reorders sections and rewrites headings because the profile told it to, and without the flag it fails its own verification for doing its job. The flag moves those two checks into a reported list. Everything else stays hard.

## Write a README with it

`readme-writing` is the odd skill out. Not voice, not AI tells. It answers one narrow question with data instead of folklore: what do currently-popular READMEs actually do?

```
/rabbit-writes:readme-writing        # or just: "write me a README", "review my README"
```

Four modes, picked from what you ask for:

| Mode | Trigger | Delivers |
|---|---|---|
| **draft** | no README yet | a complete file in the measured section order |
| **audit** | "look at my README" | findings ranked by impact, no rewrite unless you ask |
| **restructure** | content is there, order is wrong | same content, reordered, with what moved |
| **section** | "add a badges row" | that section only, matching the surrounding register |

The structural rule: **pitch → fastest path to running it → depth → community → license.** That is not taste. It is where 100 independently-authored READMEs converged.

| Measured across the corpus | |
|---|---|
| Installation section present | 84%, and it lands early (avg. position 0.33) |
| Contributing | avg. position 0.77 |
| License | avg. position 0.93, median **13 words** |
| Table of contents | 12% under a heading, 32% counting anchor lists. Tracks length, not courtesy |
| Inline `[text](url)` links | 96.8%. Reference-style `[text][ref]` is extinct at 0.2% |
| Median badge count | **5**, clustered on license, version, stars, chat, and CI |
| Centered header block | 76% |
| Length, 90th percentile | 6,040 words |

The highest-impact single fix in an audit: whatever sits between the top of the file and the first sentence that says what the thing is. Every README flagged as an anti-pattern buried its description under a hero image, a badge wall, or sponsor content.

**The caveat, since the skill demands one of everybody else.** The corpus is 100 repos by trailing-quarter star growth as of August 2026, which skews hard toward AI-agent tooling and developer CLIs. A Python data-science library or a corporate SDK may well converge somewhere else.

Heading classification is keyword-based and sentence splitting is a regex, so read the numbers as directionally right, not exact. `docs/README_WRITEUP.md` has the methodology, the ranked table, and its own limitations section. `docs/readme-analysis/` has the raw per-repo data.

## Tests

```bash
python3 scripts/validate.py                        # manifests, skills, voices, cross-refs, tripwires
python3 skills/rabbit-writes/tests/run.py          # engine, voice, verifier, fixer, invariants
python3 skills/readme-writing/tests/run.py         # structure, links, voice, 100-repo regression
```

`run.py` needs nothing installed, which is the same promise the scripts make. `pytest` collects the same files if you have it, and `run.py -k <substring>` selects by name.

The calibration fixtures assert that known slop scores high, known human prose scores zero, and a third sample with no flagged vocabulary at all still trips the uniformity detector because every sentence is the same length. Vocabulary and rhythm are independent axes, and that third fixture is the one that matters.

`tests/test_invariants.py` is a different kind of test. Half the engine reports a line number taken from a blanked copy of the document, which only works because blanking preserves length.

That fact was asserted in comments in six places and checked nowhere. It is now a property, tested over generated markdown built from the fragments that have caused real trouble. It found two live bugs in its first hour.

`skills/rabbit-writes/PROOF.md` publishes the engine scanned by its own scanner, unflattering rows included. It also says in the file that a two-sample calibration is the weakest evidence a detector can offer.

`docs/detector-corpus/` replaces that with a measured false-positive rate per register, once somebody populates it. The machinery is written and the corpus is empty. The README in that directory is the procedure.

## Where this came from

The engine is merged from seven open-source humanizer skills. Each was best at exactly one thing:

- [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop) — the portability test, minimum effective edit, detect-without-scoring
- [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) — the fingerprint/craft split, register tolerance matrix, severity tiers, "never inject these", the preservation validator, honesty about detector accuracy
- [blader/humanizer](https://github.com/blader/humanizer) — the Wikipedia pattern port, "what not to flag", "signs of human writing", sample-outranks-the-rules
- [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) — false agency, vague declaratives, meta-joiners
- [brandonwise/humanizer](https://github.com/brandonwise/humanizer) — stylometric ranges, hidden-unicode detection, reliability gating
- [angelarose210/ghostwriter](https://github.com/angelarose210/ghostwriter) — voice profile as a portable artifact, contaminated-sample handling, weighted blending
- [tamdogood/orwell-writing](https://github.com/tamdogood/builder-essential-skills/tree/main/skills/orwell-writing) — Orwell's six rules and the ASD-STE100 baseline

Plus three sources that shaped the architecture:

- [testdouble/han, human-readable-output-standard](https://github.com/testdouble/han/blob/main/docs/research/human-readable-output-standard.md) — layered instruction delivery, the audience frame over readability formulas, behaviorally anchored self-checks
- [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) — the underlying catalog and the mechanism behind it
- [Ruben Hassid, *I am just a text file*](https://ruben.substack.com/p/i-am-just-a-text-file) — taste is boundaries, and a voice profile is mostly refusals

`docs/COMPARISON.md` is the full writeup: what each repo does, tables of what they share and where they diverge, and the reasoning behind every borrow.

`readme-writing`'s rules come from the same discipline applied to a different question: what do currently-popular READMEs actually do, measured rather than assumed. `docs/README_WRITEUP.md` has the methodology, the 100-repo table, and every finding. `docs/readme-analysis/` has the raw data and per-repo notes behind it.

## Contributing a voice

Voices are welcome as pull requests. Include the `.md` and the `.rules.json`, keep general writing advice out of both, and leave `voices/ACTIVE` alone.

## License

MIT. See [LICENSE](LICENSE).
