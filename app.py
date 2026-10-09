"""RunLens Phase 1: CSV exploration and observable data-quality checks."""

import hashlib
import json

import numpy as np
import pandas as pd
import streamlit as st

from runlens import __version__
from runlens.demo import generate_demo
from runlens.io import DataValidationError, prepare_dataset, read_csv
from runlens.plotting import MAX_MARKERS, MAX_PLOT_CHANNELS, build_signal_figure
from runlens.quality import check_quality
from runlens.schemas import ImportConfig


@st.cache_data(ttl=600, max_entries=3, scope="session", show_spinner=False)
def demo_files() -> tuple[bytes, bytes, bytes]:
    demo = generate_demo()
    return (
        demo.data.to_csv(index=False).encode("utf-8"),
        demo.labels.to_csv(index=False).encode("utf-8"),
        json.dumps(demo.metadata, ensure_ascii=False, indent=2).encode("utf-8"),
    )


@st.cache_data(ttl=600, max_entries=3, scope="session", show_spinner=False)
def cached_csv(payload: bytes) -> pd.DataFrame:
    return read_csv(payload)


@st.cache_data(ttl=600, max_entries=3, scope="session", show_spinner=False)
def cached_analysis(
    payload: bytes, config: ImportConfig, source_name: str, gap_factor: float
):
    dataset = prepare_dataset(read_csv(payload), config, source_name)
    return dataset, check_quality(dataset, gap_factor=gap_factor)


st.set_page_config(
    page_title="RunLens", page_icon=":material/analytics:", layout="wide"
)
st.title("RunLens")
st.caption(f"Robot time-series explorer · v{__version__} · Phase 1")

with st.sidebar:
    st.header("数据与配置")
    source = st.selectbox(
        "数据来源", ["Synthetic Data（演示）", "上传 CSV"], key="source"
    )
    if source == "上传 CSV":
        upload = st.file_uploader(
            "上传时序 CSV", type="csv", max_upload_size=20, key="upload"
        )
        if upload is None:
            st.info("上传 UTF-8 CSV 后选择时间列、通道与时间单位。")
            st.stop()
        payload, source_name = upload.getvalue(), upload.name
    else:
        payload, label_bytes, metadata_bytes = demo_files()
        source_name = "Synthetic Data · synthetic_imu.csv"
    try:
        raw = cached_csv(payload)
    except DataValidationError as exc:
        st.error(str(exc))
        st.stop()
    identity = hashlib.sha256(payload).hexdigest()[:12]
    timestamp_column = st.selectbox(
        "时间戳列", raw.columns.tolist(), key=f"timestamp_{identity}"
    )
    candidates = [column for column in raw.columns if column != timestamp_column]
    channels = st.multiselect(
        "分析通道",
        candidates,
        default=candidates[:6],
        key=f"channels_{identity}_{timestamp_column}",
    )
    unit = st.selectbox(
        "时间戳单位（请明确指定）", ["s", "ms", "us", "ns"], key=f"unit_{identity}"
    )
    gap_factor = st.number_input(
        "间隔阈值倍数",
        min_value=1.01,
        max_value=100.0,
        value=3.0,
        step=0.5,
        key="gap_factor",
    )
    st.caption("不根据数值大小猜测单位；不排序、插值或重采样。")

if source != "上传 CSV":
    st.info(
        "Synthetic Data · 固定种子 42 的合成 IMU；"
        "包含人为尖峰、时间戳问题与缺失值，不是真实机器人记录。"
    )
    with st.expander("下载演示 CSV、参考标签与生成配置"):
        st.download_button(
            "演示 CSV", payload, "synthetic_imu.csv", "text/csv", key="download_demo"
        )
        st.download_button(
            "注入参考标签",
            label_bytes,
            "synthetic_labels.csv",
            "text/csv",
            key="download_labels",
        )
        st.download_button(
            "生成配置",
            metadata_bytes,
            "synthetic_metadata.json",
            "application/json",
            key="download_metadata",
        )

with st.expander("原始 CSV 预览（前 50 行）"):
    st.dataframe(raw.head(50), alt="原始 CSV 前 50 行，保留原始数值文本")

if not channels:
    st.warning("请选择至少一个分析通道。")
    st.stop()
try:
    config = ImportConfig(timestamp_column, tuple(channels), unit)
    dataset, report = cached_analysis(payload, config, source_name, float(gap_factor))
except ValueError as exc:
    st.error(str(exc))
    st.stop()

