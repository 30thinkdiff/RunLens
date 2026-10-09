"""CSV validation and precise, explicitly configured relative timestamps."""

from io import BytesIO

import numpy as np
import pandas as pd
import pytest

from runlens.io import DataValidationError, prepare_dataset, read_csv
from runlens.schemas import ImportConfig


@pytest.mark.parametrize(
    "payload", [b"", b" \r\n", b"t,x\n", b"t,x\n1,2,3", b"t,t\n1,2", b"t,\n1,2"]
)
def test_rejects_empty_or_malformed_csv(payload):
    with pytest.raises(DataValidationError):
        read_csv(payload)


def test_bom_crlf_euroc_and_path(tmp_path):
    payload = (
        "\ufeff#timestamp [ns],w_RS_S_x [rad s^-1]\r\n"
        "1400000000000000000,1\r\n1400000000000000001,2\r\n"
    ).encode()
    path = tmp_path / "中文 空格.csv"
    path.write_bytes(payload)
    frame = read_csv(path)
    dataset = prepare_dataset(
        frame, ImportConfig(frame.columns[0], (frame.columns[1],), "ns")
    )
    assert dataset.time_s[1] == pytest.approx(1e-9, abs=1e-18)
    assert frame.iloc[0, 0] == "1400000000000000000"
    assert read_csv(BytesIO(payload)).equals(frame)


@pytest.mark.parametrize(
    "unit,delta", [("s", 1), ("ms", 1000), ("us", 1000000), ("ns", 1000000000)]
)
def test_explicit_time_units(unit, delta):
    frame = pd.DataFrame({"t": [0, delta], "x": [1, 2]})
    data = prepare_dataset(frame, ImportConfig("t", ("x",), unit))
    np.testing.assert_allclose(data.time_s, [0, 1])


def test_fractional_absolute_timestamp_precision():
    frame = read_csv(b"t,x\n1400000000.000000001,1\n1400000000.000000002,2\n")
    data = prepare_dataset(frame, ImportConfig("t", ("x",), "s"))
    assert data.time_s[1] == pytest.approx(1e-9, abs=1e-18)


def test_invalid_values_are_preserved_and_classified():
    frame = read_csv(b"t,x\n,NaN\n10,inf\nwrong,text\n11,3\nInf,-Inf\n")
    data = prepare_dataset(frame, ImportConfig("t", ("x",)), "test.csv")
    assert data.timestamp_status.tolist() == [
        "missing",
        "valid",
        "non_numeric",
        "valid",
        "infinite",
    ]
    np.testing.assert_allclose(
        data.time_s, [np.nan, 0, np.nan, 1, np.nan], equal_nan=True
    )
    assert np.isnan(data.interval_s).all()  # never bridge over invalid timestamps
    assert data.raw.equals(frame)
    assert data.source_name == "test.csv"
    assert data.timestamp_origin == "10"


@pytest.mark.parametrize(
    "frame",
    [pd.DataFrame(), pd.DataFrame({"t": ["bad"], "x": [1]}), pd.DataFrame({"x": [1]})],
)
def test_invalid_mapping_or_all_invalid_times(frame):
    with pytest.raises(DataValidationError):
        prepare_dataset(frame, ImportConfig("t", ("x",)))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"time_unit": "auto"},
        {"channel_columns": ()},
        {"channel_columns": ("t",)},
        {"channel_columns": ("x", "x")},
    ],
)
def test_invalid_config(kwargs):
    params = {"timestamp_column": "t", "channel_columns": ("x",)} | kwargs
    with pytest.raises(ValueError):
        ImportConfig(**params)


def test_invalid_encoding_and_size_limit():
    with pytest.raises(DataValidationError):
        read_csv(b"t,x\n1,\xff")
    with pytest.raises(DataValidationError):
        read_csv(b"t,x\n1,2\n", max_bytes=3)


def test_whitespace_columns_normalized_without_losing_timestamp():
    assert read_csv(b" t , x \n1,2\n").columns.tolist() == ["t", "x"]


def test_preserves_empty_fields_and_quoted_line_breaks():
    frame = read_csv(b't,x,note\r\n0,1,"first\r\nsecond"\r\n,,\r\n')
    assert len(frame) == 2
    assert frame.iloc[1].tolist() == ["", "", ""]
    assert frame.iloc[0]["note"] == "first\r\nsecond"


@pytest.mark.parametrize("time", ["1e999999999", "1e-999999999", "1e400"])
def test_out_of_range_timestamps_are_validation_errors(time):
    frame = pd.DataFrame({"t": ["0", time], "x": [1, 2]})
    with pytest.raises(DataValidationError):
        prepare_dataset(frame, ImportConfig("t", ("x",)))


def test_rejects_preconverted_large_float_timestamp():
    frame = pd.DataFrame({"t": [1.4e18, 1.4e18 + 1e6], "x": [1, 2]})
    with pytest.raises(DataValidationError, match="浮点数"):
        prepare_dataset(frame, ImportConfig("t", ("x",), "ns"))


def test_rejects_missing_signal_column():
    with pytest.raises(DataValidationError, match="不存在的列"):
        prepare_dataset(pd.DataFrame({"t": [0], "x": [1]}), ImportConfig("t", ("y",)))
