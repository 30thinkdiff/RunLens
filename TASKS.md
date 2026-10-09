# RunLens 任务与验证状态

当前阶段：**Phase 2 — 窗口特征与频谱（已完成 Windows 本地验收）**。
用户已确认进入 Phase 2；完成后等待确认 Phase 3。

## Phase 2

- [x] 检查 Phase 1、原始要求与 Git 状态，保存阶段计划。
- [x] 添加独立 features.py、窗口/频谱配置和结果结构。
- [x] 样本窗口长度/步长、可选尾窗、九项时域统计、omit/propagate 与计数。
- [x] 稳定三轴模长作为额外通道，保留原始轴并校验映射与名称。
- [x] 矩形窗单边 FFT、周期 Hann Welch PSD、主频、PSD 积分、谱能量估计与质心。
- [x] 显式采样容差；拒绝不递增/不规则/无效采样与 NaN/Inf 信号，不插值。
- [x] 每窗频域拒绝原因、时域保留、数值范围与结果量/累计处理量限制。
- [x] Streamlit 特征表单、趋势、片段频谱、带参数和原因的完整特征 CSV。
- [x] 输入映射变化清除旧结果，减少到不足三通道时关闭模长。
- [x] SciPy 加入运行依赖并实际安装；版本更新为 0.0.3。
- [x] 已知信号验证、界面/导出回归、不覆盖已有文件的可复现特征示例。
- [x] 更新中英文指南、架构、阶段状态和实际结果。
- [x] 全套 pytest、ruff、格式、依赖完整性与 Git 差异检查通过。
- [x] 本地 Git 归档，仅提交本阶段代码/文档/测试，保留用户技能和原有示例。

### Phase 2 最终验收

2026-10-09，Windows，本项目 `.venv` 的 CPython 3.11.9：

| 检查 | 实际结果 |
| --- | --- |
| 核心测试先行 | 尚未创建 features.py 时因模块缺失失败，符合预期 |
| `python -m pytest` | **117 passed in 23.38s** |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 31 files already formatted |
| `python -m pip check` | No broken requirements found |
| `python -m runlens --version` | RunLens 0.0.3 |
| 特征示例脚本 | 实际生成 CSV 与版本/参数/计时 JSON，见 examples/PHASE2_RESULT.md |
| 原始 prompt.md | SHA-256 与 Phase 0 一致，未改动 |
| Linux/macOS CI | **未运行**；未配置 Git 远程 |

新增 50 项测试，覆盖已知数组/正弦的时域与频域、奇偶 FFT/Nyquist、
Welch 功率积分与去均值、窗口/尾窗、模长、采样拒绝与显式抖动容差、
NaN/Inf/常数/短序列、溢出与功率下溢、处理量限制、CSV 回读、
真实模拟上传/参数提交/文件替换/结果失效/不足三轴，以及脚本覆盖保护。
原有 67 项测试全部保留并通过。

实际示例：已知 16 Hz、幅值 2 正弦得到 RMS √2、FFT 幅值 2、主频 16 Hz、
PSD 积分约 2、谱能量估计约 8、谱质心 16 Hz。
默认 IMU 增加加速度模长后生成 14 窗 / 98 条记录，其中频域有效 59 条；
21 条非递增时间、14 条不规则采样、4 条信号无效，均保留时域结果。
分析计时 0.0979909 s（单次本机，不含导入库与写文件）。
完整复现方法与限制见 [PHASE2_RESULT.md](examples/PHASE2_RESULT.md)。

运行版本：RunLens 0.0.3、Streamlit 1.65.0、SciPy 1.17.1、Plotly 6.9.0、
pandas 3.0.6、NumPy 2.4.6、pytest 8.4.2、ruff 0.16.10。
尚未进行人工浏览器视觉检查或真实 EuRoC 实验；没有检测准确率结论。

## Phase 1（历史记录，已完成）

- [x] 检查现有代码和用户新增技能，保留 .agents/、.claude/ 原有未提交文件。
- [x] 新增阶段计划与独立 schemas / io / quality / demo / plotting 模块。
- [x] 严格 UTF-8 CSV 导入，保留原始表头和值，支持手动 EuRoC IMU 字段映射。
- [x] 显式 s/ms/us/ns 配置，先求差再转相对秒，避免绝对纳秒浮点精度损失。
- [x] 缺失/非法/Inf、重复、逆序、大/短间隔、常数通道和基础统计。
- [x] Streamlit 概览与信号浏览，原始预览、通道选择、局部时间段和质量标记。
- [x] Plotly 在中断和异常时间处断线，明确显示容量与数据展示限制。
- [x] 固定种子 Synthetic Data、注入标签、元数据下载及不默认覆盖的生成脚本。
- [x] 更新运行依赖与版本 0.0.2；SciPy / scikit-learn 保留为后续可选依赖。
- [x] 更新中英文文档、独立调用说明、实际示例结果。
- [x] 完整 pytest、ruff、格式、pip check 最终验收。
- [x] 检查本阶段提交范围、忽略文件与密钥扫描；以本地 Git 提交归档，不推送远程。

### Phase 1 最终验收

2026-10-09，使用本项目 `.venv` 的 Python 3.11.9：

| 检查 | 实际结果 |
| --- | --- |
| `python -m pytest` | **67 passed in 8.56s** |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 通过 |
| `python -m pip check` | No broken requirements found |
| `python -m runlens --version` | RunLens 0.0.2 |
| 示例生成与重新导入 | 成功，结果见下方与 examples/EXAMPLE_RESULT.md |
| 原始 prompt.md | SHA-256 与 Phase 0 一致，未改动 |
| Linux/macOS CI | **未运行**，未配置远程，不能宣称通过 |

