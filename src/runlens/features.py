"""Sample-window statistics and spectra with explicit sampling assumptions."""

import json

import numpy as np
import pandas as pd
from scipy import fft, signal

from runlens.schemas import (
    Dataset,
    FeatureResult,
    SpectralConfig,
    SpectrumResult,
    WindowConfig,
)

TIME_FEATURES = (
    "mean",
    "std",
    "variance",
    "rms",
    "min",
    "max",
    "peak_to_peak",
    "median",
    "iqr",
)
SPECTRAL_FEATURES = (
    "sample_rate_hz",
    "dominant_frequency_hz",
    "dc_amplitude",
    "psd_integral",
    "spectral_energy",
    "spectral_centroid_hz",
    "fft_bin_width_hz",
    "psd_bin_width_hz",
    "spectrum_duration_s",
    "welch_nperseg",
    "welch_noverlap",
    "max_relative_jitter",
)
MAX_FEATURE_ROWS = 50_000
MAX_FEATURE_VALUES = 20_000_000
FEATURE_COLUMNS = [
    "source_name",
    "timestamp_column",
    "time_unit",
    "timestamp_origin",
    "input_channels",
    "channel",
    "magnitude_axes",
    "window_size",
    "step_size",
    "include_partial",
    "nan_policy",
    "ddof",
    "include_spectral",
    "sampling_rtol",
    "remove_mean",
    "welch_nperseg_requested",
    "fft_window",
    "welch_window",
    "row_start",
    "row_end",
    "start_s",
    "end_s",
    "is_complete",
    "sample_count",
    "valid_count",
    "invalid_count",
    "timestamp_valid_count",
    "time_increasing",
    "overflow_features",
    *TIME_FEATURES,
    "spectral_status",
    "spectral_message",
    *SPECTRAL_FEATURES,
]


