"""Explicit binary evaluation over points or complete, non-overlapping trials."""

import json

import numpy as np
import pandas as pd

from runlens.schemas import DetectionResult


def _binary(values) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1 or any(
        not isinstance(v, (bool, int, float, np.bool_, np.integer, np.floating))
        or v not in (0, 1)
        for v in array
    ):
        raise ValueError("标签须为一维明确的布尔值或 0/1，不接受缺失值和类别文本。")
    return array.astype(bool)


def binary_metrics(truth, prediction) -> dict:
    """Undefined denominators are null, including empty evaluation populations."""
    truth, prediction = _binary(truth), _binary(prediction)
    if len(truth) != len(prediction):
        raise ValueError("真值与预测长度必须相同。")
    tp = int(np.sum(truth & prediction))
    fp = int(np.sum(~truth & prediction))
    tn = int(np.sum(~truth & ~prediction))
    fn = int(np.sum(truth & ~prediction))

    def ratio(numerator, denominator):
        return numerator / denominator if denominator else None

    return dict(
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        positive_support=tp + fn,
        negative_support=tn + fp,
        precision=ratio(tp, tp + fp),
        recall=ratio(tp, tp + fn),
        f1=ratio(2 * tp, 2 * tp + fp + fn),
        fpr=ratio(fp, fp + tn),
    )


def point_predictions(result: DetectionResult) -> pd.DataFrame:
    """MAD channels OR together, but all selected channels must be scorable."""
    scores = result.scores
    channels = (
        json.loads(result.metadata["channels"])
        if result.config.method == "mad"
        else ["__multivariate__"]
    )
    first, last = result.config.detect_range
    expected_rows = np.arange(first, last + 1)
    if (
        len(scores) != len(expected_rows) * len(channels)
        or scores.duplicated(["row", "channel"]).any()
        or set(scores.channel) != set(channels)
        or set(scores.row) != set(expected_rows)
        or not scores.groupby("row").size().eq(len(channels)).all()
    ):
        raise ValueError("评分表必须覆盖检测区间的每行和每个选定通道，不能缺失或重复。")
    candidate = _binary(scores.is_candidate)
    scorable = (
        scores.status.eq("ok")
        & np.isfinite(scores.score)
        & np.isfinite(scores.threshold)
    )
    working = scores.assign(scorable=scorable, candidate=candidate)
    groups = working.groupby("row", sort=True)
    points = groups.agg(
        eligible=("scorable", "all"), predicted_positive=("candidate", "any")
    )
    points["predicted_positive"] = points.predicted_positive.astype("boolean")
    points.loc[~points.eligible, "predicted_positive"] = pd.NA
    points["exclusion_reason"] = np.where(points.eligible, "", "incomplete_scoring")
    return points.reset_index()


def evaluate_units(
    points: pd.DataFrame, raw: pd.DataFrame, *, unit: str, positive
) -> tuple[pd.DataFrame, dict]:
    """Labels align by original positional row, never by a CSV's external index."""
    truth = _binary(positive)
    if len(truth) != len(raw) or unit not in ("point", "trial"):
        raise ValueError("真值长度须等于原始行数，评价单位须为 point 或 trial。")
    rows = points.row.to_numpy()
    if (
        not np.issubdtype(rows.dtype, np.integer)
        or points.row.duplicated().any()
        or np.any(rows < 0)
        or np.any(rows >= len(raw))
    ):
        raise ValueError("预测原始行须为不重复且不越界的整数。")
    points = points.copy()
    points["eligible"] = _binary(points.eligible)
    _binary(points.loc[points.eligible, "predicted_positive"])
    points["actual_positive"] = truth[rows]
    if unit == "point":
        units = points.rename(columns={"row": "unit_id"})
    else:
        if "trial_id" not in raw or raw.trial_id.isna().any():
            raise ValueError("事件评价须提供每行的完整 trial_id。")
        points["trial_id"] = raw.trial_id.to_numpy()[rows]
        all_labels = pd.DataFrame({"trial_id": raw.trial_id.to_numpy(), "truth": truth})
        if not all_labels.groupby("trial_id").truth.nunique().eq(1).all():
            raise ValueError("同一完整事件的真值必须一致。")
        total_sizes = raw.groupby("trial_id").size()
        records = []
        for trial, block in points.groupby("trial_id", sort=False):
            complete = len(block) == total_sizes.loc[trial]
            eligible = complete and bool(block.eligible.all())
            records.append(
                dict(
                    unit_id=trial,
                    row_start=int(block.row.min()),
                    row_end=int(block.row.max()),
                    sample_count=len(block),
                    eligible=eligible,
                    predicted_positive=bool(
                        block.predicted_positive.fillna(False).any()
                    )
                    if eligible
                    else None,
                    actual_positive=bool(block.actual_positive.iloc[0]),
                    exclusion_reason=""
                    if eligible
                    else ("incomplete_scoring" if complete else "incomplete_trial"),
                )
            )
        units = pd.DataFrame(
            records,
            columns=[
                "unit_id",
                "row_start",
                "row_end",
                "sample_count",
                "eligible",
                "predicted_positive",
                "actual_positive",
                "exclusion_reason",
            ],
        )
    selected = units.loc[units.eligible.astype(bool)]
    metrics = binary_metrics(
        selected.actual_positive.tolist(), selected.predicted_positive.tolist()
    )
    metrics.update(
        evaluation_unit=unit,
        total_units=len(units),
        evaluated_units=len(selected),
        excluded_units=len(units) - len(selected),
        coverage=len(selected) / len(units) if len(units) else None,
        excluded_reasons={
            str(k): int(v)
            for k, v in units.loc[~units.eligible.astype(bool)]
            .exclusion_reason.value_counts()
            .items()
        },
    )
    return units, metrics
