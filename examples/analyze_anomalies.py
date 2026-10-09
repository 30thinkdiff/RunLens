"""Reproduce candidate detection on real robot measurements and an injected copy."""

import argparse
import json
from dataclasses import replace
from importlib.metadata import version
from pathlib import Path

from runlens.anomaly import candidates_csv, detect_anomalies, detection_json, scores_csv
from runlens.io import prepare_dataset
from runlens.robot_example import MEASUREMENTS, prepare_robot_example
from runlens.schemas import DetectionConfig


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=root / "tests" / "fixtures" / "robot_execution_failures" / "lp1.data",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("examples/generated/phase3")
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    names = ["real_robot_lp1.csv", "injected_robot_lp1.csv", "summary.json"]
    for variant in ("original", "injected"):
        for method in ("mad", "isolation_forest"):
            names.extend(
                f"{variant}_{method}_{kind}.{extension}"
                for kind, extension in (
                    ("candidates", "csv"),
                    ("scores", "csv"),
                    ("config", "json"),
                )
            )
    if not args.overwrite and any((args.output / name).exists() for name in names):
        parser.error("输出文件已存在；请指定新 --output 或明确使用 --overwrite。")
    dataset, provenance = prepare_robot_example(args.input)
    injected = dataset.raw.copy(deep=True)
    injection_row = 150  # The first held-out sample, outside all reference trials.
    injected.loc[injection_row, list(MEASUREMENTS)] = 10000
    injected_dataset = prepare_dataset(
        injected, dataset.config, "Real UCI LP1 background + explicit injected spike"
    )
    summary = {
        "provenance": provenance,
        "versions": {
            p: version(p)
            for p in ("runlens", "numpy", "pandas", "scipy", "scikit-learn")
        },
        "injection": {
            "row": injection_row,
            "channels": list(MEASUREMENTS),
            "replacement_value": 10000,
        },
        "results": {},
    }
    exports = {
        "real_robot_lp1.csv": dataset.raw.to_csv(index=False).encode("utf-8"),
        "injected_robot_lp1.csv": injected.to_csv(index=False).encode("utf-8"),
    }
    for variant, target in (("original", dataset), ("injected", injected_dataset)):
        for method in ("mad", "isolation_forest"):
            config = DetectionConfig(
                method=method,
                fit_range=tuple(provenance["fit_range"]),
                detect_range=tuple(provenance["detect_range"]),
                scale_floor=1.0,
                random_state=42,
            )
            result = detect_anomalies(target, config)
            result = replace(
                result,
                metadata={
                    **result.metadata,
                    "data_provenance": provenance,
                    "modified_measurements": variant == "injected",
                    "explicit_perturbation": summary["injection"]
                    if variant == "injected"
                    else None,
                },
            )
            key = f"{variant}_{method}"
            summary["results"][key] = {
                "candidate_point_records": result.metadata["candidate_points"],
                "candidate_intervals": len(result.candidates),
                "score_status_counts": result.metadata["status_counts"],
                "analysis_elapsed_s": result.metadata["analysis_elapsed_s"],
                "at_injection_row": result.scores.loc[
                    result.scores.row == injection_row,
                    ["channel", "score", "is_candidate"],
                ].to_dict(orient="records"),
            }
            exports[f"{key}_candidates.csv"] = candidates_csv(result)
            exports[f"{key}_scores.csv"] = scores_csv(result)
            exports[f"{key}_config.json"] = detection_json(result)
    exports["summary.json"] = (
        json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    ).encode("utf-8")
    args.output.mkdir(parents=True, exist_ok=True)
    for name, payload in exports.items():
        (args.output / name).write_bytes(payload)
    print(exports["summary.json"].decode("utf-8"))


if __name__ == "__main__":
    main()
