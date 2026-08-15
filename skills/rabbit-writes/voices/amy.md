# Voice: amy

> **Only put things here that would be wrong for someone else.** "Avoid passive
> voice" and "cut filler" belong to the engine and apply to everyone. If a rule
> is true of good writing generally, leave it out. A profile that restates the
> engine drifts out of sync with it.
>
> Weight this file toward the Hard nos. Taste is boundaries, and roughly 80% of
> a working profile is refusals. Preferences are easy to state and weak in
> effect. Refusals are specific, checkable, and rare, which is what makes them
> a fingerprint.

A woman's personal-essay voice, not from an interview. Every rule below is inferred from the
samples: no person was asked, so nothing here is a stated preference. The
open questions at the bottom are what an interview would have settled. The
samples live at `scratch/amy-{1,2,3}.md`.

## Known contamination

None. The source tripped the detector's chatbot-artifact rule twice, both on
`of course,` set off by commas, in a book published years before writing
tools existed. Ruled a false positive, with the user's agreement, and the
phrase was removed from the working copies only (the source file is
untouched). Worth knowing for the engine, not for this voice: a plain
`of course,` in a human cadence is not yet a chatbot tell on its own.

## The three essentials (if you forget everything else)

1. Confess first. Start in your own mess, in specifics, before saying anything
   about the reader. The universal point arrives only after the personal
   embarrassment, never before it.
2. One sacred thing at a time, cut immediately with something ordinary or
   funny. High and low in the same sentence: scripture beside aspirin,
   prophets who smell like goats.
3. End by turning back toward love with a short declarative, never a summary
   and never a moral lifted above the story.

## Voice in one line

About 70% confession, 20% spiritual claim, 10% joke, braided rather than
layered. The failure mode is piety: drop the joke and the self-exposure and
the same sentences turn into a sermon, which is the one thing this voice
never stops making fun of.

## Dimensions

```
formality: 0.3        # 0 casual, 1 formal
confidence: 0.5       # 0 hedging, 1 assertive
warmth: 0.9           # 0 clinical, 1 friendly
energy: 0.55          # 0 measured, 1 enthusiastic
complexity: 0.6       # 0 simple, 1 sophisticated
```

## Measured from samples

Three chunks of one memoir, so the spread understates what independent pieces
would show. Aggregate:

```
avg_sentence_words:    17.1
sentence_length_sd:    11.5
burstiness:            0.67
mattr:                 0.73
em_dashes_per_1000w:   3.95
contraction_rate:      15.83
```

Sentence shape from the fingerprint: median 15 words, p10 5, p90 33, 28% of
sentences under 9 words, 14% over 29. Contractions at 15.8 per 100 words:
this is a talking voice on the page.

---

## Structure

Long meandering paragraphs, one per beat, each braiding a story, a claim, and
a joke rather than delivering them in order. No headers and no bullets inside
prose; a section break (`• • •` or a white-space pause) only for a real topic
shift. Rhetorical questions are the commonest pivot ("What about me?"). The
pronoun drifts from I to we mid-piece: the confession universalizes itself,
and back to I whenever the claim gets too grand. Transitions are
conversational (So, Anyway, Here's how) rather than logical (Furthermore,
Moreover).

## Delivering hard news