summary = report.summary
rate = summary["sample_rate_hz"]
valid_times = dataset.time_s[np.isfinite(dataset.time_s)]
lo, hi = float(np.min(valid_times)), float(np.max(valid_times))
with st.container(horizontal=True):
    st.metric("样本行", str(summary["rows"]), border=True)
    st.metric("分析通道", str(summary["channels"]), border=True)
    st.metric(
        "估计采样频率",
        f"{rate:.6g} Hz" if rate is not None else "无法估计",
        border=True,
    )
    st.metric("质量问题条目", str(len(report.issues)), border=True)
st.caption(
    f"来源：{source_name} · 相对时间范围：{lo:.9g}–{hi:.9g} s · "
    f"原始起点：{dataset.timestamp_origin} {unit}"
)
st.caption(
    "采样频率 = 1 / 有效相邻正间隔中位数；仅描述时间戳，不保证真实传感器采样率。"
)
view = st.segmented_control(
    "查看", ["数据概览", "信号浏览"], default="数据概览", key="view"
)

if view != "信号浏览":
    st.subheader("数据质量报告")
    st.markdown(
        f"大间隔：Δt > 中位数 × **{gap_factor:g}**；"
        f"短间隔：0 < Δt < 中位数 / **{gap_factor:g}**。"
        "重复按原始值检查，逆序按原始相邻有效对检查。"
    )
    if report.issues.empty:
        st.success("所选列未发现上述规则定义的质量问题。此结果不代表真实系统无故障。")
    else:
        st.warning(
            "发现可观测的数据质量问题。较大间隔仅表示异常采样间隔，不能据此确认丢帧或硬件故障。"
        )
    st.dataframe(
        pd.DataFrame([summary]), alt="样本数量、时间戳质量计数与正采样间隔统计"
    )
    st.subheader("通道统计")
    st.caption(
        "统计只使用有限值；标准差采用总体定义 ddof=0。"
        "常数判定要求至少两个有限值完全相同；不设置未经说明的物理有效范围。"
    )
    st.dataframe(report.channel_stats, alt="各通道有效值、缺失和非法值计数及基础统计")
    if report.channel_stats["is_constant"].any():
        st.warning("存在常数通道；这是一项数据观察，不代表传感器故障。")
    st.subheader("质量问题证据")
    st.caption(
        "row_start / row_end 为 0 起始的原始样本行号，包含端点。"
        "表格最多显示前 500 条；无效时间戳不能定位到时间轴。"
    )
    st.dataframe(
        report.issues.head(500), alt="质量问题的原始样本行、相对时间、通道、规则与阈值"
    )
else:
    st.subheader("信号浏览")
    plot_identity = hashlib.sha256(repr(channels).encode()).hexdigest()[:8]
    plot_channels = st.multiselect(
        "绘图通道",
        channels,
        default=channels[:3],
        max_selections=MAX_PLOT_CHANNELS,
        key=f"plot_channels_{identity}_{plot_identity}",
    )
    if lo < hi:
        time_range = st.slider(
            "相对时间范围（s）",
            min_value=lo,
            max_value=hi,
            value=(lo, hi),
            step=(hi - lo) / 1000,
            format="%.9g",
            key=f"time_range_{identity}_{timestamp_column}_{unit}",
        )
    else:
        time_range = (lo, hi)
        st.info("有效时间戳只有一个时间位置，无法选择时间区间。")
    mask = (
        np.isfinite(dataset.time_s)
        & (dataset.time_s >= time_range[0])
        & (dataset.time_s <= time_range[1])
    )
    if not plot_channels:
        st.warning("请选择至少一个绘图通道。")
    else:
        try:
            figure = build_signal_figure(
                dataset, report, tuple(plot_channels), time_range
            )
            st.plotly_chart(
                figure,
                key="signals",
                alt="所选通道随相对时间的信号曲线，质量问题处断线并标记",
            )
        except ValueError as exc:
            st.warning(str(exc))
    st.caption(
        "保留原始行序，跨异常间隔、重复、逆序、无效值或不连续原始行处断线。"
        "红色：间隔；紫色：逆序；橙色：重复；灰色：通道无效值。"
        f"最多 {MAX_MARKERS} 个可定位标记。"
    )
    st.caption(
        f"当前范围包含 {int(mask.sum()):,} 个有效时间戳行；"
        "其他无效时间戳行仍保留在原始表与质量报告。"
    )
    detail = dataset.raw.loc[mask, [timestamp_column, *channels]].copy()
    st.caption("详细表最多显示 1000 行；行号对应原始样本，不是 CSV 物理行号。")
    for base, values in [
        ("RunLens relative time (s)", dataset.time_s[mask]),
        ("RunLens sample row (0-based)", np.flatnonzero(mask)),
    ]:
        name = base
        while name in detail.columns:
            name += "_"
        detail.insert(0, name, values)
    st.dataframe(
        detail.head(1000), alt="当前时间范围内前 1000 个样本行的原始字段及相对时间"
    )
