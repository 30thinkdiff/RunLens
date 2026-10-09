"""The reproducible example exports real computations and protects existing files."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest


def test_feature_example_exports_and_refuses_overwrite(tmp_path):
    script = Path(__file__).resolve().parents[1] / "examples" / "analyze_features.py"
    command = [sys.executable, "-X", "utf8", str(script), "--output", str(tmp_path)]
    run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stderr
    summary = json.loads(run.stdout)
    assert summary["synthetic"]["feature_records"] == 98
    sine = pd.read_csv(tmp_path / "sine_features.csv")
    assert sine.iloc[0]["psd_integral"] == pytest.approx(2)
    assert sine.iloc[0]["dominant_frequency_hz"] == pytest.approx(16)
    before = (tmp_path / "synthetic_features.csv").read_bytes()
    second = subprocess.run(command, capture_output=True)
    assert second.returncode != 0
    assert (tmp_path / "synthetic_features.csv").read_bytes() == before
