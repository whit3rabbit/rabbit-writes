"""
Make `from helpers import ...` work when pytest is invoked from anywhere.
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_local_helpers():
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


def pytest_collect_file(file_path, parent):
    load_local_helpers()


def pytest_pycollect_makemodule(module_path, parent):
    load_local_helpers()


def pytest_runtest_setup(item):
    load_local_helpers()


load_local_helpers()





