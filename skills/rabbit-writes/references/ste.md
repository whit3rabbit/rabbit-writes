# ASD-STE100 Simplified Technical English

> ASD-STE100 Issue 9 (2025-01-15), the aerospace controlled-language standard.
> Used in aircraft maintenance, procedure writing, and regulatory
> documentation since 1983.

rabbit-writes runs STE checks with `scan.py --ste`. All findings are
**report-only**: every `ste-*` id is P1 or P2, so `--check` still gates on P0
alone, and nothing here is mechanically fixed. The rewrite (splitting long
sentences, reordering conditions) is a judgment call, and usually a language
model task.

The checks run over the same exempted copy every other band reads. Fenced
code, inline code spans, and quoted examples are never flagged, and a
semicolon inside a code block is not a finding. They also run ahead of the
suppression pass, so a `rabbit-allow` comment reaches them like any other
finding.

The vocabulary lives in `scripts/ste_lexicon.json`, rebuilt from the official
Issue 9 PDF: the dictionary table was parsed programmatically and every claim
in the file that cites a rule number or a dictionary ruling was checked back
against the extracted text. The file's own `_comment` fields carry the
provenance.

## Text classification

Before the sentence-length rule applies, each paragraph classifies itself:

| Class | Indicators | Sentence limit |
|---|---|---|
| **Procedural** | Steps, instructions, imperatives, "how to", numbered lists | 20 words (Rule 5.1) |
| **Descriptive** | Explanations, definitions, "the system does X", overview sections | 25 words (Rule 6.3) |

`--ste-mode procedural` or `--ste-mode descriptive` forces the limit for the
whole document. The limits themselves are data, read from the lexicon's
`punctuation_and_word_count` block, because Rules 5.1 and 6.3 carry the
numbers and a second copy in code is a second calibration.

The other checks apply in both modes: the two STE text types disagree about
sentence length and about nothing else this layer checks.

## What is checked

### 1. Sentence length

Procedural text: max 20 words. Descriptive text: max 25 words. Numbers,
numbers with units, abbreviations, and code spans each count as one word
(Rule 8.6), and hyphenated groups count as one (Rule 8.7).

```
# Violation
Run the deployment script which installs all dependencies and sets up the environment and configures the service for you.

# Compliant
Run the deployment script. It installs all dependencies. It sets up the environment.
```

### 2. Approved modal verbs only

Allowed: `can`, `will`, `must`. Banned: `should`, `would`, `may`, `might`,
`could`, `shall`.

Two of the rulings are worth knowing exactly. `could` sits inside `CAN`'s
own verb-form group and the same dictionary entry then bans it for showing
possibility. And `might` has no dictionary entry at all: it is
banned by the unlisted-word default, not by an explicit ruling.

The month is not the modal: "Released in May 2026" and "May 5" stand down,
"You may restart it" fires.

```
# Violation
You should verify that the config is loaded.

# Compliant
Make sure that the config is loaded.
```

### 3. No -ing verb after a comma

STE bans -ing forms as clause openers. This catches the common
"..., making it easy to..." pattern. Gerunds as nouns are fine:
"Running the script is safe."

```
# Violation
Install the package, making it available globally.

# Compliant
Install the package. It is then available globally.
```

### 4. Condition before command

Required conditions come before the action (`if`, `when`, `unless`). The
check fires only on imperatives: a declarative sentence that happens to carry
a command verb mid-sentence is not a command, and a condition that opens the
next sentence is not this sentence's trailing clause.

```
# Violation
Do X if Y is true.

# Compliant
If Y is true, do X.
```

### 5. Banned verbs

`check`, `verify`, `confirm`, and `ensure` are all ruled `MAKE SURE (v)` in
the Part 2 dictionary. Replace with "make sure that" (verify a state),
"examine" (look for faults), or "measure" (get a value).

### 6. Phrasal verbs

Rule 9.3 is a productive-grammar constraint, not a word list: do not combine
two approved words into a phrase whose meaning is not the approved meaning of
its parts. The standard says outright that phrasal verbs are not usually
listed in the dictionary, so there is no lookup table to enforce. The scanner
flags exactly the rule's own worked examples ("put out" for extinguish,
"give off" for release) and stands down for its named approved exceptions
(`PUT ON`, `COME ON`, `GO OFF`, each restricted to one sense). The general
constraint is left to the writer, because that is where the standard leaves
it.

