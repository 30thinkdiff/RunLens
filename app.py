"""RunLens: CSV exploration, data quality and window/spectral features."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from runlens import __version__
from runlens.anomaly import candidates_csv, detect_anomalies, detection_json, scores_csv
from runlens.demo import generate_demo
from runlens.experiments import run_robot_experiments
from runlens.features import (
    SPECTRAL_FEATURES,
    TIME_FEATURES,
    SpectralAnalysisError,
    add_vector_magnitude,
    analyze_spectrum,
    extract_features,
    feature_csv,
)
from runlens.io import DataValidationError, prepare_dataset, read_csv
from runlens.plotting import (
    MAX_MARKERS,
    MAX_PLOT_CHANNELS,
    build_candidate_figure,
    build_signal_figure,
)
from runlens.quality import check_quality
from runlens.reporting import analysis_report, html_bytes, json_bytes, markdown_bytes
from runlens.schemas import DetectionConfig, ImportConfig, SpectralConfig, WindowConfig


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


@st.cache_data(ttl=600, max_entries=3, scope="session", show_spinner=False)
def cached_features(payload, import_config, window_config, source_name, axes, name):
    dataset = prepare_dataset(read_csv(payload), import_config, source_name)
    result = extract_features(
        dataset, window_config, magnitude_axes=axes, magnitude_name=name
    )
    return result, feature_csv(result)


@st.cache_data(ttl=600, max_entries=2, scope="session", show_spinner=False)
def cached_detection(payload, import_config, detection_config, source_name):
    dataset = prepare_dataset(read_csv(payload), import_config, source_name)
    result = detect_anomalies(dataset, detection_config)
    return result, candidates_csv(result), scores_csv(result), detection_json(result)


@st.cache_data(ttl=600, max_entries=2, scope="session", show_spinner=False)
def cached_experiments(fixture_path: str, fixture_sha256: str):
    fixture = Path(fixture_path)
    if hashlib.sha256(fixture.read_bytes()).hexdigest() != fixture_sha256:
        raise ValueError("实验数据发生变化，请重新提交。")
    result = run_robot_experiments(fixture)
    return (
        result,
        json_bytes(result.report),
        markdown_bytes(result.report),
        html_bytes(result.report),
    )


st.set_page_config(
    page_title="RunLens", page_icon=":material/analytics:", layout="wide"
)
st.title("RunLens")
st.caption(f"Robot time-series explorer · v{__version__} · Phase 4")

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
feature_identity = (identity, config, source_name)
if st.session_state.get("feature_identity") != feature_identity:
    st.session_state["feature_identity"] = feature_identity
    st.session_state.pop("feature_result", None)
    st.session_state.pop("feature_csv", None)
    st.session_state.pop("detection_output", None)
report_context = (feature_identity, float(gap_factor))
if st.session_state.get("report_context") != report_context:
    st.session_state["report_context"] = report_context
    st.session_state.pop("analysis_report_output", None)
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
if timestamp_column == "synthetic_time_s":
    st.warning(
        "此字段标注为 synthetic_time_s；LP1 示例使用的是构造时间轴，"
        "仅供导入和定位，不可解释为真实采样率或物理频率。"
    )
view = st.segmented_control(
    "查看",
    ["数据概览", "信号浏览", "特征分析", "异常检测", "实验与报告"],
    default="数据概览",
    key="view",
)

if view in (None, "数据概览"):
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
elif view == "信号浏览":
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
            detection_output = st.session_state.get("detection_output")
            if detection_output is None:
                figure = build_signal_figure(
                    dataset, report, tuple(plot_channels), time_range
                )
            else:
                figure = build_candidate_figure(
                    dataset,
                    report,
                    detection_output[0],
                    tuple(plot_channels),
                    time_range,
                )
            st.plotly_chart(
                figure,
                key="signals",
                alt="所选通道的原始信号、质量断线与已计算的候选区间",
            )
        except ValueError as exc:
            st.warning(str(exc))
    st.caption(
        "保留原始行序，跨异常间隔、重复、逆序、无效值或不连续原始行处断线。"
        "红色：间隔；紫色：逆序；橙色：重复；灰色：通道无效值。"
        f"最多 {MAX_MARKERS} 个可定位标记。"
    )
    if st.session_state.get("detection_output") is not None:
        st.caption("青色虚线/阴影：最近一次成功提交检测得到的候选，最多 50 个区间。")
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
elif view == "特征分析":
    st.subheader("窗口特征")
    st.caption(
        "按原始样本行滑动窗口，窗口和步长单位为样本；不排序或插值。"
        "统计按样本等权计算，std/variance 使用 ddof=0。"
    )
    with st.form("feature_config"):
        with st.container(horizontal=True):
            window_size = st.number_input(
                "窗口长度（样本）", 1, 100_000, 256, key="window_size"
            )
            step_size = st.number_input(
                "步长（样本）", 1, 100_000, 128, key="step_size"
            )
            nan_policy = st.selectbox(
                "无效信号值策略", ["omit", "propagate"], key="nan_policy"
            )
        st.caption(
            "omit：时域统计忽略 NaN/Inf 并记录数量；propagate：有无效值则统计为空。"
            "两种策略都不会删掉样本后计算频谱。"
        )
        include_partial = st.checkbox("保留尾部不足长度的窗口", key="include_partial")
        include_spectral = st.checkbox(
            "计算窗口频域特征", value=True, key="include_spectral"
        )
        with st.container(horizontal=True):
            sampling_rtol = st.number_input(
                "采样间隔相对容差",
                0.0,
                0.05,
                1e-6,
                step=1e-6,
                format="%.6g",
                key="sampling_rtol",
            )
            welch_nperseg = st.number_input(
                "Welch 分段长度（样本）", 2, 100_000, 256, key="welch_nperseg"
            )
        remove_mean = st.checkbox(
            "频谱分析前去除整段均值", value=True, key="remove_mean"
        )
        if len(channels) < 3:
            st.session_state["use_magnitude"] = False
        use_magnitude = st.checkbox(
            "增加三轴模长通道", disabled=len(channels) < 3, key="use_magnitude"
        )
        default_axes = (
            ["accel_x", "accel_y", "accel_z"]
            if {"accel_x", "accel_y", "accel_z"} <= set(channels)
            else channels[:3]
        )
        axes = st.multiselect(
            "模长的三个轴",
            channels,
            default=default_axes,
            max_selections=3,
            key=f"magnitude_axes_{identity}_{timestamp_column}_{tuple(channels)}",
        )
        magnitude_name = st.text_input(
            "模长通道名称", value="vector_magnitude", key="magnitude_name"
        )
        submitted = st.form_submit_button("计算窗口特征", key="compute_features")
    if submitted:
        st.session_state.pop("analysis_report_output", None)
        try:
            window_config = WindowConfig(
                window_size=int(window_size),
                step_size=int(step_size),
                include_partial=include_partial,
                nan_policy=nan_policy,
                include_spectral=include_spectral,
                spectral=SpectralConfig(
                    sampling_rtol=float(sampling_rtol),
                    welch_nperseg=int(welch_nperseg),
                    remove_mean=remove_mean,
                ),
            )
            with st.spinner("计算窗口特征…"):
                result, csv_bytes = cached_features(
                    payload,
                    config,
                    window_config,
                    source_name,
                    tuple(axes) if use_magnitude else None,
                    magnitude_name,
                )
            st.session_state["feature_result"] = result
            st.session_state["feature_csv"] = csv_bytes
        except ValueError as exc:
            st.session_state.pop("feature_result", None)
            st.session_state.pop("feature_csv", None)
            st.error(str(exc))
    result = st.session_state.get("feature_result")
    if result is not None:
        table = result.table
        st.caption(
            f"已计算：窗口 {result.config.window_size}、"
            f"步长 {result.config.step_size}、无效值策略 {result.config.nan_policy}；"
            f"共 {len(table):,} 条窗口×通道记录。"
            "表格显示前 1000 条，CSV 包含全部记录与配置；行号从 0 起、包含两端。"
        )
        st.download_button(
            "下载特征 CSV",
            st.session_state["feature_csv"],
            "runlens_features.csv",
            "text/csv",
            key="download_features",
        )
        st.dataframe(table.head(1000), alt="窗口特征、计算配置和频谱拒绝原因")
        if table.empty:
            st.info("没有满足长度的窗口；请缩短窗口或保留尾部不足长度的窗口。")
        else:
            st.dataframe(
                table["spectral_status"].value_counts().rename("records").reset_index(),
                alt="窗口频谱各状态的记录数",
            )
            rejected = ~table["spectral_status"].isin(["ok", "disabled"])
            if rejected.any():
                st.warning(
                    f"{int(rejected.sum())} 条记录的频谱未计算；"
                    "时域结果仍保留，原因见 spectral_status / spectral_message。"
                )
            if table["overflow_features"].ne("").any():
                st.warning(
                    "部分时域指标超出数值范围，已置空并记录在 overflow_features。"
                )
            with st.container(horizontal=True):
                trend_channel = st.selectbox(
                    "特征趋势通道", table["channel"].unique(), key="trend_channel"
                )
                trend_metric = st.selectbox(
                    "特征趋势指标",
                    [*TIME_FEATURES, *SPECTRAL_FEATURES],
                    key="trend_metric",
                )
            trend = table.loc[table["channel"] == trend_channel]
            if len(trend) <= 20_000:
                figure = go.Figure(
                    go.Scatter(
                        x=trend["start_s"].tolist(),
                        y=trend[trend_metric].tolist(),
                        mode="markers",
                        name=trend_metric,
                    )
                )
                figure.update_layout(
                    xaxis_title="窗口起点（相对秒）", yaxis_title=trend_metric
                )
                st.plotly_chart(
                    figure, key="feature_trend", alt="各窗口特征随窗口起点变化的散点图"
                )
            else:
                st.info("趋势图超过 20,000 个窗口，请增大步长；CSV 仍包含全部记录。")
    else:
        st.info("设置参数并点击“计算窗口特征”以生成结果。")

    st.subheader("所选片段的 FFT 与 Welch PSD")
    spectrum_signals = dataset.signals
    spectrum_config = result.config.spectral if result is not None else SpectralConfig()
    if result is not None and result.magnitude_axes is not None:
        spectrum_signals = add_vector_magnitude(
            spectrum_signals, result.magnitude_axes, result.magnitude_name
        )
    spectrum_channel = st.selectbox(
        "频谱通道", spectrum_signals.columns.tolist(), key="spectrum_channel"
    )
    if len(dataset.time_s) > 1:
        spectrum_range = st.slider(
            "频谱原始样本行范围（包含两端）",
            0,
            len(dataset.time_s) - 1,
            (0, min(255, len(dataset.time_s) - 1)),
            key=f"spectrum_range_{identity}",
        )
    else:
        spectrum_range = (0, 0)
    st.caption(
        f"当前频谱配置：相对容差 {spectrum_config.sampling_rtol:g}，"
        f"Welch 分段上限 {spectrum_config.welch_nperseg}，"
        f"去除均值 {spectrum_config.remove_mean}。"
        "提交上方表单后更新。频谱需要至少两个有限样本和严格递增、近似等间隔的时间戳。"
    )
    first, last = spectrum_range
    try:
        spectrum = analyze_spectrum(
            spectrum_signals[spectrum_channel].iloc[first : last + 1],
            dataset.time_s[first : last + 1],
            config=spectrum_config,
            interval_s=dataset.interval_s[first + 1 : last + 1],
        )
    except SpectralAnalysisError as exc:
        st.warning(f"频谱未计算（{exc.code}）：{exc}")
    else:
        for key, title, x, y, ylabel in [
            (
                "fft",
                "单边 FFT 幅值谱（矩形窗）",
                spectrum.frequency_hz,
                spectrum.amplitude,
                "幅值（信号单位）",
            ),
            (
                "psd",
                "Welch PSD（周期 Hann 窗，50% 重叠）",
                spectrum.psd_frequency_hz,
                spectrum.psd_density,
                "PSD（信号单位²/Hz）",
            ),
        ]:
            figure = go.Figure(go.Scatter(x=x.tolist(), y=y.tolist(), name=title))
            figure.update_layout(
                title=title, xaxis_title="频率（Hz）", yaxis_title=ylabel
            )
            st.plotly_chart(figure, key=key, alt=f"{spectrum_channel} 的{title}")
        st.dataframe(
            pd.DataFrame([spectrum.features]), alt="所选片段的频域指标及分辨率"
        )
        st.caption(
            "主频取非 DC FFT 最大幅值所在频率格点；常数去均值后主频为空。"
            "PSD 积分单位为信号单位²；频谱能量估计 = PSD 积分 × N/fs，"
            "单位为信号单位²·s，不能解释为机械能。频谱指标描述预处理后的信号。"
        )
elif view == "异常检测":
    st.subheader("异常候选检测")
    st.info(
        "在指定参考区间拟合，在不重叠的检测区间评分。"
        "请确认参考区间适合代表期望工况；算法不能保证它正常。"
        "结果是统计候选，不是硬件故障、根因或故障概率。"
    )
    n = len(dataset.signals)
    if n < 6:
        st.warning(
            "至少需要 6 行才能分出 5 个 MAD 参考样本和检测样本；请使用更长记录。"
        )
        st.stop()
    split = max(5, min(400, n // 5))
    with st.form("detection_config"):
        method = st.selectbox(
            "检测方法", ["mad", "isolation_forest"], key="detection_method"
        )
        fit_range = st.slider(
            "参考样本行区间（包含两端）",
            0,
            n - 1,
            (0, split - 1),
            key=f"fit_range_{identity}",
        )
        detect_range = st.slider(
            "检测样本行区间（包含两端）",
            0,
            n - 1,
            (split, n - 1),
            key=f"detect_range_{identity}",
        )
        with st.container(horizontal=True):
            threshold = st.number_input(
                "MAD 分数阈值", 0.1, 100.0, 3.5, step=0.5, key="mad_threshold"
            )
            scale_floor = st.number_input(
                "最小鲁棒尺度（信号单位）",
                0.0,
                value=0.0,
                format="%.6g",
                key="scale_floor",
            )
        st.caption(
            "MAD = median(abs(x − 参考中位数))；尺度 = max(1.4826 × MAD, 最小尺度)。"
            "默认 MAD=0 时不评分；最小尺度须根据量化精度与单位明确设置。"
            "不同量纲通道可分批检测。"
        )
        with st.container(horizontal=True):
            contamination_mode = st.selectbox(
                "IF 阈值设置", ["auto", "指定 contamination"], key="contamination_mode"
            )
            contamination = st.number_input(
                "IF contamination", 0.001, 0.5, 0.02, step=0.01, key="contamination"
            )
            seed = st.number_input("IF 随机种子", 0, 2**32 - 1, 42, key="if_seed")
        with st.container(horizontal=True):
            trees = st.number_input("IF 树数量", 10, 300, 100, key="if_trees")
            max_samples = st.number_input(
                "IF 每棵树样本上限", 16, 1024, 256, key="if_max_samples"
            )
        st.caption(
            "IF 将所选通道组成逐行多变量向量，需要至少 16 个完整有限参考行。"
            "按参考区间拟合最大绝对值缩放；分数 = −decision_function，阈值为 0。"
            "contamination 只控制训练阈值，不是故障发生比例。"
        )
        submitted = st.form_submit_button("运行检测", key="run_detection")
    if submitted:
        st.session_state.pop("analysis_report_output", None)
        try:
            detection_config = DetectionConfig(
                method=method,
                fit_range=tuple(fit_range),
                detect_range=tuple(detect_range),
                threshold=float(threshold),
                scale_floor=float(scale_floor),
                contamination="auto"
                if contamination_mode == "auto"
                else float(contamination),
                n_estimators=int(trees),
                max_samples=int(max_samples),
                random_state=int(seed),
                gap_factor=float(gap_factor),
            )
            with st.spinner("拟合参考区间并检测…"):
                st.session_state["detection_output"] = cached_detection(
                    payload, config, detection_config, source_name
                )
        except ValueError as exc:
            st.session_state.pop("detection_output", None)
            st.error(str(exc))
    output = st.session_state.get("detection_output")
    if output is None:
        st.caption("设置参数并点击“运行检测”；修改表单后请重新提交。")
    else:
        result, candidate_bytes, score_bytes, config_bytes = output
        st.caption(
            f"已计算：{result.config.method}；参考 {result.config.fit_range}，"
            f"检测 {result.config.detect_range}，"
            f"间隔倍数 {result.config.gap_factor:g}。"
            "评价单位为原始采样行；MAD 每通道评分，IF 每行联合评分，分数不可直接比较。"
        )
        with st.container(horizontal=True):
            st.metric(
                "候选点记录", int(result.metadata["candidate_points"]), border=True
            )
            st.metric("候选区间", len(result.candidates), border=True)
            st.download_button(
                "候选区间 CSV",
                candidate_bytes,
                "runlens_candidates.csv",
                "text/csv",
                key="download_candidates",
            )
            st.download_button(
                "逐行分数 CSV",
                score_bytes,
                "runlens_scores.csv",
                "text/csv",
                key="download_scores",
            )
            st.download_button(
                "检测配置 JSON",
                config_bytes,
                "runlens_detection.json",
                "application/json",
                key="download_detection_config",
            )
        st.subheader("参考基准与评分状态")
        st.dataframe(
            result.baselines, alt="仅用参考区间拟合的中位数、MAD、尺度或 IF 缩放"
        )
        st.dataframe(
            result.scores.status.value_counts().rename("records").reset_index(),
            alt="有效评分、无效值、零 MAD 和参考不足等状态计数",
        )
        skipped = int(result.scores.status.ne("ok").sum())
        if skipped:
            st.warning(
                f"{skipped} 条评分记录被跳过；查看状态与基准，不把跳过当作正常。"
            )
        st.subheader("候选区间列表")
        st.caption(
            "行号从 0 开始、包含端点。仅合并相邻候选行，"
            "正常/无效行与异常时间间隔打断区间。"
            "列表与选择框显示前 1000 条；CSV 保留全部记录。"
        )
        st.dataframe(
            result.candidates.head(1000), alt="候选区间的原始行、时间、方法、分数和阈值"
        )
        if result.candidates.empty:
            st.info("本次参数下没有可定位候选区间；不代表系统无故障。")
        options = [None, *result.candidates.head(1000).index.tolist()]
        candidate_index = st.selectbox(
            "定位候选区间",
            options,
            format_func=lambda index: (
                "自选样本范围"
                if index is None
                else f"#{index} · {result.candidates.loc[index, 'channel']} · "
                f"行 {result.candidates.loc[index, 'row_start']}–"
                f"{result.candidates.loc[index, 'row_end']}"
            ),
            key=f"candidate_choice_{identity}_{hashlib.sha256(config_bytes).hexdigest()[:12]}",
        )
        if candidate_index is None:
            first, last = st.slider(
                "局部原始样本行范围",
                0,
                n - 1,
                (
                    result.config.detect_range[0],
                    min(
                        result.config.detect_range[0] + 999,
                        result.config.detect_range[1],
                    ),
                ),
                key=f"candidate_range_{identity}",
            )
            default_plot_channels = channels[:3]
        else:
            event = result.candidates.loc[candidate_index]
            first = max(0, int(event.row_start) - 25)
            last = min(n - 1, int(event.row_end) + 25)
            default_plot_channels = (
                [event.channel] if result.config.method == "mad" else channels[:3]
            )
        selected_channels = st.multiselect(
            "候选绘图通道",
            channels,
            default=default_plot_channels,
            max_selections=MAX_PLOT_CHANNELS,
            key=f"candidate_channels_{identity}_{candidate_index}_{tuple(channels)}",
        )
        context_times = dataset.time_s[first : last + 1]
        finite_times = context_times[np.isfinite(context_times)]
        if selected_channels and len(finite_times):
            try:
                figure = build_candidate_figure(
                    dataset,
                    report,
                    result,
                    tuple(selected_channels),
                    (float(np.min(finite_times)), float(np.max(finite_times))),
                    candidate_index=candidate_index,
                )
                st.plotly_chart(
                    figure,
                    key="candidate_signals",
                    alt="候选区间附近的原始信号及质量断线，青色标记统计候选",
                )
            except ValueError as exc:
                st.warning(str(exc))
        else:
            st.info("请选择绘图通道，并确保局部范围有有效时间戳。")
        st.caption(
            f"局部行范围 {first}–{last}；信号图按这些行覆盖的时间范围显示，"
            "重复时间可对应其他原始行，请结合悬停行号和详情。最多高亮 50 个候选区间。"
        )
        local_scores = result.scores.loc[result.scores.row.between(first, last)]
        if len(local_scores) <= 20_000:
            figure = go.Figure()
            for channel, block in local_scores.groupby("channel", sort=False):
                figure.add_trace(
                    go.Scatter(
                        x=block.row.tolist(),
                        y=block.score.tolist(),
                        mode="markers",
                        name=channel,
                    )
                )
            score_threshold = (
                result.config.threshold if result.config.method == "mad" else 0
            )
            figure.add_hline(y=score_threshold, line_dash="dash")
            figure.update_layout(
                xaxis_title="原始样本行", yaxis_title="异常分数（非概率）"
            )
            st.plotly_chart(
                figure, key="anomaly_scores", alt="局部原始行的异常分数与实际阈值"
            )
        else:
            st.info("局部分数图超过 20,000 条评分记录，请缩小范围；不自动抽稀。")
        st.dataframe(
            dataset.raw.iloc[first : last + 1].head(1000),
            alt="所选候选附近前 1000 行原始测量",
        )
        st.dataframe(
            local_scores.head(1000), alt="局部评分与未评分原因，显示前 1000 条"
        )

else:
    st.subheader("实验与报告")
    report_mode = st.radio(
        "报告内容",
        ["当前数据分析报告", "内置真实记录实验"],
        key="report_mode",
        horizontal=True,
    )
    if report_mode == "当前数据分析报告":
        st.caption(
            "报告记录当前质量检查及已提交的特征、检测结果；未运行的步骤标为空。"
            "当前数据未提供异常真值，因此不计算 precision、recall、F1 或 FPR。"
            "报告内表格预览最多 20 条，完整 CSV 在对应分析页面下载。"
        )
        with st.form("analysis_report_form"):
            submitted = st.form_submit_button("生成当前数据报告", key="generate_report")
        if submitted:
            try:
                output = st.session_state.get("detection_output")
                snapshot = analysis_report(
                    dataset,
                    report,
                    features=st.session_state.get("feature_result"),
                    detection=output[0] if output is not None else None,
                    input_sha256=hashlib.sha256(payload).hexdigest(),
                )
                st.session_state["analysis_report_output"] = (
                    snapshot,
                    json_bytes(snapshot),
                    markdown_bytes(snapshot),
                    html_bytes(snapshot),
                )
            except ValueError as exc:
                st.session_state.pop("analysis_report_output", None)
                st.error(str(exc))
        output = st.session_state.get("analysis_report_output")
        if output is not None:
            snapshot, report_json, report_md, report_html = output
            st.caption(f"报告生成时间（UTC）：{snapshot['analyzed_at_utc']}")
            with st.container(horizontal=True):
                st.download_button(
                    "下载报告 JSON",
                    report_json,
                    "runlens_report.json",
                    "application/json",
                    key="download_report_json",
                )
                st.download_button(
                    "下载报告 Markdown",
                    report_md,
                    "runlens_report.md",
                    "text/markdown",
                    key="download_report_md",
                )
                st.download_button(
                    "下载报告 HTML",
                    report_html,
                    "runlens_report.html",
                    "text/html",
                    key="download_report_html",
                )
            st.json(snapshot, expanded=False)
        else:
            st.info("点击生成报告；数据、映射、质量参数或已提交结果变化后需重新生成。")
    else:
        st.info(
            "此实验使用仓库内 UCI LP1 真实六轴力/力矩记录，"
            "独立于当前上传文件。"
            "前十个 normal 完整事件参考；其余事件留出。原始数据许可 CC BY 4.0。"
            "时间轴为构造时钟，测量单位未注明，不用于真实 IMU 频率结论。"
        )
        st.caption(
            "固定参数：MAD 3.5、尺度下限 1；"
            "IF auto、100 棵树、max_samples 256、种子 42。"
            "事件标签按 normal/其他类别评价，任意候选点使事件为正；"
            "注入任务只用留出正常事件，在三处六轴替换为 10000，按点评价人为替换检出。"
            "不根据测试标签选参数；完整可评分点/事件才进入指标，覆盖率单独报告。"
        )
        with st.form("robot_experiment_form"):
            submitted = st.form_submit_button("运行真实记录实验", key="run_experiments")
        if submitted:
            try:
                fixture = (
                    Path(__file__).resolve().parent
                    / "tests/fixtures/robot_execution_failures/lp1.data"
                )
                fingerprint = hashlib.sha256(fixture.read_bytes()).hexdigest()
                with st.spinner("运行固定划分实验并生成报告…"):
                    st.session_state["experiment_output"] = cached_experiments(
                        str(fixture), fingerprint
                    )
            except (OSError, ValueError) as exc:
                st.session_state.pop("experiment_output", None)
                st.error(f"真实记录实验未完成：{exc}")
        output = st.session_state.get("experiment_output")
        if output is not None:
            experiment, report_json, report_md, report_html = output
            st.caption(
                f"实际运行时间戳（UTC）：{experiment.report['analyzed_at_utc']}；"
                "重复提交可能复用 600 秒会话缓存。"
            )
            st.dataframe(
                experiment.metrics,
                alt="真实事件与注入点两个独立评价任务的混淆矩阵、指标、覆盖率和实际计时",
            )
            st.warning(
                "事件指标与注入点指标不可混用。强尖峰注入结果不代表自然故障定位能力，候选不等于硬件诊断。"
            )
            with st.container(horizontal=True):
                st.download_button(
                    "实验 JSON",
                    report_json,
                    "robot_experiments.json",
                    "application/json",
                    key="download_experiment_json",
                )
                st.download_button(
                    "实验 Markdown",
                    report_md,
                    "robot_experiments.md",
                    "text/markdown",
                    key="download_experiment_md",
                )
                st.download_button(
                    "实验 HTML",
                    report_html,
                    "robot_experiments.html",
                    "text/html",
                    key="download_experiment_html",
                )
                st.download_button(
                    "实验指标 CSV",
                    experiment.metrics.to_csv(index=False).encode("utf-8"),
                    "metrics.csv",
                    "text/csv",
                    key="download_experiment_metrics",
                )
                st.download_button(
                    "逐单位预测 CSV",
                    experiment.predictions.to_csv(index=False).encode("utf-8"),
                    "predictions.csv",
                    "text/csv",
                    key="download_experiment_predictions",
                )
            st.json(experiment.report, expanded=False)
            st.caption(
                "完整测量、特征、评分和划分文件可运行 "
                "examples/run_experiments.py 导出；见用户指南。"
            )
