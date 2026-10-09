"""Detector contracts, honest skipped states, leakage guards and interval bounds."""

from io import BytesIO

import numpy as np
import pandas as pd
import pytest

from runlens.anomaly import candidates_csv, detect_anomalies, detection_json, scores_csv
from runlens.demo import generate_demo
from runlens.io import prepare_dataset
from runlens.schemas import DetectionConfig, ImportConfig


def data(values, *, times=None, **other):
    return prepare_dataset(
        pd.DataFrame(
            {
                "t": np.arange(len(values)) if times is None else times,
                "x": values,
                **other,
            }
        ),
        ImportConfig("t", ("x", *other)),
        "Synthetic contract data",
    )


def config(**kwargs):
    return DetectionConfig(fit_range=(0, 4), detect_range=(5, 8), **kwargs)


def test_mad_finds_known_spike_and_exports_baseline():
    result = detect_anomalies(data([0, 1, 2, 1, 0, 1, 20, 21, 1]), config())
    assert result.scores["row"].tolist() == [5, 6, 7, 8]
    assert result.scores["is_candidate"].tolist() == [False, True, True, False]
    assert result.baselines.iloc[0]["median"] == 1
    assert result.baselines.iloc[0]["mad"] == 1
    assert result.baselines.iloc[0]["scale"] == pytest.approx(1.4826)
    event = result.candidates.iloc[0]
    assert event["row_start"] == 6 and event["row_end"] == 7
    assert event["candidate_count"] == 2
    assert event["peak_score"] == pytest.approx(20 / 1.4826)
    assert event["peak_row"] == 7


def test_zero_mad_disables_scoring_until_floor_is_explicit():
    dataset = data([0] * 5 + [0, 0.1, 20, 0])
    disabled = detect_anomalies(dataset, config())
    assert disabled.candidates.empty
    assert set(disabled.scores["status"]) == {"zero_mad"}
    assert disabled.scores["score"].isna().all()
    floor = detect_anomalies(dataset, config(scale_floor=1))
    assert floor.scores["is_candidate"].tolist() == [False, False, True, False]


def test_fit_statistics_do_not_change_with_detection_values():
    first = detect_anomalies(data([0, 1, 2, 1, 0, 1, 2, 1, 2]), config())
    second = detect_anomalies(data([0, 1, 2, 1, 0, 1e6, 1e6, 1e6, 1e6]), config())
    pd.testing.assert_frame_equal(first.baselines, second.baselines)


def test_nonfinite_signal_and_timestamp_are_not_candidates():
    result = detect_anomalies(
        data(
            [0, 1, 2, 1, 0, np.nan, np.inf, 100, 1],
            times=[0, 1, 2, 3, 4, 5, 6, np.nan, 8],
        ),
        config(),
    )
    assert result.scores["status"].tolist() == [
        "invalid_signal",
        "invalid_signal",
        "invalid_timestamp",
        "ok",
    ]
    assert result.candidates.empty


def test_sparse_fit_is_reported_per_channel():
    dataset = data(
        [0, 1, 2, 1, 0, 20, 1, 1, 1], y=[0, np.nan, np.nan, 1, 0, 100, 100, 100, 100]
    )
    result = detect_anomalies(dataset, config())
    assert set(result.scores.loc[result.scores.channel == "y", "status"]) == {
        "insufficient_fit"
    }
    assert result.candidates.channel.tolist() == ["x"]


@pytest.mark.parametrize(
    "times",
    [
        [0, 1, 2, 3, 4, 5, 10, 11, 12],
        [0, 1, 2, 3, 4, 5, 5, 6, 7],
        [0, 1, 2, 3, 4, 5, 4.5, 6, 7],
    ],
)
def test_candidates_do_not_merge_across_timing_barriers(times):
    result = detect_anomalies(
        data([0, 1, 2, 1, 0, 20, 20, 1, 1], times=times), config()
    )
    assert result.candidates.row_start.tolist() == [5, 6]
    assert result.candidates.row_end.tolist() == [5, 6]


def test_normal_or_skipped_rows_break_candidate_runs():
    result = detect_anomalies(data([0, 1, 2, 1, 0, 20, np.nan, 20, 20]), config())
    assert result.candidates.row_start.tolist() == [5, 7]
    assert result.candidates.row_end.tolist() == [5, 8]


def test_large_finite_mad_inputs_do_not_overflow_baseline():
    result = detect_anomalies(
        data([1e308, 1e308, 1e308, 1e308, 1e308, -1e308, 1e308, 1e308, 1e308]),
        config(scale_floor=1e307),
    )
    assert result.baselines.iloc[0]["median"] == 1e308
    assert result.scores.iloc[0]["score"] == pytest.approx(20)
    assert result.scores.iloc[0]["is_candidate"]


