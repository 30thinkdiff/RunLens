"""Deterministic synthetic data and truthful injection reference labels."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from runlens.demo import generate_demo
from runlens.io import prepare_dataset
from runlens.quality import check_quality
from runlens.schemas import ImportConfig


def test_demo_is_deterministic_and_labeled_synthetic():
    first, second = generate_demo(), generate_demo()
    pd.testing.assert_frame_equal(first.data, second.data)
    pd.testing.assert_frame_equal(first.labels, second.labels)
    assert first.metadata["source"] == "Synthetic Data"
    assert first.metadata["seed"] == 42


def test_injected_quality_events_match_rule_results():
    demo = generate_demo()
    data = prepare_dataset(demo.data, ImportConfig("timestamp", ("accel_x", "accel_z")))
    report = check_quality(data)
    for kind in ["duplicate_timestamp", "reverse_timestamp", "large_interval"]:
        expected = demo.labels.loc[demo.labels["kind"] == kind].iloc[0]
        actual = report.issues.loc[report.issues["kind"] == kind].iloc[0]
        assert actual.row_start == expected.row_start
        assert actual.row_end == expected.row_end
    assert (demo.labels["kind"] == "spike").sum() == 2


def test_optional_vibration_changes_data_and_adds_reference_interval():
    normal, vibration = generate_demo(), generate_demo(vibration=True)
    assert not normal.data.equals(vibration.data)
    assert "vibration_change" in vibration.labels["kind"].values


def test_generator_writes_portable_outputs_without_overwriting(tmp_path):
    script = Path(__file__).resolve().parents[1] / "examples" / "generate_demo.py"
    output = tmp_path / "中文 空格"
    args = [sys.executable, "-X", "utf8", str(script), "--output", str(output)]
    result = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", check=True
    )
    assert "Synthetic Data: 2000 rows" in result.stdout
    assert len(pd.read_csv(output / "synthetic_imu.csv")) == 2000
    assert (
        json.loads((output / "synthetic_metadata.json").read_text(encoding="utf-8"))[
            "source"
        ]
        == "Synthetic Data"
    )
    original = (output / "synthetic_imu.csv").read_bytes()
    again = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    assert again.returncode != 0
    assert "Output exists" in again.stderr
    assert (output / "synthetic_imu.csv").read_bytes() == original
