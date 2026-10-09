# RunLens Phase 2 架构

核心模块可以独立于 Streamlit 导入和测试。当前数据流如下：

```text
CSV bytes / pathlib.Path
  → read_csv：严格解析原始字符串表
  → ImportConfig：时间列、通道、显式单位
  → prepare_dataset：原始表 + 相对秒 + 精确相邻间隔 + 数值通道
  → check_quality：摘要 + 通道统计 + 质量规则证据
  → build_signal_figure：保留原始行序、断线和质量标记
  → WindowConfig / SpectralConfig → extract_features / analyze_spectrum
  → FeatureResult / SpectrumResult → feature_csv
  → Streamlit：概览 / 信号浏览 / 特征分析 / 频谱 / 下载
```

## 模块职责

| 模块 | 职责 |
| --- | --- |
| schemas.py | 导入/窗口/频谱配置与 Dataset、质量/特征/频谱结果对象 |
| io.py | CSV 校验、数值分类、精确相对时间、原始数据保留 |
| quality.py | 重复/逆序/间隔规则、无效值统计、常数观察 |
| plotting.py | Plotly 图形、按通道纵轴、过滤与断线 |
| demo.py | 固定种子合成数据、注入参考标签和生成配置 |
| features.py | 样本窗口、九项时域统计、稳定三轴模长、FFT/Welch、CSV |
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
- FeatureResult 为每个窗口/通道保存配置、原始行边界、有效样本计数、
  时域指标、频域状态/原因及指标。窗口基于原始行，缺失值不会改变窗口边界。
- analyze_spectrum 接受可选精确相邻间隔，并核对相对时间与原始间隔一致性。
  先验证采样，再做 FFT/Welch；无法计算时抛出带原因码的 SpectralAnalysisError。
  extract_features 捕获该错误、保留时域指标并把频域置空。
- FFT 单边幅值与 Welch density 使用不同窗和归一化；配置及实际 Welch
  分段长度均写入结果，不隐式插值。详细定义见 USER_GUIDE.md。
- 使用缩放计算时域统计和频谱，稳定 hypot 求模长；无法表示的指标显式拒绝
  或置空。常数/零信号不虚构主频。计算前检查结果行数与累计样本处理量。

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

from runlens.features import extract_features, feature_csv
from runlens.schemas import WindowConfig

features = extract_features(dataset, WindowConfig(window_size=256, step_size=128))
print(features.table[["row_start", "channel", "rms", "spectral_status"]])
# 在自己选择的输出目录写入；注意检查已有文件，避免覆盖。
csv_bytes = feature_csv(features)
```

## 缓存与显示

Streamlit 缓存仅在会话内存中，TTL 600 秒、每个函数最多 3 个条目。
CSV 内容变化时，字段映射和过滤使用新的键；不同用户不会共享上传结果。
窗口计算由 st.form 提交，结果与导出字节一起缓存；当前会话仅保存一份显示结果。
来源/时间映射/单位/通道变化清除旧显示结果，避免把旧配置结果误用于新数据。
Plotly 与数值核心均不依赖浏览器/操作系统命令，显示限制见用户指南。

MAD、Isolation Forest、评估与分析报告是后续阶段的
新增模块；当前不提供空实现或虚构算法结果。
