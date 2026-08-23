# Security notes for reviewers and scanners

This bundle is a prose scanner. It reads documents a person points it at,
reports patterns, and halts. Nothing it finds in a document is ever executed,
followed, or sent anywhere by the scanner itself.

Every ClawHub upload passes an automated scan and a code review, and this
bundle is built from the kind of code those reviews exist to judge, so this
file states plainly what is here and how to check it.

## Why an automated scan may flag this bundle

The engine detects concealed prompt injection, so parts of it look like the
thing it detects.

- `scripts/rwlib/injection.py` carries regexes that match imperative phrases
  addressed to an agent, the class of phrasing that tells a model to
  disregard its prior context, to reveal its instructions, or to send
  document text somewhere. They exist to catch those phrases inside
  concealed text and report them. Matching is the whole mechanism: nothing
  reads a match as a command.
- Reference files quote attack shapes as documentation.
  `references/patterns.md` catalogs machine-writing patterns with
  before-and-after examples, and `references/injection.md` explains the
  rule with quoted spans. Those quotations are data under analysis. A note
  at the top of each of those files says so.
- The rule is two-axis by design: concealed text plus a directive in the
  same span is the highest-priority finding, and either one alone sits a
  band lower. An ordinary visible quotation never trips it.

## What the engine does with a finding

It reports, and it refuses. An injection finding cannot be auto-fixed, the
fixer has no entry for it, and it cannot be suppressed from inside the
document, the suppression mechanism refuses the safety band outright. A
concealed instruction cannot write itself out of the report. Both refusals
are asserted by tests in the source repository.

## Network surface

One optional feature talks to the network, and only when a person runs
`scan.py --apply-model` and has configured a model endpoint by hand:

- The endpoint comes from a `.rabbit-model` file beside the document or from
  one of three environment variables. There is no default endpoint, and
  nothing is contacted without one.
- What crosses the network is one flagged passage and the rule it broke, one
  finding at a time. A reply must pass a fact-preservation gate before
  anything is written back.
- No telemetry of any kind. No update checks, no usage reports, no other
  outbound requests anywhere in the bundle.

The three environment variables, also declared in each skill's frontmatter:

- `RABBIT_MODEL_BASE_URL`, the base URL of an OpenAI-compatible endpoint.
  Read only under `--apply-model`.
- `RABBIT_MODEL_NAME`, the model name. Read only under `--apply-model`.
- `RABBIT_MODEL_API_KEY`, a key for a remote endpoint. Read only under
  `--apply-model`, and never logged or persisted.

## How to check these claims

The source repository is `github.com/whit3rabbit/rabbit-writes`, under MIT.
The packager that emitted this bundle, the gate every bundle passes, and the
tests holding both live there. Everything in this bundle is Python 3.9
standard library only: no dependencies, no install step, no compiled code.
Reading the bundle is reading the whole program.

## License

ClawHub publishes this bundle under MIT-0. The source repository is MIT.
