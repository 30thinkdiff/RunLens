"""Small shared data structures, independent of Streamlit."""

from dataclasses import dataclass, field
from decimal import Decimal

import numpy as np
import pandas as pd

TIME_SCALES = {
    "s": Decimal("1"),
    "ms": Decimal("0.001"),
    "us": Decimal("0.000001"),
    "ns": Decimal("0.000000001"),
}


@dataclass(frozen=True)
class ImportConfig:
    timestamp_column: str
    channel_columns: tuple[str, ...]
    time_unit: str = "s"

    def __post_init__(self) -> None:
        if self.time_unit not in TIME_SCALES:
            raise ValueError("时间单位必须为 s、ms、us 或 ns。")
        if not self.channel_columns or len(set(self.channel_columns)) != len(
            self.channel_columns
        ):
            raise ValueError("请选择至少一个通道，且通道不能重复。")
        if self.timestamp_column in self.channel_columns:
            raise ValueError("时间列不能同时作为信号通道。")


@dataclass(frozen=True)
class Dataset:
    raw: pd.DataFrame
    signals: pd.DataFrame
    time_s: np.ndarray
    interval_s: np.ndarray  # interval ending at each row; first row is NaN
    timestamp_status: np.ndarray
    timestamp_values: tuple[Decimal | None, ...]
    timestamp_origin: str
    config: ImportConfig
    source_name: str


@dataclass(frozen=True)
class QualityReport:
    summary: dict[str, int | float | None]
    channel_stats: pd.DataFrame
    issues: pd.DataFrame
    gap_factor: float


@dataclass(frozen=True)
class DemoData:
    data: pd.DataFrame
    labels: pd.DataFrame
    metadata: dict


@dataclass(frozen=True)
class SpectralConfig:
    sampling_rtol: float = 1e-6
    welch_nperseg: int = 256
    remove_mean: bool = True

    def __post_init__(self) -> None:
        if not np.isfinite(self.sampling_rtol) or not 0 <= self.sampling_rtol <= 0.05:
            raise ValueError("采样间隔相对容差必须在 0 到 0.05 之间。")
        if (
            isinstance(self.welch_nperseg, bool)
            or not isinstance(self.welch_nperseg, int)
            or self.welch_nperseg < 2
        ):
            raise ValueError("Welch 分段长度必须为至少 2 的整数。")


@dataclass(frozen=True)
class WindowConfig:
    window_size: int = 256
    step_size: int = 128
    include_partial: bool = False
    nan_policy: str = "omit"
    include_spectral: bool = True
    spectral: SpectralConfig = field(default_factory=SpectralConfig)

    def __post_init__(self) -> None:
        for value in (self.window_size, self.step_size):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("窗口长度和步长必须为正整数样本数。")
        if self.nan_policy not in ("omit", "propagate"):
            raise ValueError("缺失值策略必须为 omit 或 propagate。")


@dataclass(frozen=True)
class SpectrumResult:
    frequency_hz: np.ndarray
    amplitude: np.ndarray
    psd_frequency_hz: np.ndarray
    psd_density: np.ndarray
    features: dict[str, float | int | bool | None]


@dataclass(frozen=True)
class FeatureResult:
    table: pd.DataFrame
    config: WindowConfig
    magnitude_axes: tuple[str, str, str] | None
    magnitude_name: str


@dataclass(frozen=True)
class DetectionConfig:
    method: str = "mad"
    fit_range: tuple[int, int] = (0, 399)
    detect_range: tuple[int, int] = (400, 1999)
    threshold: float = 3.5
    scale_floor: float = 0.0
    contamination: float | str = "auto"
    n_estimators: int = 100
    max_samples: int = 256
    random_state: int = 42
    gap_factor: float = 3.0

    def __post_init__(self) -> None:
        if self.method not in ("mad", "isolation_forest"):
            raise ValueError("检测方法必须为 mad 或 isolation_forest。")
        for bounds in (self.fit_range, self.detect_range):
            if (
                len(bounds) != 2
                or any(isinstance(v, bool) or not isinstance(v, int) for v in bounds)
                or not 0 <= bounds[0] <= bounds[1]
            ):
                raise ValueError(
                    "参考/检测区间必须为非负整数样本行，且起点不晚于终点。"
                )
        if max(self.fit_range[0], self.detect_range[0]) <= min(
            self.fit_range[1], self.detect_range[1]
        ):
            raise ValueError("参考区间与检测区间不能重叠，避免拟合与检测数据泄漏。")
        if not np.isfinite(self.threshold) or self.threshold <= 0:
            raise ValueError("MAD 阈值必须为正有限数。")
        if not np.isfinite(self.scale_floor) or self.scale_floor < 0:
            raise ValueError("最小鲁棒尺度必须为非负有限数。")
        if self.contamination != "auto" and (
            not isinstance(self.contamination, (int, float))
            or not np.isfinite(self.contamination)
            or not 0 < self.contamination <= 0.5
        ):
            raise ValueError("IF contamination 必须为 auto 或 (0, 0.5] 内的数值。")
        for name, value, lo, hi in (
            ("树数量", self.n_estimators, 10, 300),
            ("每棵树样本上限", self.max_samples, 16, 1024),
            ("随机种子", self.random_state, 0, 2**32 - 1),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not lo <= value <= hi
            ):
                raise ValueError(f"{name}必须为 {lo} 到 {hi} 内的整数。")
        if not np.isfinite(self.gap_factor) or self.gap_factor <= 1:
            raise ValueError("区间合并的间隔倍数必须为大于 1 的有限数。")


@dataclass(frozen=True)
class DetectionResult:
    scores: pd.DataFrame
    candidates: pd.DataFrame
    baselines: pd.DataFrame
    config: DetectionConfig
    metadata: dict
