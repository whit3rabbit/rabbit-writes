---
name: rabbit-rewrites
description: Rewrite the prose the engine flagged using a small local model over an OpenAI-compatible endpoint, instead of spending a frontier model on it. Use when the user wants to de-slop or humanize a draft offline, on a Raspberry Pi, in CI, or in a pre-commit hook, mentions llama.cpp, llama-server, Ollama, LM Studio, vLLM, or OpenRouter for writing work, asks which local model is good enough to clean up their writing, wants rewriting that costs no API tokens, or asks to benchmark or compare models on a rewriting task. Covers endpoint setup, planning what would be sent, applying gated rewrites in place, and measuring a model's pass rate.
license: MIT
metadata:
  version: "0.1.0"
---

# Model-backed rewriting

Detection in this plugin needs no model. `scan.py` is pure Python and runs on a Pi today. Rewriting is the part that needs one, and this is the path that uses a small local model for it rather than a frontier model.

**Paths.** `${CLAUDE_PLUGIN_ROOT}/skills/` means the directory holding this skill and its siblings (`rabbit-writes`, `voice-setup`, `rabbit-readme-improver`, `rabbit-reads`, `rabbit-rewrites`). Claude Code expands the variable. On a host that doesn't, such as Codex, resolve it that way by hand.

The design rests on one fact and one mechanism.

**The fact.** A tell sits in a sentence. Send that sentence and the rule it broke, and the request is about 150 tokens whatever the document's length. The document is never sent, so there is no chunking strategy, no overlap window, and no context limit to design around. A 10,000-word draft with 40 findings is 40 independent 150-token calls.

**The mechanism.** A small model is not trusted, it is gated. Every reply has to survive `verify.py`, which is the same check that decides whether `--apply-safe` writes at all, plus a rescan proving the tell is gone and nothing new arrived. A rejected reply is retried with the reason attached, then abandoned, and the original text stays. That is what makes a 1.7B a plausible engine here and what makes "which model" a measurement rather than an argument.

## Set up an endpoint

Any server speaking `POST {base_url}/chat/completions` works. There is one client, and the URL does the rest.

```bash
llama-server -m qwen3-1.7b-q4_k_m.gguf --port 8080 -c 4096 --flash-attn
```

```bash
ollama serve   # then use http://127.0.0.1:11434/v1
```

Point the tool at it once, in a `.rabbit-model` file beside the document or at the repository root, next to `.rabbit-voice`:

```json
{
  "base_url": "http://127.0.0.1:8080/v1",
  "model": "qwen3-1.7b",
  "context_tokens": 4096,
  "max_output_tokens": 640,
  "temperature": 0.2
}
```

For a hosted endpoint, name the environment variable holding the key. Never the key itself:

```json
{
  "base_url": "https://openrouter.ai/api/v1",
  "model": "qwen/qwen3-4b-instruct",
  "api_key_env": "OPENROUTER_API_KEY"
}
```

`$RABBIT_MODEL_BASE_URL`, `$RABBIT_MODEL_NAME` and `$RABBIT_MODEL_API_KEY` are the fallback for CI. Nothing is configured by default and nothing is auto-discovered: a tool that quietly finds a server on port 11434 is a tool that quietly ships somebody's draft to whatever is listening there.

**Thinking is turned off in every request, and you want it that way.** Most current small models are hybrid reasoning models, and a reasoning block eats the output budget before the model reaches the rewrite. Measured on Qwen3.5-0.8B-Q4_K_M over the battery below: thinking on scored 0 accepted out of 15 at 8.6 seconds a passage, all fifteen dying at `max_tokens` with an empty reply. Thinking off, the same model scored 10 of 15 at 0.47 seconds. Set `"disable_thinking": false` if you have a model that needs it, and raise `max_output_tokens` well past 640 when you do.

## Run it

Deterministic fixes first. They are free, they are correct, and they leave the model a smaller job.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/scripts/scan.py draft.md --apply-safe --write
```

Then see what would be sent, without sending any of it. Run this first on a document that is not yours.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/scripts/scan.py draft.md --apply-model --model-plan
```

Then the rewrite. Without `--write` it is a dry run that prints every before and after.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/scripts/scan.py draft.md --apply-model
python3 ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/scripts/scan.py draft.md --apply-model --write
python3 ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/scripts/scan.py draft.md --apply-model --stdout | diff draft.md -
```

`--model-limit N` stops after N passages and lists what it dropped. `--model-attempts N` changes how many tries each passage gets before it is left alone, and each retry is told why the last one was rejected.

## Which model

Do not take a recommendation, take a measurement. The bench runs a fixed battery of twelve passages through whatever endpoint is configured and reports the pass rate through the same gate the real run uses.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-rewrites/scripts/bench.py --model-endpoint http://127.0.0.1:8080/v1 --model-name qwen3-1.7b
python3 ${CLAUDE_PLUGIN_ROOT}/skills/rabbit-rewrites/scripts/bench.py --repeat 3 --json > qwen3-1.7b.json
```

Read the rejection histogram before the pass rate. A model failing mostly on "nothing improved" wants a better prompt or more parameters. One failing on "number altered or removed" is unsafe for this job at any size, and its pass rate is beside the point.

Two things worth knowing before you pick. Sub-2B models are reported to struggle with multi-step instructions, and the reason one is plausible here is that the task is deliberately single-step and single-passage. And a model trained on the same prose everything else was trained on will reach for a second tell while removing the first, which the gate catches and counts as a rejection rather than a fix.

## What this will not do

**It will not match a voice.** Rewriting a passage to hit a stored fingerprint is not a sentence-level task and a small model cannot do it. This is the de-slop path. Voice conversion stays with `rabbit-writes` and a capable model.

**It will not check grammar.** The gate proves a rewrite kept every number, date, path, and quotation, and lost the tell. A fluent-sounding but ungrammatical reply passes every check here. Read the diff.

**It will not touch code, tables, headings, or lists.** Only prose blocks are sent, and a finding inside anything else is reported as not sent rather than skipped silently.

**It will not fix everything the scan reports.** Document-wide measurements (lexical diversity, paragraph-length distribution) are not reachable by editing any one passage, and the safety band is never rewritten at all. Both are listed under "not sent to the model" with the reason.

## Safety

**A document carrying a concealed instruction is not sent to any model.** A rewriter is exactly what that text is written for, so the run refuses before the first request, quotes the span, and writes nothing. Nothing in the safety band is fixable and a `rabbit-allow` comment cannot clear it.

**No key in a committed file.** `.rabbit-model` names an environment variable and is rejected outright if it carries an `api_key`.

**No document text over plain http off this machine.** `http://` reaches loopback and nothing else unless the config sets `allow_insecure` for a host you control.

## Where things live

| Path | What it holds |
| --- | --- |
| `${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/scripts/rwlib/endpoint.py` | the endpoint, its config resolution, and the three refusals above |
| `${CLAUDE_PLUGIN_ROOT}/skills/rabbit-writes/scripts/rwlib/rewrite.py` | unit planning, the prompts, the gate, the retry loop |
| `${CLAUDE_PLUGIN_ROOT}/skills/rabbit-rewrites/scripts/bench.py` | the model bench |
| `${CLAUDE_PLUGIN_ROOT}/skills/rabbit-rewrites/scripts/battery.json` | the twelve passages it scores against |

Editing `battery.json` changes what every published pass rate means, which is what its `version` key is for.
