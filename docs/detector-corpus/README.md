# Labeled corpus

`PROOF.md` says, in the file itself, that scoring one hand-written human sample
against one hand-written slop sample is the weakest form of evidence a detector
can offer. It guards against a regression. It does not measure anything.

This directory is the replacement, and half of it is populated. Thirty
generated samples are registered: attributed PR bodies from the load-bearing
dataset, each a pinned row whose text carries the Claude Code footer. The
human half is still empty, and that is the state of the false-positive
evidence, written down rather than glossed. Anyone can gather it, including
you, and `score.py` publishes a rate the moment it lands. The generated half
already publishes one: 9 of 30 detected at P1 under lexicon 7.

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

## Sourcing from a published dataset

A `human` sample can prove its date two ways. One is a web archive capture from
before the cutoff. The other is a published research corpus that was collected
before the cutoff, which is at least as good and easier to cite: the collection
date is documented and reviewed, where a capture is one URL one crawler happened
to visit.

A dataset sample records `dataset`, `config`, `split`, `row`, `revision`,
`field`, `collected`, `license`, and `why_credible` instead of the archive
fields. The `revision` is required and pinned. A dataset name with no revision
is a name rather than a citation: rows get added and reordered, and the hash
stops pointing at anything.

`fetch_samples.py` refetches those through the Hugging Face datasets viewer,
which is plain JSON over HTTPS. That is the reason it works here at all: pulling
one row does not require `datasets`, `pyarrow`, and a hundred megabytes of
transitive dependency in a repository whose whole claim is that it is stdlib.

### What was checked, and what it came to

Searched August 2026, against the two bars that matter: text demonstrably
written before 2022-11-30, and text in one of this engine's six registers.

| Candidate | Date bar | Register bar |
|---|---|---|
| [RAID](https://huggingface.co/datasets/liamdugan/raid) | **fails** | mixed |
| [Blog Authorship Corpus](https://huggingface.co/datasets/barilan/blog_authorship_corpus) | passes (2004) | poor |
| [WritingPrompts](https://huggingface.co/datasets/euclaise/writingprompts) | passes (2018) | poor |
| [CNN/DailyMail](https://huggingface.co/datasets/abisee/cnn_dailymail) | passes (2015) | poor |

**RAID is the one to be careful about.** It is the obvious choice, it is
MIT-licensed, it is the largest benchmark in this area, and secondary sources
describe its human text as pre-2022 and Wayback-sourced. [The paper says
otherwise](https://arxiv.org/html/2405.07940v1): the abstracts domain is
filtered so that "only papers from 2023 or later are present in the data", and
no Wayback sourcing is described anywhere in it. Taking the summary at its word
would have put post-cutoff text into the corpus under a `human` label, which is
precisely the failure the cutoff rule exists to prevent. Read the paper.

The other three clear the date bar and fail the register one. This engine
measures business and technical prose across six named registers, and 2004
teenage blog posts, Reddit creative fiction, and news wire copy are none of
them. A false-positive rate for `technical-blog` measured over short stories is
not a false-positive rate for `technical-blog`. The Blog Authorship Corpus also
cannot be read through the viewer API at all, because it ships a Python loading
script.

So nothing was added. The schema and the fetcher are here and tested, and the
gap is a sourcing problem rather than a tooling one: what this needs is
pre-2022 archived engineering blog posts, changelogs, docs pages, and
correspondence, which is a crawl somebody has to do rather than a dataset
somebody has already published.

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

The second shape is a dataset row that carries the model's own attribution: a
pull-request body ending in the literal "Generated with Claude Code" footer.
The prompt is unknowable for scraped prose, so what stands in for it is the
attribution itself. It is recorded in `why_credible`, with `model` naming the
basis rather than a model id. Such a sample pins what any dataset sample pins:
dataset, immutable revision, loader, path, split, row, and field, plus the
collected date and license. The loader is `github-jsonl` for a pinned
raw.githubusercontent JSONL file. The first batch comes
from `louisabraham/load-bearing` through
`scripts/claude-vocab-research/05_pick_pr_samples.py`, which prints the exact
`add_sample.py` command for each candidate body after a human reads it.

The footer text matches no catalogue pattern today, so scoring the engine over
these samples is not circular. Detection has to come from the prose, not the
signature. The day a pattern matches the footer, that changes, and the samples
would need relabeling as trivial. That fact rides along in each sample's notes.

## Why the text is not committed

Hash-only. The manifest records the source URL, the archive URL, the publication
date, why that date is credible, the register, the word count, and the SHA-256
of the normalized text. The text itself lands in `texts/`, which git ignores.

The claim is public and checkable. The prose stays with whoever wrote it. Anyone
can refetch from the archive URLs, run `score.py --verify`, and either reproduce
the hashes or find out a sample moved, in which case it is excluded rather than
quietly rescored.

`fetch_samples.py` is that refetch, and it is the one script in this repository
that makes network requests. Nothing calls it, no test reaches it, and CI does
not run it.

```bash
python3 fetch_samples.py --dry-run   # what it would fetch, no requests
python3 fetch_samples.py             # fetch what this checkout is missing
python3 fetch_samples.py --all       # refetch everything and check the hashes
```

Reproducibility has a limit, and the manifest records it per sample rather than
implying it. A text this script extracted carries
`provenance.extraction: "fetch_samples"` and should refetch to the same bytes. A
text somebody pasted in by hand does not carry it and will not: two people
trimming the same page's navigation by eye do not agree to the byte. The script
reports those as manual rather than as failures, and a mismatch never overwrites
a good local copy. It writes the fetched bytes to `<id>.fetched.txt` beside it
and leaves the two for a person, because "the source was edited" and "our
extractor drifted" look identical from inside the script and only the first one
kills the sample.

The harness itself is tested over a synthetic corpus, with the network stubbed:

```bash
python3 test_corpus_harness.py
```

That exists because the code that will publish a false-positive rate the day
somebody populates this had never run over a populated corpus. A harness whose
first real run is the run that produces the published number is a harness nobody
should believe.

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

# an attributed dataset row (a PR body with the Claude Code footer)
python3 add_sample.py ~/picked/gen-lb-20260824-r4.txt \
  --id gen-lb-20260824-r4 --label generated --register docs \
  --model "claude (self-attributed: Claude Code footer in the body)" \
  --generated 2026-08-24 \
  --dataset louisabraham/load-bearing \
  --revision 2a233f653fd72b431850b957b2d28c5c4dbdbaa6 \
  --loader github-jsonl --path data/days/2026-08-24.jsonl \
  --split 2026-08-24 --row 4 --field body \
  --collected 2026-08-27 --license "MIT (author-confirmed)" \
  --why-credible "the body carries the literal Claude Code attribution footer"

python3 score.py            # the rates, with intervals
python3 score.py --verify   # hashes only
```

Aim for at least 20 human samples per register before quoting a rate for that
register. `score.py` prints anything smaller with the sample size attached and
the interval doing the arguing.

Spread the human samples across registers and across writers. Fifty posts by one
person measures how well the engine handles that person.

## What a result would change

The generated half turned a disclaimer into a number already: the detection
rate at P1 over 30 attributed PR bodies, published by `score.py` and pinned in
`PROOF.md`. The human half is what the central honesty claim still needs: a
populated human corpus turns "detector false-positive rates above 60% on
non-native English writers are the reason this tool reports named findings
instead of a score" from a citation of somebody else's research into a
measurement of this engine.

Until then that disclaimer stands, and it should.
