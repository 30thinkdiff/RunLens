"""Signal figures preserve row order and visibly break across quality defects."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from runlens.schemas import Dataset, DetectionResult, QualityReport

MAX_PLOT_ROWS = 20_000
MAX_PLOT_CHANNELS = 8
MAX_MARKERS = 50


def build_signal_figure(
    dataset: Dataset,
    report: QualityReport,
    channels: tuple[str, ...],
    time_range: tuple[float, float],
) -> go.Figure:
    """Plot finite timestamps without interpolation, sorting or silent decimation."""
    if (
        not channels
        or len(channels) > MAX_PLOT_CHANNELS
        or len(set(channels)) != len(channels)
    ):
        raise ValueError(f"请选择 1 到 {MAX_PLOT_CHANNELS} 个不同绘图通道。")
    if any(channel not in dataset.signals for channel in channels):
        raise ValueError("绘图通道必须包含在导入配置中。")
    lo, hi = time_range
    if not np.isfinite([lo, hi]).all() or lo > hi:
        raise ValueError("时间范围必须有限且起点不晚于终点。")
    indices = np.flatnonzero(
        np.isfinite(dataset.time_s) & (dataset.time_s >= lo) & (dataset.time_s <= hi)
    )
    if len(indices) > MAX_PLOT_ROWS:
        raise ValueError(
            f"当前范围超过 {MAX_PLOT_ROWS:,} 行；请缩小时间范围。不会自动抽稀数据。"
        )
    fig = make_subplots(
        rows=len(channels), cols=1, shared_xaxes=True, subplot_titles=list(channels)
    )
    nominal = report.summary["nominal_interval_s"]
    for plot_row, channel in enumerate(channels, start=1):
        x, y, row_numbers = [], [], []
        previous = None
        for index in indices:
            dt = dataset.interval_s[index]
            broken = previous is not None and (
                index != previous + 1
                or not np.isfinite(dt)
                or dt <= 0
                or (
                    nominal is not None
                    and (
                        dt > nominal * report.gap_factor
                        or dt < nominal / report.gap_factor
                    )
                )
            )
            if broken:
                x.append(None)
                y.append(None)
                row_numbers.append(None)
            value = dataset.signals[channel].iloc[index]
            x.append(float(dataset.time_s[index]))
            y.append(float(value) if np.isfinite(value) else None)
            row_numbers.append(int(index))
            previous = index
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                customdata=row_numbers,
                name=channel,
                mode="lines+markers" if len(indices) <= 100 else "lines",
                connectgaps=False,
                hovertemplate=(
                    "t=%{x:.9g} s<br>value=%{y:.6g}<br>row=%{customdata}"
                    "<extra>%{fullData.name}</extra>"
                ),
            ),
            row=plot_row,
            col=1,
        )
        fig.update_yaxes(title_text="Value", row=plot_row, col=1)
    colors = {
        "large_interval": "#d62728",
        "short_interval": "#d62728",
        "reverse_timestamp": "#9467bd",
        "duplicate_timestamp": "#ff7f0e",
    }
    marked = 0
    for issue in report.issues.itertuples(index=False):
        if not np.isfinite([issue.start_s, issue.end_s]).all():
            continue
        start, end = sorted((issue.start_s, issue.end_s))
        if (
            end < lo
            or start > hi
            or (
                issue.channel not in channels
                and issue.channel != dataset.config.timestamp_column
            )
        ):
            continue
        if marked >= MAX_MARKERS:
            break
        for row, channel in enumerate(channels, start=1):
            if issue.channel not in (channel, dataset.config.timestamp_column):
                continue
            color = colors.get(issue.kind, "#7f7f7f")
            if start == end:
                fig.add_vline(
                    x=start, line_color=color, line_dash="dot", row=row, col=1
                )
            else:
                fig.add_vrect(
                    x0=max(start, lo),
                    x1=min(end, hi),
                    fillcolor=color,
                    opacity=0.12,
                    line_width=0,
                    row=row,
                    col=1,
                )
        marked += 1
    fig.update_xaxes(
        title_text="Relative time (s)",
        range=[lo, hi] if lo < hi else None,
        row=len(channels),
        col=1,
    )
    fig.update_layout(
        height=max(320, 210 * len(channels)),
        showlegend=False,
        margin={"t": 40, "b": 40},
        hovermode="closest",
    )
    return fig


def build_candidate_figure(
    dataset: Dataset,
    quality: QualityReport,
    result: DetectionResult,
    channels: tuple[str, ...],
    time_range: tuple[float, float],
    *,
    candidate_index: int | None = None,
) -> go.Figure:
    """Add candidate highlights while retaining quality breaks and row hover data."""
    fig = build_signal_figure(dataset, quality, channels, time_range)
    candidates = result.candidates
    if candidate_index is not None:
        if candidate_index not in candidates.index:
            raise ValueError("所选候选区间不存在。")
        candidates = candidates.loc[[candidate_index]]
    lo, hi = time_range
    marked = 0
    for event in candidates.itertuples(index=False):
        if event.end_s < lo or event.start_s > hi:
            continue
        if result.config.method == "mad" and event.channel not in channels:
            continue
        if marked >= MAX_MARKERS:
            break
        for row, channel in enumerate(channels, 1):
            if result.config.method == "mad" and event.channel != channel:
                continue
            if event.start_s == event.end_s:
                fig.add_vline(
                    x=event.start_s,
                    line_color="#008B8B",
                    line_width=2,
                    line_dash="dash",
                    row=row,
                    col=1,
                )
            else:
                fig.add_vrect(
                    x0=max(event.start_s, lo),
                    x1=min(event.end_s, hi),
                    fillcolor="#008B8B",
                    opacity=0.2,
                    line_width=0,
                    row=row,
                    col=1,
                )
        marked += 1
    return fig
