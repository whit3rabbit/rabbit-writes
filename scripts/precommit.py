#!/usr/bin/env python3
"""
Run one of the checkers over the files pre-commit hands it.

pre-commit passes a batch of staged paths in a single invocation. `scan.py` and
`readme_check.py` each take one file, because each prints one report about one
document and a report about six documents at once is a log. Rather than bend
both CLIs into something that answers a question nobody asked interactively,
this loops.

    python3 scripts/precommit.py scan   [scan args]        -- FILE...
    python3 scripts/precommit.py readme [readme args]      -- FILE...

Without `--`, the split is positional: pre-commit lays out `entry` words, then
`args:`, then the staged filenames, so everything up to the first token that is
not a flag and is not a flag's value is an argument and the rest are files.

A flag's value has to be recognised by name, which is why VALUE_FLAGS exists.
The first version of this guessed by asking whether a token was a file on disk,
and `--voice-rules whit3rabbit.rules.json` is a flag whose value is a file: the
profile was scanned as if it were somebody's draft, `--voice-rules` was left
with nothing after it, and argparse failed every staged file with exit 2. The
shipped `rabbit-scan-voice` hook did that on every commit.

Exit 1 if any file failed, after running all of them. Stopping at the first
failure hides the other five, and somebody fixing a commit wants the whole list.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKERS = {
    "scan": os.path.join(ROOT, "skills", "rabbit-writes", "scripts", "scan.py"),
    "readme": os.path.join(ROOT, "skills", "readme-writing", "scripts",
                           "readme_check.py"),
}

# Options that take a separate value, across both checkers. `--flag=value` needs
# no entry here, and neither does a store_true flag. Keep this in step with the
# two argparse blocks: a value-taking option missing from it gets its value read
# as a filename, which is the bug this list exists to prevent.
VALUE_FLAGS = {"--profile", "--voice-rules", "--sarif-uri"}


def split_args(argv):
    """(flags, files). Files are whatever follows the last argument."""
    if "--" in argv:
        cut = argv.index("--")
        return argv[:cut], argv[cut + 1:]
    flags, index = [], 0
    while index < len(argv):
        token = argv[index]
        if not token.startswith("-"):
            break
        flags.append(token)
        index += 1
        if token in VALUE_FLAGS and index < len(argv):
            flags.append(argv[index])
            index += 1
    return flags, argv[index:]


def main(argv):
    if not argv or argv[0] not in CHECKERS:
        print("usage: precommit.py {%s} [args] -- FILE..."
              % "|".join(sorted(CHECKERS)), file=sys.stderr)
        return 2
    checker = CHECKERS[argv[0]]
    flags, files = split_args(argv[1:])
    if not files:
        return 0

    failed = []
    for path in files:
        result = subprocess.run([sys.executable, checker, path] + flags)
        if result.returncode:
            failed.append(path)
    if failed:
        print("\n%d file(s) with a P0 finding: %s"
              % (len(failed), ", ".join(failed)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