@pytest.mark.parametrize(
    "params",
    [
        {"method": "magic"},
        {"threshold": 0},
        {"threshold": np.nan},
        {"scale_floor": -1},
        {"contamination": 0},
        {"contamination": 0.9},
        {"n_estimators": 0},
        {"random_state": -1},
        {"gap_factor": 1},
        {"fit_range": (0, 5), "detect_range": (5, 10)},
        {"fit_range": (-1, 5)},
        {"fit_range": (0, 1.5)},
    ],
)
def test_invalid_configuration_rejected(params):
    with pytest.raises(ValueError):
        DetectionConfig(**params)


def test_out_of_bounds_and_short_data_rejected():
    with pytest.raises(ValueError):
        detect_anomalies(data([1]), config())


def test_csv_and_json_include_configuration_and_original_rows():
    import json

    result = detect_anomalies(data([0, 1, 2, 1, 0, 20, 1, 1, 1]), config())
    candidates = pd.read_csv(BytesIO(candidates_csv(result)))
    scores = pd.read_csv(BytesIO(scores_csv(result)))
    assert candidates.row_start.tolist() == [5]
    assert candidates.method.tolist() == ["mad"]
    assert scores.row.tolist() == [5, 6, 7, 8]
    assert scores.fit_end.tolist() == [4] * 4
    metadata = json.loads(detection_json(result))
    assert metadata["config"]["fit_range"] == [0, 4]
    assert metadata["evaluation_unit"] == "original sample rows"
    assert metadata["source_name"] == "Synthetic contract data"
    assert len(metadata["data_sha256"]) == 64


def if_data():
    # Deterministic contract values; real robot trials are tested separately.
    fit = np.sin(np.arange(64))
    return data(
        np.r_[fit, 0.1, 100, 0.2, -100],
        y=np.r_[np.cos(np.arange(64)), 0.2, 100, 0.1, -100],
    )


def if_config(**kwargs):
    return DetectionConfig(
        method="isolation_forest", fit_range=(0, 63), detect_range=(64, 67), **kwargs
    )


def test_isolation_forest_detects_extreme_multichannel_points_repeatably():
    first = detect_anomalies(if_data(), if_config())
    second = detect_anomalies(if_data(), if_config())
    np.testing.assert_array_equal(first.scores.score, second.scores.score)
    assert first.scores.loc[first.scores.row.isin([65, 67]), "is_candidate"].all()
    assert first.scores.score.notna().all()
    assert set(first.scores.channel) == {"__multivariate__"}
    assert (first.scores.is_candidate == (first.scores.score > 0)).all()


def test_isolation_fit_scaling_and_offset_ignore_detection_data():
    original = if_data()
    modified = data(
        np.r_[np.sin(np.arange(64)), [1e8] * 4],
        y=np.r_[np.cos(np.arange(64)), [1e8] * 4],
    )
    first = detect_anomalies(original, if_config(contamination=0.1))
    second = detect_anomalies(modified, if_config(contamination=0.1))
    pd.testing.assert_frame_equal(first.baselines, second.baselines)
    assert first.metadata["if_offset"] == second.metadata["if_offset"]


def test_if_constant_and_insufficient_baselines_are_not_fabricated():
    constant = detect_anomalies(data([1] * 64 + [100] * 4), if_config())
    assert constant.candidates.empty
    assert set(constant.scores.status) == {"constant_baseline"}
    short = detect_anomalies(data([1] * 9), config(method="isolation_forest"))
    assert set(short.scores.status) == {"insufficient_fit"}


@pytest.mark.parametrize("method", ["mad", "isolation_forest"])
def test_existing_demo_reference_spikes_are_detected(method):
    demo = generate_demo()
    channels = tuple(column for column in demo.data if column != "timestamp")
    dataset = prepare_dataset(
        demo.data, ImportConfig("timestamp", channels), "Synthetic Data"
    )
    result = detect_anomalies(dataset, DetectionConfig(method=method))
    spikes = demo.labels.loc[demo.labels.kind == "spike", "row_start"]
    for row in spikes:
        assert result.scores.loc[result.scores.row == row, "is_candidate"].any()


def test_if_invalid_and_unrepresentable_rows_are_skipped_without_clipping():
    values = np.r_[np.sin(np.arange(64)) * 1e-200, np.nan, np.inf, 1e200, 0]
    result = detect_anomalies(data(values), if_config())
    assert result.scores.status.tolist() == [
        "invalid_signal",
        "invalid_signal",
        "numeric_range",
        "ok",
    ]
    assert not result.scores.is_candidate.iloc[:3].any()
