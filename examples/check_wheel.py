"""Smoke-test core imports and real measurements directly from a built wheel."""

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "tests/fixtures/robot_execution_failures/lp1.data",
    )
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        parser.error("请指定已构建的 .whl 文件。")
    sys.path.insert(0, str(wheel))
    import runlens
    from runlens.anomaly import detect_anomalies
    from runlens.features import extract_features
    from runlens.quality import check_quality
    from runlens.reporting import analysis_report, json_bytes
    from runlens.robot_example import prepare_robot_example
    from runlens.schemas import DetectionConfig, WindowConfig

    if not str(runlens.__file__).startswith(str(wheel)):
        raise RuntimeError("模块没有从 wheel 导入，不能算独立构建验收。")
    dataset, provenance = prepare_robot_example(args.fixture)
    quality = check_quality(dataset)
    features = extract_features(
        dataset, WindowConfig(window_size=15, step_size=15, include_spectral=False)
    )
    detection = detect_anomalies(
        dataset,
        DetectionConfig(
            fit_range=tuple(provenance["fit_range"]),
            detect_range=tuple(provenance["detect_range"]),
            scale_floor=1,
        ),
    )
    report = analysis_report(dataset, quality, features=features, detection=detection)
    print(
        json_bytes(
            dict(
                version=runlens.__version__,
                imported_from=str(runlens.__file__),
                rows=len(dataset.raw),
                feature_records=len(features.table),
                score_records=len(detection.scores),
                report_schema_version=report["report_schema_version"],
                original_sha256=provenance["original_sha256"],
            )
        ).decode("utf-8")
    )


if __name__ == "__main__":
    main()