### 7. Passive voice

STE prefers active voice (and Rule 3.4 bans the auxiliary constructions that
produce most passives). Rewrite with `you`, `we`, or the actor as subject.
P2, advisory: adjectival participles and passives read the same to a regex.

```
# Violation
The configuration is loaded by the system.

# Compliant
The system loads the configuration.
```

### 8. Semicolons

Rule 8.1: all standard punctuation except the semicolon. Write two sentences
instead. The `;` closing an HTML entity is markup and does not count.

### 9. Vocabulary

The `ai_slop` block flags AI-overused words and filler ("simply", "leverage",
"in order to", "it's important to"). This block is deliberately outside the
standard: the words are not in the ASD dictionary, and the file's own
comment says where they came from.

## What is data but not checked

Three lexicon tables are reference material for a writer or a model prompt,
and no checker reads them. Each says so in its own `_comment`:

- `banned_words_software`: the dictionary rulings for `run`, `execute`,
  `display`, `render`, `present`, `destroy`, `drop`, and the `delete`
  priority order (the dictionary bans it for `erase`/`remove`, Rule 1.12
  lists it as a technical-verb fallback, and the rule itself resolves the
  tension: the approved verb wins when it fits).
- `technical_verb_categories`: Rule 1.12's "Computer processes and
  applications" verb list, the most software-relevant paragraph in the
  standard. A technical verb is legal only when no approved dictionary verb
  covers the same instruction.
- `recurring_errors`: verified Part 2 rulings for the words writers get
  wrong most (`however` to `but`, `therefore` to `thus`, `perform` to `do`,
  the three senses of `complete`). Several need sense discrimination no
  regex can do, which is why the table informs a rewrite rather than a
  check.

Rules the standard carries that this layer does not check: the six allowed
verb forms and the perfect-tense ban (Rules 3.2 and 3.4, partially visible
through the passive check), the one-word-one-meaning principle, the
six-sentences-per-paragraph cap (Rule 6.6), and the contraction ban (Rule
4.2). If a check for one of these lands, it lands in `rwlib/ste.py` with a
test and a corpus number, not in this file first.

## Suppression

STE findings suppress the same way as every other finding, with the
engine's own comment syntax:

```
<!-- rabbit-allow: ste-sentence-procedural (spec quote, kept verbatim) -->
```

The comment must name the finding id and carry a reason in parentheses. See
`rwlib/suppress.py` for the mechanism, including why the safety band refuses
it.

## Finding IDs

| ID | Priority | Description |
|---|---|---|
| `ste-sentence-procedural` | P1 | Procedural sentence over 20 words |
| `ste-sentence-descriptive` | P1 | Descriptive sentence over 25 words |
| `ste-modal` | P1 | Banned modal verb |
| `ste-ing-verb` | P1 | -ing verb after comma |
| `ste-condition-order` | P1 | Condition after command verb |
| `ste-banned-verb` | P1 | Banned verb used as verb |
| `ste-phrasal-verb` | P1 | A phrasal verb Rule 9.3 itself names |
| `ste-passive` | P2 | Passive voice construction |
| `ste-no-punctuation` | P2 | Semicolon used |
| `ste-vocab` | P1 | AI-overused vocabulary item |

The ids and priorities live in `STE_PRIORITIES` in `rwlib/ste.py`, and
`STE_FINDING_IDS` derives from it, so the two cannot disagree. The
`suppression-*` ids belong to `rwlib/lexicon.py` and are deliberately not
restated there.

## Official standard

ASD-STE100 Simplified Technical English, Issue 9 (2025-01-15),
[asd-ste100.org](https://asd-ste100.org), free download. The shipped lexicon
was built from that PDF directly.

## Sources and references

- [ASD-STE100 official specification](https://asd-ste100.org): the
  authoritative standard, and the source the shipped lexicon was parsed
  from.
- [AminBlg/SimpleEnglish](https://github.com/AminBlg/SimpleEnglish): an
  agent skill that applies ASD-STE100 to LLM-generated documentation, and
  the inspiration for this layer. It uses a 53-rule agent-driven approach
  against this module's deterministic scanner, and its
  [`word-swaps.md`](https://github.com/AminBlg/SimpleEnglish/blob/main/skills/simple-english/references/word-swaps.md)
  is the source of the `ai_slop` block.
