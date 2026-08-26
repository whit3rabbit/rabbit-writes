# Criteria: what a memory file (CLAUDE.md / AGENTS.md) earns its lines with

No grades. A score out of 100 tells nobody what to cut, and a letter tells them even less. Every judgment here resolves to a named failure mode with evidence, and every piece of content gets one of six dispositions. The mechanical half of these checks lives in `scripts/claude_check.py`. This file is the judgment half.

## What the file is for

A memory file (`CLAUDE.md` or `AGENTS.md`) is loaded into every session, whether the session needs it or not. The root file is a map plus rules: where am I, what commands run this project, which conventions differ from defaults, which mistakes have actually happened. Everything else is either derivable from the code or belongs somewhere that loads on demand.

The universal tie-breaker is the removal test: **would deleting this line cause the agent to make mistakes?** If not, the line is spending context on nothing. Apply it to every line, including the ones that survive every other check.

## Include and exclude

| Include | Exclude |
|---|---|
| Commands Claude cannot guess, with a one-line purpose each | Anything readable straight out of the code |
| Testing instructions and the preferred runner | Standard language conventions Claude already knows |
| Code style rules that differ from defaults | Long explanations or tutorials (link to docs instead) |
| Repository etiquette (branch naming, PR conventions) | File-by-file descriptions of the codebase |
| Architectural decisions specific to this project | Information that changes frequently |
| Environment quirks (required env vars, broken tooling) | Self-evident practices (write clean code, add tests) |
| Gotchas that caused a real mistake | Narratives about past fixes |
| Verification instructions the model would not already run | Re-check and double-check instructions the model performs anyway |

The last row cuts both ways on current models. Claude verifies its own work and catches its own mistakes without being told, so an instruction demanding a verification step it already performs compounds into wasted work. Keep verification lines only when they name a project-specific command or a check the model would genuinely skip.

## The failure modes

Each one below is a name to use in the audit report, with evidence: the file, the line, the quoted text, and for the mechanical ones the measured number.

### changelog-drift

The file narrates what changed instead of stating what is true. Tells: past-tense fix narration, commit references, before-and-after phrasing. Git already holds the history.

Before: a bullet explaining that the config parser was rewritten last month because the old one mishandled quotes, referencing the commit.
After: one line stating the standing rule the rewrite established, or nothing, because the code now handles quotes and says so.

### wrong-altitude

A fact scoped to one module, crate, or package sits in the root file, where every session pays for it. A nested CLAUDE.md in that directory loads exactly when Claude works there. The reverse also occurs: a rule that governs the whole repository buried inside one module's file.

### derivable

The line restates what reading the code reveals in seconds: what a class does, what a directory is named, what a function returns. The class name already says it. Cut it, or replace it with the one thing the code cannot say (the why, the constraint, the trap).

### bullet-bloat

A list item running to paragraph length. A bullet is a retrieval unit: one fact, one rule, one command. Past that it is prose wearing a dash, and the fact inside it stops being findable. Split it, cut it, or move the depth out.

### emphasis-inflation

IMPORTANT on every third line. Emphasis is a budget: when many lines shout, none stands out, and the one rule that genuinely needs it drowns. Strip emphasis down to the one or two lines that get skipped without it.

### duplicate-homes

The same fact stated in two CLAUDE.md files, or in a CLAUDE.md and a doc it links. Two copies drift, and the reader cannot tell which one is current. One home per fact: keep the copy at the right altitude, link or delete the rest.

### dead-command

A fenced command referencing a path that no longer exists. One command that fails on paste costs trust in every other line of the file.

### broken-import

An `@path` import that resolves to nothing. It loads nothing, silently, and reads as if it works.

### scope-creep

Instructions about how to behave in general rather than about this repository: generic engineering advice, personality direction, restated defaults. A memory file is project context, not a system prompt.

### ambiguity

A rule phrased so two readings lead to different work. If Claude keeps asking questions the file already answers, or keeps violating a rule that is present, the phrasing is the defect (or the file is so long the rule is getting lost, which is oversize, not ambiguity).

### missing-load-bearing

The absences: no build or test commands, no env-var quirks, no note about the one tool that behaves strangely on this machine. Judged against the repository, not a template. A project with an obvious standard toolchain may legitimately need almost nothing.

## The six dispositions

Every finding, and every content block the judgment pass reads, resolves to one of these. The report lists them as a table before any edit happens.

| Disposition | Test |
|---|---|
| **keep** | Survives the removal test as written |
| **tighten** | The fact earns its place, the words do not. Cut to the fact |
| **merge** | Two or more lines carry one fact. Combine into the sharpest version |
| **move-to-docs** | Depth worth keeping that no session needs by default. Goes to `.claude/docs/<topic>.md` with a one-line link back, keeping the repo's own `docs/` for its users |
| **move-to-module** | A fact scoped to one directory. Goes to a CLAUDE.md in that directory, and the root copy goes away |
| **delete** | Fails the removal test outright |

`@import` versus a plain link, for anything moved: an import loads every session and a link loads when followed. Import only what must always be in context. Default to the link.

## Emphasis, when it is earned

If Claude keeps skipping one instruction, add emphasis to that line alone. That is the entire budget. The mechanical check in `claude_check.py` counts marker words against it.
