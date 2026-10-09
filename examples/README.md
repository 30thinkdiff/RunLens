# 示例数据

所有示例均为 **Synthetic Data**，不是实际机器人记录。
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
当前仍仅检测质量规则；Phase 2 增加窗口与频谱特征，尖峰/振动标签供后续统计方法评估，
当前没有检测准确率、F1 或故障概率结果。

真实执行的质量结果见 [EXAMPLE_RESULT.md](EXAMPLE_RESULT.md)。
公开真实数据未捆绑；下载与导入说明见中文用户指南。

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
