# rabbit-rewrites

Benchmarks and drives the model-backed rewrite path over an OpenAI-compatible endpoint. The rewrite engine itself (`rwlib/endpoint.py`, `rwlib/rewrite.py`) lives in `skills/rabbit-writes/scripts/rwlib/` and is documented there. This skill's own scripts exercise that engine rather than owning it.

## Commands

```bash
# Run the skill test suite (the model battery, and the bench that scores against it)
python3 skills/rabbit-rewrites/tests/run.py

# Benchmark a running endpoint against the battery
python3 skills/rabbit-rewrites/scripts/bench.py --model-endpoint http://127.0.0.1:8080/v1 --model-name qwen2.5-3b

# Repeat for a stabler pass rate, and save JSON
python3 skills/rabbit-rewrites/scripts/bench.py --repeat 3 --json > qwen2.5-3b.json
```

## Structure

- `scripts/bench.py`: The model-benchmarking runner.
- `scripts/battery.json`: The passages scored in the benchmark.
- `references/models.md`: Recommended local models, download sources, and quantization notes.

## Gotchas

- **A battery case that raises no findings is invisible from reading the file.** Three of the original twelve in `battery.json` did: one used technical-blog vocabulary the register correctly exempts, one used a hedge not in the lexicon, and one was 24 words under the 120-word floor that gates every stylometric finding (`wc >= 120` in `scan.py`). The bench happily printed a pass rate over nine cases while reporting twelve. `test_every_battery_case_actually_raises_a_finding` is the guard, and `test_every_battery_case_carries_a_fact_to_lose` is the other half: a case with no number, path, or quotation in it can only ever measure fluency, never preservation.
