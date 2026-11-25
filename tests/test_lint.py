"""Linting as a test: `pytest` fails if ruff finds problems in the checked paths."""
import importlib.util
import subprocess
import sys

import pytest

# Files we keep lint-clean. Older modules are not listed yet; add them once cleaned.
LINTED_PATHS = [
    "app/api",
    "app/cloud",
    "app/pipeline/batch_pipeline.py",
    "frontend",
    "tests",
]


@pytest.mark.skipif(importlib.util.find_spec("ruff") is None, reason="ruff not installed")
def test_ruff_check_passes():
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", *LINTED_PATHS],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"ruff found problems:\n{result.stdout}"
