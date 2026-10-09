"""Portable reports include evidence, bound previews and escape input text."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from runlens.anomaly import detect_anomalies
from runlens.features import extract_features
from runlens.io import prepare_dataset
from runlens.quality import check_quality
from runlens.reporting import analysis_report, html_bytes, json_bytes, markdown_bytes
from runlens.robot_example import prepare_robot_example
from runlens.schemas import DetectionConfig, WindowConfig

FIXTURE = Path(__file__).parent / "fixtures/robot_execution_failures/lp1.data"


def test_real_snapshot_has_parameters_and_no_unlabeled_metrics():
    dataset, meta = prepare_robot_example(FIXTURE)
    features = extract_features(
        dataset, WindowConfig(window_size=15, step_size=15, include_spectral=False)
    )
    detection = detect_anomalies(
        dataset,
        DetectionConfig(
            fit_range=tuple(meta["fit_range"]),
            detect_range=tuple(meta["detect_range"]),
            scale_floor=1,
        ),
    )
    snapshot = analysis_report(
        dataset, check_quality(dataset), features=features, detection=detection
    )
    exported = json.loads(json_bytes(snapshot))
    assert exported["evaluation"] is None
    assert exported["features"]["config"]["window_size"] == 15
    assert exported["features"]["record_count"] == 528
    assert len(exported["features"]["records_preview"]) == 20
    assert exported["detection"]["metadata"]["config"]["fit_range"] == [0, 149]
    assert exported["source"]["time_axis"].startswith("constructed")
    assert exported["analyzed_at_utc"].endswith("+00:00")
    assert exported["detection"]["candidate_record_unit"] == "row × channel"
    assert b"NaN" not in json_bytes(snapshot) and b"Infinity" not in json_bytes(
        snapshot
    )


def test_results_from_different_data_are_rejected():
    dataset, meta = prepare_robot_example(FIXTURE)
    detection = detect_anomalies(
        dataset,
        DetectionConfig(
            fit_range=tuple(meta["fit_range"]),
            detect_range=tuple(meta["detect_range"]),
            scale_floor=1,
        ),
    )
    changed = dataset.raw.copy()
    changed.loc[0, "Fx"] = 10000
    other = prepare_dataset(changed, dataset.config, "changed")
    with pytest.raises(ValueError, match="不一致"):
        analysis_report(other, check_quality(other), detection=detection)


def test_untrusted_text_cannot_be_html_or_markdown_code():
    hostile = "<script>alert(1)</script>|\n[click](https://evil.example)```"
    report = {"source": hostile, "records": [{"channel": hostile}], "limits": [hostile]}
    html = html_bytes(report).decode("utf-8")
    markdown = markdown_bytes(report).decode("utf-8")
    assert "<script>" not in html and "<script>" not in markdown
    assert "[click](https://evil.example)" not in markdown and "```" not in markdown
    assert "&lt;script&gt;" in html and "&#124;" in markdown
    assert json.loads(json_bytes(report))["source"] == hostile


def test_standard_json_nulls_missing_and_non_finite_values():
    result = json.loads(
        json_bytes({"items": [np.nan, np.inf, -np.inf, pd.NA, np.int64(4)]})
    )
    assert result == {"items": [None, None, None, None, 4]}


def test_missing_optional_steps_are_explicit():
    dataset, _ = prepare_robot_example(FIXTURE)
    snapshot = analysis_report(dataset, check_quality(dataset))
    assert snapshot["features"] is None and snapshot["detection"] is None
    assert "null" in markdown_bytes(snapshot).decode("utf-8")


def test_stale_real_quality_and_features_are_rejected():
    original, _ = prepare_robot_example(FIXTURE)
    quality = check_quality(original)
    features = extract_features(
        original, WindowConfig(window_size=15, include_spectral=False)
    )
    changed = original.raw.copy()
    changed.loc[0, "Fx"] = 10000
    current = prepare_dataset(changed, original.config, original.source_name)
    with pytest.raises(ValueError, match="质量.*不一致"):
        analysis_report(current, quality)
    with pytest.raises(ValueError, match="特征.*不一致"):
        analysis_report(current, check_quality(current), features=features)


def test_same_bytes_different_mapping_cannot_reuse_results():
    from runlens.schemas import ImportConfig

    dataset, meta = prepare_robot_example(FIXTURE)
    quality = check_quality(dataset)
    features = extract_features(
        dataset, WindowConfig(window_size=15, include_spectral=False)
    )
    detection = detect_anomalies(
        dataset,
        DetectionConfig(
            fit_range=tuple(meta["fit_range"]),
            detect_range=tuple(meta["detect_range"]),
            scale_floor=1,
        ),
    )
    remapped = prepare_dataset(
        dataset.raw,
        ImportConfig("synthetic_time_s", ("Fx", "Fy"), "ms"),
        dataset.source_name,
    )
    for old in ({"quality": quality}, {"features": features}, {"detection": detection}):
        with pytest.raises(ValueError, match="不一致"):
            analysis_report(
                remapped,
                old.get("quality", check_quality(remapped)),
                features=old.get("features"),
                detection=old.get("detection"),
            )


def test_empty_features_keep_provenance_and_cannot_be_reused_for_changed_data():
    dataset, _ = prepare_robot_example(FIXTURE)
    features = extract_features(dataset, WindowConfig(window_size=5000))
    snapshot = analysis_report(dataset, check_quality(dataset), features=features)
    assert snapshot["features"]["record_count"] == 0
    assert snapshot["features"]["provenance"]["data_sha256"]
    changed = dataset.raw.copy()
    changed.loc[0, "Fx"] = 10000
    other = prepare_dataset(changed, dataset.config)
    with pytest.raises(ValueError):
        analysis_report(other, check_quality(other), features=features)


def test_real_csv_bom_crlf_and_lf_have_one_portable_identity():
    from runlens.io import read_csv
    from runlens.provenance import dataset_identity

    dataset, _ = prepare_robot_example(FIXTURE)
    lf = dataset.raw.to_csv(index=False, lineterminator="\n").encode("utf-8")
    crlf = b"\xef\xbb\xbf" + lf.replace(b"\n", b"\r\n")
    first = prepare_dataset(read_csv(lf), dataset.config)
    second = prepare_dataset(read_csv(crlf), dataset.config)
    assert dataset_identity(first) == dataset_identity(second)
    assert dataset_identity(first)["fingerprint_format"].endswith("LF")


def test_manual_result_without_provenance_requests_recalculation():
    from dataclasses import replace

    dataset, _ = prepare_robot_example(FIXTURE)
    quality = check_quality(dataset)
    with pytest.raises(ValueError, match="重新计算"):
        analysis_report(dataset, replace(quality, provenance={}))
