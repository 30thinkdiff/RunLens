"""Verify the installed package and its public command-line entry point."""

import subprocess
import sys
from pathlib import Path


def test_package_version_matches_installed_metadata():
    from importlib.metadata import version

    from runlens import __version__

    assert __version__ == version("runlens")


def test_module_reports_version():
    from runlens import __version__

    result = subprocess.run(
        [sys.executable, "-m", "runlens", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == f"RunLens {__version__}"
    assert result.stderr == ""


def test_startup_page_runs_without_errors():
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=15).run()

    assert not app.exception
    assert app.title[0].value == "RunLens"
    assert "Phase 0" in app.info[0].value
