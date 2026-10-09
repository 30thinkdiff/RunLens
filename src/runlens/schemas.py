"""Small shared data structures, independent of Streamlit."""

from dataclasses import dataclass, field
from decimal import Decimal
from numbers import Real

import numpy as np
import pandas as pd

TIME_SCALES = {
    "s": Decimal("1"),
    "ms": Decimal("0.001"),
    "us": Decimal("0.000001"),
    "ns": Decimal("0.000000001"),
}


def _finite_number(value, label: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{label}必须为有限数值，不能为布尔值或文本。")
    try:
        normalized = float(value)
    except OverflowError as exc:
        raise ValueError(f"{label}超出支持的数值范围。") from exc
    if not np.isfinite(normalized):
        raise ValueError(f"{label}必须为有限数值。")
    return normalized


def _boolean(value, label: str) -> bool:
    if not isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{label}必须为布尔值。")
    return bool(value)


@dataclass(frozen=True)
class ImportConfig:
    timestamp_column: str
    channel_columns: tuple[str, ...]
    time_unit: str = "s"

    def __post_init__(self) -> None:
        if not isinstance(self.time_unit, str) or self.time_unit not in TIME_SCALES:
            raise ValueError("时间单位必须为 s、ms、us 或 ns。")
        if (
            not isinstance(self.timestamp_column, str)
            or not self.timestamp_column.strip()
        ):
            raise ValueError("时间列名必须为非空文本。")
        if not isinstance(self.channel_columns, (tuple, list)) or any(
            not isinstance(column, str) or not column.strip()
            for column in self.channel_columns
        ):
            raise ValueError("通道必须为非空文本列名组成的 list 或 tuple。")
        object.__setattr__(self, "channel_columns", tuple(self.channel_columns))
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
    provenance: dict = field(default_factory=dict)


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
        tolerance = _finite_number(self.sampling_rtol, "采样间隔相对容差")
        if not 0 <= tolerance <= 0.05:
            raise ValueError("采样间隔相对容差必须在 0 到 0.05 之间。")
        object.__setattr__(self, "sampling_rtol", tolerance)
        object.__setattr__(
            self, "remove_mean", _boolean(self.remove_mean, "去均值开关")
        )
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
        if not isinstance(self.spectral, SpectralConfig):
            raise ValueError("频谱配置必须为 SpectralConfig。")
        object.__setattr__(
            self, "include_partial", _boolean(self.include_partial, "尾窗开关")
        )
        object.__setattr__(
            self, "include_spectral", _boolean(self.include_spectral, "频域开关")
        )
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
    provenance: dict = field(default_factory=dict)


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
        if not isinstance(self.method, str) or self.method not in (
            "mad",
            "isolation_forest",
        ):
            raise ValueError("检测方法必须为 mad 或 isolation_forest。")
        for field_name in ("fit_range", "detect_range"):
            bounds = getattr(self, field_name)
            if (
                not isinstance(bounds, (list, tuple))
                or len(bounds) != 2
                or any(isinstance(v, bool) or not isinstance(v, int) for v in bounds)
                or not 0 <= bounds[0] <= bounds[1]
            ):
                raise ValueError(
                    "参考/检测区间必须为非负整数样本行，且起点不晚于终点。"
                )
            object.__setattr__(self, field_name, tuple(bounds))
        if max(self.fit_range[0], self.detect_range[0]) <= min(
            self.fit_range[1], self.detect_range[1]
        ):
            raise ValueError("参考区间与检测区间不能重叠，避免拟合与检测数据泄漏。")
        threshold = _finite_number(self.threshold, "MAD 阈值")
        scale_floor = _finite_number(self.scale_floor, "最小鲁棒尺度")
        gap_factor = _finite_number(self.gap_factor, "间隔阈值倍数")
        if threshold <= 0:
            raise ValueError("MAD 阈值必须为正有限数。")
        if scale_floor < 0:
            raise ValueError("最小鲁棒尺度必须为非负有限数。")
        object.__setattr__(self, "threshold", threshold)
        object.__setattr__(self, "scale_floor", scale_floor)
        object.__setattr__(self, "gap_factor", gap_factor)
        if not (
            isinstance(self.contamination, str) and self.contamination == "auto"
        ) and (not 0 < _finite_number(self.contamination, "IF contamination") <= 0.5):
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
        if gap_factor <= 1:
            raise ValueError("区间合并的间隔倍数必须为大于 1 的有限数。")


@dataclass(frozen=True)
class DetectionResult:
    scores: pd.DataFrame
    candidates: pd.DataFrame
    baselines: pd.DataFrame
    config: DetectionConfig
    metadata: dict
