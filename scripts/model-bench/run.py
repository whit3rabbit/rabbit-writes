#!/usr/bin/env python3
"""
Run `rabbit-rewrites/scripts/bench.py` across several models and tabulate.

    python3 scripts/model-bench/run.py --model qwen2.5:7b --model gemma2:latest
    python3 scripts/model-bench/run.py --all-ollama --repeat 3
    python3 scripts/model-bench/run.py --endpoint http://127.0.0.1:8080/v1 --model qwen3-1.7b

The bench answers "does this model clear the gate". This answers "which of these
models clears it more often, and what does each one cost", which is the question
you actually have when picking one.

Three things it does that running bench.py by hand does not:

  1. **Starts the server and stops it again.** Only if it started it. A server
     that was already up belongs to somebody else and is left alone.
  2. **Warms each model before timing it.** Ollama loads weights on the first
     request, so an unwarmed run charges 4.7GB of disk read to the first
     passage and reports a seconds-per-unit that is mostly file IO. The first
     measured run of qwen2.5:7b was 3x the second for exactly this reason.
  3. **Writes each result to `docs/model-bench/`,** so a published number has a
     file behind it rather than a paste from somebody's terminal.

This lives outside the skill on purpose. It drives the shipped bench and is not
part of it: nothing here is packaged into a skill archive, because a comparison
harness is a thing a maintainer runs and not a thing a skill does.

Stdlib only, 3.9+.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCH = os.path.join(ROOT, "skills", "rabbit-rewrites", "scripts", "bench.py")
OUT_DIR = os.path.join(ROOT, "docs", "model-bench")
OLLAMA_ENDPOINT = "http://127.0.0.1:11434/v1"

# Long enough for a 7B on CPU to finish twelve passages with retries, short
# enough that a wedged server fails the run instead of hanging the afternoon.
BENCH_TIMEOUT = 3600
WARM_TIMEOUT = 600


def reachable(endpoint, timeout=2):
    try:
        with urllib.request.urlopen(endpoint.rstrip("/") + "/models",
                                    timeout=timeout):
            return True
    except (urllib.error.URLError, OSError):
        return False


def start_ollama():
    """(handle_or_None, note). None means it was already up and is not ours."""
    if reachable(OLLAMA_ENDPOINT):
        return None, "ollama was already running, leaving it alone"
    try:
        proc = subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        raise SystemExit("ollama is not installed (no `ollama` on PATH). "
                         "Pass --endpoint for a server that is already up.")
    for _ in range(60):
        if reachable(OLLAMA_ENDPOINT):
            return proc, "started ollama serve"
        time.sleep(0.5)
    proc.terminate()
    raise SystemExit("ollama serve did not come up on %s" % OLLAMA_ENDPOINT)


def ollama_models():
    try:
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit("--all-ollama needs `ollama` on PATH to list models")
    names = []
    for line in out.stdout.splitlines()[1:]:
        name = line.split()[0] if line.split() else ""
        # Embedding models answer /v1/models and cannot hold a chat. Skipping
        # by name is crude and the alternative is a probe per model, which
        # costs a weight load each to learn something the name already says.
        if name and "minilm" not in name and "embed" not in name:
            names.append(name)
    return names


def warm(endpoint, model):
    """One tiny completion, so the weight load is not charged to passage one."""
    body = json.dumps({"model": model, "stream": False, "max_tokens": 1,
                       "messages": [{"role": "user", "content": "hi"}]}).encode()
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=WARM_TIMEOUT) as response:
            response.read()
    except (urllib.error.URLError, OSError) as exc:
        return None, str(exc)
    return time.monotonic() - started, None


def run_bench(endpoint, model, repeat, attempts):
    cmd = [sys.executable, BENCH, "--model-endpoint", endpoint,
           "--model-name", model, "--repeat", str(repeat),
           "--attempts", str(attempts), "--json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=BENCH_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, "timed out after %ds; the server is wedged or the model is too slow for the battery" % BENCH_TIMEOUT
    if result.returncode != 0:
        return None, (result.stderr or result.stdout)[:600]
    try:
        return json.loads(result.stdout), None
    except ValueError:
        return None, (result.stdout or result.stderr)[:600]


def table(rows):
    header = ("%-22s %6s %9s %7s %12s %9s"
              % ("model", "units", "accepted", "1st try", "findings", "sec/unit"))
    lines = [header, "-" * len(header)]
    for name, payload, error in rows:
        if payload is None:
            lines.append("%-22s  failed: %s" % (name, (error or "")[:60]))
            continue
        s = payload["summary"]
        lines.append("%-22s %6d %4d %3.0f%% %7d %5d -> %-3d %9.2f"
                     % (name, s["units"], s["accepted"], s["accepted_pct"],
                        s["first_attempt"], s["findings_before"],
                        s["findings_after"], s["seconds_per_unit"]))
    return "\n".join(lines)


def rejections(rows):
    lines = []
    for name, payload, _error in rows:
        if payload is None:
            continue
        by = payload["summary"]["rejected_by"]
        if not by:
            lines.append("  %-22s nothing rejected" % name)
            continue
        lines.append("  %-22s %s" % (name, ", ".join(
            "%s x%d" % (reason, count) for reason, count in by.items())))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        prog="run.py",
        description="Score several models against the rewrite gate and compare.")
    ap.add_argument("--model", action="append", default=[],
                    help="model name, repeatable")
    ap.add_argument("--all-ollama", action="store_true",
                    help="every chat model `ollama list` reports")
    ap.add_argument("--endpoint", default=OLLAMA_ENDPOINT,
                    help="OpenAI-compatible base URL (default: local ollama)")
    ap.add_argument("--repeat", type=int, default=1,
                    help="battery passes per model (default 1)")
    ap.add_argument("--attempts", type=int, default=3,
                    help="tries per passage (default 3)")
    ap.add_argument("--out", default=OUT_DIR, help="where the JSON goes")
    args = ap.parse_args()

    handle, note = (None, "using %s as given" % args.endpoint)
    if args.endpoint == OLLAMA_ENDPOINT:
        handle, note = start_ollama()
    print(note)

    try:
        models = list(args.model)
        if args.all_ollama and args.endpoint != OLLAMA_ENDPOINT:
            ap.error("--all-ollama lists local ollama models and cannot be "
                     "combined with a custom --endpoint; name models with "
                     "--model instead")
        if args.all_ollama:
            models += [m for m in ollama_models() if m not in models]
        if not models:
            ap.error("name at least one --model, or pass --all-ollama")

        os.makedirs(args.out, exist_ok=True)
        rows = []
        for model in models:
            seconds, error = warm(args.endpoint, model)
            if error:
                print("%-22s warm-up failed: %s" % (model, error[:80]))
                rows.append((model, None, error))
                continue
            print("%-22s warm in %.1fs, running %d pass(es)..."
                  % (model, seconds, args.repeat))
            payload, error = run_bench(args.endpoint, model, args.repeat,
                                       args.attempts)
            rows.append((model, payload, error))
            if payload is not None:
                payload["warm_seconds"] = round(seconds, 2)
                path = os.path.join(args.out,
                                    model.replace(":", "-").replace("/", "-") + ".json")
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, indent=2)
                print("  -> %s" % os.path.relpath(path, ROOT))
            else:
                print("  failed: %s" % (error or "")[:200])

        print("\n" + table(rows))
        print("\nrejected by:")
        print(rejections(rows))
        print("\nRead the rejection column before the pass rate. 'findings went'")
        print("means the model rewrote without improving. 'number altered' means")
        print("it dropped a fact, and that is disqualifying at any pass rate.")
        return 0 if any(p is not None for _n, p, _e in rows) else 1
    finally:
        if handle is not None:
            handle.terminate()
            print("\nstopped the ollama server this script started")


if __name__ == "__main__":
    sys.exit(main())
