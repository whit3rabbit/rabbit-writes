#!/usr/bin/env python3
"""
Render the root AGENTS.md from CLAUDE.md, the one home of the repo instructions.

    python3 scripts/agents_md.py

Codex reads AGENTS.md and never CLAUDE.md, and it does not process CLAUDE.md's
`@path` imports, so the instructions have to exist twice. A hand-maintained
second copy drifts the way every copied instruction file here has: this repo's
own AGENTS.md once shipped a case-insensitive claude-to-Codex replacement that
renamed the `rabbit-claude-md` skill, the `.claude-plugin/` directory, and the
`.claude/docs/` imports into paths that do not exist. The file is generated
instead: edit CLAUDE.md, run this script, and `scripts/validate.py` fails when
AGENTS.md no longer matches the render.

The transform is the substitutions below, each pinned to a sentence that must
appear exactly once. An anchor that stops matching means CLAUDE.md changed a
sentence this file rephrases, and the anchor has to be updated on purpose
rather than silently rendering stale guidance. Stdlib only, 3.9+.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (CLAUDE.md anchor, AGENTS.md replacement). Codex loads neither the per-skill
# CLAUDE.md files nor the `.claude/docs/` imports automatically, so those two
# facts are rephrased from "loaded automatically" into instructions to read;
# everything else renders verbatim.
TRANSFORM = (
    (
        "Each skill under `skills/<name>/` carries its own `CLAUDE.md` with "
        "that skill's structure, gotchas, and regeneration commands, loaded "
        "automatically when Claude works in that directory.",
        "Each skill under `skills/<name>/` carries its own `CLAUDE.md` with "
        "that skill's structure, gotchas, and regeneration commands. Claude "
        "loads it automatically when working in that directory, and Codex "
        "does not, so read it before working there.",
    ),
    (
        "Deeper cross-skill detail lives under `.claude/docs/`, imported "
        "below so it is always in context. Which one governs which area:",
        "Deeper cross-skill detail lives under `.claude/docs/`, which Codex "
        "does not import automatically. Read the one that governs the area "
        "before touching it:",
    ),
    (": @.claude/docs/packaging.md", ": `.claude/docs/packaging.md`"),
    (": @.claude/docs/validate-internals.md",
     ": `.claude/docs/validate-internals.md`"),
    (": @.claude/docs/hooks.md", ": `.claude/docs/hooks.md`"),
)


def render(claude_md):
    """AGENTS.md content rendered from CLAUDE.md text.

    Raises ValueError when an anchor is missing or duplicated, which is the
    signal that CLAUDE.md and this transform have drifted apart.
    """
    out = claude_md
    for anchor, replacement in TRANSFORM:
        count = out.count(anchor)
        if count != 1:
            raise ValueError("anchor appears %d times, expected exactly once: %r"
                             % (count, anchor[:60]))
        out = out.replace(anchor, replacement)
    return out


def main():
    claude_path = os.path.join(ROOT, "CLAUDE.md")
    with open(claude_path, encoding="utf-8") as fh:
        claude_md = fh.read()
    try:
        agents_md = render(claude_md)
    except ValueError as exc:
        print("cannot render AGENTS.md: %s" % exc, file=sys.stderr)
        return 1
    with open(os.path.join(ROOT, "AGENTS.md"), "w", encoding="utf-8") as fh:
        fh.write(agents_md)
    print("wrote AGENTS.md from CLAUDE.md (%d substitutions)" % len(TRANSFORM))
    return 0


if __name__ == "__main__":
    sys.exit(main())
