# Phase 1 实际示例结果

这是 2026-10-09 在 Windows、Python 3.11.9 上生成并重新导入
`examples/generated/synthetic_imu.csv` 后的真实质量检查结果。
数据来源为 **Synthetic Data**，固定种子 42，不是实际机器人记录。

## 复现

从项目根目录执行生成命令（输出已存在时用新目录，默认不会覆盖）：

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -X utf8 examples/generate_demo.py
```

Linux/macOS：

```bash
.venv/bin/python examples/generate_demo.py
```

然后上传生成的 CSV，选择 `timestamp`、`s`、全部六个 IMU 通道，
间隔阈值倍数设为 3；也可使用应用默认演示得到相同规则结论。

| 观测项 | 实际值 |
| --- | --- |
| 样本行数 | 2000 |
| 通道数 | 6 |
| 有效时间戳 | 2000 |
| 相邻正间隔数量 | 1997 |
| 正间隔中位数 | 0.01 s |
| 估计采样频率 | 100 Hz |
| 最大正间隔 | 0.11 s |
| 重复时间戳 | 1 |
| 逆序相邻对 | 1 |
| 大间隔 | 1 |
| 短间隔 | 0 |

## 质量证据

| 类型 | 原始样本行（0 起始、含端点） | 通道 | 指标 | 阈值 |
| --- | --- | --- | --- | --- |
| large_interval | 699–700 | timestamp | 0.11 s | > 0.03 s |
| duplicate_timestamp | 1300 | timestamp | 原始值此前出现 | 重复值规则 |
| reverse_timestamp | 1499–1500 | timestamp | -0.005 s | < 0 s |
| missing_value | 1700 | accel_z | 1 个缺失值 | 缺失值规则 |

生成器另外在 accel_x 的第 400、1000 行注入尖峰；这两个标签是已知
注入位置，当前质量规则未进行统计尖峰检测。总计 6 个注入参考标签，
不等于 6 个检测结果；本阶段没有计算 precision、recall、F1、故障概率
或分析性能指标。

运行依赖版本：RunLens 0.0.2、NumPy 2.4.6、pandas 3.0.6、
Plotly 6.9.0、Streamlit 1.65.0。不同依赖版本可能影响末位浮点值。
Linux/macOS 尚未实际执行 CI，本记录不代表这些平台已通过。
