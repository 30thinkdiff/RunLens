# RunLens Phase 1 架构

核心模块可以独立于 Streamlit 导入和测试。当前数据流如下：

```text
CSV bytes / pathlib.Path
  → read_csv：严格解析原始字符串表
  → ImportConfig：时间列、通道、显式单位
  → prepare_dataset：原始表 + 相对秒 + 精确相邻间隔 + 数值通道
  → check_quality：摘要 + 通道统计 + 质量规则证据
  → build_signal_figure：保留原始行序、断线和质量标记
  → Streamlit：概览 / 信号浏览 / 原始数据详情
```

## 模块职责

| 模块 | 职责 |
| --- | --- |
| schemas.py | ImportConfig、Dataset、QualityReport、DemoData |
| io.py | CSV 校验、数值分类、精确相对时间、原始数据保留 |
| quality.py | 重复/逆序/间隔规则、无效值统计、常数观察 |
| plotting.py | Plotly 图形、按通道纵轴、过滤与断线 |
| demo.py | 固定种子合成数据、注入参考标签和生成配置 |
| app.py | 用户输入、会话缓存和结果显示，不实现核心算法 |

## 关键数据约定

- 原始样本行号从 0 开始；区间两端均包含。原始 CSV 字段值不被修改。
- CSV 时间列先解析为 Decimal。起点为首个有效时间戳，求差后才转浮点秒。
  `interval_s[i]` 表示结束于第 i 行的原始相邻间隔，第一行为 NaN。
- 无效时间戳打断相邻关系；不跨越无效行估计间隔。
- 数据集保留原始配置、起点、时间戳状态和 Decimal 值，重复检查不会
  依赖舍入后的浮点绝对时间。
- 数值通道可能含 NaN/Inf；统计只使用有限值。缺失、无限值和非法文本
  分开计数。超出可分析数值范围的时间输入会返回 DataValidationError。
- nominal_interval_s 使用正间隔中位数；sample_rate_hz 为其倒数。
  没有正间隔或频率超出浮点范围时，频率为 None。
- 质量证据包括 kind、样本行、相对时间、通道、指标、阈值和规则。
  无法定位的时间为 NaN，界面仍显示对应原始行。

## 独立调用示例

安装项目后可在 Python 中运行：

```python
from pathlib import Path

from runlens.io import prepare_dataset, read_csv
from runlens.quality import check_quality
from runlens.schemas import ImportConfig

raw = read_csv(Path("examples") / "generated" / "synthetic_imu.csv")
config = ImportConfig("timestamp", ("accel_x", "gyro_z"), "s")
dataset = prepare_dataset(raw, config, "Synthetic Data")
report = check_quality(dataset, gap_factor=3.0)
print(report.summary)
print(report.issues)
```

## 缓存与显示

Streamlit 缓存仅在会话内存中，TTL 600 秒、每个函数最多 3 个条目。
CSV 内容变化时，字段映射和过滤使用新的键；不同用户不会共享上传结果。
Plotly 与数值核心均不依赖浏览器/操作系统命令，显示限制见用户指南。

时域/频域特征、MAD、Isolation Forest、评估与分析报告是后续阶段的
新增模块；当前不提供空实现或虚构算法结果。
