"""Actionable input boundaries using real robot measurements as background."""

from io import StringIO
from pathlib import Path

import pandas as pd
import pytest

from runlens.io import DataValidationError, prepare_dataset, read_csv
from runlens.robot_example import prepare_robot_example
from runlens.schemas import DetectionConfig, ImportConfig, SpectralConfig, WindowConfig

FIXTURE = Path(__file__).parent / "fixtures/robot_execution_failures/lp1.data"


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ImportConfig("t", "Fx"),
        lambda: ImportConfig("t", ("Fx",), []),
        lambda: ImportConfig("t", (None,)),
        lambda: DetectionConfig(threshold="3.5"),
        lambda: DetectionConfig(threshold=True),
        lambda: DetectionConfig(fit_range=None),
        lambda: DetectionConfig(contamination=True),
        lambda: WindowConfig(spectral={}),
        lambda: WindowConfig(include_partial="False"),
        lambda: SpectralConfig(remove_mean="False"),
        lambda: SpectralConfig(sampling_rtol="0.01"),
        lambda: DetectionConfig(threshold=10**1000),
    ],
)
def test_bad_configuration_types_are_clear_value_errors(factory):
    with pytest.raises(ValueError):
        factory()


def test_channel_and_interval_lists_cannot_change_after_configuration():
    real, _ = prepare_robot_example(FIXTURE)
    channels = ["Fx", "Fy"]
    config = ImportConfig("synthetic_time_s", channels)
    channels.clear()
    dataset = prepare_dataset(real.raw, config)
    assert dataset.signals.columns.tolist() == ["Fx", "Fy"]
    assert hash(config)
    bounds = [0, 149]
    detection = DetectionConfig(fit_range=bounds)
    bounds[1] = 450
    assert detection.fit_range == (0, 149)


@pytest.mark.parametrize("limit", [0, True, "100", float("nan")])
def test_invalid_read_limit_rejected(limit):
    with pytest.raises(ValueError):
        read_csv(b"t,x\n0,1\n", max_bytes=limit)


def test_text_stream_reports_how_to_open_binary_input():
    with pytest.raises(DataValidationError, match="二进制"):
        read_csv(StringIO("t,x\n0,1\n"))


def test_real_csv_in_unicode_space_path_and_caps(tmp_path, monkeypatch):
    import runlens.io as io

    real, _ = prepare_robot_example(FIXTURE)
    folder = tmp_path / "真实 机器人"
    folder.mkdir()
    path = folder / "六轴 测量.csv"
    payload = real.raw.to_csv(index=False, lineterminator="\n").encode("utf-8")
    path.write_bytes(payload)
    parsed = read_csv(path)
    assert len(parsed) == 1320
    pd.testing.assert_frame_equal(
        prepare_dataset(parsed, real.config).signals, real.signals
    )
    with pytest.raises(DataValidationError):
        read_csv(path, max_bytes=100)
    monkeypatch.setattr(io, "MAX_ROWS", 20)
    with pytest.raises(DataValidationError, match="20"):
        read_csv(payload)
    monkeypatch.setattr(io, "MAX_COLUMNS", 2)
    with pytest.raises(DataValidationError, match="2 列"):
        read_csv(payload)


def test_file_reads_never_request_unlimited_bytes(tmp_path, monkeypatch):
    path = tmp_path / "growing.csv"
    path.write_bytes(b"t,x\n0,1\n")
    original_open = Path.open
    requests = []

    class GuardedFile:
        def __enter__(self):
            self.stream = original_open(path, "rb")
            return self

        def __exit__(self, *args):
            self.stream.close()

        def read(self, size=-1):
            requests.append(size)
            assert 0 < size <= 101, "file read exceeded the declared memory bound"
            return self.stream.read(size)

    monkeypatch.setattr(Path, "open", lambda self, *args, **kwargs: GuardedFile())
    assert len(read_csv(path, max_bytes=100)) == 1
    assert requests
