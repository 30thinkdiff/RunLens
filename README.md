# RunLens

A cross-platform toolkit for robot time-series data analysis, feature extraction,
and anomaly detection.

**Status: Phase 0 — project initialization.** Version `0.0.1` provides an installable
Python package, a version command, and a Streamlit startup page. CSV analysis,
synthetic examples, features, anomaly detection and reports are planned in later
phases; they are not available yet.

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

## Dependencies and layout

Streamlit is the Phase 0 runtime dependency. `dev` adds pytest and ruff.
The `analysis` extra declares pandas, NumPy, SciPy, scikit-learn and Plotly for
later phases (`pip install -e ".[analysis,dev]"`). Dependency ranges allow updates;
they do not guarantee identical versions across machines. Later experiments must
record installed versions and seeds alongside results.

- `app.py`: Streamlit startup page.
- `src/runlens/`: independently installable package and CLI.
- `tests/`: package/entry-point smoke tests.
- `examples/`: staged example-data documentation.
- `docs/`: Chinese guide and implementation plan.
- `.github/workflows/tests.yml`: three-platform CI.

## Roadmap and limitations

1. Phase 1: CSV upload, timestamp/channel mapping, signal plots, quality checks,
   clearly labeled synthetic IMU data with a fixed seed and reference labels.
2. Phase 2: windowed time-domain features, FFT/Welch and feature export.
3. Phase 3: robust statistical rules, candidate intervals, then Isolation Forest.
4. Phase 4: reproducible comparisons and report export from actual runs.
5. Phase 5: full documentation, boundary tests and verified CI before v0.1.0.

RunLens will report observable data-quality issues and statistical anomaly
candidates; these are not diagnoses of robot hardware faults. No analysis results
or accuracy figures exist at Phase 0. The current version is an initialization
scaffold, not a data-analysis product.

## License

Original project code is licensed under [MIT](LICENSE). Dependencies retain their
own licenses. Public datasets are not bundled; their redistribution terms must be
checked before adding any data.
