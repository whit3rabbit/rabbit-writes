# Labeled corpus

`PROOF.md` says, in the file itself, that scoring one hand-written human sample
against one hand-written slop sample is the weakest form of evidence a detector
can offer. It guards against a regression. It does not measure anything.

This directory is the replacement, and right now it is empty. That is the state
of the evidence and it is written down rather than glossed: the harness works,
the protocol is here, and nobody has gathered the texts. Anyone can, including
you, and `score.py` will publish the result the moment they do.

## What it measures

The false-positive rate of the P0 band, per register, with a 95% Wilson
interval.

P0, because that is the band the README calls evidence rather than opinion, and
the one `--check` fails CI on. A P1 on human prose is not an error: good writing
has wordiness in it, and the craft band is supposed to say so. A P0 on human
prose is the tool calling somebody a liar.

Per register, because the tolerance matrix exists precisely because the
registers behave differently. A pooled rate hides the register where the engine
is worst, which is the one a reader needs.

With an interval, because "0 of 12 flagged" is not a 0% error rate. It is
somewhere under 25%, and saying so is the difference between a measurement and
a boast. See `wilson()` in `scripts/detector-corpus/corpus_io.py` for why the
usual normal approximation is wrong at rates this close to zero.

## What counts as a human sample

Prose with **archive evidence** that it predates 2022-11-30, when chat-based
generation became something a working writer could plausibly have used.

An archive capture, not an author's word and not a live URL. A live page can be
edited. A Wayback capture from 2019 cannot. This is a higher bar than most
detector evaluations clear, and it is the only bar that makes the resulting
number mean anything: a corpus of "prose the maintainer believes is human" tests
the maintainer.

`add_sample.py` refuses a `human` label with a publication date after the
cutoff.

## What counts as a generated sample

Prose from a named model, with the prompt recorded verbatim and the date it was
produced. The prompt matters: "write a blog post about X" and "write a blog post
about X in a plain, concrete voice, no filler" produce different documents, and
a corpus built only from the first measures the engine against slop nobody was
trying to avoid.

## Why the text is not committed

Hash-only. The manifest records the source URL, the archive URL, the publication
date, why that date is credible, the register, the word count, and the SHA-256
of the normalized text. The text itself lands in `texts/`, which git ignores.

The claim is public and checkable. The prose stays with whoever wrote it. Anyone
can refetch from the archive URLs, run `score.py --verify`, and either reproduce
the hashes or find out a sample moved, in which case it is excluded rather than
quietly rescored.

## Populating it

```bash
cd scripts/detector-corpus

# a human sample
python3 add_sample.py ~/fetched/locking-2019.txt \
  --id human-0001 --label human --register technical-blog \
  --source-url  https://example.dev/posts/distributed-locking \
  --archive-url https://web.archive.org/web/20190304120000/https://example.dev/posts/distributed-locking \
  --published 2019-03-04 \
  --why-credible "Wayback capture 2019-03-04, three years before the cutoff"

# a generated one
python3 add_sample.py ~/generated/locking.txt \
  --id gen-0001 --label generated --register technical-blog \
  --model claude-sonnet-4-5 --generated 2026-08-11 \
  --prompt "Write a 700-word blog post about distributed locking"

python3 score.py            # the rates, with intervals
python3 score.py --verify   # hashes only
```

Aim for at least 20 human samples per register before quoting a rate for that
register. `score.py` prints anything smaller with the sample size attached and
the interval doing the arguing.

Spread the human samples across registers and across writers. Fifty posts by one
person measures how well the engine handles that person.

## What a result would change

`PROOF.md` currently carries a disclaimer where a number belongs. A populated
corpus turns the project's central honesty claim, that detector false-positive
rates above 60% on non-native English writers are the reason this tool reports
named findings instead of a score, from a citation of somebody else's research
into a measurement of this engine.

Until then the disclaimer stands, and it should.
