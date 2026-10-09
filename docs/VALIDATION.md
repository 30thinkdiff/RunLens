# RunLens 验收与发布记录

本页记录可查证证据，不把配置、命令说明或待办当作测试通过。Phase 5 的本地检查和
三平台 CI 分开记录；只有待发布提交在 Windows/Ubuntu/macOS 都实际成功，才发布 v0.1.0。

## 必需功能与测试映射

| 条目 | 现有验证位置 |
| --- | --- |
| 空文件、字段不存在、格式/编码/读取上限 | test_io.py、test_boundaries.py、test_app.py |
| 大绝对 ns、明确单位、重复/逆序/间隔 | test_io.py、test_quality.py、test_real_data.py |
| NaN/Inf/常数/短序列、保留原始数据 | test_quality.py、test_features.py、test_anomaly.py |
| RMS/总体标准差、正弦主频/PSD、三轴模长 | test_features.py、test_feature_example.py |
| 参考隔离、零 MAD、IF 缩放/种子、候选合并 | test_anomaly.py、test_real_data.py |
| 明确注入、完整事件、指标单位/覆盖率 | test_evaluation.py、test_experiments.py |
| CSV/标准 JSON/转义报告、旧来源拒绝 | test_reporting.py、test_anomaly_example.py |
| 上传→质量→特征→检测→报告、结果失效 | test_app.py、test_smoke.py |

真实背景来自随仓库提供的 UCI LP1 原文件；CI 不在线下载测试数据。公式/数值边界仍用
小数组验证数学性质，不能用真实数据替代解析真值。完整平台日志会运行全部测试。

## 本地命令

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest --junitxml=examples/generated/phase5/junit.xml
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m runlens --version
.\.venv\Scripts\python.exe -X utf8 examples/run_experiments.py --output examples/generated/phase5/experiment
```

Linux/macOS 用 `.venv/bin/python`；CI 执行相同核心检查并保存 JUnit、实验 JSON/报告/CSV。
复现直接依赖版本可使用 `pip install -c requirements-verified.txt -e ".[dev]"`。
该文件不是所有间接依赖的锁文件；Python补丁版本、依赖版本和平台仍以实际运行报告为准。

## 构建验证

核心 wheel 不包含根目录 Streamlit 应用和公开 fixture。运行网页请克隆/下载完整 Git 源码，
从根目录执行 `python -m streamlit run app.py`。wheel 验收在独立进程用 -I 导入 wheel 内
模块并复跑真实质量→特征→检测→报告；仍使用当前环境的第三方依赖，不等于全新空环境安装。

```powershell
.\.venv\Scripts\python.exe -m pip wheel --no-deps --wheel-dir examples/generated/phase5/packages .
.\.venv\Scripts\python.exe -X utf8 -I examples/check_wheel.py --wheel examples/generated/phase5/packages/runlens-0.1.0-py3-none-any.whl
```

## 当前证据

Phase 4：Windows CPython 3.11.9，193 passed in 86.67s；ruff/格式/依赖检查通过。
Phase 5：Windows CPython 3.11.9，219 passed in 92.04s；ruff/58 文件格式/依赖检查通过。
wheel 独立导入真实全流程与 23 文件实验复跑通过，详见 examples/PHASE5_RESULT.md。
Phase 5 首轮 0.0.6 三平台实际通过：
[Actions 37951954582](https://github.com/30thinkdiff/RunLens/actions)，
精确提交 `history-rewritten`。
Windows、Ubuntu、macOS 三个 job 均 success，包含测试、固定真实实验和证据上传。
已认证下载并核对三个 artifact 内的 JUnit 与 metrics.csv：每平台 219 项测试，
失败/错误/跳过均 0；四组真实实验计数与本地一致，覆盖率均 1。

| 首轮平台 | CPython / 架构 | JUnit 测试秒数 | 结果 |
| --- | --- | --- | --- |
| windows-latest | 3.11.9 / AMD64 | 79.602 | 219 passed |
| ubuntu-latest | 3.11.17 / x86_64 | 78.624 | 219 passed |
| macos-latest | 3.11.9 / arm64 | 63.526 | 219 passed |

平台名称对应本次 hosted runner，并非所有 Windows/Linux/macOS 发行版或架构。
v0.1.0 标签只指向该版本自身通过三平台验收的提交；发布页记录最终 CI 运行链接与 SHA。
AppTest 为无浏览器交互验证，人工视觉检查另行记录，目前未执行。

## GitHub Actions 与版本发布清单

**已发布 v0.1.0**：[Release](https://github.com/30thinkdiff/RunLens/releases/tag/v0.1.0)，
标签提交 `history-rewritten`。
该版本自身 [CI 37953164976](https://github.com/30thinkdiff/RunLens/actions)
三平台实际成功，各 219 passed、无错误/失败/跳过；下载的真实实验计数、覆盖率、
数据身份与版本均已核对。平台/计时见 examples/PHASE5_RESULT.md。

仓库：[30thinkdiff/RunLens](https://github.com/30thinkdiff/RunLens)，使用现有 master 分支。
用户于本阶段提供地址，origin 已连接；先验检查远程为空，避免覆盖既有历史。
当前流程只测试并上传证据，无自动发布步骤。官方 Action 标签已只读核对并固定提交：
[checkout](https://github.com/actions/checkout)、[setup-python](https://github.com/actions/setup-python)、
[upload-artifact](https://github.com/actions/upload-artifact)。三平台的产物各有唯一名称，保留 14 天。

- [x] 本地代码、文档、完整测试、原始数据/需求 SHA 检查通过。
- [x] Git 暂存/历史范围检查：无用户日志、密钥、环境、大型数据、技能目录；fixture 许可完整。
- [x] 推送已核对的提交，记录实际 CI 运行链接与 head_sha。
- [x] 对该提交核对三个 job 的成功结论和测试/实验产物，不只看总体图标。
- [x] 首轮 CI 无失败；如果后续运行失败，修复后完整复跑，不能跳过失败测试。
- [x] 首轮通过后升级 0.1.0，本地 219 passed in 83.25s；wheel、真实实验与各检查通过。
- [x] 0.1.0 准确提交自身三平台成功，真实产物再次核对。
- [x] 正式标签准确指向验收提交，Release 公开发布并上传已验证 wheel。

发布执行条件：该版本自身三平台检查成功、每个 job 与产物再次核对，tag v0.1.0
指向该准确提交。发布说明须附安装方式、真实实验/误报局限、许可、平台与 CI 链接。
最终执行证据以 [v0.1.0 发布页](https://github.com/30thinkdiff/RunLens/releases/tag/v0.1.0)
记载的准确提交、运行和 wheel 附件为准；不存在该页面或标签时不可声称已正式发布。

发布到 GitHub 不等于发布 PyPI；不创建或上传 PyPI 包。以后增加数据集须另外核查许可。
