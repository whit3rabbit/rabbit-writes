#!/usr/bin/env python3
"""
The battery, and the bench that scores a model against it.

The first test here is the one that earns the file. Three of the original twelve
cases raised no findings at all in the register they declared, so the bench sent
nothing for them and quietly reported a pass rate over nine cases while printing
"12 case(s)". One was a real exemption doing its job (`robust` and `seamless` are
technical-blog vocabulary), one used a hedge that is not in the lexicon, and one
was 24 words under the 120-word floor that gates the stylometric findings. None
of the three is visible from reading the file.

Stdlib only, 3.9+.
"""

import re

import helpers

FACT_RX = re.compile(r"\d|`[^`]+`|\"[^\"]+\"")


def test_every_battery_case_actually_raises_a_finding():
    scan = helpers.scan_module()
    silent = []
    for case in helpers.battery()["cases"]:
        findings, _stats = scan.scan(case["text"], case["register"])
        if not findings:
            silent.append(case["id"])
    assert not silent, ("these cases raise nothing in their declared register, "
                        "so the bench counts them and sends nothing: %s" % silent)


def test_every_battery_case_carries_a_fact_to_lose():
    # A case with no number, path, version or quotation in it cannot fail the
    # preservation half of the gate, so it only ever measures fluency.
    thin = [case["id"] for case in helpers.battery()["cases"]
            if not FACT_RX.search(case["text"])]
    assert not thin, thin


def test_every_battery_case_declares_a_real_register():
    from rwlib import registers
    known = set(registers.registers())
    unknown = [case["id"] for case in helpers.battery()["cases"]
               if case["register"] not in known]
    assert not unknown, unknown


def test_battery_case_ids_are_unique():
    ids = [case["id"] for case in helpers.battery()["cases"]]
    assert len(ids) == len(set(ids)), ids


def test_the_battery_covers_both_unit_kinds():
    from rwlib import rewrite
    scan = helpers.scan_module()
    kinds = set()
    for case in helpers.battery()["cases"]:
        findings, _ = scan.scan(case["text"], case["register"])
        units, _ = rewrite.plan(case["text"], findings, burstiness_floor=0.45)
        kinds.update(u["kind"] for u in units)
    assert kinds == {"span", "block"}, kinds


def test_a_case_with_a_quotation_is_present():
    # The gate's quotation check has to be exercised by something, and a model
    # rewriting around somebody's words is the failure it exists for.
    assert any('"' in case["text"] for case in helpers.battery()["cases"])


def test_rejection_reasons_bucket_by_class():
    bench = helpers.bench_module()
    cases = [
        ("still contains 'delve into'", "still contains"),
        ("findings went 3 -> 3, so nothing improved", "findings went"),
        ("length went to 240% of the original, outside 35-190%", "length went to"),
        ("the model returned the passage unchanged", "the model returned"),
        ("number altered or removed: 3,200 (3,000 appeared)",
         "number altered or removed"),
    ]
    for reason, want in cases:
        assert bench._short(reason) == want, reason


def test_summarize_counts_a_first_attempt_acceptance():
    bench = helpers.bench_module()
    cases = [{
        "id": "x", "findings_before": 4, "findings_after": 1,
        "records": [
            {"accepted": True, "attempts": []},
            {"accepted": True, "attempts": ["still contains 'delve into'"]},
            {"accepted": False, "attempts": ["findings went 2 -> 2, so nothing improved"] * 3},
        ],
    }]
    summary = bench.summarize(cases, 6.0)
    assert summary["units"] == 3
    assert summary["accepted"] == 2
    assert summary["first_attempt"] == 1
    assert summary["findings_removed_pct"] == 75.0
    assert summary["seconds_per_unit"] == 2.0
    assert summary["rejected_by"]["findings went"] == 3
    assert summary["rejected_by"]["still contains"] == 1


def test_a_word_swapping_stub_clears_the_gate_on_the_simplest_case():
    bench = helpers.bench_module()
    scan = helpers.scan_module()
    case = next(c for c in helpers.battery()["cases"]
                if c["id"] == "tier1-single-word")

    def reply(prompt):
        return helpers.passage_of(prompt).replace("delve into", "read")

    endpoint = helpers.StubEndpoint(reply)
    result = bench.run_case(case, endpoint, 3, scan.BANDS["burstiness"][0])
    assert result["units"] == 1
    assert result["records"][0]["accepted"], result["records"][0]["attempts"]
    assert result["findings_after"] == 0
    assert "14 March" in result["after"], "the date did not survive"


def test_a_stub_that_drops_a_number_is_rejected_every_time():
    bench = helpers.bench_module()
    scan = helpers.scan_module()
    case = next(c for c in helpers.battery()["cases"]
                if c["id"] == "facts-under-pressure")

    def reply(prompt):
        passage = helpers.passage_of(prompt)
        passage = re.sub(r"(?i)in today's fast-paced deployment landscape, ",
                         "", passage)
        return passage.replace("1,240", "1,200")

    endpoint = helpers.StubEndpoint(reply)
    result = bench.run_case(case, endpoint, 2, scan.BANDS["burstiness"][0])
    record = result["records"][0]
    assert not record["accepted"]
    assert any("number" in a for a in record["attempts"]), record["attempts"]
    assert result["after"] == case["text"], "a rejected rewrite reached the text"


def test_a_stub_that_answers_the_question_is_rejected():
    bench = helpers.bench_module()
    scan = helpers.scan_module()
    case = next(c for c in helpers.battery()["cases"]
                if c["id"] == "tier1-single-word")
    endpoint = helpers.StubEndpoint(
        lambda prompt: "Sure! Retry logic is the code that decides whether to "
                       "try a failed request again, and how many times, and how "
                       "long to wait between the attempts it makes.")
    result = bench.run_case(case, endpoint, 1, scan.BANDS["burstiness"][0])
    assert not result["records"][0]["accepted"]


def test_the_bench_report_never_claims_the_result_sounds_like_anybody():
    bench = helpers.bench_module()
    summary = bench.summarize([{"id": "x", "findings_before": 1,
                                "findings_after": 0,
                                "records": [{"accepted": True, "attempts": []}]}],
                              1.0)
    endpoint = helpers.StubEndpoint(lambda p: p)
    text = bench.report(summary, endpoint, 1, 1)
    assert "not a quality score" in text
    assert "sounds like you" in text
