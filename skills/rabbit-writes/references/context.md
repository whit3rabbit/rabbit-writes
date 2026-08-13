# Register and voice

Two independent axes. **Register** sets how strict to be. **Voice** sets how the prose should sound. You can write blunt for a blog or warm for docs.

---

## Register profiles

Infer from the text unless the user names one.

| Signal | Register |
|---|---|
| Under 300 words with hashtags or @-mentions | `linkedin` |
| Code blocks, API references, architecture | `technical-blog` |
| Salutation plus fundraising language | `investor-email` |
| Step-by-step instructions, parameter docs, README shape | `docs` |
| Short reply, chat, DM, issue comment | `casual` |
| No strong signal | `blog`, the safe default, all rules at full strength |

If the inference feels wrong, say which register you picked and why. The user can override.

## Tolerance matrix

Rules not listed apply at full strength everywhere.

| Rule | linkedin | blog | technical-blog | investor-email | docs | casual |
|---|---|---|---|---|---|---|
| Em dashes | relaxed (2/post) | strict | strict | strict | relaxed | skip |
| Bold overuse | relaxed (hooks OK) | strict | strict | strict | relaxed | skip |
| Emoji in headers | relaxed (1-2, end of line) | strict | strict | strict | skip | skip |
| Excessive bullets | skip | strict | relaxed | strict | skip | skip |
| Hedging | strict | strict | relaxed ("may" is accurate) | strict | relaxed | skip |
| Tier-1 vocabulary | strict | strict | **partial**, see below | strict | **partial**, see below | P0 only |
| Promotional language | relaxed (some sell expected) | strict | strict | **extra strict** | strict | skip |
| Significance inflation | strict | strict | strict | **extra strict** | relaxed | skip |
| Copula avoidance | skip | strict | relaxed | strict | skip | skip |
| Uniform paragraph length | skip | strict | strict | strict | skip | skip |
| Numbered-list inflation | relaxed | strict | relaxed | strict | skip | skip |
| Rhetorical questions | relaxed (1 hook) | strict | strict | strict | skip | skip |
| Transition phrases | skip | strict | strict | strict | relaxed | skip |
| Generic conclusions | skip | strict | strict | **extra strict** | skip | skip |
| Hashtag stuffing | strict | strict | strict | **extra strict** | skip | skip |
| Bullet-NP lists | strict | strict | relaxed | strict | relaxed (parameter lists) | skip |
| Subjectless fragments | relaxed (the register) | strict | relaxed | strict | skip | skip |
| Boilerplate clusters | strict | strict | strict | **extra strict** | relaxed | skip |
| Future-narrative closers | strict | strict | strict | **extra strict** | skip | skip |
| Social endorsement closers | strict | strict | strict | strict | skip | relaxed (1 in a DM) |
| Wall-of-text replies | strict | skip | skip | skip | skip | strict |
| Curly quotes | skip | skip | relaxed (plain-text contexts) | skip | relaxed | relaxed |
| Tier-2 clusters | strict | strict | **partial**, see below | strict | **partial**, see below | skip |
| Tier-3 density | skip | strict | **partial**, see below | strict | **partial**, see below | skip |
| Confidence calibration | strict | strict | strict | strict | strict | skip |
| Signposting | strict | strict | strict | strict | strict | skip |
| Diff-anchored writing | strict | strict | skip | strict | skip | strict |
| List-label periods | strict | strict | strict | strict | skip | strict |

**Extra strict** means flag borderline instances. In an investor email, one "thriving ecosystem" undermines the message.

**Skip** means do not audit this category here. The rule does not apply.

**Relaxed** means the rule still runs and reports past a tolerance, not that it stops running. `scan.py` holds those tolerances in `PROFILE_RELAX` as hit allowances: `linkedin` reports the third em dash, `docs` the fifth curly quote, either of `technical-blog` and `docs` the third stacked hedge.

One kind of cell has no mechanical form: a rule with no pattern in `lexicon.json`. Bold overuse, excessive bullets, copula avoidance, numbered-list inflation, bullet-NP lists, subjectless fragments, hashtag stuffing, and wall-of-text replies are yours to apply by reading. Every other cell is implemented. This table is not the source: `scripts/registers.json` is, and this block is rendered from it by `python3 scripts/rwlib/registers.py --write`. `scripts/validate.py` fails if the two disagree, so editing the markdown by hand fails the build rather than documenting a tolerance the engine never had.

**Vocabulary exceptions, `technical-blog` and `docs`.** This is what **partial** means in the three vocabulary rows, and it is why those two registers do not take a hit allowance: an allowance would let a second `delve` through, and this does not. These words carry real technical meaning and are not flagged in either register: `robust`, `comprehensive`, `seamless`, `ecosystem`, `leverage` (actual platform leverage), `facilitate`, `underpin`, `streamline`, `scalable`, `dynamic`. Still flagged at full strength: `delve`, `tapestry`, `beacon`, `embark`, `testament to`, `game-changer`, `harness`. The list itself is `technical_exempt` in `lexicon.json`.

P0 fingerprints (chatbot artifacts, cutoff disclaimers, citation leaks, tracking parameters, hidden unicode, placeholders) apply at full strength in **every** register, including `casual`.

---

## Voice personas

A persona is optional. If the writer does not name one, infer from the input's existing register and impose nothing. Each is a set of concrete targets, not a vibe, and the parenthetical says where it belongs.

**`casual`** (*blog, social, community*): Contractions throughout, because their absence reads stiff. Average sentence under 14 words, fragments fine. At least one first-person or concrete-anecdote touch. Near-zero jargon. Keep warm hedges ("I think", "honestly"), cut corporate ones ("it's worth noting").

**`professional`** (*LinkedIn, investor email, pitches*): Active voice for most sentences, varied in length. One concrete claim per paragraph: a number, a name, a date. Never "experts say." Make the ask explicit. Low tolerance for hedging.

**`technical`** (*docs, technical blog*): Plain copulatives ("X is Y") over inflated substitutes. One idea per sentence. Imperative mood for instructions. Jargon is fine, defined on first use. Tables and lists only where content is genuinely list-shaped.

**`warm`** (*mentorship, onboarding, thank-yous*): Address the reader as "you" and acknowledge them at least once. Cut intensifiers ("very", "truly", "incredibly") in favor of stronger verbs. No performative empathy ("I completely understand how you feel"). Medium sentences, 15-20 words, unhurried.

**`blunt`** (*decision memos, hard feedback*): Lead with the claim and cut the windup. Periods for emphasis, not dashes. No padding to reach a rule of three. Near-zero hedging. Short declaratives with the occasional long sentence for contrast.

## How the axes compose

A voice target always applies, even where a register would skip that category: `technical` voice still prefers plain copulatives inside a `casual` register that otherwise ignores copula avoidance.

Where both govern the same rule and agree, they reinforce. Where they disagree, **resolve toward the stricter of the two.** A `warm` voice in `docs` still gets no decorative tables.

A user-supplied writing sample outranks both. See `voice.md`.

Sensible pairings: casual↔casual, professional↔linkedin/investor-email, technical↔docs/technical-blog.
