"""
Make `from helpers import ...` work when pytest is invoked from anywhere,
including when other test subdirectories also define a `helpers.py`.

A single invocation when conftest is loaded resolves `helpers` for this directory
without needing repeated reimport hooks on every test run.
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

helpers_path = os.path.join(HERE, "helpers.py")
if os.path.exists(helpers_path):
    if "helpers" in sys.modules:
        del sys.modules["helpers"]
    spec = importlib.util.spec_from_file_location("helpers", helpers_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["helpers"] = mod
    spec.loader.exec_module(mod)

if HERE in sys.path:
    sys.path.remove(HERE)
sys.path.insert(0, HERE)
