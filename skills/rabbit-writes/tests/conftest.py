"""
Make `from helpers import ...` work when pytest is invoked from anywhere.

pytest inserts a test file's own directory into sys.path only under rootdir
conventions this repo does not follow (no package, no installed distribution,
scripts that live inside a plugin directory). Without this, `pytest` from the
repository root collects these files and fails every one of them on the import,
which reads as a broken suite rather than a missing path entry.

run.py does the same thing for the no-pytest case. There is nothing else in
here: the tests take no fixture arguments on purpose, so they behave identically
under both runners. helpers.py says why.
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





