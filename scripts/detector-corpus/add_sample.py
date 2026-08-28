#!/usr/bin/env python3
"""
Register one text in the labeled corpus.

    python3 add_sample.py TEXT.txt \\
        --id human-0007 --label human --register technical-blog \\
        --source-url https://example.dev/posts/locking \\
        --archive-url https://web.archive.org/web/20190304.../https://example.dev/posts/locking \\
        --published 2019-03-04 \\
        --why-credible "Wayback capture 2019-03-04, three years before the cutoff"

    python3 add_sample.py OUT.txt \\
        --id gen-0007 --label generated --register technical-blog \\
        --model claude-sonnet-4-5 --generated 2026-08-11 \\
        --prompt "Write a 700-word blog post about distributed locking"

    python3 add_sample.py PR_BODY.txt \\
        --id gen-lb-20260824-r4 --label generated --register docs \\
        --model "claude (self-attributed: Claude Code footer in the body)" \\
        --generated 2026-08-24 \\
        --dataset louisabraham/load-bearing --revision <40-hex commit> \\
        --loader github-jsonl --path data/days/2026-08-24.jsonl \\
        --split 2026-08-24 --row 4 --field body \\
        --collected 2026-08-27 --license "MIT (author-confirmed)" \\
        --why-credible "the body carries the literal Claude Code footer"

The text is copied into docs/detector-corpus/texts/, which git ignores, and its
SHA-256 goes in the manifest. That split is the whole design: the claim is
public and checkable, the prose stays with whoever owns it. See corpus_io.py.

Rejects a `human` sample published after the generation cutoff, and rejects a
duplicate hash: the same post fetched twice under two ids would count twice in
a rate, which is how a corpus quietly becomes smaller than it says it is.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
ENGINE = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")
for _path in (HERE, ENGINE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import corpus_io  # noqa: E402
from rwlib import cli_error, registers  # noqa: E402


def main():
    examples = [
        "python3 scripts/detector-corpus/add_sample.py TEXT.txt --id human-0007 --label human --register technical-blog --source-url https://example.dev/posts/locking --archive-url https://web.archive.org/... --published 2019-03-04 --why-credible 'Wayback capture 2019-03-04'",
        "python3 scripts/detector-corpus/add_sample.py OUT.txt --id gen-0007 --label generated --register technical-blog --model claude-sonnet-4-5 --generated 2026-08-11 --prompt 'Write a 700-word blog post...'"
    ]
    ap = cli_error.LLMArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples
    )

    ap.add_argument("file", help="the text to register")
    ap.add_argument("--id", required=True)
    ap.add_argument("--label", required=True, choices=corpus_io.LABELS)
    ap.add_argument("--register", required=True,
                    help="which register this document is written in, so a "
                         "false-positive rate can be reported per register")
    ap.add_argument("--source-url")
    ap.add_argument("--archive-url",
                    help="a web archive capture. This is the evidence, not the "
                         "source URL: a live page can be edited")
    ap.add_argument("--published", help="YYYY-MM-DD, from the archive capture")
    ap.add_argument("--why-credible",
                    help="one sentence on why the date can be believed")
    ap.add_argument("--model", help="for a generated sample")
    ap.add_argument("--prompt", help="for a generated sample, verbatim")
    ap.add_argument("--generated", help="YYYY-MM-DD, for a generated sample")
    ap.add_argument("--dataset",
                    help="dataset provenance: the dataset a row is pinned in, "
                         "as owner/name (human or generated samples)")
    ap.add_argument("--revision",
                    help="dataset provenance: the immutable revision the hash "
                         "was taken at. A Hub commit sha, or a 40-hex git "
                         "commit for github-jsonl")
    ap.add_argument("--config", help="dataset provenance: the Hub config, if "
                                     "the dataset has more than one")
    ap.add_argument("--split", help="dataset provenance: the split, or the "
                                    "day for github-jsonl")
    ap.add_argument("--row", help="dataset provenance: the 0-based row index, "
                                  "or the 0-based line for github-jsonl")
    ap.add_argument("--field", help="dataset provenance: the column holding "
                                    "the text")
    ap.add_argument("--loader", help="dataset provenance: 'github-jsonl' for a "
                                     "raw.githubusercontent JSONL pin. Absent "
                                     "means the Hub datasets-viewer")
    ap.add_argument("--path", help="github-jsonl provenance: the file's path "
                                   "inside the repository")
    ap.add_argument("--collected", help="dataset provenance: YYYY-MM-DD the "
                                        "snapshot was gathered")
    ap.add_argument("--license", help="dataset provenance: the terms the "
                                      "dataset ships under")
    ap.add_argument("--notes")
    args = ap.parse_args()

    with open(args.file, encoding="utf-8") as fh:
        text = corpus_io.normalize(fh.read())
    sha = corpus_io.digest(text)
    words = len(text.split())

    manifest = corpus_io.load()
    for existing in manifest["samples"]:
        if existing["sha256"] == sha and existing["id"] != args.id:
            print("that text is already in the corpus as %r. Counting it twice "
                  "would shrink the corpus without changing the number it "
                  "reports." % existing["id"], file=sys.stderr)
            return 1

    provenance = {"source_url": args.source_url, "archive_url": args.archive_url,
                  "published": args.published, "why_credible": args.why_credible,
                  "model": args.model, "prompt": args.prompt,
                  "generated": args.generated, "dataset": args.dataset,
                  "revision": args.revision, "config": args.config,
                  "split": args.split, "row": args.row, "field": args.field,
                  "loader": args.loader, "path": args.path,
                  "collected": args.collected, "license": args.license,
                  "notes": args.notes}
    sample = {
        "id": args.id,
        "label": args.label,
        "register": args.register,
        "words": words,
        "sha256": sha,
        "provenance": {k: v for k, v in provenance.items() if v},
    }

    manifest["samples"] = [s for s in manifest["samples"] if s["id"] != args.id]
    manifest["samples"].append(sample)

    # Validated against the engine's register list, not just for shape. Without
    # it a mistyped --register was accepted here and surfaced far away: score.py
    # revalidates the whole manifest and refuses to publish a rate for any sample
    # when one entry names a register that does not exist, so a typo at add time
    # silently disabled the harness rather than failing the command that caused it.
    issues = corpus_io.problems({"samples": [sample]}, registers.registers())
    if issues:
        for issue in issues:
            print("  %s" % issue, file=sys.stderr)
        print("\nnot added.", file=sys.stderr)
        return 1

    os.makedirs(corpus_io.TEXTS_DIR, exist_ok=True)
    destination = corpus_io.text_path(sample)
    if os.path.abspath(args.file) != os.path.abspath(destination):
        with open(destination, "w", encoding="utf-8") as fh:
            fh.write(text)
    corpus_io.save(manifest)
    print("added %s (%s, %s, %d words, %s)"
          % (sample["id"], sample["label"], sample["register"], words, sha[:12]))
    print("text in %s, which git ignores. The hash is the committed claim."
          % os.path.relpath(destination, corpus_io.REPO_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
