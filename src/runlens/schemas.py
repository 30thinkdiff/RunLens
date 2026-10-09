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
