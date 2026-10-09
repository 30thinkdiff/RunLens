"""Small attributed robot-trial adapter; its plotting clock is constructed."""

import hashlib
from pathlib import Path

import pandas as pd

from runlens.io import prepare_dataset
from runlens.schemas import Dataset, ImportConfig

MEASUREMENTS = ("Fx", "Fy", "Fz", "Tx", "Ty", "Tz")
LP1_SHA256 = "e146de5aeaffd864f0e57ce2fe0b58e98582c3e808e6c0e8deb9b25a54ef0cb5"


def load_robot_trials(path: Path) -> pd.DataFrame:
    """Read original LP1 events without changing integer sensor measurements."""
    with Path(path).open("rb") as source:
        raw = source.read(100_001)
    if len(raw) > 100_000:
        raise ValueError("机器人小样本文件超出 100 KB 示例限制。")
    lines = [line.strip() for line in raw.decode("utf-8").splitlines() if line.strip()]
    if not lines or len(lines) % 16:
        raise ValueError("每条事件须为一个标签和 15 行六轴测量。")
    records = []
    for start in range(0, len(lines), 16):
        label = lines[start]
        if len(label.split()) != 1:
            raise ValueError("事件标签必须为单个文本字段。")
        for sample, line in enumerate(lines[start + 1 : start + 16]):
            fields = line.split()
            if len(fields) != 6:
                raise ValueError("每个测量样本必须包含六个整数。")
            try:
                values = [int(value) for value in fields]
            except ValueError as exc:
                raise ValueError("测量值必须为整数。") from exc
            records.append(
                dict(
                    trial_id=start // 16,
                    trial_label=label,
                    sample_index=sample,
                    **dict(zip(MEASUREMENTS, values, strict=True)),
                )
            )
    table = pd.DataFrame(records)
    table.attrs["original_sha256"] = hashlib.sha256(raw).hexdigest()
    return table


def prepare_robot_example(path: Path, *, fit_trials: int = 10) -> tuple[Dataset, dict]:
    """Split by complete trial IDs, keeping a declared clock and original labels."""
    original = load_robot_trials(path)
    normal_ids = original.loc[original.trial_label == "normal", "trial_id"].unique()
    if not isinstance(fit_trials, int) or not 2 <= fit_trials < len(normal_ids):
        raise ValueError("参考事件数须至少为 2，且保留至少一个正常事件用于检测。")
    fit_ids = normal_ids[:fit_trials].tolist()
    reference = original.loc[original.trial_id.isin(fit_ids)]
    detection = original.loc[~original.trial_id.isin(fit_ids)]
    combined = pd.concat([reference, detection], ignore_index=True)
    # 315 ms / 15 is an explicit convention, not an observed timestamp sequence.
    event_order = pd.factorize(combined.trial_id, sort=False)[0]
    combined.insert(0, "synthetic_time_s", event_order + combined.sample_index * 0.021)
    combined = combined[
        ["synthetic_time_s", *MEASUREMENTS, "trial_id", "trial_label", "sample_index"]
    ]
    dataset = prepare_dataset(
        combined,
        ImportConfig("synthetic_time_s", MEASUREMENTS, "s"),
        "Real robot measurements · UCI LP1 · constructed plotting clock",
    )
    metadata = {
        "dataset": "UCI Robot Execution Failures, LP1",
        "source_url": "https://archive.ics.uci.edu/dataset/138/robot+execution+failures",
        "doi": "10.24432/C5M89N",
        "license": "CC BY 4.0",
        "creators": "Luis Seabra Lopes and Luis M. Camarinha-Matos",
        "original_sha256": original.attrs["original_sha256"],
        "is_known_fixture": original.attrs["original_sha256"] == LP1_SHA256,
        "reference_trial_ids": fit_ids,
        "detection_trial_ids": detection.trial_id.unique().tolist(),
        "fit_range": [0, len(reference) - 1],
        "detect_range": [len(reference), len(combined) - 1],
        "sample_time_convention_s": 0.021,
        "trial_start_convention_s": 1.0,
        "time_axis": "constructed, not measured; no physical frequency/timing claims",
        "label_unit": "whole trial, not point anomaly labels",
        "measurement_units": (
            "not specified in source file; unchanged original integers"
        ),
    }
    return dataset, metadata
