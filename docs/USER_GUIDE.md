# RunLens 中文使用指南

## 当前能做什么

Phase 1 已提供 CSV 导入、时间戳/通道/单位映射、基础质量报告和 Plotly 曲线。
默认内置 Synthetic Data，可直接演示，也可下载 CSV、注入标签与生成配置。
滑动窗口特征、FFT/Welch、MAD/Isolation Forest 及报告导出尚未实现。
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
页面显示版本、数据配置、数据概览和信号浏览；终端 Ctrl+C 停止服务。
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
后续开发用 `.[analysis,dev]` 安装 SciPy/scikit-learn 依赖。

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

## 容量与显示限制

CSV 上限为 20 MiB、100,000 个样本行、64 列。绘图最多 8 个通道、
20,000 行；超出时需缩小时间范围，不会自动抽稀。红色标记间隔问题，
紫色标记逆序，橙色标记重复，灰色标记通道无效值。
曲线在异常间隔、非递增时间、无效值或不连续原始行处断开。
最多绘制前 50 个可定位标记、显示前 500 条证据和 1000 行详情；
核心结果保存全部问题。上传数据只使用有上限和时效的会话内存缓存，
应用不会自动将上传文件保存到仓库。

生成合成演示文件的跨平台命令和标签说明见 [examples/README.md](../examples/README.md)。

## Git 与阶段推进

仓库已初始化，保留现有分支和用户文件。`.gitignore` 排除环境、缓存、
私有配置以及 `data/`、`reports/`；不要把真实实验数据或密钥直接提交。
本地提交不等于公开发布。本轮完成 Phase 1 后，等待确认 Phase 2。

三平台 CI 配置不是已通过的证据。实际测试结果与尚未验证内容见
[TASKS.md](../TASKS.md)。
