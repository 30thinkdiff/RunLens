"""Portable, bounded analysis snapshots and escaped standalone report exports."""

import hashlib
import html
import json
import platform
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version

import numpy as np
import pandas as pd

from runlens.schemas import Dataset, DetectionResult, FeatureResult, QualityReport

PREVIEW_ROWS = 20


def _safe(value):
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, np.generic):
        return _safe(value.item())
    if value is pd.NA or (isinstance(value, float) and not np.isfinite(value)):
        return None
    return value


def json_bytes(report: dict) -> bytes:
    return (
        json.dumps(_safe(report), ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    ).encode("utf-8")


def environment_versions() -> dict:
    return {
        name: version(name)
        for name in ("runlens", "numpy", "pandas", "scipy", "scikit-learn", "streamlit")
    }


def runtime_environment() -> dict:
    return dict(
        python=platform.python_version(),
        platform=platform.system(),
        machine=platform.machine(),
        timing_clock="time.perf_counter",
        detector_parallelism="Isolation Forest n_jobs=1",
    )


def analysis_report(
    dataset: Dataset,
    quality: QualityReport,
    *,
    features: FeatureResult | None = None,
    detection: DetectionResult | None = None,
    input_sha256: str | None = None,
) -> dict:
    """Include submitted results only; unlabeled datasets have no accuracy metrics."""
    fingerprint = hashlib.sha256(
        dataset.raw.to_csv(index=False).encode("utf-8")
    ).hexdigest()
    if detection is not None and detection.metadata["data_sha256"] != fingerprint:
        raise ValueError("检测结果与当前数据不一致，请重新检测后生成报告。")
    constructed = dataset.config.timestamp_column == "synthetic_time_s"
    report = dict(
        report_type="current_dataset_analysis",
        report_schema_version=1,
        analyzed_at_utc=datetime.now(UTC).isoformat(),
        versions=environment_versions(),
        runtime=runtime_environment(),
        source=dict(
            name=dataset.source_name,
            input_bytes_sha256=input_sha256,
            normalized_table_sha256=fingerprint,
            row_count=len(dataset.raw),
            time_axis="constructed plotting clock; not measured"
            if constructed
            else "user-mapped numeric timestamps; units explicitly supplied",
        ),
        sampling=dict(
            import_config=asdict(dataset.config),
            timestamp_origin=dataset.timestamp_origin,
            rate_interpretation="constructed clock only; no physical frequency claims"
            if constructed
            else "positive adjacent interval median estimate",
        ),
        quality=dict(
            summary=quality.summary,
            gap_factor=quality.gap_factor,
            rule="large dt > positive median × factor; short 0 < dt < median / factor",
            channel_stats=quality.channel_stats.to_dict(orient="records"),
            issue_count=len(quality.issues),
            preview_limit=PREVIEW_ROWS,
            issues_preview=quality.issues.head(PREVIEW_ROWS).to_dict(orient="records"),
        ),
        features=None,
        detection=None,
        evaluation=None,
        limitations=[
            "No anomaly truth supplied: precision, recall, F1 and FPR unavailable.",
            "Quality defects and candidates are observations, not hardware diagnoses.",
            "Bounded previews; download full feature/candidate/score CSV separately.",
            "No interpolation or resampling; spectra reject invalid sampling.",
        ],
    )
    if features is not None:
        report["features"] = dict(
            config=asdict(features.config),
            magnitude_axes=features.magnitude_axes,
            magnitude_name=features.magnitude_name,
            record_count=len(features.table),
            spectral_status_counts=features.table.spectral_status.value_counts().to_dict(),
            preview_limit=PREVIEW_ROWS,
            records_preview=features.table.head(PREVIEW_ROWS).to_dict(orient="records"),
        )
    if detection is not None:
        report["detection"] = dict(
            metadata=detection.metadata,
            baselines=detection.baselines.to_dict(orient="records"),
            preview_limit=PREVIEW_ROWS,
            candidate_preview=detection.candidates.iloc[:PREVIEW_ROWS, :10].to_dict(
                orient="records"
            ),
            candidate_record_unit="row × channel"
            if detection.config.method == "mad"
            else "joint row",
            actual_score_threshold=detection.config.threshold
            if detection.config.method == "mad"
            else 0.0,
        )
    if constructed:
        report["limitations"].append(
            "LP1 has no measured timestamps or stated force/torque units."
        )
    return _safe(report)


def _text(value) -> str:
    if value is None:
        return "null (undefined / unavailable)"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    return str(value)


def _markdown(value) -> str:
    # HTML entities prevent user-controlled Markdown links, fences and raw HTML.
    escaped = (
        html.escape(_text(value), quote=True).replace("\n", " ").replace("\r", " ")
    )
    for char in "\\`*_{}[]()#+.!|~":
        escaped = escaped.replace(char, f"&#{ord(char)};")
    return escaped


def _render(report: dict, *, markup: str) -> bytes:
    report = _safe(report)
    is_html = markup == "html"
    escape = (
        (lambda value: html.escape(_text(value), quote=True)) if is_html else _markdown
    )
    output = [
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        "<title>RunLens report</title><body><h1>RunLens report</h1>"
        if is_html
        else "# RunLens report\n"
    ]

    def emit(value, depth=2):
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, dict) or (isinstance(child, list) and child):
                    level = min(depth, 6)
                    output.append(
                        f"<h{level}>{escape(key)}</h{level}>"
                        if is_html
                        else f"\n{'#' * level} {escape(key)}\n"
                    )
                    emit(child, depth + 1)
                else:
                    content = f"{escape(key)}: {escape(child)}"
                    output.append(f"<p>{content}</p>" if is_html else f"\n{content}\n")
        elif isinstance(value, list) and all(isinstance(row, dict) for row in value):
            columns = list(dict.fromkeys(key for row in value for key in row))
            if is_html:
                output.append(
                    '<table border="1"><thead><tr>'
                    + "".join(f"<th>{escape(c)}</th>" for c in columns)
                    + "</tr></thead><tbody>"
                )
                for row in value:
                    output.append(
                        "<tr>"
                        + "".join(f"<td>{escape(row.get(c))}</td>" for c in columns)
                        + "</tr>"
                    )
                output.append("</tbody></table>")
            else:
                output.append("\n| " + " | ".join(escape(c) for c in columns) + " |")
                output.append("| " + " | ".join("---" for _ in columns) + " |")
                output.extend(
                    "| " + " | ".join(escape(row.get(c)) for c in columns) + " |"
                    for row in value
                )
                output.append("\n")
        elif isinstance(value, list):
            if is_html:
                output.append(
                    "<ul>" + "".join(f"<li>{escape(v)}</li>" for v in value) + "</ul>"
                )
            else:
                output.append("\n" + "\n".join(f"- {escape(v)}" for v in value) + "\n")
        else:
            output.append(
                f"<p>{escape(value)}</p>" if is_html else f"\n{escape(value)}\n"
            )

    emit(report)
    if is_html:
        output.append("</body></html>")
    return ("\n".join(output) + "\n").encode("utf-8")


def markdown_bytes(report: dict) -> bytes:
    return _render(report, markup="markdown")


def html_bytes(report: dict) -> bytes:
    return _render(report, markup="html")
