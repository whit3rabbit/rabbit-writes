# rabbit-reads

Skill for distilling books, papers, and theses into terse per-concept cheatsheet doc sets with a README index.

## Commands

```bash
# Normalize a source to plain text (txt, md, docx, pdf, doc, rtf, html, odt, epub)
python3 skills/rabbit-reads/scripts/extract_text.py <source>

# Map section line ranges over the normalized text, cut into fan-out batches
python3 skills/rabbit-reads/scripts/map_structure.py <source> --book-type <type> --batches <n>

# Check a notes folder against its book type
python3 skills/rabbit-reads/scripts/check_notes.py <notes-dir> --book-type <type>

# Check with the rabbit-writes engine scanner under a voice profile
python3 skills/rabbit-reads/scripts/check_notes.py <notes-dir> --book-type <type> --scan --voice-rules <profile>

# Check the paraphrase rule against the normalized source
python3 skills/rabbit-reads/scripts/check_notes.py <notes-dir> --book-type <type> --source scratch/book.txt

# Run the skill test suite
python3 skills/rabbit-reads/tests/run.py
```

## Structure & Architecture

- **`SKILL.md`**: Frontmatter, three modes (`distill`, `extend`, `verify`), and the seven-phase workflow: normalize, map, plan, fan out, index, verify, deliver.
- **`scripts/`**:
  - `extract_text.py`: Normalizes any source format to plain text, and runs `rwlib.injection` over every one of them before writing. External tools: `pdftotext` for pdf, `textutil` for doc, rtf, html, and odt. The output is an intermediate and belongs under `scratch/` or outside the repo.
  - `map_structure.py`: Maps section headings to line ranges over the normalized text and cuts them into fan-out batches. `--book-type` selects the segmentation grammar from `references/book-types/`.
  - `check_notes.py`: Verifies a notes folder against its book type: line band, template sections, kind markers, Source line shape, README index, See also links. `--scan` runs the `rabbit-writes` engine scanner over every doc, and `--voice-rules` passes a profile through to it. `--source` checks the paraphrase rule against the normalized source.
- **`references/book-types/`**: One file per source type, the one home of that type's contract. The header lines (`**Kind markers:**`, `**Length band:**`, `**Template sections:**`, `**Source line:**`, `**Free-form files:**`) are parsed by `check_notes.py` and by the repo `scripts/validate.py`.
- **`references/fanout-prompt.md`**: The subagent boilerplate for the fan-out phase, with placeholders in curly braces.
- **`tests/`**: The skill's test suite, stdlib runner in `tests/run.py`.

## Conventions & Gotchas

- **scratch/ rule**: The normalized source text and every intermediate live under a gitignored `scratch/` at the repo root or outside the repo, never in a tracked path. A normalized copy of a copyrighted book is the book. The notes folder is the deliverable and the only thing that ships.
- **External tools**: `pdftotext` and `textutil` are external dependencies. `pdftotext` comes from poppler (`brew install poppler` on macOS, `apt install poppler-utils` on Debian). `textutil` ships with macOS and does not exist on Linux, so doc, rtf, and odt inputs there need conversion by hand first. (html, epub, txt, and md use the stdlib).
- **Non-ASCII as escapes**: Any non-ASCII character in a script constant is written as a unicode escape (backslash u 2014 for the em dash), never a literal. House rule inherited from `rabbit-writes`: a tool that normalizes whitespace silently breaks a literal.
- **Book-type header grammar**: The header lines are the one home of a type's contract, and two readers parse them, `check_notes.py` and the repo `scripts/validate.py`. Reword or reorder one and both break. A new book type is a new file following the grammar, not a code change.
- **The safety scan reads markup, not the output.** `extract_text.py` runs `injection.scan` over the raw xhtml of each epub chapter and the raw markup of an html file, before `strip_xhtml` touches them, because `TAG_RX` is a negated class and deletes a multi-line html comment whole. Scanned after the strip, a concealed directive is a directive nobody sees and nobody is told about, which is worse than not looking. The cost is that a finding's `line` is a line in that markup rather than in the text file, which is why the epub findings carry the chapter name in the label. `rwlib.docx_text` already made the same trade with its paragraph numbers. A safety P0 costs exit 1 in one place in `main()`, for every format, and the text is still written: a reader has to see what was extracted before judging it.
- **The invisible-character sweep is a note and not a finding, on purpose.** A tag run that decodes to words is `injection.tag_runs`' P0 and comes back through the safety scan. Everything under that floor is the paste residue `scan.py` reports on the notes once they exist, and inventing a priority for it here would be a second lexicon. `invisible_note` counts through `rwlib.artifacts` so the counting rule has one home, and strips nothing.
- **The engine scan runs under the `docs` register rather than the engine's default `blog`.** A note is a reference doc by shape. The observable difference is significance-inflation, a P0 relaxed to an allowance of 1 there, which is what test_scan_runs_under_the_docs_register pins with a pair: one hit passes, two fail. SCAN_PROFILE is a module constant rather than a book-type header field, because the shape is a property of the note format and every book type shares it.
- **`scan_problems` reads structured findings, never the report.** It runs `--check --json` and pins `findings.SCHEMA_VERSION`. It used to grep the P0 block out of the human report by heading, which is exactly the fragile consumer `rwlib/findings.py`'s docstring describes: a cosmetic change to that heading broke the summary silently and the failure still said "P0 finding present".
- **`--source` is opt-in and the notes stay checkable without it.** The normalized source lives under a gitignored `scratch/` and is usually gone by the time somebody re-checks a folder, so its absence is a check that does not run rather than a battery that cannot. `source_windows` stores hashes of ten-word windows rather than the windows, because a book is a million of them: a hash collision costs one line a human dismisses, and storing the tuples costs hundreds of megabytes per run.
- **CLI drift**: The Script CLI section in `SKILL.md` restates the argparse definitions by hand, and nothing checks it mechanically: `check_claude_md` in `scripts/validate.py` only reads files literally named `CLAUDE.md` (never `SKILL.md`), and only counts required positionals in a fenced `python3` line, not named flags. It does read this file's own Commands block above, so keep that block, `SKILL.md`'s Script CLI section, and the scripts' `add_argument` calls in sync by hand when a flag changes.
