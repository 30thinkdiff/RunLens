# RunLens 中文使用指南

## 当前能做什么

Phase 2（0.0.3）已提供 CSV 导入、时间戳/通道/单位映射、基础质量报告、
Plotly 曲线、滑动窗口特征、三轴模长、FFT/Welch 和特征 CSV 导出。
默认内置 Synthetic Data，可直接演示，也可下载 CSV、注入标签与生成配置。
MAD/Isolation Forest 及完整分析报告导出尚未实现。
请先在项目根目录执行以下命令。

## Windows PowerShell

确认使用 CPython 3.11，而不是其他版本或 MSYS2 Python：

```powershell
py -3.11 --version
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m runlens --version
.\.venv\Scripts\python.exe -m streamlit run app.py
```

若没有可用的 `py` 启动器，用 Python 3.11 的实际路径代替 `py -3.11`。
本工作区若已配置 `.tools/python311/python.exe`，可用项目内环境：

```powershell
.\.tools\python311\python.exe --version
.\.tools\python311\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

`.tools/` 和 `.venv/` 不进入 Git，其他人克隆仓库后需自行安装 Python 3.11。
使用虚拟环境解释器的完整相对路径，无需激活环境或修改 PowerShell 执行策略。
IDE 解释器选择 `.venv/Scripts/python.exe`。

## Linux / macOS

准备好 Python 3.11、pip 和 venv 后执行：

```bash
python3.11 --version
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m runlens --version
.venv/bin/python -m streamlit run app.py
```

部分 Linux 发行版需要通过其软件包管理器安装对应的 venv 组件。
macOS 使用适配本机架构的 Python；本项目未在本机验证 Intel/Apple Silicon。

## 启动与检查

浏览器打开 Streamlit 输出的本地 URL（默认 `http://localhost:8501`）。
页面显示版本、数据配置、数据概览、信号浏览和特征分析；终端 Ctrl+C 停止服务。
`runlens` 命令用于命令行信息，不负责启动 Web 服务。

Windows 验证：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
```

Linux/macOS 将上述 `.\.venv\Scripts\python.exe` 替换为 `.venv/bin/python`。

安装失败时先检查解释器版本、网络与报错；不要删除失败测试或忽略错误。
SciPy 已是运行依赖；后续 Phase 3 用 `.[analysis,dev]` 安装 scikit-learn。

## CSV 分析操作

1. 启动后默认使用 **Synthetic Data**，查看样本数、估计采样频率和质量证据。
2. 左侧选择“上传 CSV”，上传带表头的 UTF-8 文件（支持 BOM、CRLF/LF）。
3. 指定时间戳列和至少一个数值通道；时间列不能同时作为信号通道。
4. 显式选择 `s`（秒）、`ms`（毫秒）、`us`（微秒）或 `ns`（纳秒）。
   不根据大小自动判断单位。时间戳应是数值，不支持日期/ISO 文本。
5. “数据概览”查看时间戳质量、采样间隔、各通道统计和检测依据。
6. 切到“信号浏览”，选绘图通道，拖动时间范围；Plotly 支持缩放与悬停。
   详情表保留原始字段和 0 起始样本行号。

普通 CSV 示例：

```csv
timestamp,accel_x,gyro_z
0,0.1,0.01
0.01,0.2,0.02
0.02,0.3,0.01
```

这段数据应选择 `timestamp`、`s` 和 `accel_x`/`gyro_z`，估计频率为 100 Hz。

EuRoC MAV 的 IMU CSV 导入：从 [官方数据集页](https://projects.asl.ethz.ch/datasets/euroc-mav/)
取得数据后，上传解压目录中的 `mav0/imu0/data.csv`。保留带 `#` 的表头，
手动选择 `#timestamp [ns]`（或文件中的实际名称）以及角速度/加速度通道，
时间单位选择 `ns`。仓库没有捆绑真实数据；尚未运行真实 EuRoC 记录实验。

## 质量规则与解释

- 起点为首个有效原始时间戳。内部先用十进制数求差，再转相对秒，
  防止直接将绝对纳秒时间转为浮点而损失精度；原始字段仍保存。
