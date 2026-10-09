# RunLens

A cross-platform toolkit for robot time-series data analysis, feature extraction,
and anomaly detection.

**Status: Phase 1 — CSV exploration and data-quality checks.** Version `0.0.2`
supports UTF-8 CSV upload, explicit timestamp/channel mapping, relative time in
s/ms/us/ns, interactive Plotly signals, and a quality report with row-level evidence.
The default example is clearly labeled **Synthetic Data** and needs no download.
Windowed features, FFT/Welch, statistical anomaly detection and report export
remain planned for later phases.

中文安装说明见 [用户指南](docs/USER_GUIDE.md)。需求见 [PRD.md](PRD.md)，
阶段进度和真实测试状态见 [TASKS.md](TASKS.md)。

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

The CI workflow runs Python 3.11 installation, tests and lint checks on
`windows-latest`, `ubuntu-latest`, and `macos-latest`. CI has not run until this
repository is pushed to GitHub and the workflow completes successfully.

## Try the workflow

1. Start the app. The default Synthetic Data contains periodic IMU signals, noise,
   two injected spikes, duplicate/reversed timestamps, a large interval and a missing value.
2. Inspect the overview and quality evidence; each rule reports its original sample
   rows, channel and threshold. Spikes are reference injections, not yet detected.
3. Switch to signal exploration, choose channels and a relative time range. Lines
   break at invalid samples and timing defects, with separate axes per channel.
4. Choose CSV upload to analyze your own file; select the timestamp column,
   channels and **explicit units**. EuRoC-style IMU headers are retained and can
   be mapped manually; numeric timestamps are required.

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

## Dependencies and layout

Runtime dependencies are Streamlit, pandas, NumPy and Plotly. Streamlit 1.65+
provides the accessible chart/table names, session-scoped caches and tested upload
interactions used here. `dev` adds pytest and ruff; the `analysis` extra adds
SciPy/scikit-learn for later phases (`pip install -e ".[analysis,dev]"`).
Dependency ranges allow updates;
they do not guarantee identical versions across machines. Later experiments must
record installed versions and seeds alongside results.

- `app.py`: Streamlit overview and signal explorer.
- `src/runlens/`: independently callable CSV, quality, demo and plotting modules.
- `tests/`: numerical, input-validation, plot and interactive upload tests.
- `examples/`: fixed-seed synthetic generator and actual example result.
- `docs/`: Chinese guide and implementation plan.
- `.github/workflows/tests.yml`: three-platform CI.

## Roadmap and limitations

1. Phase 1 (implemented locally): CSV mapping, signals, quality checks and labeled examples.
2. Phase 2: windowed time-domain features, FFT/Welch and feature export.
3. Phase 3: robust statistical rules, candidate intervals, then Isolation Forest.
4. Phase 4: reproducible comparisons and report export from actual runs.
5. Phase 5: full documentation, boundary tests and verified CI before v0.1.0.

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
There is no statistical spike detection, FFT, feature/report export or accuracy
measurement yet. Linux/macOS require actual CI results before verification claims.

## License

Original project code is licensed under [MIT](LICENSE). Dependencies retain their
own licenses. Public datasets are not bundled; their redistribution terms must be
checked before adding any data.
