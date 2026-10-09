"""The real-data command produces reproducible, attributed artifacts safely."""

import json
import subprocess
import sys
from pathlib import Path


def test_anomaly_example_exports_provenance_and_refuses_overwrite(tmp_path):
    script = Path(__file__).resolve().parents[1] / "examples" / "analyze_anomalies.py"
    cmd = [sys.executable, "-X", "utf8", str(script), "--output", str(tmp_path)]
    run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stderr
    summary = json.loads(run.stdout)
    assert summary["provenance"]["license"] == "CC BY 4.0"
    assert summary["provenance"]["time_axis"].startswith("constructed")
    assert all(
        item["is_candidate"]
        for item in summary["results"]["injected_mad"]["at_injection_row"]
    )
    assert summary["results"]["injected_isolation_forest"]["at_injection_row"][0][
        "is_candidate"
    ]
    original = (tmp_path / "real_robot_lp1.csv").read_bytes()
    retry = subprocess.run(cmd, capture_output=True)
    assert retry.returncode != 0
    assert (tmp_path / "real_robot_lp1.csv").read_bytes() == original
