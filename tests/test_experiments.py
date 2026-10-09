"""Real measurements, declared perturbations, complete splits and export audit."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from runlens.evaluation import binary_metrics
from runlens.experiments import run_robot_experiments
from runlens.robot_example import LP1_SHA256, MEASUREMENTS

FIXTURE = Path(__file__).parent / "fixtures/robot_execution_failures/lp1.data"


@pytest.fixture(scope="module")
def experiment():
    return run_robot_experiments(FIXTURE)


def test_complete_trials_and_reference_not_injected(experiment):
    splits = experiment.report["splits"]
    fit = set(splits["reference_trial_ids"])
    assert len(fit) == 10
    assert not fit & set(splits["real_trial_evaluation_ids"])
    assert not fit & set(splits["injection_background_trial_ids"])
    assert len(splits["real_trial_evaluation_ids"]) == 78
    assert len(splits["injection_background_trial_ids"]) == 11
    original = experiment.datasets["real_robot_lp1"]
    assert original.groupby("trial_id").size().eq(15).all()
    background = experiment.datasets["normal_robot_background"]
    altered = experiment.datasets["injected_robot_background"]
    pd.testing.assert_frame_equal(background.iloc[:150], altered.iloc[:150])
    pd.testing.assert_frame_equal(original.iloc[:150], altered.iloc[:150])
    unchanged = ~altered.index.isin([150, 225, 300])
    pd.testing.assert_frame_equal(background.loc[unchanged], altered.loc[unchanged])
    assert altered.loc[[150, 225, 300], list(MEASUREMENTS)].eq(10000).all().all()
    assert experiment.report["data_provenance"]["original_sha256"] == LP1_SHA256
    for method in ("mad", "isolation_forest"):
        pd.testing.assert_frame_equal(
            experiment.detections[f"real_trials_{method}"].baselines,
            experiment.detections[f"injected_points_{method}"].baselines,
        )


def test_metrics_recompute_from_individual_predictions(experiment):
    for row in experiment.metrics.to_dict(orient="records"):
        selected = experiment.predictions.loc[
            (experiment.predictions.scenario == row["scenario"])
            & (experiment.predictions.method == row["method"])
            & experiment.predictions.eligible
        ]
        actual = binary_metrics(
            selected.actual_positive.tolist(), selected.predicted_positive.tolist()
        )
        for key, value in actual.items():
            assert row[key] == value
        assert row["coverage"] == 1
        assert row["analysis_elapsed_s"] > 0 and row["evaluation_elapsed_s"] > 0
    assert (
        experiment.metrics.query("scenario == 'real_trials'")
        .positive_support.eq(67)
        .all()
    )
    assert (
        experiment.metrics.query("scenario == 'injected_points'")
        .positive_support.eq(3)
        .all()
    )


def test_repeated_seed_predictions_and_analytical_checks(experiment):
    repeat = run_robot_experiments(FIXTURE)
    pd.testing.assert_frame_equal(experiment.predictions, repeat.predictions)
    checks = experiment.report["reference_checks"]
    assert checks["quality"]["passed"] and checks["known_features"]["passed"]
    assert len(experiment.real_features.table) == 528
    assert experiment.real_features.table.spectral_status.eq("disabled").all()
    assert experiment.report["timing"]["experiment_elapsed_s"] > 0


def test_script_exports_metrics_reports_and_protects_every_output(tmp_path):
    script = Path(__file__).resolve().parents[1] / "examples/run_experiments.py"
    cmd = [sys.executable, "-X", "utf8", str(script), "--output", str(tmp_path)]
    first = subprocess.run(cmd, capture_output=True, encoding="utf-8")
    assert first.returncode == 0, first.stderr
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["report_type"] == "fixed_robot_experiments"
    assert len(list(tmp_path.iterdir())) == 23
    metrics = pd.read_csv(tmp_path / "metrics.csv")
    predictions = pd.read_csv(tmp_path / "predictions.csv")
    assert len(predictions) == 2 * (78 + 165) and len(metrics) == 4
    assert (
        (tmp_path / "report.html")
        .read_text(encoding="utf-8")
        .startswith("<!doctype html>")
    )
    for path in tmp_path.iterdir():
        if path.name != "quality_probe.csv":
            path.unlink()
    sentinel = (tmp_path / "quality_probe.csv").read_bytes()
    retry = subprocess.run(cmd, capture_output=True, encoding="utf-8")
    assert retry.returncode != 0
    assert (tmp_path / "quality_probe.csv").read_bytes() == sentinel
    assert not (tmp_path / "report.json").exists()
