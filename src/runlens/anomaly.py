"""Reference-fitted anomaly candidates, not calibrated hardware-fault diagnoses."""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from runlens.schemas import Dataset, DetectionConfig, DetectionResult

MAX_SCORE_ROWS = 500_000
SCORE_COLUMNS = [
    "channel",
    "row",
    "time_s",
    "value",
    "score",
    "threshold",
    "is_candidate",
    "status",
    "fit_count",
    "baseline_median",
    "baseline_mad",
    "robust_scale",
    "rule",
]
CANDIDATE_COLUMNS = [
    "channel",
    "row_start",
    "row_end",
    "start_s",
    "end_s",
    "candidate_count",
    "peak_row",
    "peak_score",
    "threshold",
    "rule",
]


def _mad_scores(dataset, config, rows):
    blocks, baselines = [], []
    fit = slice(config.fit_range[0], config.fit_range[1] + 1)
    fit_times = np.isfinite(dataset.time_s[fit])
    for channel in dataset.signals:
        values = dataset.signals[channel].to_numpy(dtype=float)
        training = values[fit]
        training = training[np.isfinite(training) & fit_times]
        baseline = dict(
            channel=channel,
            fit_count=len(training),
            median=np.nan,
            mad=np.nan,
            scale=np.nan,
            status="insufficient_fit",
        )
        score = np.full(len(rows), np.nan)
        if len(training) >= 5:
            norm = max(float(np.max(np.abs(training))), config.scale_floor) or 1.0
            normalized = training / norm
            center = float(np.median(normalized))
            mad = float(np.median(np.abs(normalized - center)))
            scale = max(1.4826 * mad, config.scale_floor / norm)
            with np.errstate(over="ignore", under="ignore", invalid="ignore"):
                raw_scale = scale * norm
                raw_mad = mad * norm
            status = (
                "zero_mad"
                if scale == 0
                else "numeric_range"
                if not np.isfinite([raw_scale, raw_mad]).all()
                else "ok"
            )
            baseline.update(
                median=center * norm, mad=raw_mad, scale=raw_scale, status=status
            )
            if status == "ok":
                with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                    score = np.abs(values[rows] / norm - center) / scale
        status = np.full(len(rows), baseline["status"], dtype=object)
        status[~np.isfinite(values[rows])] = "invalid_signal"
        status[~np.isfinite(dataset.time_s[rows])] = "invalid_timestamp"
        if baseline["status"] == "ok":
            status[(status == "ok") & ~np.isfinite(score)] = "numeric_range"
        score[status != "ok"] = np.nan
        blocks.append(
            pd.DataFrame(
                {
                    "channel": channel,
                    "row": rows,
                    "time_s": dataset.time_s[rows],
                    "value": values[rows],
                    "score": score,
                    "threshold": config.threshold,
                    "is_candidate": (status == "ok") & (score > config.threshold),
                    "status": status,
                    "fit_count": baseline["fit_count"],
                    "baseline_median": baseline["median"],
                    "baseline_mad": baseline["mad"],
                    "robust_scale": baseline["scale"],
                    "rule": "abs(x - reference median) / robust scale > threshold",
                },
                columns=SCORE_COLUMNS,
            )
        )
        baselines.append(baseline)
    return pd.concat(blocks, ignore_index=True), pd.DataFrame(baselines), {}


def _if_scores(dataset, config, rows):
    values = dataset.signals.to_numpy(dtype=float)
    fit = slice(config.fit_range[0], config.fit_range[1] + 1)
    training = values[fit]
    valid_fit = np.isfinite(training).all(axis=1) & np.isfinite(dataset.time_s[fit])
    training = training[valid_fit]
    status = np.full(len(rows), "insufficient_fit", dtype=object)
    score = np.full(len(rows), np.nan)
    baselines, details = [], {}
    if len(training) >= 16:
        constant = np.all(training == training[0], axis=0)
        maxima = np.max(np.abs(training), axis=0)
        divisors = np.where(maxima == 0, 1.0, maxima)
        baselines = [
            dict(
                channel=channel,
                fit_count=len(training),
                max_abs=float(scale),
                divisor=float(divisor),
                is_constant=bool(is_constant),
            )
            for channel, scale, divisor, is_constant in zip(
                dataset.signals, maxima, divisors, constant, strict=True
            )
        ]
        if constant.all():
            status[:] = "constant_baseline"
        else:
            model = IsolationForest(
                n_estimators=config.n_estimators,
                max_samples=min(config.max_samples, len(training)),
                contamination=config.contamination,
                random_state=config.random_state,
                n_jobs=1,
            )
            model.fit(training / divisors)
            with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                transformed = values[rows] / divisors
            finite = np.isfinite(transformed).all(axis=1) & (
                np.abs(transformed) <= np.finfo(np.float32).max
            ).all(axis=1)
            status[:] = "numeric_range"
            status[finite] = "ok"
            if finite.any():
                score[finite] = -model.decision_function(transformed[finite])
            details = {
                "if_offset": float(model.offset_),
                "if_max_samples_actual": int(model.max_samples_),
                "scaling": "per-channel max-absolute scaling fitted on reference only",
            }
    if not baselines:
        baselines = [
            dict(
                channel=channel,
                fit_count=len(training),
                max_abs=np.nan,
                divisor=np.nan,
                is_constant=None,
            )
            for channel in dataset.signals
        ]
    status[~np.isfinite(values[rows]).all(axis=1)] = "invalid_signal"
    status[~np.isfinite(dataset.time_s[rows])] = "invalid_timestamp"
    score[status != "ok"] = np.nan
    scores = pd.DataFrame(
        {
            "channel": "__multivariate__",
            "row": rows,
            "time_s": dataset.time_s[rows],
            "value": np.nan,
            "score": score,
            "threshold": 0.0,
            "is_candidate": (status == "ok") & (score > 0),
            "status": status,
            "fit_count": len(training),
            "baseline_median": np.nan,
            "baseline_mad": np.nan,
            "robust_scale": np.nan,
            "rule": "-IsolationForest.decision_function > 0 (not a fault probability)",
        },
        columns=SCORE_COLUMNS,
    )
    return scores, pd.DataFrame(baselines), details


