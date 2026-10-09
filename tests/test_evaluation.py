"""Evaluation uses explicit units and never labels skipped scores as normal."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from runlens.anomaly import detect_anomalies
from runlens.evaluation import binary_metrics, evaluate_units, point_predictions
from runlens.robot_example import prepare_robot_example
from runlens.schemas import DetectionConfig

FIXTURE = Path(__file__).parent / "fixtures/robot_execution_failures/lp1.data"


def test_confusion_counts_and_metrics():
    result = binary_metrics([1, 1, 0, 0, 0], [1, 0, 1, 0, 0])
    assert [result[k] for k in ("tp", "fp", "tn", "fn")] == [1, 1, 2, 1]
    assert result["precision"] == 0.5
    assert result["recall"] == 0.5
    assert result["f1"] == 0.5
    assert result["fpr"] == pytest.approx(1 / 3)


def test_undefined_denominators_are_null():
    assert binary_metrics([], [])["f1"] is None
    result = binary_metrics([0, 0], [0, 0])
    assert result["precision"] is None
    assert result["recall"] is None
    assert result["f1"] is None
    assert result["fpr"] == 0
    assert binary_metrics([1], [0])["fpr"] is None


@pytest.mark.parametrize(
    "truth,prediction",
    [(["normal"], [0]), ([np.nan], [0]), ([2], [0]), ([1], []), ([[1]], [[0]])],
)
def test_metrics_reject_ambiguous_labels(truth, prediction):
    with pytest.raises(ValueError):
        binary_metrics(truth, prediction)


@pytest.fixture
def real_result():
    dataset, meta = prepare_robot_example(FIXTURE)
    result = detect_anomalies(
        dataset,
        DetectionConfig(
            fit_range=tuple(meta["fit_range"]),
            detect_range=tuple(meta["detect_range"]),
            scale_floor=1,
        ),
    )
    return dataset, result


def test_mad_merges_channel_records_before_point_metrics(real_result):
    dataset, result = real_result
    points = point_predictions(result)
    assert len(points) == 1170
    assert points.eligible.all()
    assert points.predicted_positive.sum() < result.scores.is_candidate.sum()
    units, metrics = evaluate_units(
        points, dataset.raw, unit="trial", positive=dataset.raw.trial_label.ne("normal")
    )
    assert len(units) == 78
    assert metrics["total_units"] == metrics["evaluated_units"] == 78
    assert metrics["positive_support"] == 67
    assert metrics["negative_support"] == 11


def test_partial_channel_invalidates_point_and_complete_event(real_result):
    dataset, result = real_result
    scores = result.scores.copy()
    scores.loc[(scores.row == 150) & (scores.channel == "Fx"), "status"] = (
        "invalid_signal"
    )
    points = point_predictions(replace(result, scores=scores))
    assert not points.iloc[0].eligible
    assert pd.isna(points.iloc[0].predicted_positive)
    units, metrics = evaluate_units(
        points, dataset.raw, unit="trial", positive=dataset.raw.trial_label.ne("normal")
    )
    assert metrics["excluded_units"] == 1
    assert metrics["evaluated_units"] == 77
    assert units.iloc[0].exclusion_reason == "incomplete_scoring"


def test_duplicate_or_missing_score_record_rejected(real_result):
    _, result = real_result
    for scores in (
        pd.concat([result.scores, result.scores.iloc[:1]]),
        result.scores.iloc[1:],
    ):
        with pytest.raises(ValueError):
            point_predictions(replace(result, scores=scores))


def test_event_truth_must_be_constant_within_whole_trial(real_result):
    dataset, result = real_result
    truth = dataset.raw.trial_label.ne("normal")
    truth.iloc[150] = not truth.iloc[150]
    with pytest.raises(ValueError):
        evaluate_units(
            point_predictions(result), dataset.raw, unit="trial", positive=truth
        )


@pytest.mark.parametrize("score", [np.nan, np.inf])
def test_non_finite_scores_are_excluded_even_if_status_is_ok(real_result, score):
    _, result = real_result
    scores = result.scores.copy()
    scores.loc[(scores.row == 150) & (scores.channel == "Fx"), "score"] = score
    points = point_predictions(replace(result, scores=scores))
    assert not points.iloc[0].eligible


def test_text_eligibility_cannot_silently_become_true(real_result):
    dataset, result = real_result
    points = point_predictions(result)
    points["eligible"] = "False"
    with pytest.raises(ValueError):
        evaluate_units(
            points,
            dataset.raw,
            unit="point",
            positive=dataset.raw.trial_label.ne("normal"),
        )


def test_text_point_prediction_is_rejected_before_trial_aggregation(real_result):
    dataset, result = real_result
    points = point_predictions(result)
    points["predicted_positive"] = "False"
    with pytest.raises(ValueError):
        evaluate_units(
            points,
            dataset.raw,
            unit="trial",
            positive=dataset.raw.trial_label.ne("normal"),
        )


def test_partial_trial_and_empty_evaluation_do_not_invent_normal(real_result):
    dataset, result = real_result
    points = point_predictions(result).iloc[:-1]
    units, metrics = evaluate_units(
        points, dataset.raw, unit="trial", positive=dataset.raw.trial_label.ne("normal")
    )
    assert metrics["excluded_units"] == 1
    assert units.iloc[-1].exclusion_reason == "incomplete_trial"
    _, empty = evaluate_units(
        points.iloc[:0],
        dataset.raw,
        unit="point",
        positive=dataset.raw.trial_label.ne("normal"),
    )
    assert empty["total_units"] == 0 and empty["coverage"] is None
