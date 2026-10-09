# 示例数据

本节 IMU 示例为 **Synthetic Data**，不是实际机器人记录。
文末另有明确来源的 Phase 3 真实机器人力/力矩示例与 Phase 4 实验报告。
Phase 5 的边界、来源、wheel 与三平台验收见 [PHASE5_RESULT.md](PHASE5_RESULT.md)，
固定实验使用独立目录 `examples/generated/phase5/experiment`，保留历史生成物。
默认种子 42、2000 个样本、名义频率 100 Hz，包含六个 IMU 通道、
周期信号、标准差 0.03 的噪声、两处尖峰、一个大间隔、重复与逆序
时间戳以及一个缺失通道值。加速度单位 m/s²，角速度单位 rad/s。

安装项目后，在仓库根目录运行：

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -X utf8 examples/generate_demo.py
```

Linux/macOS：

```bash
.venv/bin/python examples/generate_demo.py
```

输出到被 Git 忽略的 `examples/generated/`：

- `synthetic_imu.csv`：时间戳单位秒，可上传到 RunLens。
- `synthetic_labels.csv`：人为注入参考标签，不是检测器输出。
- `synthetic_metadata.json`：来源、种子、频率、单位和标签层级。

也可直接启动应用，使用内置演示并下载同样的文件，无需外部下载。
生成器默认拒绝覆盖已有文件；可用 `--output` 指定新目录。
`--overwrite` 仅在明确希望替换输出时使用。
`--vibration` 可添加局部振动变化，`--seed`、`--samples`、`--sample-rate`
可调整数据；采样点数至少 100，频率必须为正有限数。

标签 `row_start` / `row_end` 使用 0 起始原始样本行，包含端点；
时间字段为该行对应的相对秒，逆序区间的端点可能逆序。
Phase 3 已提供 MAD / IF 候选检测；已有尖峰标签用于检测回归，振动标签供后续
方法评估。当前没有真实数据准确率、F1 或故障概率结论。

真实执行的质量结果见 [EXAMPLE_RESULT.md](EXAMPLE_RESULT.md)。
EuRoC 等大型公开数据未捆绑；下载与导入说明见中文用户指南。

## Phase 2 特征复现

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -X utf8 examples/analyze_features.py
```

Linux/macOS：

```bash
.venv/bin/python examples/analyze_features.py
```

输出到 `examples/generated/phase2/`：`synthetic_features.csv`、
`sine_features.csv` 和 `summary.json`，记录实际特征、拒绝原因、配置、
版本与分析运行时间。该脚本不改动 Phase 1 示例；默认拒绝覆盖，
可指定新的 `--output`，明确需要覆盖时用 `--overwrite`。
已知正弦与种子 42 IMU 的实际结果见 [PHASE2_RESULT.md](PHASE2_RESULT.md)。

## Phase 3 真实机器人记录

Windows：

```powershell
.\.venv\Scripts\python.exe -X utf8 examples/analyze_anomalies.py
```

Linux/macOS：

```bash
.venv/bin/python examples/analyze_anomalies.py
```

读取随仓库提供、已核查 CC BY 4.0 许可的 UCI LP1 小型力/力矩记录，
无需联网；不改动原始数据。输出到 `examples/generated/phase3/`：
原始测量转换 CSV、明确注入的副本，以及各方法/副本的候选 CSV、
逐行分数 CSV、配置 JSON 和 `summary.json`。默认拒绝覆盖，
可用 `--output` 指定新目录；明确覆盖时用 `--overwrite`。

1320 个真实六轴测量行来自 88 个独立事件。前十个正常标签事件
完整用于参考（0–149 行），其他事件完整用于检测（150–1319 行）。
`synthetic_time_s` 是显式构造的定位时钟，不是原始实测时间；
不能用其频谱或采样间隔推断实际机器人参数。副本第 150 行的六轴值替换为 10000。
事件级分类标签不能直接用于逐点准确率评价。
派生 CSV 对外再分发时保留源作者、CC BY 4.0 与修改说明。

实际结果与参数见 [PHASE3_RESULT.md](PHASE3_RESULT.md)，来源、原始 SHA 和许可见
[fixture README](../tests/fixtures/robot_execution_failures/README.md)。

## Phase 4 固定实验与报告

```powershell
.\.venv\Scripts\python.exe -X utf8 examples/run_experiments.py
```

```bash
.venv/bin/python examples/run_experiments.py
```

四类实验：真实测量副本的时间质量规则、解析常数/正弦特征、真实正常背景的明确注入点
比较、真实 LP1 完整事件分类。MAD 与 IF 参数固定，不根据留出标签调优。
完整产物输出到 `examples/generated/phase4/`；23 个文件包含报告 JSON/Markdown/HTML、
指标、逐单位预测、划分、四份测量表、真实特征，以及每种任务/方法的评分/候选/配置。
默认拒绝覆盖任一目标，用 `--output` 保留独立运行。实际结果及误报局限见
[PHASE4_RESULT.md](PHASE4_RESULT.md)。点与事件指标不可混用，注入不是自然故障真值。
