"""Small shared data structures, independent of Streamlit."""

from dataclasses import dataclass
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