- 不修改原始行序，不自动排序、删除行、填补 NaN、插值或重采样。
- 频率 = `1 / median(有效原始相邻对的正间隔)`；缺失/非法时间戳打断相邻关系。
- 大间隔 > 中位数 × 阈值倍数；短间隔 < 中位数 / 阈值倍数（默认 3）。
  倍数必须大于 1。大间隔只说明观测到时间异常，不能确认真实丢帧。
- `duplicate_timestamp` 表示数值时间戳曾出现过（包括非相邻重复）；
  `reverse_timestamp` 表示原始相邻有效时间戳差小于零。
- NaN/空值、Inf 和非数值内容分别计数；通道统计只使用有限值，
  标准差采用总体定义 `ddof=0`；至少两个相同有限值才标注常数通道。
- `row_start` / `row_end` 是 0 起始的样本行号，端点都包含；
  并非 CSV 物理行号（引号内换行和空行可能影响物理行号）。
- 全部时间戳无效、无数据行、重复/空列名或字段数不一致会显示错误；
  混合无效时间戳仍保留并报告，但这些行不能定位到时间轴。

正常静止信号也可能是常数；输入中大部分间隔异常或采样率分段变化时，
中位数基准可能无法代表期望频率。系统不推断机器人故障根因。

## 窗口特征与 CSV 导出

1. 切到“特征分析”，设置窗口长度与步长，单位均为**样本数**。
   默认 256/128；窗口从原始第 0 行开始，按步长前进，不按时间重新分组。
2. 默认只保留完整窗口；可勾选保留尾部不足长度的窗口。
   数据不足一窗时默认返回空结果，仍可下载含表头的 CSV。
3. 选择无效值策略：`omit` 在时域统计中排除 NaN/Inf，并记录数量；
   `propagate` 遇到任何无效值就把统计指标留空。两者均不改变原始数据。
4. 可增加三轴模长，明确选择三个不同通道与不冲突的名称。模长为
   `sqrt(x²+y²+z²)`，使用稳定计算；任一轴无效则模长无效，原始轴仍保留。
   三轴应具有相同单位且对应同一物理量；不要把加速度和角速度混合求模长。
5. 点击“计算窗口特征”；计算量较大时等待完成。修改表单后必须再次提交，
   页面结果与 CSV 显示的是最后一次成功提交的参数。
6. 查看前 1000 条记录和特征趋势；“下载特征 CSV”包含完整结果。
   更换 CSV、时间列、单位或分析通道会清除旧结果，需重新计算。

指标 `mean/std/variance/rms/min/max/peak_to_peak/median/iqr` 分别为均值、
总体标准差、总体方差、均方根、最小值、最大值、峰峰值、中位数和四分位距。
`std/variance` 的 `ddof=0`；分位数使用线性插值，IQR = Q75 − Q25。
这些是**样本等权统计**，不规则时间戳下不代表时间加权统计。
无有限样本时统计留空；单个有限样本的总体标准差/方差为零。
超出可表示数值范围的指标留空，并记录在 `overflow_features`。

每条 CSV 记录对应“窗口 × 通道”，保存来源、时间列/单位/原始起点、
输入通道、模长轴、窗口/步长、无效值策略、频谱设置、0 起始且包含两端的
原始行号、相对起止时间、完整窗标识和有效值计数。频域不满足条件时，
时域仍保留，`spectral_status` 和 `spectral_message` 记录原因，频域指标为空。
`disabled` 表示用户关闭了窗口频域特征；片段频谱仍可独立查看。

## FFT / Welch 的条件与定义

“所选片段的 FFT 与 Welch PSD”按原始样本行选择范围，包含两端。
默认查看前 256 行；独立于滑动窗口计算，可选已计算的模长通道。
提交特征表单后，片段频谱使用该次提交的频谱参数。

- 至少两个样本；信号与时间均须有限，时间严格递增。
  NaN/Inf 不会被删除后再做 FFT；重复、逆序、无效时间戳均拒绝计算。
