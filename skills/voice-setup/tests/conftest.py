"""
Make `from helpers import ...` work when pytest is invoked from anywhere.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
