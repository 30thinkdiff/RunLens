"""Frozen LP1 protocols: real trial labels and separately labeled perturbations."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from runlens.anomaly import detect_anomalies
from runlens.evaluation import evaluate_units, point_predictions
from runlens.features import analyze_spectrum, extract_features, time_domain_features
from runlens.io import prepare_dataset
from runlens.quality import check_quality
from runlens.reporting import environment_versions, runtime_environment
from runlens.robot_example import MEASUREMENTS, prepare_robot_example
from runlens.schemas import (
    DetectionConfig,
    DetectionResult,
    FeatureResult,
    WindowConfig,
)


@dataclass(frozen=True)
class ExperimentResult:
    report: dict
    metrics: pd.DataFrame
    predictions: pd.DataFrame
    detections: dict[str, DetectionResult]
    datasets: dict[str, pd.DataFrame]
    real_features: FeatureResult


def _reference_checks(original) -> tuple[dict, pd.DataFrame]:
    """Analytical formula checks plus declared time defects on actual measurements."""
    started = perf_counter()
    probe = original.raw.iloc[:15].copy().reset_index(drop=True)
    times = np.arange(15) * 0.021
    times[4] = times[3]
    times[8] = times[7] - 0.0105
    times[11:] += 0.21
    probe["synthetic_time_s"] = times
    quality = check_quality(
        prepare_dataset(
            probe, original.config, "LP1 measurements + injected time defects"
        )
    )
    expected = [
        ("duplicate_timestamp", 4, 4),
        ("reverse_timestamp", 7, 8),
        ("large_interval", 10, 11),
    ]
    actual = list(
        quality.issues[["kind", "row_start", "row_end"]].itertuples(
            index=False, name=None
        )
    )
    sine = 2 * np.sin(2 * np.pi * 8 * np.arange(64) / 64)
    sine_stats = time_domain_features(sine)
    constant_stats = time_domain_features(np.full(64, 3.0))
    spectrum = analyze_spectrum(sine, np.arange(64) / 64)
    feature_checks = [
        dict(case="constant RMS", actual=constant_stats["rms"], expected=3.0),
        dict(
            case="constant population std", actual=constant_stats["std"], expected=0.0
        ),
        dict(case="sine RMS", actual=sine_stats["rms"], expected=float(np.sqrt(2))),
        dict(
            case="sine population std",
            actual=sine_stats["std"],
            expected=float(np.sqrt(2)),
        ),
        dict(
            case="sine dominant Hz",
            actual=spectrum.features["dominant_frequency_hz"],
            expected=8.0,
        ),
        dict(
            case="sine FFT peak amplitude",
            actual=float(spectrum.amplitude[8]),
            expected=2.0,
        ),
        dict(
            case="sine PSD integral",
            actual=spectrum.features["psd_integral"],
            expected=2.0,
        ),
    ]
    for item in feature_checks:
        item["passed"] = bool(
            np.isclose(item["actual"], item["expected"], rtol=1e-10, atol=1e-10)
        )
    return dict(
        quality=dict(
            source="first real LP1 trial; only plotting timestamps modified",
            expected=[dict(kind=k, row_start=a, row_end=b) for k, a, b in expected],
            actual=quality.issues.to_dict(orient="records"),
            passed=set(actual) == set(expected),
            gap_factor=3.0,
        ),
        known_features=dict(
            source="Analytical Synthetic Data, not robot measurements",
            formula="64 samples; t=n/64 seconds; sine=2*sin(2*pi*8*n/64); constant=3",
            tolerance=dict(rtol=1e-10, atol=1e-10),
            results=feature_checks,
            passed=all(item["passed"] for item in feature_checks),
        ),
        elapsed_s=perf_counter() - started,
    ), probe


def run_robot_experiments(path: Path) -> ExperimentResult:
    """No test-label threshold search; all injected values are outside reference."""
    started = perf_counter()
    original, provenance = prepare_robot_example(path, fit_trials=10)
    if not set(original.raw.trial_label) <= {
        "normal",
        "collision",
        "fr_collision",
        "obstruction",
    }:
        raise ValueError("LP1 实验只接受已声明的四种完整事件标签。")
    reference = original.raw.iloc[:150]
    normal = original.raw.iloc[150:].loc[
        original.raw.iloc[150:].trial_label.eq("normal")
    ]
    background = pd.concat([reference, normal], ignore_index=True)
    if len(background) <= 300:
        raise ValueError("固定 LP1 注入协议需要至少 151 个留出正常样本。")
    injection_rows = [150, 225, 300]
    altered = background.copy(deep=True)
    original_values = altered.loc[injection_rows, list(MEASUREMENTS)].to_dict(
        orient="records"
    )
    altered.loc[injection_rows, list(MEASUREMENTS)] = 10000
    injected = prepare_dataset(
        altered, original.config, "UCI LP1 normal background + explicit perturbations"
    )
    prepared_elapsed = perf_counter() - started
    reference_checks, quality_probe = _reference_checks(original)
    feature_started = perf_counter()
    real_features = extract_features(
        original, WindowConfig(window_size=15, step_size=15, include_spectral=False)
    )
    feature_elapsed = perf_counter() - feature_started
    report = dict(
        report_type="fixed_robot_experiments",
        report_schema_version=1,
        analyzed_at_utc=datetime.now(UTC).isoformat(),
        versions=environment_versions(),
        runtime=runtime_environment(),
        data_provenance=provenance,
        protocol=dict(
            name="LP1 fixed protocols v1",
            fit_trials=10,
            fit_selection="first 10 normal trials in source order",
            method_selection="MAD 3.5 / floor 1 vs IF auto; frozen presets",
            channels=list(MEASUREMENTS),
            aggregation="any candidate channel → point; any candidate point → trial",
            eligibility=(
                "all channels scored per point; all original samples per trial"
            ),
            threshold_tuning="none; test labels do not select parameters or seeds",
            real_label_definition=(
                "whole trial: normal negative; "
                "collision/fr_collision/obstruction positive"
            ),
            injected_label_definition=(
                "point: replacement positive; non-replaced real background negative"
            ),
            metric_definitions=dict(
                precision="TP/(TP+FP)",
                recall="TP/(TP+FN)",
                f1="2TP/(2TP+FP+FN)",
                fpr="FP/(FP+TN)",
                undefined="null for a zero denominator",
            ),
        ),
        splits=dict(
            reference_trial_ids=provenance["reference_trial_ids"],
            real_trial_evaluation_ids=provenance["detection_trial_ids"],
            injection_background_trial_ids=normal.trial_id.unique().tolist(),
            real_fit_range=[0, 149],
            real_detect_range=[150, len(original.raw) - 1],
            injection_fit_range=[0, 149],
            injection_detect_range=[150, len(altered) - 1],
        ),
        perturbations=[
            dict(
                row=row,
                trial_id=int(altered.trial_id.iloc[row]),
                sample_index=int(altered.sample_index.iloc[row]),
                channels=list(MEASUREMENTS),
                replacement_value=10000,
                original_values=values,
            )
            for row, values in zip(injection_rows, original_values, strict=True)
        ],
        real_quality_summary=check_quality(original).summary,
        reference_checks=reference_checks,
        real_time_features=dict(
            config=asdict(real_features.config),
            interpretation=(
                "one trial per window, six channels; no physical frequency claims"
            ),
            record_count=len(real_features.table),
            analysis_elapsed_s=feature_elapsed,
            records_preview=real_features.table[
                ["row_start", "row_end", "channel", "rms", "std", "spectral_status"]
            ]
            .head(12)
            .to_dict(orient="records"),
        ),
        results=[],
        timing=dict(data_preparation_s=prepared_elapsed),
        limitations=[
            "LP1 force/torque data: constructed clock, unspecified units; not IMU.",
            "Single split: 10 reference trials, only 11 held-out normal trials.",
            "Trial labels evaluate whole-trial classification, not point faults.",
            "Strong artificial spikes: point metrics measure replacements only.",
            "Both tasks reuse held-out normal data; they are not independent datasets.",
            "Any-point aggregation amplifies false positives; no label-based tuning.",
            "Wall times: scoring/merging/hashes; excludes import/read/export.",
            "Candidates are not hardware diagnoses; Linux/macOS CI has not run.",
        ],
    )
    detections, metric_rows, predictions = {}, [], []
    for scenario, dataset, unit, truth in (
        ("real_trials", original, "trial", original.raw.trial_label.ne("normal")),
        ("injected_points", injected, "point", injected.raw.index.isin(injection_rows)),
    ):
        for method in ("mad", "isolation_forest"):
            config = DetectionConfig(
                method=method,
                fit_range=(0, 149),
                detect_range=(150, len(dataset.raw) - 1),
                scale_floor=1.0,
            )
            result = detect_anomalies(dataset, config)
            evaluation_started = perf_counter()
            units, metrics = evaluate_units(
                point_predictions(result), dataset.raw, unit=unit, positive=truth
            )
            evaluation_elapsed = perf_counter() - evaluation_started
            key = f"{scenario}_{method}"
            detections[key] = result
            records = dict(
                scenario=scenario,
                method=method,
                **metrics,
                analysis_elapsed_s=result.metadata["analysis_elapsed_s"],
                evaluation_elapsed_s=evaluation_elapsed,
            )
            metric_rows.append(records)
            predictions.append(
                units.assign(scenario=scenario, method=method, evaluation_unit=unit)
            )
            report["results"].append(
                dict(
                    **records,
                    detection_configuration=result.metadata,
                    actual_score_threshold=config.threshold if method == "mad" else 0.0,
                    baselines=result.baselines.to_dict(orient="records"),
                )
            )
    report["timing"]["experiment_elapsed_s"] = perf_counter() - started
    report["timing"]["boundary"] = (
        "read/prepare, reference checks, features, detections, evaluation/report; "
        "excludes rendering, writing and imports"
    )
    return ExperimentResult(
        report,
        pd.DataFrame(metric_rows),
        pd.concat(predictions, ignore_index=True),
        detections,
        {
            "real_robot_lp1": original.raw,
            "normal_robot_background": background,
            "injected_robot_background": altered,
            "quality_probe": quality_probe,
        },
        real_features,
    )
