# RunLens

A cross-platform toolkit for robot time-series data analysis, feature extraction,
and anomaly detection.

**Status: Phase 5 — validated core and v0.1.0 release.** Version `0.1.0`
supports UTF-8 CSV upload, explicit timestamp/channel mapping, relative time in
s/ms/us/ns, interactive Plotly signals, and a quality report with row-level evidence.
The default example is clearly labeled **Synthetic Data** and needs no download.
It also supports sample-based sliding windows, nine time-domain statistics,
optional three-axis magnitude, FFT/Welch spectra, and feature CSV export with
configuration and rejection reasons. MAD and Isolation Forest fit only on a
disjoint reference interval, produce candidate intervals, and export scores,
candidates and configuration. Reports export as JSON, Markdown and simple HTML.
Fixed experiments compare MAD and IF using real whole-trial labels and separately
labeled perturbations on held-out real normal measurements. Metrics include
precision, recall, F1, FPR, coverage, confusion counts and measured runtime.

中文安装说明见 [用户指南](docs/USER_GUIDE.md)。需求见 [PRD.md](PRD.md)，
阶段进度和真实测试状态见 [TASKS.md](TASKS.md)。

[Download v0.1.0](https://github.com/30thinkdiff/RunLens/releases/tag/v0.1.0) —
[release CI](https://github.com/30thinkdiff/RunLens/actions/runs/37955842348)
passed on Windows, Ubuntu and macOS, with 219 tests per platform and verified
real-experiment artifacts. The cleaned release tag points to verified commit `b54e129`.
Local task prompts are excluded from every published Git revision.
Real-data downloads and import settings: [REAL_DATA_DOWNLOADS.md](docs/REAL_DATA_DOWNLOADS.md).

## Requirements

- CPython **3.11**, pip and venv; a regular CPU is sufficient.
- No ROS, Docker, Conda, Node.js, GPU, or external service is required.
- Target platforms: Windows 10/11, Linux, macOS. Only actual local/CI results
  establish verification; configuring a CI matrix does not prove compatibility.

Use a Python 3.11 interpreter explicitly if your default Python has another version.
Official downloads: [Python.org](https://www.python.org/downloads/).

## Windows PowerShell

Run from the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m runlens --version
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If the Python launcher is unavailable, replace `py -3.11` with
`& "path/to/python311/python.exe"`. This workspace may also contain an ignored
local interpreter; see the Chinese user guide. No shell activation or execution
policy change is required. Open the local URL printed by Streamlit; Ctrl+C stops it.

## Linux / macOS

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m runlens --version
.venv/bin/python -m streamlit run app.py
```

## Verify

Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
```

Linux / macOS:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pip check
```

The CI workflow runs Python 3.11 installation, tests, lint and fixed real-data
experiments on `windows-latest`, `ubuntu-latest`, and `macos-latest`, preserving
JUnit and experiment artifacts. Actual platform and release evidence is recorded
in [VALIDATION.md](docs/VALIDATION.md). To reproduce verified direct dependency
versions, install with `pip install -c requirements-verified.txt -e ".[dev]"`.
This constraints file does not lock every transitive dependency.

## Try the workflow

1. Start the app. The default Synthetic Data contains periodic IMU signals, noise,
   two injected spikes, duplicate/reversed timestamps, a large interval and a missing value.
2. Inspect the overview and quality evidence; each rule reports its original sample
   rows, channel and threshold. Injected spikes have separate reference labels.
3. Switch to signal exploration, choose channels and a relative time range. Lines
   break at invalid samples and timing defects, with separate axes per channel.
4. Choose CSV upload to analyze your own file; select the timestamp column,
   channels and **explicit units**. EuRoC-style IMU headers are retained and can
   be mapped manually; numeric timestamps are required.
5. Open **特征分析** (feature analysis), configure the window/step in samples and
   submit the form. Inspect feature trends and download the complete feature CSV.
   Three-axis magnitude adds a channel while preserving the original axes.
6. Choose an original sample-row range for FFT/Welch. Irregular, duplicate,
   reversed or invalid timestamps are rejected explicitly without interpolation.
   A rejected spectrum does not discard the window's time-domain statistics.
7. Open **异常检测** (anomaly detection), choose MAD or Isolation Forest, and
   select disjoint reference/detection row ranges. Submit, inspect fitting and
   skipped-row evidence, select a candidate for local plots, and export CSV/JSON.
   Cyan highlights also appear in signal exploration after a successful run.
8. Open **实验与报告** (experiments and reports), generate a current-data snapshot,
   or run the explicitly separate bundled robot experiment. Uploaded CSVs have
   no supplied ground truth, so their snapshots do not contain accuracy metrics.

Generate local examples in Windows:

```powershell
.\.venv\Scripts\python.exe -X utf8 examples/generate_demo.py
```

Linux / macOS:

```bash
.venv/bin/python examples/generate_demo.py
```

Outputs are CSV, injection labels and generation metadata under `examples/generated/`.
The generator refuses existing output files by default. The same files can be
downloaded from the app. See [example instructions](examples/README.md) and the
[actual example result](examples/EXAMPLE_RESULT.md).

Reproduce Phase 2 computations with
`python -X utf8 examples/analyze_features.py` using your virtual environment's
interpreter. Outputs go to `examples/generated/phase2/`, with overwrite protection.
See the [actual Phase 2 results](examples/PHASE2_RESULT.md).

Reproduce Phase 3 on real robot measurements (no network required):

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe -X utf8 examples/analyze_anomalies.py
```

```bash
# Linux / macOS
.venv/bin/python examples/analyze_anomalies.py
```

The small attributed [UCI Robot Execution Failures LP1 fixture](tests/fixtures/robot_execution_failures/README.md)
has 88 real force/torque trials and is separately CC BY 4.0 licensed. Tests use
unchanged recordings and explicitly perturbed copies, alongside numerical unit
contracts. The file has no measured sample timestamps: the converted CSV's
`synthetic_time_s` is a declared plotting convention, not physical timing evidence.
Fit/detection splits preserve whole trial IDs. See [actual Phase 3 results](examples/PHASE3_RESULT.md).

## Dependencies and layout

Runtime dependencies are Streamlit, pandas, NumPy, SciPy, scikit-learn and Plotly. Streamlit 1.65+
provides the accessible chart/table names, session-scoped caches and tested upload
interactions used here. `dev` adds pytest and ruff; `analysis` remains an empty
compatibility extra because analysis dependencies are now required at runtime.
Dependency ranges allow updates;
they do not guarantee identical versions across machines. Later experiments must
record installed versions and seeds alongside results.

- `app.py`: Streamlit overview, signals, features, spectra and anomaly candidates.
- `src/runlens/`: independently callable CSV, quality, features, anomaly and plotting modules.
- `tests/`: numerical, input-validation, plot and interactive upload tests.
- `examples/`: fixed-seed synthetic generator and actual example result.
- `docs/`: Chinese guide and implementation plan.
- `.github/workflows/tests.yml`: three-platform CI.

## Roadmap and limitations

1. Phase 1 (implemented locally): CSV mapping, signals, quality checks and labeled examples.
2. Phase 2 (implemented locally): time-domain features, FFT/Welch and feature export.
3. Phase 3 (implemented locally): MAD, candidate intervals, Isolation Forest and real-data regressions.
4. Phase 4 (implemented locally): fixed real-data comparisons and actual report export.
5. Phase 5: boundary hardening, source consistency, course outlines and release validation.

Quality, feature and detection reports share a normalized UTF-8/LF table fingerprint
and import mapping. A report rejects stale results even when identical CSV bytes
are interpreted with different time units or channels. Recompute results after
changing data or mapping. Core upgrades also invalidate cached page results.
See the [course report outline](docs/COURSE_REPORT_OUTLINE.md),
[technical disclosure outline](docs/TECHNICAL_DISCLOSURE_OUTLINE.md),
[changelog](CHANGELOG.md) and [Phase 5 results](examples/PHASE5_RESULT.md).
The wheel contains the Python core; clone the full repository to run `app.py`
and access the bundled real-data fixture.

RunLens reports observable quality issues; these are not diagnoses of hardware
faults. Nominal sample rate is the reciprocal of the median positive interval
between adjacent valid rows. Large/short intervals use a configurable factor
(default 3); this baseline may be misleading when most intervals are corrupted or
the intended sample rate changes. No repairs or interpolation are applied.

Limits: CSV 20 MiB / 100,000 rows / 64 columns; plots 20,000 rows and 8 channels.
Oversized plot ranges are rejected without downsampling. The UI shows at most
50 issue markers, 500 evidence rows and 1,000 detail rows; core results retain all
issues. Invalid timestamps are reported but cannot be placed on the time axis.
Finite-only channel statistics use population standard deviation (`ddof=0`).
Features are sample-weighted; window size and step are sample counts, not seconds.
Results are limited to 50,000 window/channel records and 20 million cumulative
window values. Feature tables show 1,000 records, while CSV retains the full result.
The default sampling tolerance is `1e-6` relative to the median interval. A relaxed
tolerance is an explicit approximation, not a repair. FFT amplitude uses a
rectangular window; Welch uses periodic Hann with 50% overlap. Global mean removal
defaults on. PSD integral is `sum(PSD) * Δf` in signal units squared; spectral
energy estimate is that integral times `N/fs`, in signal units squared × seconds.
It is not mechanical energy. Definitions and resolution limits are in the guide.
MAD uses a reference median and `max(1.4826 * MAD, configured scale floor)`.
Zero MAD with no explicit floor disables that channel; skipped rows are not normal
decisions. IF scores multivariate raw channel vectors, not window features, and
uses only reference-fitted max-absolute scaling. Both are point detectors and may
flag legitimate changes in operating conditions. Candidate scores are not fault
probabilities, and score/count units differ across per-channel MAD and joint IF.
Scoring is limited to 500,000 records, with no imputation or clipping.
Report tables contain bounded previews (20 rows); full feature/score/candidate CSVs
are separate. Whole-trial and injected-point metrics must not be mixed. The fixed
LP1 split has only 11 held-out normal trials and can produce substantial false
positives; injected strong spikes do not establish natural fault accuracy.
Linux/macOS require actual CI results before verification claims.

Reproduce all four experiment categories (quality, analytical features, method
comparison, real-data analysis), with 23 attributed artifacts and overwrite protection:

```powershell
.\.venv\Scripts\python.exe -X utf8 examples/run_experiments.py
```

```bash
.venv/bin/python examples/run_experiments.py
```

Outputs: `examples/generated/phase4/`; use `--output` for a new directory.
The actual measurements, fixed splits, point/trial predictions and report results
are described in [PHASE4_RESULT.md](examples/PHASE4_RESULT.md).

## License

Original project code is licensed under [MIT](LICENSE). Dependencies retain their
own licenses. The small real robot test fixture is separately **CC BY 4.0**;
attribution and provenance are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Large public datasets and private user logs are not bundled.