测试覆盖真实模拟上传/字段映射/单位和范围切换、文件替换与错误提示，
空/畸形 CSV、BOM/CRLF、纳秒精度、非法/越界时间、NaN/Inf、重复/逆序、
间隔规则、常数/短序列、超大有限值统计、绘图断线与容量限制、
合成数据确定性/标签及生成器不覆盖已有文件。

### Phase 1 已执行的示例

2026-10-09，Windows、Python 3.11.9。执行生成器并重新导入生成的 CSV：
2000 行、6 通道、6 个注入标签。估计采样频率 100 Hz；实际报告 4 个质量
问题：大间隔（699–700）、重复（1300）、逆序（1499–1500）、accel_z
缺失（1700），短间隔 0。完整说明见 examples/EXAMPLE_RESULT.md。

两处尖峰是注入标签，尚无统计检测结果；不计算本阶段检测准确率。
界面交互通过 AppTest 模拟真实文件上传、单位/通道配置与时间过滤验证，
尚未进行人工浏览器视觉检查或真实 EuRoC 数据实验。

运行版本：RunLens 0.0.2、Streamlit 1.65.0、Plotly 6.9.0、
pandas 3.0.6、NumPy 2.4.6、pytest 8.4.2、ruff 0.16.10。

## Phase 0（历史记录，已完成）

- [x] 阅读 prompt.md 与附件，确认内容一致及阶段边界。
- [x] 检查目录：仅有 prompt.md，无已有业务代码。
- [x] 检查 Git：2.47.0.windows.2，master，尚无提交、无远程。
- [x] 整理 PRD.md 与实施计划。
- [x] 建立 Python 3.11 虚拟环境。
- [x] 配置 pyproject.toml、src 包、最小命令行与 Streamlit 启动页。
- [x] 添加最小 pytest 测试并真实运行。
- [x] 添加 README、中文使用说明、MIT License、Git 忽略规则。
- [x] 添加 Windows/Ubuntu/macOS Python 3.11 CI 配置。
- [x] 运行 lint、格式、依赖完整性与启动检查。
- [x] 检查待提交文件：无环境目录、大型数据或检测到的密钥；prompt.md 内容未改动。

阶段成果以本地 Git 提交归档，使用 `git log -1 --oneline` 查看提交号。
本轮不推送远程、不发布版本。

## 后续阶段

- [x] Phase 1 功能：CSV 导入/映射、相对时间、质量检查、Plotly 曲线、合成数据与标签。
- [x] Phase 2：窗口特征、三轴模长、FFT/Welch、特征 CSV 导出。
- [ ] Phase 3：MAD、候选区间、Isolation Forest 与拟合/评估分离。
- [ ] Phase 4：可复现实验、评价单位、方法比较、真实计时、结构化报告。
- [ ] Phase 5：完整边界测试、文档与课程报告提纲、CI 验收、v0.1.0。

## 当前环境与已知问题

- 默认 python 为 MSYS2 Python 3.14.5，缺少 pip/pytest 和分析依赖。
- 已下载并验证 Python Software Foundation 签名的官方 Python 3.11.9
  安装包，安装到被忽略的 `.tools/python311/`，创建 `.venv/`。
  原有 Python 与 PATH 保持原配置；IDE 应选择 `.venv/Scripts/python.exe`。
- 已安装并直接声明 Streamlit、pandas、NumPy、Plotly、SciPy；
  analysis 可选依赖组中的 scikit-learn 留待 Phase 3，尚未安装或验证。
- 未配置远程，不能触发 GitHub Actions。Linux/macOS 尚未验证。
- CSV 上限 20 MiB / 100000 行 / 64 列；图最多 20000 行 / 8 通道。
  超出绘图限制时需缩小范围，不自动抽稀。UI 表格和标记也有明确显示上限。
- 中位数间隔基准在多数间隔异常或分段采样率时可能不能代表期望频率。
- 窗口结果最多 50000 条窗口×通道记录、累计处理量最多 2000 万个信号值。
  采样相对容差默认 1e-6，放宽后是显式近似假设；谱能量估计不代表机械能。
- 尚无统计异常检测、完整报告导出；不发布 v0.1.0。

## Phase 0 验证记录（历史）

2026-10-09，Windows 本地，CPython 3.11.9；RunLens 0.0.1、
Streamlit 1.65.0、pytest 8.4.2、ruff 0.16.10、pip 24.0。

| 检查 | 实际结果 |
| --- | --- |
| 实现前包测试 | 2 项因 runlens 尚未实现而失败，符合预期 |
| `python -m pip install -e ".[dev]"` | 成功安装可编辑包 |
| `python -m pytest` | **3 passed in 1.74s**，覆盖安装元数据、模块版本命令、Streamlit 页面 |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 通过 |
| `python -m pip check` | No broken requirements found |
| `python -m runlens --version` / `runlens --version` | RunLens 0.0.1 |
| 临时本地 Streamlit 服务 | `127.0.0.1:18501/_stcore/health` 返回 HTTP 200，检查后停止 |
| 原始需求文件 | SHA-256 与初始值一致，未修改 |
| Linux/macOS CI | **未运行**，不能宣称通过 |

上述命令均由 `.venv` 中的解释器执行。UI 通过 Streamlit AppTest 执行，
未执行人工浏览器视觉检查。没有在本阶段测量分析性能或检测准确率。

下一阶段建议：确认后进入 Phase 3，先实现中位数/MAD 和候选区间，再增加
Isolation Forest；处理 MAD=0、拟合/评估分离，并记录方法、参数和分数定义。