class SpectralAnalysisError(ValueError):
    """A rejected spectrum with a machine-readable reason, not a fault diagnosis."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _real_vector(values) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1 or np.iscomplexobj(array):
        raise ValueError("输入必须为一维实数序列。")
    return array.astype(float)


def _quantile(ordered: np.ndarray, fraction: float) -> float:
    position = (len(ordered) - 1) * fraction
    lower = int(np.floor(position))
    upper = int(np.ceil(position))
    if ordered[lower] == ordered[upper]:
        return float(ordered[lower])
    weight = position - lower
    return float((1 - weight) * ordered[lower] + weight * ordered[upper])


def time_domain_features(values, *, nan_policy: str = "omit") -> dict:
    """Population statistics; omit excludes all non-finite values, with counts.

    IQR uses linear interpolation at the 25th/75th sample quantiles.
    Propagate leaves statistics undefined if any input is non-finite.
    """
    if nan_policy not in ("omit", "propagate"):
        raise ValueError("缺失值策略必须为 omit 或 propagate。")
    array = _real_vector(values)
    finite = array[np.isfinite(array)]
    result = {name: np.nan for name in TIME_FEATURES}
    result.update(
        sample_count=len(array),
        valid_count=len(finite),
        invalid_count=len(array) - len(finite),
        overflow_features="",
    )
    if not finite.size or (nan_policy == "propagate" and len(finite) != len(array)):
        return result
    magnitude = float(np.max(np.abs(finite))) or 1.0
    normalized = finite / magnitude
    ordered = np.sort(finite)
    std = float(np.std(normalized) * magnitude)
    with np.errstate(over="ignore", invalid="ignore"):
        calculated = {
            "mean": float(np.mean(normalized) * magnitude),
            "std": std,
            "variance": float(np.float64(std) * std),
            "rms": float(np.sqrt(np.mean(normalized**2)) * magnitude),
            "min": float(ordered[0]),
            "max": float(ordered[-1]),
            "peak_to_peak": float(ordered[-1] - ordered[0]),
            "median": _quantile(ordered, 0.5),
            "iqr": _quantile(ordered, 0.75) - _quantile(ordered, 0.25),
        }
    overflow = [name for name, value in calculated.items() if not np.isfinite(value)]
    result.update(
        {
            name: value if np.isfinite(value) else np.nan
            for name, value in calculated.items()
        }
    )
    result["overflow_features"] = ",".join(overflow)
    return result


def add_vector_magnitude(
    signals: pd.DataFrame, axes: tuple[str, str, str], name: str = "vector_magnitude"
) -> pd.DataFrame:
    """Append a three-axis norm, preserving every input channel and row."""
    if (
        len(axes) != 3
        or len(set(axes)) != 3
        or any(axis not in signals for axis in axes)
    ):
        raise ValueError("模长需要三个不同且已导入的通道。")
    if not name.strip() or name in signals:
        raise ValueError("模长通道名称不能为空或与已有通道重复。")
    vectors = signals[list(axes)].to_numpy(dtype=float)
    with np.errstate(over="ignore", invalid="ignore"):
        magnitude = np.hypot.reduce(vectors, axis=1)
    magnitude[~np.isfinite(vectors).all(axis=1) | ~np.isfinite(magnitude)] = np.nan
    augmented = signals.copy(deep=True)
    augmented[name] = magnitude
    return augmented


def _sampling_info(
    time_s: np.ndarray, config: SpectralConfig, interval_s=None
) -> tuple[float, float]:
    if len(time_s) < 2:
        raise SpectralAnalysisError("too_short", "频谱至少需要两个样本。")
    if not np.isfinite(time_s).all():
        raise SpectralAnalysisError(
            "invalid_timestamp", "所选范围含无效时间戳，不计算频谱。"
        )
    displayed_dt = np.diff(time_s)
    dt = displayed_dt if interval_s is None else _real_vector(interval_s)
    if len(dt) != len(time_s) - 1:
        raise ValueError("相邻间隔数量与时间序列不一致。")
    if not np.isfinite(dt).all():
        raise SpectralAnalysisError(
            "invalid_timestamp", "相邻时间戳关系无效，不计算频谱。"
        )
    if np.any(dt <= 0) or np.any(displayed_dt <= 0):
        raise SpectralAnalysisError(
            "non_increasing_time", "所选范围含重复或逆序时间戳，不计算频谱。"
        )
    if not np.allclose(dt, displayed_dt, rtol=max(config.sampling_rtol, 1e-12), atol=0):
        raise SpectralAnalysisError(
            "numeric_range", "相对时间与原始间隔的数值精度不足，不能确认频谱有效。"
        )
    median = float(np.median(dt))
    rate = 1 / median
    if not np.isfinite(rate) or rate <= 0:
        raise SpectralAnalysisError("numeric_range", "采样频率超出可表示范围。")
    deviation = float(np.max(np.abs(dt / median - 1)))
    if deviation > config.sampling_rtol:
        raise SpectralAnalysisError(
            "irregular_sampling",
            f"间隔最大相对偏差 {deviation:.6g} "
            f"超过容差 {config.sampling_rtol:g}；未插值或重采样。",
        )
    return rate, deviation


def analyze_spectrum(
    values, time_s, *, config: SpectralConfig | None = None, interval_s=None
) -> SpectrumResult:
    """One-sided rectangular FFT amplitude and periodic-Hann Welch density.

    PSD integral = sum(density) * bin width (signal units squared).
    Spectral energy estimate = PSD integral * N/fs (signal units squared * seconds).
    Both describe the processed signal; no mechanical energy is inferred.
    """
    config = config or SpectralConfig()
    array, times = _real_vector(values), _real_vector(time_s)
    if len(array) != len(times):
        raise ValueError("信号与时间样本数必须一致。")
    rate, jitter = _sampling_info(times, config, interval_s)
    if not np.isfinite(array).all():
        raise SpectralAnalysisError(
            "invalid_signal", "信号含 NaN/Inf；不会删除样本后强行做 FFT。"
        )
    magnitude = float(np.max(np.abs(array))) or 1.0
    processed = array / magnitude
    if config.remove_mean:
        processed = processed - np.mean(processed)
    n = len(array)
    frequency = fft.rfftfreq(n, d=1 / rate)
    amplitude = np.abs(fft.rfft(processed)) / n
    amplitude[1 : -1 if n % 2 == 0 else None] *= 2
    nperseg = min(config.welch_nperseg, n)
    overlap = nperseg // 2
    psd_frequency, normalized_psd = signal.welch(
        processed,
        fs=rate,
        window=signal.get_window("hann", nperseg, fftbins=True),
        nperseg=nperseg,
        noverlap=overlap,
        detrend=False,
        return_onesided=True,
        scaling="density",
        average="mean",
    )
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        amplitude = amplitude * magnitude
        density = (normalized_psd * magnitude) * magnitude
        bin_width = rate / nperseg
        power = float(np.sum(density) * bin_width)
        duration = n / rate
        energy = power * duration
    if (
        not np.isfinite(amplitude).all()
        or not np.isfinite(density).all()
        or not np.isfinite([power, duration, energy]).all()
        or (np.any(processed != 0) and power == 0)
    ):
        raise SpectralAnalysisError(
            "numeric_range", "频域数值超出可表示范围；不输出溢出或被舍入为零的功率。"
        )
    peak = int(np.argmax(amplitude[1:])) + 1
    threshold = 10 * np.finfo(float).eps * float(np.max(amplitude))
    dominant = float(frequency[peak]) if amplitude[peak] > threshold else None
    # Normalize weights before their sum to avoid avoidable overflow in the centroid.
    weight_scale = float(np.max(density)) or 1.0
    weights = density / weight_scale
    centroid = (
        float(np.sum(psd_frequency * weights) / np.sum(weights)) if power > 0 else None
    )
    features = {
        "sample_rate_hz": rate,
        "dominant_frequency_hz": dominant,
        "dc_amplitude": float(amplitude[0]),
        "psd_integral": power,
        "spectral_energy": energy,
        "spectral_centroid_hz": centroid,
        "fft_bin_width_hz": rate / n,
        "psd_bin_width_hz": bin_width,
        "spectrum_duration_s": duration,
        "welch_nperseg": nperseg,
        "welch_noverlap": overlap,
        "max_relative_jitter": jitter,
    }
    return SpectrumResult(frequency, amplitude, psd_frequency, density, features)


def extract_features(
    dataset: Dataset,
    config: WindowConfig | None = None,
    *,
    magnitude_axes: tuple[str, str, str] | None = None,
    magnitude_name: str = "vector_magnitude",
) -> FeatureResult:
    """Retain time-domain features even when a window's spectrum is rejected."""
    config = config or WindowConfig()
    signals = dataset.signals
    if magnitude_axes is not None:
        signals = add_vector_magnitude(signals, magnitude_axes, magnitude_name)
    n = len(signals)
    starts = list(range(0, n, config.step_size))
    if not config.include_partial:
        starts = [start for start in starts if start + config.window_size <= n]
    if len(starts) * len(signals.columns) > MAX_FEATURE_ROWS:
        raise ValueError("特征结果超过 50,000 条窗口×通道记录；请增大步长或减少通道。")
    work = sum(min(config.window_size, n - start) for start in starts)
    if work * len(signals.columns) > MAX_FEATURE_VALUES:
        raise ValueError(
            "窗口累计处理量超过 20,000,000 个信号值；请增大步长或缩短窗口。"
        )
    metadata = {
        "source_name": dataset.source_name,
        "timestamp_column": dataset.config.timestamp_column,
        "time_unit": dataset.config.time_unit,
        "timestamp_origin": dataset.timestamp_origin,
        "input_channels": json.dumps(
            dataset.config.channel_columns, ensure_ascii=False
        ),
        "window_size": config.window_size,
        "step_size": config.step_size,
        "include_partial": config.include_partial,
        "nan_policy": config.nan_policy,
        "ddof": 0,
        "include_spectral": config.include_spectral,
        "sampling_rtol": config.spectral.sampling_rtol,
        "remove_mean": config.spectral.remove_mean,
        "welch_nperseg_requested": config.spectral.welch_nperseg,
        "fft_window": "boxcar",
        "welch_window": "periodic_hann",
    }
    records = []
    for start in starts:
        stop = min(n, start + config.window_size)
        times = dataset.time_s[start:stop]
        intervals = dataset.interval_s[start + 1 : stop]
        temporal = {
            "row_start": start,
            "row_end": stop - 1,
            "start_s": float(times[0]),
            "end_s": float(times[-1]),
            "is_complete": stop - start == config.window_size,
            "timestamp_valid_count": int(np.count_nonzero(np.isfinite(times))),
            "time_increasing": bool(
                len(times) >= 2
                and np.isfinite(times).all()
                and np.isfinite(intervals).all()
                and np.all(intervals > 0)
            ),
        }
        for channel in signals:
            values = signals[channel].iloc[start:stop].to_numpy(dtype=float)
            row = {
                **metadata,
                **temporal,
                "channel": channel,
                "magnitude_axes": json.dumps(magnitude_axes, ensure_ascii=False)
                if magnitude_axes is not None and channel == magnitude_name
                else "",
                **time_domain_features(values, nan_policy=config.nan_policy),
                **{name: np.nan for name in SPECTRAL_FEATURES},
                "spectral_status": "disabled",
                "spectral_message": "未启用窗口频域特征",
            }
            if config.include_spectral:
                try:
                    spectrum = analyze_spectrum(
                        values, times, config=config.spectral, interval_s=intervals
                    )
                except SpectralAnalysisError as exc:
                    row.update(spectral_status=exc.code, spectral_message=str(exc))
                else:
                    row.update(
                        {
                            name: value if value is not None else np.nan
                            for name, value in spectrum.features.items()
                        }
                    )
                    row.update(
                        spectral_status="ok",
                        spectral_message="满足显式采样容差，无插值",
                    )
            records.append(row)
    return FeatureResult(
        pd.DataFrame(records, columns=FEATURE_COLUMNS),
        config,
        magnitude_axes,
        magnitude_name,
    )


def feature_csv(result: FeatureResult) -> bytes:
    """UTF-8 feature rows with their source, configuration and rejection reasons."""
    return result.table.to_csv(index=False, lineterminator="\n").encode("utf-8")
