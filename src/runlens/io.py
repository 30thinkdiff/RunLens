"""Strict UTF-8 CSV input and precise, explicitly configured timestamps."""

import csv
from decimal import Decimal, DecimalException, InvalidOperation, Underflow, localcontext
from io import StringIO
from pathlib import Path
from typing import BinaryIO

import numpy as np
import pandas as pd

from runlens.schemas import TIME_SCALES, Dataset, ImportConfig

MISSING_TOKENS = frozenset({"", "nan", "na", "n/a", "null", "none"})
MAX_BYTES = 20 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 64


class DataValidationError(ValueError):
    """An actionable input error, suitable for display to a user."""


def read_csv(
    source: bytes | str | Path | BinaryIO, *, max_bytes: int = MAX_BYTES
) -> pd.DataFrame:
    """Read strings without numeric inference; reject ragged or ambiguous CSVs.

    Paths refer to local files. Binary streams are read from their current position.
    Blank physical lines are ignored by CSV parsing; empty fields remain in the table.
    """
    try:
        if isinstance(source, (str, Path)):
            path = Path(source)
            if path.stat().st_size > max_bytes:
                raise DataValidationError("CSV 超过文件大小上限（20 MiB）。")
            payload = path.read_bytes()
        elif isinstance(source, bytes):
            payload = source
        else:
            payload = source.read(max_bytes + 1)
    except OSError as exc:
        raise DataValidationError(f"无法读取文件：{exc}") from exc
    if len(payload) > max_bytes:
        raise DataValidationError("CSV 超过文件大小上限（20 MiB）。")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DataValidationError(
            "CSV 需要 UTF-8 编码（可带 BOM）。请转换编码后再上传。"
        ) from exc
    try:
        reader = csv.reader(StringIO(text, newline=""), strict=True)
        header = next(reader, None)
        if header is None:
            raise DataValidationError("CSV 文件为空。")
        columns = [field.strip() for field in header]
        if not all(columns) or len(set(columns)) != len(columns):
            raise DataValidationError("CSV 表头不能包含空列名或重复列名。")
        if len(columns) > MAX_COLUMNS:
            raise DataValidationError(f"CSV 最多支持 {MAX_COLUMNS} 列。")
        rows = []
        for row in reader:
            if not row:  # blank physical line, not a row of empty fields
                continue
            if len(row) != len(columns):
                raise DataValidationError(
                    f"CSV 第 {reader.line_num} 行的字段数与表头不一致。"
                )
            rows.append(row)
            if len(rows) > MAX_ROWS:
                raise DataValidationError(f"CSV 最多支持 {MAX_ROWS:,} 个样本行。")
    except csv.Error as exc:
        raise DataValidationError(f"CSV 格式错误：{exc}") from exc
    if not rows:
        raise DataValidationError("CSV 只有表头，没有数据行。")
    return pd.DataFrame(rows, columns=columns)


def numeric_values(series: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Classify missing, infinite and non-numeric channel values separately."""
    tokens = series.astype(str).str.strip()
    missing = tokens.str.lower().isin(MISSING_TOKENS).to_numpy()
    values = pd.to_numeric(tokens, errors="coerce").to_numpy(dtype=float)
    status = np.full(len(series), "valid", dtype=object)
    status[missing] = "missing"
    status[np.isinf(values)] = "infinite"
    status[np.isnan(values) & ~missing] = "non_numeric"
    return values, status


def prepare_dataset(
    frame: pd.DataFrame, config: ImportConfig, source_name: str = "CSV"
) -> Dataset:
    """Retain rows and fields; never sort, interpolate or guess time units."""
    if frame.empty:
        raise DataValidationError("没有可分析的数据行。")
    required = [config.timestamp_column, *config.channel_columns]
    absent = [column for column in required if column not in frame.columns]
    if absent:
        raise DataValidationError(f"不存在的列：{', '.join(absent)}")
    if not frame.columns.is_unique:
        raise DataValidationError("数据列名不能重复。")
    raw = frame.copy(deep=True).reset_index(drop=True)
    values: list[Decimal | None] = []
    statuses = []
    for item in raw[config.timestamp_column]:
        token = str(item).strip()
        if token.lower() in MISSING_TOKENS:
            values.append(None)
            statuses.append("missing")
            continue
        try:
            if len(token) > 80:
                raise DataValidationError("时间戳长度超过支持范围。")
            value = Decimal(token)
        except InvalidOperation:
            values.append(None)
            statuses.append("non_numeric")
            continue
        if not value.is_finite():
            values.append(None)
            statuses.append("infinite")
            continue
        if isinstance(item, (float, np.floating)) and abs(item) > 2**53:
            raise DataValidationError(
                "大绝对时间戳已经是浮点数，可能失去精度；"
                "请从原始 CSV 字符串或整数导入。"
            )
        values.append(value)
        statuses.append("valid")
    origin_row = next((i for i, value in enumerate(values) if value is not None), None)
    if origin_row is None:
        raise DataValidationError("时间戳全部无效；请选择数值时间列并指定单位。")
    origin = values[origin_row]
    scale = TIME_SCALES[config.time_unit]
    try:
        with localcontext() as context:
            context.prec = 90
            context.traps[Underflow] = True
            time_s = np.array(
                [
                    float((value - origin) * scale) if value is not None else np.nan
                    for value in values
                ]
            )
            intervals = np.full(len(values), np.nan)
            for i in range(1, len(values)):
                if values[i] is not None and values[i - 1] is not None:
                    difference = (values[i] - values[i - 1]) * scale
                    intervals[i] = float(difference)
                    if difference != 0 and intervals[i] == 0:
                        raise DataValidationError("采样间隔小于可表示的数值范围。")
    except (DecimalException, OverflowError) as exc:
        raise DataValidationError("时间范围超出可分析的数值范围。") from exc
    if np.isinf(time_s).any() or np.isinf(intervals).any():
        raise DataValidationError("时间范围超出可分析的数值范围。")
    signals = pd.DataFrame(
        {column: numeric_values(raw[column])[0] for column in config.channel_columns}
    )
    return Dataset(
        raw,
        signals,
        time_s,
        intervals,
        np.array(statuses),
        tuple(values),
        str(raw.iloc[origin_row][config.timestamp_column]),
        config,
        source_name,
    )
