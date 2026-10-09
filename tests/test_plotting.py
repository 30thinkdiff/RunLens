"""Plotting must not hide interruptions or join across filtered-out rows."""

import numpy as np
import pandas as pd
import pytest

from runlens.io import prepare_dataset
from runlens.plotting import MAX_PLOT_ROWS, build_signal_figure
from runlens.quality import check_quality
from runlens.schemas import ImportConfig


def figure(times, values=None, time_range=None):
    frame = pd.DataFrame(
        {"t": times, "x": values if values is not None else np.ones(len(times))}
    )
    data = prepare_dataset(frame, ImportConfig("t", ("x",)))
    report = check_quality(data)
    limits = time_range or (
        float(np.nanmin(data.time_s)),
        float(np.nanmax(data.time_s)),
    )
    return build_signal_figure(data, report, ("x",), limits)


def test_large_gap_breaks_line_and_preserves_both_endpoints():
    plot = figure([0, 1, 2, 12, 13])
    assert list(plot.data[0].x) == [0, 1, 2, None, 12, 13]
    assert plot.data[0].connectgaps is False
    assert plot.layout.shapes[0].x0 == 2
    assert plot.layout.shapes[0].x1 == 12


@pytest.mark.parametrize("times", [[0, 1, 1, 2], [0, 1, 0.5, 2], [0, "bad", 1, 2]])
def test_invalid_or_non_increasing_time_breaks_lines(times):
    assert None in figure(times).data[0].x


def test_missing_or_infinite_signal_does_not_connect():
    plot = figure([0, 1, 2, 3], [1, np.nan, np.inf, 4])
    assert list(plot.data[0].y) == [1, None, None, 4]
    assert not plot.data[0].connectgaps


def test_filter_keeps_original_rows_and_does_not_bridge_out_of_range_row():
    plot = figure([0, 1, 10, 2, 3], time_range=(1, 3))
    assert list(plot.data[0].customdata) == [1, None, 3, 4]


def test_large_views_are_rejected_instead_of_silently_downsampled():
    with pytest.raises(ValueError, match="20,000"):
        figure(list(range(MAX_PLOT_ROWS + 1)))
