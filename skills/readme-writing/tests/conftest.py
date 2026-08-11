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

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
