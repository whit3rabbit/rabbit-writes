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
from rwlib import registers  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
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
                  "generated": args.generated, "notes": args.notes}
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
