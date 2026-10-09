"""Offline regressions on actual attributed robot force/torque measurements."""

import hashlib
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from runlens.anomaly import candidates_csv, detect_anomalies
from runlens.features import extract_features
from runlens.io import prepare_dataset, read_csv
from runlens.robot_example import LP1_SHA256, MEASUREMENTS, prepare_robot_example
from runlens.schemas import DetectionConfig, WindowConfig

FIXTURE = Path(__file__).parent / "fixtures" / "robot_execution_failures" / "lp1.data"


@pytest.fixture
def real_example():
    return prepare_robot_example(FIXTURE)


def cfg(metadata, method="mad"):
    return DetectionConfig(
        method=method,
        fit_range=tuple(metadata["fit_range"]),
        detect_range=tuple(metadata["detect_range"]),
        scale_floor=1,
    )


def test_real_fixture_is_unmodified_and_splits_preserve_complete_trials(real_example):
    dataset, metadata = real_example
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == LP1_SHA256
    assert len(dataset.raw) == 1320
    assert dataset.raw.trial_id.nunique() == 88
    assert dataset.raw.groupby("trial_id").size().eq(15).all()
    assert not set(metadata["reference_trial_ids"]) & set(
        metadata["detection_trial_ids"]
    )
    assert dataset.raw.loc[:149, "trial_label"].eq("normal").all()
    assert dataset.raw.loc[0, list(MEASUREMENTS)].tolist() == [-1, -1, 63, -3, -1, 0]
    assert metadata["time_axis"].startswith("constructed")


@pytest.mark.parametrize("method", ["mad", "isolation_forest"])
def test_real_unchanged_trial_workflow_and_exports(real_example, method):
    dataset, metadata = real_example
    before = dataset.raw.copy(deep=True)
    # Roundtrip the actual CSV import path, not just an in-memory fake dataset.
    raw = read_csv(dataset.raw.to_csv(index=False).encode("utf-8"))
    imported = prepare_dataset(raw, dataset.config, dataset.source_name)
    result = detect_anomalies(imported, cfg(metadata, method))
    assert not result.scores.empty
    scored = result.scores.loc[result.scores.status == "ok", "score"]
    assert not scored.empty and np.isfinite(scored).all()
    assert result.candidates.row_start.ge(150).all()
    # A candidate never spans two unrelated source trials.
    for event in result.candidates.itertuples():
        assert (
            dataset.raw.loc[event.row_start : event.row_end, "trial_id"].nunique() == 1
        )
    restored = pd.read_csv(BytesIO(candidates_csv(result)))
    assert len(restored) == len(result.candidates)
    pd.testing.assert_frame_equal(dataset.raw, before)


def test_real_quantization_zero_mad_is_explicit(real_example):
    dataset, metadata = real_example
    result = detect_anomalies(
        dataset,
        DetectionConfig(
            fit_range=tuple(metadata["fit_range"]),
            detect_range=tuple(metadata["detect_range"]),
        ),
    )
    assert result.baselines["mad"].eq(0).any()
    disabled = result.baselines.loc[result.baselines.status == "zero_mad", "channel"]
    assert not disabled.empty
    assert not result.scores.loc[
        result.scores.channel.isin(disabled), "is_candidate"
    ].any()


@pytest.mark.parametrize("method", ["mad", "isolation_forest"])
def test_known_injected_spike_on_real_background_is_detected(real_example, method):
    dataset, metadata = real_example
    copy = dataset.raw.copy(deep=True)
    injected_row = 150  # First held-out normal trial, beyond the reference boundary.
    original = detect_anomalies(dataset, cfg(metadata, method))
    assert not original.scores.loc[
        original.scores.row == injected_row, "is_candidate"
    ].any()
    copy.loc[injected_row, list(MEASUREMENTS)] = 10000
    modified = prepare_dataset(
        copy, dataset.config, "Real LP1 background + injected spike"
    )
    result = detect_anomalies(modified, cfg(metadata, method))
    at_spike = result.scores.loc[result.scores.row == injected_row]
    assert at_spike.is_candidate.any()
    assert dataset.raw.loc[injected_row, "Fx"] != 10000


def test_injected_missing_sample_on_real_background_is_not_imputed(real_example):
    dataset, metadata = real_example
    copy = dataset.raw.copy(deep=True)
    copy.loc[300, "Fx"] = np.nan
    modified = prepare_dataset(
        copy, dataset.config, "Real LP1 background + missing sample"
    )
    result = detect_anomalies(modified, cfg(metadata, "isolation_forest"))
    row = result.scores.loc[result.scores.row == 300].iloc[0]
    assert row.status == "invalid_signal" and not row.is_candidate
    assert np.isnan(row.score)


def test_real_time_domain_features_match_independent_numpy_calculation(real_example):
    dataset, _ = real_example
    features = extract_features(
        dataset, WindowConfig(window_size=15, step_size=15, include_spectral=False)
    )
    reference = dataset.signals.Fz.iloc[:15].to_numpy()
    row = features.table.loc[features.table.channel == "Fz"].iloc[0]
    assert row["mean"] == pytest.approx(np.mean(reference))
    assert row["std"] == pytest.approx(np.std(reference))
    assert row["rms"] == pytest.approx(np.sqrt(np.mean(reference**2)))
    assert features.table.spectral_status.eq("disabled").all()