def _candidate_intervals(dataset, scores, nominal, gap_factor):
    events = []
    for channel, block in scores.groupby("channel", sort=False):
        selected = block.loc[block.is_candidate]
        run = []

        def finish(run, channel):
            if not run:
                return
            peak = max(run, key=lambda item: item.score)
            first, last = run[0], run[-1]
            events.append(
                dict(
                    channel=channel,
                    row_start=int(first.row),
                    row_end=int(last.row),
                    start_s=float(first.time_s),
                    end_s=float(last.time_s),
                    candidate_count=len(run),
                    peak_row=int(peak.row),
                    peak_score=float(peak.score),
                    threshold=float(peak.threshold),
                    rule=peak.rule,
                )
            )

        for record in selected.itertuples(index=False):
            dt = dataset.interval_s[record.row]
            broken = run and (
                record.row != run[-1].row + 1
                or not np.isfinite(dt)
                or dt <= 0
                or (
                    nominal is not None
                    and (dt > nominal * gap_factor or dt < nominal / gap_factor)
                )
            )
            if broken:
                finish(run, channel)
                run = []
            run.append(record)
        finish(run, channel)
    return pd.DataFrame(events, columns=CANDIDATE_COLUMNS)


def detect_anomalies(dataset: Dataset, config: DetectionConfig) -> DetectionResult:
    """Fit exclusively on a disjoint reference range; score original detection rows."""
    started = perf_counter()
    n = len(dataset.signals)
    if config.fit_range[1] >= n or config.detect_range[1] >= n:
        raise ValueError("参考/检测区间超出数据样本行范围。")
    rows = np.arange(config.detect_range[0], config.detect_range[1] + 1)
    count = len(rows) * (len(dataset.signals.columns) if config.method == "mad" else 1)
    if count > MAX_SCORE_ROWS:
        raise ValueError("评分结果超过 500,000 条；请缩小检测范围或减少通道。")
    scorer = _mad_scores if config.method == "mad" else _if_scores
    scores, baselines, details = scorer(dataset, config, rows)
    fit_dt = dataset.interval_s[config.fit_range[0] + 1 : config.fit_range[1] + 1]
    positive = fit_dt[np.isfinite(fit_dt) & (fit_dt > 0)]
    nominal = float(np.median(positive)) if len(positive) else None
    candidates = _candidate_intervals(dataset, scores, nominal, config.gap_factor)
    provenance = dict(
        source_name=dataset.source_name,
        method=config.method,
        timestamp_column=dataset.config.timestamp_column,
        time_unit=dataset.config.time_unit,
        timestamp_origin=dataset.timestamp_origin,
        channels=json.dumps(dataset.config.channel_columns, ensure_ascii=False),
        fit_start=config.fit_range[0],
        fit_end=config.fit_range[1],
        detect_start=config.detect_range[0],
        detect_end=config.detect_range[1],
        mad_threshold=config.threshold,
        scale_floor=config.scale_floor,
        contamination=config.contamination,
        n_estimators=config.n_estimators,
        max_samples=config.max_samples,
        random_state=config.random_state,
        gap_factor=config.gap_factor,
    )
    for table in (scores, candidates):
        for name, value in provenance.items():
            table[name] = value
    metadata = dict(
        **provenance,
        config=asdict(config),
        **details,
        evaluation_unit="original sample rows",
        score_direction="higher means more anomalous; no calibrated probability",
        data_sha256=hashlib.sha256(
            dataset.raw.to_csv(index=False).encode("utf-8")
        ).hexdigest(),
        fingerprint_format="normalized raw-table CSV, UTF-8",
        versions={
            name: version(name)
            for name in ("runlens", "numpy", "pandas", "scikit-learn")
        },
        analyzed_at_utc=datetime.now(UTC).isoformat(),
        nominal_interval_s=nominal,
        score_records=len(scores),
        candidate_points=int(scores.is_candidate.sum()),
        candidate_intervals=len(candidates),
        status_counts={str(k): int(v) for k, v in scores.status.value_counts().items()},
        analysis_elapsed_s=perf_counter() - started,
        limitations=(
            "Reference data may contain anomalies; candidates are not fault diagnoses."
        ),
    )
    return DetectionResult(scores, candidates, baselines, config, metadata)


def candidates_csv(result: DetectionResult) -> bytes:
    return result.candidates.to_csv(index=False, lineterminator="\n").encode("utf-8")


def scores_csv(result: DetectionResult) -> bytes:
    return result.scores.to_csv(index=False, lineterminator="\n").encode("utf-8")


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def detection_json(result: DetectionResult) -> bytes:
    metadata = {
        **result.metadata,
        "baselines": result.baselines.to_dict(orient="records"),
    }
    return (
        json.dumps(_json_safe(metadata), ensure_ascii=False, allow_nan=False, indent=2)
        + "\n"
    ).encode("utf-8")
