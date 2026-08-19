# Academic calibration corpus

Nineteen open-access research papers, used to calibrate the `academic` register in `skills/rabbit-writes/scripts/registers.json`. The repository's rule is that a new detector is calibrated against real documents before it is wired to anything, and the 100-README corpus that calibrated the safety band cannot answer this question: a README is not a paper.

## What is here

`manifest.json` carries one entry per paper: DOI, journal, subject facet, publication date, license URL, source URL, per-section word counts, and a SHA-256 of the extracted text.

`summary.json` carries what the engine found, per register, per finding id, with the terms that drove each vocabulary rule. `PROOF.md` quotes it.

`texts/` is not in git. The prose belongs to whoever wrote it, and CC BY permits redistribution without obliging it. Hashes travel better than 800KB.

## Reproduce it

```bash
python3 scripts/academic-research/01_fetch_corpus.py
```

That refetches the DOIs the manifest already names and verifies each extracted text against its recorded hash. It needs no judgment: the committed manifest fully determines the corpus.

```bash
python3 scripts/academic-research/01_fetch_corpus.py --verify
```

Hash-checks what is already on disk, with no network at all.

`--discover` is the third mode and it is the one not to run casually. It queries the PLOS search API and pins a new paper set, which moves every number measured against the old one.

## Why PLOS, and only PLOS

Every PLOS article is CC BY 4.0 and says so in machine-readable form inside its own JATS XML, which `01_fetch_corpus.py` reads and refuses to proceed without. The PMC Open Access subset was considered and dropped for this pass: its licenses vary per article, several are non-commercial or no-derivatives, and each one needs a check PLOS makes unnecessary. Adding PMC later means adding a fetcher, not relaxing the license rule.

Six subject facets, four papers each, so the corpus describes a register rather than one field's habits. A vocabulary exemption calibrated only on computer science would exempt whatever computer scientists happen to overuse.

## Which sections

Abstract, introduction, results, and discussion or conclusion. Those four are prose and they are where the register's characteristic vocabulary lives. Methods is skipped because it is procedural text full of equations and reagent lists, and scoring it would measure the genre of a protocol rather than the register of a paper.

## What it decided

The corpus cut the candidate exemption list from seven words to two, and it did so by asking one question of each: does this word appear across the corpus, or many times in one paper?

`holistic` raised 11 hits and appears in fewer than two papers. That is one author's habit, not a register fact, and exempting it would have hidden a real finding on the strength of a single document. `significant` and `effective` were on the list because a synthetic sample fired `tier3-density` on them. Nineteen real papers never fire that rule at all, because it needs 2% of all words and no real paper reaches it.

What survived is `paradigm`, `paradigms`, and `transformation`, each of which carries a technical sense in a paper that it does not carry in a blog post. `crucial` appears in six papers and was still rejected, on the grounds that it means the same thing everywhere and is an intensifier rather than a term.

`utilize`, `in terms of`, and `it is important to note that` fire on 14 of 19 papers and are left at full strength on purpose. Academic writing being full of them is a fact about academic writing, not a reason to stop reporting them, and academic style guides say so too.
