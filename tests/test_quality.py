"""Quality checks refer to original row order and observable evidence."""

import numpy as np
import pandas as pd
import pytest

from runlens.io import prepare_dataset
from runlens.quality import check_quality
from runlens.schemas import ImportConfig


def analyze(times, values=None, factor=3.0):
    frame = pd.DataFrame(
        {"t": times, "x": values if values is not None else np.ones(len(times))}
    )
    return check_quality(
        prepare_dataset(frame, ImportConfig("t", ("x",))), gap_factor=factor
    )


def test_regular_constant_signal():
    result = analyze([0, 0.01, 0.02, 0.03])
    assert result.summary["sample_rate_hz"] == pytest.approx(100)
    assert result.issues.empty
    stats = result.channel_stats.iloc[0]
    assert stats["is_constant"]
    assert stats["std"] == 0
    assert stats["mean"] == 1


def test_duplicates_reverse_and_gap_are_reported_without_sorting():
    result = analyze([0, 0.01, 0.01, 0.005, 0.02, 0.03, 0.13, 0.14])
    assert result.summary["duplicate_count"] == 1
    assert result.summary["reverse_count"] == 1
    assert result.summary["large_interval_count"] == 1
    assert result.summary["sample_rate_hz"] == pytest.approx(100)
    gap = result.issues.query("kind == 'large_interval'").iloc[0]
    assert (gap.row_start, gap.row_end) == (5, 6)
    assert gap.value == pytest.approx(0.1)
    assert gap.threshold == pytest.approx(0.03)


def test_non_adjacent_duplicates():
    assert analyze([0, 1, 2, 0]).summary["duplicate_count"] == 1


def test_short_intervals_and_configurable_threshold():
    result = analyze([0, 1, 2, 2.1, 3.1, 5.1], factor=1.5)
    assert result.summary["short_interval_count"] == 1
    assert result.summary["large_interval_count"] == 1


@pytest.mark.parametrize("times", [[0], [1, 1], [3, 2, 1]])
def test_no_positive_baseline(times):
    assert analyze(times).summary["sample_rate_hz"] is None


def test_missing_nan_inf_and_non_numeric_signal():
    result = analyze([0, 1, 2, 3, 4], ["NaN", "inf", "bad", "", "2"])
    stats = result.channel_stats.iloc[0]
    assert stats["missing_count"] == 2
    assert stats["infinite_count"] == 1
    assert stats["non_numeric_count"] == 1
    assert stats["finite_count"] == 1


def test_all_invalid_signal_has_no_fabricated_statistics():
    stats = analyze([0, 1], ["NaN", "inf"]).channel_stats.iloc[0]
    assert stats["finite_count"] == 0
    assert np.isnan(stats["mean"])
    assert not stats["is_constant"]


def test_invalid_timestamp_breaks_adjacency():
    result = analyze([0, "bad", 5, 6])
    assert result.summary["non_numeric_timestamp_count"] == 1
    assert result.summary["large_interval_count"] == 0
    assert result.summary["sample_rate_hz"] == 1


@pytest.mark.parametrize("factor", [1, 0, float("nan"), float("inf")])
def test_invalid_factor(factor):
    with pytest.raises(ValueError):
        analyze([0, 1], factor=factor)


def test_large_finite_values_do_not_overflow_statistics():
    with np.errstate(over="raise", invalid="raise"):
        constant = analyze([0, 1], [1e308, 1e308]).channel_stats.iloc[0]
        balanced = analyze([0, 1], [-1e308, 1e308]).channel_stats.iloc[0]
    assert constant["mean"] == 1e308
    assert constant["median"] == 1e308
    assert constant["std"] == 0
    assert balanced["mean"] == 0
    assert balanced["std"] == 1e308