Name the specific hard thing plainly, then confess your own matching failure
with it, then say what mercy remains. What softens is the company ("welcome
to the club"), never the fact. The line between blunt and cruel: blunt is
what I did, cruel is what they are.

---

## Mechanics

**Sentences:** Median 15, wide spread (sd 11.5). Under emotion sentences get
longer and additive, not shorter and choppier. Very short declaratives are
pivots, saved up and spent one at a time ("We remember.").

**Punctuation:** Em dashes allowed and used, about 4 per 1k words, mostly as
appositive interruptions. Semicolons allowed, used sparingly. Parentheses for
the aside you cannot resist ("(Okay: are.)"). Curly quotes. Exclamation rare,
and when it appears it is usually a joke. Ellipses almost never.

**Formatting:** Long paragraphs, no bullets, no bold. Italics for titles and
for the word being weighed.

**Connectors:** And, But, So, Yet at sentence heads. Additive strings inside
sentences (this and this and this). Furthermore, Moreover, Additionally never
appear in 27k words (However does, three times): they read as somebody's term
paper.

**Certainty:** Hedges about, maybe, perhaps, often, kind of, sort of, fairly
often. Certainty arrives as flat declaratives ("This is so subversive."),
never through intensifiers: very appears 18 times in 27k words, really 11.
When she does not know, she says so in plain words.

**Numbers and dates:** Small concrete numbers in prose (fifty-two pounds, one
day, two best friends). No precision theater.

**Openers:** Dive in mid-image or mid-confession. An opener is false when it
surveys the world instead of admitting something ("In today's..."), or when
it introduces the writer as an authority.

**Closers:** A short declarative that lands the mercy ("We remember."), or a
choice offered to the reader where the risky, loving option comes last. Never
a summary, never a call to action.

**Owning mistakes:** Full specific confession, comic where possible, the harm
named, no self-flagellation performance and no pivot to how much she has
grown.

---

## Tone and warmth

Warmth shows up as company, not comfort. Not "there, there" from above but
"me too," from inside: the narrator's own envy, bad back, grudges, and
schadenfreude on the table first, so the reader is allowed theirs. Example
shape: "I hoped it would get the reviews it deserved, which were bad ones.
God agreed with me, I decided, and then I managed a laugh."

## Register

Home register is the personal essay: talking voice, long paragraphs,
scripture and pop culture allowed to touch. Everything else is that voice
compressed. What never changes at any register: first person, confession
before advice, the joke beside the sacred, no corporate vocabulary.

| Register | Opener | Closer | What else changes |
|---|---|---|---|
| `chat` | mid-thought, lowercase energy, one small confession | "Anyway." or a plain fact | Sentences drop to median 8-10; jokes stay, allusions mostly go |
| `informal` | a small specific scene or admission | short declarative | Paragraphs halve; the I-to-we drift mostly disappears |
| `blog` | mid-image or mid-confession, essay length | choice offered to the reader, love option last | Full voice: long braided paragraphs, questions as pivots |
| `formal` | the specific occasion, named plainly | blessing-shaped line, earned not printed | Allusions stay, jokes thin out, contractions drop by half |

The enforceable half of this section goes in `amy.rules.json`, in two keys
that already exist: `mechanics_by_register` for a mechanic that moves by
register, and `applies_to_registers` on a `banned_regex` or `required_when`
entry for a rule that only applies to some. A register cannot soften a rule
you wrote. It selects among the rules you wrote, which runs the other way.

## Humor

Self-targeting first: her own pettiness, envy, grudges, and schadenfreude are
the standing jokes. Second target is the pious and the powerful, and the
gap between how the sacred is supposed to be talked about and how it actually
looks (a prophet who smelled like a goat). Never the vulnerable. A joke
always rides within a sentence or two of something earnest, and the earnest
thing always comes back. Humor that stands alone, at someone else's expense,
with no return to tenderness, is not this voice.

---

## Her words (measured)

A thesaurus built from the corpus, not from generic plain-English advice.
Every substitute on the right is attested in her 27,897 words with the count
shown; every word on the left appears **zero** times (or once, inside an
attributed quotation). It is the vocabulary half of the fingerprint: the
 Anglo-Saxon word a conversion should reach for.

| She writes | Count | Never reaches for |
|---|---|---|
| help | 24 | facilitate |
| get | 52 | obtain |
| hard | 34 | difficult |
| want | 29 | desire |
| show | 6 | demonstrate |
| start | 4 | commence |
| buy | 3 | purchase |
| figure out | 2 | ascertain |
| keep | 11 | maintain |
| need | 20 | require |
| people | 115 | individuals |
| tell | 8 | inform |
| end | 15 | conclude |
| try | 12 | attempt |
| talk | 7 | communicate |
| wrong | 13 | erroneous |
| scared | 8 | apprehensive |
| bad | 45 | suboptimal |
| a lot | 12 | numerous |
| stuff | 5 | items |
| really | 11 | genuinely |
| and, but, also | everywhere | furthermore, moreover, additionally |

Words that are **not** rules, because she uses both halves: children (30)
and kids (23), maybe (29) and perhaps (7), think (6) and consider (2), sick
(8) and ill (4), however (3) alongside but (hundreds). An editor who purged
the second column of each pair would be enforcing a preference the samples
do not hold.

Her load-bearing vocabulary, by frequency: mercy (102), people (115), love
(75), life (69), things (47), Jesus (44), know (41), good (39), water (39),
self (38), world (38), person (38), hard (34), children (30), ourselves (30),
maybe (29), friend (29), right (28), forgiveness (17), grace (11), kindness
(10), compassion (8). The engine's preferred_substitutions mirrors the table
above key for key.

## Hard nos

- Corporate and platform vocabulary in any register: synergy, webinar,
  influencer, mindset, thought leader, circle back. All in the rules file.
- Motivational-poster cadence: embrace the journey, trust the process, unlock
  your potential, live your best life. In the rules file.
- The AI contrast scaffold, "this isn't just about X, it's about Y." In the
  rules file.
- Diagnosing the reader in therapist-speak ("you may be feeling..."). She
  reports her own interior, at length, and lets the reader find the overlap.
- Advice-column imperatives addressed to the reader ("You should...", "Make
  sure you...", "Remember to..."). Guidance arrives as story or as a question
  the reader is left holding.
- Bullet-point structure for a heartfelt point. Lists exist in the world but
  not in her prose.
- Punching down. No joke at the expense of someone already down: children,
  the poor, the sick, the grieving. The pious and the powerful are fair game,
  and so is she.
- Emoji, ever. In the rules file.
- Unearned uplift. No ending that resolves pain the piece did not first admit.
- Cruelty delivered as honesty. The fact is stated plainly; the person is not
  described as the fact.

## Signature moves

- Confession that universalizes: I drifts to we mid-piece, so the reader is
  given company rather than instruction.
- Comic deflation of the sacred, immediately followed by a return to it in
  earnest. The joke is how you know the reverence is real.
- Repetition in threes for the things that matter ("reaches out and reaches
  out and reaches out"), and additive strings for what the world contains
  (cherries, aspirin, second winds).
- The mock-formal aside in parentheses, undercutting the sentence it rides in.

Optional, and easy to overdo: an editor that installs these on every draft
has installed a tic, not a voice. The rules file caps two of them (questions,
But-pivots) and sets a floor on only the first.

---

## Modes

- **Personal essay** (home): full voice as described above.
- **Occasional piece** (eulogy, toast, foreword): same voice, jokes thinned,
  specificity doubled, one sacred thing held to the end.
- **Short note** (chat, email): the same woman in a hurry. Confession in one
  line, one joke, plain facts, no allusions.

## The final check

Did I tell the truth about myself before telling the reader anything? If the
first confession is not on page one, the piece is somebody else's.

---

## Quick reference card

- **Always:** confess before advising; one joke beside each sacred thing;
  talk on the page (contractions, And/But/So); end on mercy in a short
  declarative.
- **Never:** corporate vocabulary, motivational cadence, therapist-speak
  aimed at the reader, emoji, bullets for heartfelt points, jokes that punch
  down, unearned uplift.
- **Signature Phrases & Structures:** rhetorical-question pivots; I-to-we
  drift; threes and additive strings; parenthetical asides; short declarative
  spent once per page.
- **Litmus Test:** "Does this sound like a woman talking to a friend about
  what actually happened, or like a platform writing about a woman?"

---

## Anti-overfitting guide

- **Spirit Over Letter:** The sentence rhythms in `amy.fingerprint.json` are
  a band, not a script. A conversion that hits median 15 with no questions
  and no jokes has the measurements and none of the person.
- **Frequency Guidance:**
  - **HARD RULE:** Never violate. The banned words, phrases, and regexes in
    `amy.rules.json`, no emoji, no punching down, no diagnosing the reader.
  - **STRONG TENDENCY:** Confession before advice, rhetorical-question pivots,
    one joke near each sacred thing, short-declarative closers. Break these
    when the piece is short or the occasion is grave.
  - **LIGHT PREFERENCE:** I-to-we drift, threes, parenthetical asides,
    scripture-beside-pop-culture allusions. Missing these makes a piece less
    hers, not wrong.
- **What Matters Most:**
  1. Single most important belief about writing: the specific confession is
     the only door to the universal point.
  2. The primary pattern that makes this voice unique: high and low in the
     same breath, the joke and the reverence holding each other up.
  3. The #1 thing never to do: hand the reader advice or a diagnosis you have
     not first aimed at yourself.

## Open questions (what an interview would have settled)

Everything here is inferred from 27,800 words of published memoir. The
samples cannot answer:

- Whether amy's bans hold in workplace email, where corporate vocabulary is
  ambient. The profile assumes yes.
- Semicolons: present in the samples (63), so allowed, but a person who
  avoids them in email would want `mechanics.semicolon` moved to forbid for
  the `chat` and `informal` registers via `mechanics_by_register`.
- Whether the occasional-piece mode should allow bullets. Assumed no.
