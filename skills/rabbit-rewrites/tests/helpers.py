#!/usr/bin/env python3
"""
Shared fixtures for the rabbit-rewrites tests.

Thin on purpose. The rewriting logic and its gate live in the engine
(`rwlib/rewrite.py`, `rwlib/endpoint.py`) and are tested by
`skills/rabbit-writes/tests/test_rewrite.py`, where the engine's own scan and
verify are already on hand. What is left here is the skill's own surface: the
battery, and the bench that scores a model against it.

Same shape as the other four test directories: memoized module functions and
tests that take no arguments, so `run.py` and pytest behave identically.

Stdlib only, 3.9+.
"""

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SCRIPTS = os.path.join(SKILL, "scripts")
ENGINE = os.path.join(os.path.dirname(SKILL), "rabbit-writes", "scripts")
BATTERY_PATH = os.path.join(SCRIPTS, "battery.json")

for path in (ENGINE, SCRIPTS):
    if path not in sys.path:
        sys.path.insert(0, path)

_CACHE = {}


def load_module(name, path):
    key = ("module", name, path)
    if key not in _CACHE:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CACHE[key] = module
    return _CACHE[key]


def bench_module():
    return load_module("rw_bench_test", os.path.join(SCRIPTS, "bench.py"))


def scan_module():
    return load_module("rw_scan_test", os.path.join(ENGINE, "scan.py"))


def battery():
    if "battery" not in _CACHE:
        with open(BATTERY_PATH, encoding="utf-8") as fh:
            _CACHE["battery"] = json.load(fh)
    return _CACHE["battery"]


class StubEndpoint:
    """An Endpoint's shape with a scripted or computed reply.

    `reply` is called with the user prompt and returns the completion, so a test
    can stand in for a model that swaps a word, one that answers the question,
    or one that hands back the passage untouched.
    """

    def __init__(self, reply, context_tokens=4096):
        self.reply = reply
        self.calls = []
        self.temperature = 0.2
        self.context_tokens = context_tokens
        self.max_output_tokens = 640
        self.model = "stub"
        self.base_url = "http://127.0.0.1:1/v1"

    def input_budget(self):
        return max(0, self.context_tokens - self.max_output_tokens - 256)

    def describe(self):
        return "stub @ %s (no key, ctx %d)" % (self.base_url, self.context_tokens)

    def complete(self, system, user, temperature=None, opener=None):
        self.calls.append(user)
        return self.reply(user)


def passage_of(prompt):
    """The passage out of a bench prompt, the way a stub model would read it."""
    return prompt.split("to rewrite:\n", 1)[-1]
