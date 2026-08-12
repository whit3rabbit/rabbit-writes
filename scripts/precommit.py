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
A checker that crashed and a checker that found a P0 both stop the commit, and
they are reported as two different things: the first is a bug in here, and
calling it "a P0 finding" sends the committer hunting through their prose for
something that was never there.
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
VALUE_FLAGS = {"--profile", "--voice", "--voice-rules", "--sarif-uri"}

# Of those, the ones whose value names a file that may live in this repository
# rather than the committer's. `--profile` is a register name and `--sarif-uri`
# is deliberately recorded relative to the consuming repository root, so neither
# belongs here.
PLUGIN_PATH_FLAGS = {"--voice-rules"}


def resolve_plugin_paths(flags):
    """Point a plugin-relative flag value at this repository.

    pre-commit runs a hook with the *consuming* repository as the working
    directory, so the old `rabbit-scan-voice` default of
    `skills/rabbit-writes/voices/whit3rabbit.rules.json` resolved to nothing in
    anybody else's tree: scan.py exited 2 on every staged file and the hook was
    dead on arrival everywhere except here.

    That hook says `--voice auto` now and asks scan.py to resolve the profile,
    so nothing shipped depends on this any more. It stays for the person who
    points `args` at a profile this plugin bundles, which is a reasonable thing
    to write and still resolves nowhere without it.

    Only rewritten when the value does not exist where it was written and does
    exist under ROOT. A committer pointing `args` at their own profile keeps
    winning, and a typo in that path still reaches the checker's own error
    message instead of being silently redirected at somebody else's voice.

    Both spellings, `--flag value` and `--flag=value`. split_args tells the
    reader the second needs no VALUE_FLAGS entry, which is true of the split and
    was not true of this: `args: [--voice-rules=skills/...]` got no fallback,
    scan.py exited 2 on every staged file, and the hook blocked the commit over
    a path the caller never chose.
    """
    out = list(flags)
    for index, token in enumerate(out):
        prefix, target = "", index
        if token in PLUGIN_PATH_FLAGS:
            if index + 1 >= len(out):
                continue
            value, target = out[index + 1], index + 1
        elif "=" in token and token.split("=", 1)[0] in PLUGIN_PATH_FLAGS:
            flag, _, value = token.partition("=")
            prefix = flag + "="
        else:
            continue
        if os.path.exists(value):
            continue
        candidate = os.path.join(ROOT, value)
        if os.path.exists(candidate):
            out[target] = prefix + candidate
    return out


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
    flags = resolve_plugin_paths(flags)

    # Exit 1 is the checkers' "found a P0". Anything else non-zero is the
    # checker failing to run at all: 2 for a file it cannot open or a voice
    # rules file it cannot read, and argparse's own 2 for a usage error. Both
    # stop the commit, and the checker has already printed its reason to stderr.
    blocked, broken = [], []
    for path in files:
        result = subprocess.run([sys.executable, checker, path] + flags)
        if result.returncode == 1:
            blocked.append(path)
        elif result.returncode:
            broken.append("%s (exit %d)" % (path, result.returncode))
    if blocked:
        print("\n%d file(s) with a P0 finding: %s"
              % (len(blocked), ", ".join(blocked)), file=sys.stderr)
    if broken:
        print("\n%s could not check %d file(s), see the errors above: %s"
              % (os.path.basename(checker), len(broken), ", ".join(broken)),
              file=sys.stderr)
    return 1 if blocked or broken else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
