# The reconstruction eval

This directory is empty and the harness in `scripts/voice-eval/` is not. That is
the same arrangement `docs/detector-corpus/` has, for the same reason: gathering
real writing from a real person, with their consent, is the expensive half, and
a scorer written afterwards gets written to fit whatever data turned up.

## What it measures

Every other number this repository publishes scores one detector. This scores
the conversion, end to end, with labels nobody had to write:

1. Take a piece the writer actually wrote. That is the **original**, and it is
   the answer key.
2. Deslop it into a neutral register. That is the **neutralized** text.
3. Convert the neutralized text back into their voice, through the skill and
   nothing else. That is the **reconstruction**.

Then measure how much of the gap the conversion closed. If the round trip works,
the reconstruction lands near the original. If the conversion only fixes
punctuation, it lands near the neutralized text and the number says so.

`recovered = (neutralized - reconstructed) / (neutralized - original)`

1.0 is a round trip that landed exactly. 0.0 moved nothing. Negative means the
conversion made the writing less like its author, which is the reading this eval
exists to surface and the one no per-finding report can give.

Two halves are scored separately, because they fail separately. The Delta half
is register, the six-measure half is construction, and a pass can recover one
without the other: restoring the marker rates while leaving every sentence the
same length has not brought the writing back.

## What it is not

It is a measurement of a pipeline. It says nothing about the writer, and nothing
at all about who wrote anything. A reconstruction that scores 0.4 means the
round trip lost some of the register, not that its author is inconsistent.
`skills/rabbit-writes/references/false-positives.md` applies here with the rest.

It is also not a benchmark to optimize. A conversion that games this number by
copying the original has not converted anything, which is why step 2 has to be
performed and stored rather than derived.

## Building a triple

Steps 2 and 3 need a model, so this is a procedure a person or an agent runs.
The scorer is offline arithmetic over the three finished texts.

1. **Ask first.** The prose stays on the machine it was gathered on. `texts/` is
   gitignored and the manifest carries hashes only, so a published number is
   checkable without this directory being public. That is not a formality: a
   voice profile is a claim about somebody and their writing is theirs.
2. **Pick a piece over 250 words** that they wrote before any of this touched
   it. Under the reliability floor the measures are noise and the scorer says
   so rather than hiding it.
3. **Neutralize it.** Run `deslop` with no profile, or write the neutral version
   by hand. The goal is a document that says the same things in nobody's voice.
   Check it: `scan.py neutralized.md --voice <name>` should report a distance
   well outside the band. If it does not, the neutralization did not happen and
   the conversion has nothing to recover.
4. **Convert it back**, through the skill, with only the profile as input.
   Never show the conversion pass the original. It is the answer key, and a
   reconstruction written with it in context measures nothing.
5. **Store all three** under `texts/`, add the triple to `manifest.json` with
   its `sha256` for each role, and record which profile it belongs to.

```json
{
  "id": "dana-2026-01-migration-note",
  "voice": "dana",
  "original": "dana-01-original.md",
  "neutralized": "dana-01-neutralized.md",
  "reconstructed": "dana-01-reconstructed.md",
  "sha256": {"original": "...", "neutralized": "...", "reconstructed": "..."}
}
```

Then:

```bash
python3 scripts/voice-eval/reconstruct.py
python3 scripts/voice-eval/reconstruct.py --verify   # have the texts moved?
```

## How many

Enough that a mean means something, and the honest floor is higher than it looks.
One triple is an anecdote. Three is a direction. The per-triple numbers are worth
more than the mean either way, because a conversion that recovers the register on
a report and loses it on an email has told you something specific about the
profile, and the average of those two has told you nothing.

Until any of them exist, `PROOF.md` says plainly that the pipeline's end-to-end
behaviour rests on the synthetic fixtures in `skills/rabbit-writes/tests/`, which
own their ground truth and are not real writing.