- 用有效相邻间隔中位数估计 `fs`。要求每个间隔的
  `abs(Δt / median(Δt) − 1)` 不超过相对容差，默认 `1e-6`，上限 `0.05`。
  容差为 0 表示对精确原始间隔要求完全相等，直接浮点时间可能产生微小误差。
  放宽容差就是接受近似等间隔假设；报告显示实测 `max_relative_jitter`。
  不插值或重采样，拒绝原因不是故障诊断。
- 默认先去除整个所选片段的均值；时域统计仍使用原始信号。
  关闭后频谱保留 DC；Welch 不额外逐段去趋势。
- FFT 为实数单边幅值谱，矩形窗，`abs(rfft)/N`，除 DC 与偶数长度的
  Nyquist 外乘 2。纵轴单位同输入信号，分辨率 `fs/N`。
- Welch PSD 使用显式周期 Hann，分段长度取 `min(用户配置, N)`，
  重叠数为分段长度的一半向下取整、均值平均、`density` 归一化。
  PSD 纵轴为信号单位²/Hz，频率格点间隔为 `fs/nperseg`。
- `dominant_frequency_hz` 取非 DC FFT 最大幅值的频率格点；数值噪声
  级的非 DC 分量不作为主频。零信号或常数去均值后主频、谱质心为空。
- `psd_integral = sum(PSD) × Δf`，单位为信号单位²，使用完整单边离散
  频率格点求和（包含 DC/Nyquist），不使用会减半端点权重的梯形积分。
- `spectral_energy = psd_integral × N/fs`，是基于 Welch 的能量估计，
  单位为信号单位²·s；`N/fs` 是频谱时长约定，和首尾时间差 `(N−1)/fs`
  不同。它不是机械能，也不保证等于原始非平稳信号平方和积分。
- `spectral_centroid_hz = sum(f × PSD) / sum(PSD)`，使用 Welch 功率权重，
  包含 DC；功率为零时为空。所有频域指标描述预处理后的信号。

短窗口频率分辨率较差；非整数周期会产生谱泄漏，主频是格点估计，
不是精确参数拟合。Welch 分段长度和去均值设置会改变非平稳信号的积分。
高于 Nyquist 的真实频率无法从这些采样唯一恢复，系统不判断真实信号是否混叠。
算法约定参考 SciPy 官方 [rfft 文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.fft.rfft.html)
与 [Welch 文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html)。

实际已知信号验证及复现命令见 [Phase 2 结果](../examples/PHASE2_RESULT.md)。

## 容量与显示限制

CSV 上限为 20 MiB、100,000 个样本行、64 列。绘图最多 8 个通道、
20,000 行；超出时需缩小时间范围，不会自动抽稀。红色标记间隔问题，
紫色标记逆序，橙色标记重复，灰色标记通道无效值。
曲线在异常间隔、非递增时间、无效值或不连续原始行处断开。
最多绘制前 50 个可定位标记、显示前 500 条证据和 1000 行详情；
核心结果保存全部问题。上传数据只使用有上限和时效的会话内存缓存，
应用不会自动将上传文件保存到仓库。

窗口特征最多 50,000 条“窗口 × 通道”记录，并限制累计处理量为
20,000,000 个窗口信号值（重叠窗口重复计入）。超出时在计算前报错，
请增大步长、缩短窗口或减少通道。趋势图最多 20,000 个窗口点，
不自动抽稀；CSV 保留全部已计算记录。表单驱动计算且缓存有 TTL/条目上限。

生成合成演示文件的跨平台命令和标签说明见 [examples/README.md](../examples/README.md)。

## Git 与阶段推进

仓库已初始化，保留现有分支和用户文件。`.gitignore` 排除环境、缓存、
私有配置以及 `data/`、`reports/`；不要把真实实验数据或密钥直接提交。
本地提交不等于公开发布。本轮完成 Phase 2 后，等待确认 Phase 3。

三平台 CI 配置不是已通过的证据。实际测试结果与尚未验证内容见
[TASKS.md](../TASKS.md)。
