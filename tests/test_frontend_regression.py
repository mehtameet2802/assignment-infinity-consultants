import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
JS_TEST = REPO_ROOT / "tests" / "js" / "frontend_regression.test.mjs"


def _ensure_jsdom_installed() -> None:
    if (REPO_ROOT / "node_modules" / "jsdom").is_dir():
        return
    npm = shutil.which("npm")
    if npm is None:
        pytest.skip("npm is not installed; cannot install jsdom for frontend tests")
    subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_frontend_js_regression_suite():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")

    _ensure_jsdom_installed()

    result = subprocess.run(
        [node, "--test", str(JS_TEST)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    assert result.returncode == 0, (
        f"frontend regression tests failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
