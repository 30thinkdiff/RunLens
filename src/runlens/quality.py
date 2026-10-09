"""Deterministic quality rules with row-level evidence and explicit thresholds."""

import numpy as np
import pandas as pd

from runlens.io import numeric_values
from runlens.schemas import Dataset, QualityReport

ISSUE_COLUMNS = [
    "kind",
    "row_start",
    "row_end",
    "start_s",
    "end_s",
    "channel",
    "value",
    "threshold",
    "rule",
]


def _median(values: np.ndarray) -> float:
    """Avoid overflow when averaging two large middle values."""
    lower, upper = (len(values) - 1) // 2, len(values) // 2
    middle = np.partition(values, (lower, upper))
    if middle[lower] == middle[upper]:
        return float(middle[lower])
    return float(middle[lower] / 2 + middle[upper] / 2)


def check_quality(dataset: Dataset, *, gap_factor: float = 3.0) -> QualityReport:
    """Estimate nominal dt by median positive adjacent intervals, without repairs.

    Rates describe observable timestamps, not a sensor's guaranteed acquisition rate.
    Non-adjacent duplicate values are counted; invalid timestamps break adjacency.
    """
    if not np.isfinite(gap_factor) or gap_factor <= 1:
        raise ValueError("间隔阈值倍数必须为大于 1 的有限数。")
    positive = dataset.interval_s[
        np.isfinite(dataset.interval_s) & (dataset.interval_s > 0)
    ]
    nominal = _median(positive) if positive.size else None
    issues = []

    def add(kind, start, end, channel, value, threshold, rule):
        issues.append(
            {
                "kind": kind,
                "row_start": start,
                "row_end": end,
                "start_s": dataset.time_s[start],
                "end_s": dataset.time_s[end],
                "channel": channel,
                "value": value,
                "threshold": threshold,
                "rule": rule,
            }
        )

    seen = set()
    for row, value in enumerate(dataset.timestamp_values):
        if value is None:
            add(
                f"{dataset.timestamp_status[row]}_timestamp",
                row,
                row,
                dataset.config.timestamp_column,
                None,
                None,
                "时间戳必须为有限数值；无效行保留但不参与时间计算",
            )
        else:
            if value in seen:
                add(
                    "duplicate_timestamp",
                    row,
                    row,
                    dataset.config.timestamp_column,
                    0.0,
                    0.0,
                    "该原始时间戳此前已出现",
                )
            seen.add(value)
        dt = dataset.interval_s[row]
        if np.isfinite(dt) and dt < 0:
            add(
                "reverse_timestamp",
                row - 1,
                row,
                dataset.config.timestamp_column,
                dt,
                0.0,
                "原始相邻有效时间戳差 < 0",
            )
        if nominal is not None and np.isfinite(dt) and dt > 0:
            if dt > nominal * gap_factor:
                add(
                    "large_interval",
                    row - 1,
                    row,
                    dataset.config.timestamp_column,
                    dt,
                    nominal * gap_factor,
                    "相邻正间隔 > 正间隔中位数 × 阈值倍数；不等同于真实丢帧",
                )
            elif dt < nominal / gap_factor:
                add(
                    "short_interval",
                    row - 1,
                    row,
                    dataset.config.timestamp_column,
                    dt,
                    nominal / gap_factor,
                    "相邻正间隔 < 正间隔中位数 / 阈值倍数",
                )

    stats = []
    for column in dataset.config.channel_columns:
        values, status = numeric_values(dataset.raw[column])
        finite = values[np.isfinite(values)]
        # Normalize before sums/squares to avoid overflow from finite inputs.
        magnitude = float(np.max(np.abs(finite))) if finite.size else 1.0
        magnitude = magnitude or 1.0
        normalized = finite / magnitude
        stats.append(
            {
                "channel": column,
                "finite_count": int(finite.size),
                **{
                    f"{kind}_count": int(np.count_nonzero(status == kind))
                    for kind in ("missing", "infinite", "non_numeric")
                },
                "mean": float(np.mean(normalized) * magnitude)
                if finite.size
                else np.nan,
                "std": float(np.std(normalized) * magnitude) if finite.size else np.nan,
                "min": float(np.min(finite)) if finite.size else np.nan,
                "max": float(np.max(finite)) if finite.size else np.nan,
                "median": _median(finite) if finite.size else np.nan,
                "is_constant": bool(finite.size >= 2 and np.all(finite == finite[0])),
            }
        )
        # Group consecutive invalid rows instead of creating one alert per cell.
        for kind in ("missing", "infinite", "non_numeric"):
            mask = status == kind
            boundaries = np.diff(np.r_[False, mask, False].astype(int))
            for start, end in zip(
                np.flatnonzero(boundaries == 1),
                np.flatnonzero(boundaries == -1),
                strict=True,
            ):
                add(
                    f"{kind}_value",
                    int(start),
                    int(end - 1),
                    column,
                    int(end - start),
                    None,
                    "通道包含缺失或非有限/非法数值；未填补或替换原始数据",
                )

    issue_table = pd.DataFrame(issues, columns=ISSUE_COLUMNS)
    summary = {
        "rows": len(dataset.raw),
        "channels": len(dataset.config.channel_columns),
        "valid_timestamp_count": int(
            np.count_nonzero(dataset.timestamp_status == "valid")
        ),
        **{
            f"{kind}_timestamp_count": int(
                np.count_nonzero(dataset.timestamp_status == kind)
            )
            for kind in ("missing", "infinite", "non_numeric")
        },
        "positive_interval_count": int(positive.size),
        "nominal_interval_s": nominal,
        "sample_rate_hz": (
            1 / nominal if nominal is not None and np.isfinite(1 / nominal) else None
        ),
        "min_positive_interval_s": float(np.min(positive)) if positive.size else None,
        "max_positive_interval_s": float(np.max(positive)) if positive.size else None,
        "mean_positive_interval_s": (
            float(np.mean(positive / np.max(positive)) * np.max(positive))
            if positive.size
            else None
        ),
        "duplicate_count": sum(
            item["kind"] == "duplicate_timestamp" for item in issues
        ),
        "reverse_count": sum(item["kind"] == "reverse_timestamp" for item in issues),
        "large_interval_count": sum(
            item["kind"] == "large_interval" for item in issues
        ),
        "short_interval_count": sum(
            item["kind"] == "short_interval" for item in issues
        ),
    }
    return QualityReport(summary, pd.DataFrame(stats), issue_table, gap_factor)
