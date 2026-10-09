"""Export fixed experiments on real robot trials and explicitly injected copies."""

import argparse
from pathlib import Path

from runlens.anomaly import candidates_csv, detection_json, scores_csv
from runlens.experiments import run_robot_experiments
from runlens.features import feature_csv
from runlens.reporting import html_bytes, json_bytes, markdown_bytes


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=root / "tests/fixtures/robot_execution_failures/lp1.data",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("examples/generated/phase4")
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    names = [
        "report.json",
        "report.md",
        "report.html",
        "metrics.csv",
        "predictions.csv",
        "splits.json",
        "real_robot_lp1.csv",
        "normal_robot_background.csv",
        "injected_robot_background.csv",
        "quality_probe.csv",
        "real_features.csv",
    ]
    for scenario in ("real_trials", "injected_points"):
        for method in ("mad", "isolation_forest"):
            for kind, extension in (
                ("candidates", "csv"),
                ("scores", "csv"),
                ("config", "json"),
            ):
                names.append(f"{scenario}_{method}_{kind}.{extension}")
    if not args.overwrite and any((args.output / name).exists() for name in names):
        parser.error("输出文件已存在；请选择新 --output 或明确使用 --overwrite。")
    result = run_robot_experiments(args.input)
    exports = {
        "report.json": json_bytes(result.report),
        "report.md": markdown_bytes(result.report),
        "report.html": html_bytes(result.report),
        "splits.json": json_bytes(result.report["splits"]),
        "real_features.csv": feature_csv(result.real_features),
        "metrics.csv": result.metrics.to_csv(index=False, lineterminator="\n").encode(
            "utf-8"
        ),
        "predictions.csv": result.predictions.to_csv(
            index=False, lineterminator="\n"
        ).encode("utf-8"),
    }
    exports.update(
        {
            f"{name}.csv": frame.to_csv(index=False, lineterminator="\n").encode(
                "utf-8"
            )
            for name, frame in result.datasets.items()
        }
    )
    for key, detection in result.detections.items():
        exports[f"{key}_scores.csv"] = scores_csv(detection)
        exports[f"{key}_candidates.csv"] = candidates_csv(detection)
        exports[f"{key}_config.json"] = detection_json(detection)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, payload in exports.items():
        # Exclusive creation also protects files introduced after preflight.
        with (args.output / name).open("wb" if args.overwrite else "xb") as destination:
            destination.write(payload)
    print(result.metrics.to_string(index=False))
    print(f"Reports: {args.output.resolve()}")


if __name__ == "__main__":
    main()
