#!/usr/bin/env python3
"""Run the test suite using pytest when available, else the bundled shim."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS = ROOT / "tests"

sys.path.insert(0, str(ROOT))

try:
    import pytest  # type: ignore
except ImportError:
    sys.path.insert(0, str(TESTS))
    from _pytest_shim import run

    sys.exit(run(TESTS))
else:
    sys.exit(pytest.main([str(TESTS), "-q"]))
