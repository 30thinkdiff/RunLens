"""Reproducible synthetic IMU examples; these are not real robot recordings."""

import numpy as np
import pandas as pd

from runlens.schemas import DemoData


def generate_demo(
    *,
    seed: int = 42,
    sample_count: int = 2000,
    sample_rate: float = 100.0,
    vibration: bool = False,
) -> DemoData:
    """Create periodic signals, noise, spikes and explicit quality defects."""
    if not isinstance(sample_count, int) or not 100 <= sample_count <= 100_000:
        raise ValueError("演示样本数必须为 100 到 100000 的整数。")
    if not np.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError("演示采样频率必须为正有限数。")
    rng = np.random.default_rng(seed)
    base_t = np.arange(sample_count) / sample_rate
    time = base_t.copy()
    gap_row, duplicate_row, reverse_row = [
        int(sample_count * fraction) for fraction in (0.35, 0.65, 0.75)
    ]
    time[gap_row:] += 10 / sample_rate
    time[duplicate_row] = time[duplicate_row - 1]
    time[reverse_row] = time[reverse_row - 1] - 0.5 / sample_rate
    channels = {
        "accel_x": np.sin(2 * np.pi * 5 * base_t),
        "accel_y": 0.5 * np.cos(2 * np.pi * 3 * base_t),
        "accel_z": 9.81 + 0.1 * np.sin(2 * np.pi * 2 * base_t),
        "gyro_x": 0.2 * np.sin(2 * np.pi * 4 * base_t),
        "gyro_y": 0.15 * np.cos(2 * np.pi * 4 * base_t),
        "gyro_z": 0.1 * np.sin(2 * np.pi * 1 * base_t),
    }
    for channel in channels:
        channels[channel] = channels[channel] + rng.normal(0, 0.03, sample_count)
    labels = []

    def label(kind, start, end, channel):
        labels.append(
            {
                "kind": kind,
                "row_start": start,
                "row_end": end,
                "start_s": float(time[start]),
                "end_s": float(time[end]),
                "channel": channel,
            }
        )

    for row in (int(sample_count * 0.2), int(sample_count * 0.5)):
        channels["accel_x"][row] += 8
        label("spike", row, row, "accel_x")
    label("large_interval", gap_row - 1, gap_row, "timestamp")
    label("duplicate_timestamp", duplicate_row, duplicate_row, "timestamp")
    label("reverse_timestamp", reverse_row - 1, reverse_row, "timestamp")
    missing_row = int(sample_count * 0.85)
    channels["accel_z"][missing_row] = np.nan
    label("missing_value", missing_row, missing_row, "accel_z")
    if vibration:
        start, stop = int(sample_count * 0.7), int(sample_count * 0.8)
        channels["gyro_x"][start:stop] += 0.8 * np.sin(
            2 * np.pi * 20 * base_t[start:stop]
        )
        label("vibration_change", start, stop - 1, "gyro_x")
    data = pd.DataFrame({"timestamp": time, **channels})
    metadata = {
        "source": "Synthetic Data",
        "seed": seed,
        "sample_count": sample_count,
        "nominal_sample_rate_hz": sample_rate,
        "timestamp_unit": "s",
        "noise_std": 0.03,
        "vibration": vibration,
        "units": {"accel": "m/s^2", "gyro": "rad/s"},
        "label_unit": "original sample rows (zero-based, inclusive)",
        "note": "Injection reference labels; not hardware fault labels.",
    }
    return DemoData(data, pd.DataFrame(labels), metadata)
