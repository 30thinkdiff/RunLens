"""Reproduce Phase 2 known-signal checks and synthetic window exports."""

import argparse
import json
import platform
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from runlens.demo import generate_demo
from runlens.features import analyze_spectrum, extract_features, feature_csv
from runlens.io import prepare_dataset
from runlens.schemas import ImportConfig, WindowConfig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("examples/generated/phase2")
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    paths = {
        name: args.output / name
        for name in ("synthetic_features.csv", "sine_features.csv", "summary.json")
    }
    if not args.overwrite and any(path.exists() for path in paths.values()):
        parser.error("输出文件已存在；请使用新的 --output 或明确指定 --overwrite。")

    started = perf_counter()
    t = np.arange(1024) / 256
    sine = 2 * np.sin(2 * np.pi * 16 * t)
    known = prepare_dataset(
        pd.DataFrame({"timestamp": t, "sine": sine}),
        ImportConfig("timestamp", ("sine",)),
        "Synthetic Data · known sine",
    )
    known_features = extract_features(
        known, WindowConfig(window_size=1024, step_size=1024)
    )
    spectrum = analyze_spectrum(sine, t)
    demo = generate_demo()
    channels = tuple(column for column in demo.data if column != "timestamp")
    dataset = prepare_dataset(
        demo.data, ImportConfig("timestamp", channels), "Synthetic Data · seed 42"
    )
    result = extract_features(dataset, magnitude_axes=("accel_x", "accel_y", "accel_z"))
    elapsed = perf_counter() - started
    summary = {
        "source": "Synthetic Data",
        "seed": 42,
        "versions": {
            "python": platform.python_version(),
            **{
                package: version(package)
                for package in ("runlens", "numpy", "pandas", "scipy")
            },
        },
        "window_config": {
            "window_size": 256,
            "step_size": 128,
            "include_partial": False,
            "nan_policy": "omit",
            "sampling_rtol": 1e-6,
            "welch_nperseg": 256,
            "remove_mean": True,
            "magnitude_axes": ["accel_x", "accel_y", "accel_z"],
        },
        "known_sine": {
            "samples": 1024,
            "sample_rate_hz": 256,
            "frequency_hz": 16,
            "amplitude": 2,
            "rms": float(known_features.table.iloc[0]["rms"]),
            "fft_peak_amplitude": float(np.max(spectrum.amplitude)),
            **spectrum.features,
        },
        "synthetic": {
            "samples": len(dataset.signals),
            "input_channels": list(channels),
            "feature_records": len(result.table),
            "windows": int(result.table["row_start"].nunique()),
            "statuses": {
                str(key): int(value)
                for key, value in result.table["spectral_status"].value_counts().items()
            },
            "first_accel_x": result.table.iloc[0][
                ["row_start", "row_end", "rms", "dominant_frequency_hz"]
            ].to_dict(),
        },
        "analysis_elapsed_s": elapsed,
        "limitations": (
            "No anomaly detector, real-data accuracy or cross-platform claim."
        ),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    paths["synthetic_features.csv"].write_bytes(feature_csv(result))
    paths["sine_features.csv"].write_bytes(feature_csv(known_features))
    paths["summary.json"].write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
