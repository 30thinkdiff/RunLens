# RunLens 任务与验证状态

当前阶段：**Phase 4 — 实验评价与分析报告（已完成 Windows 本地验收）**。
用户已确认进入 Phase 4，继续优先真实测量测试；完成后等待确认 Phase 5。

## Phase 4

- [x] 保存实施计划，确认真实事件标签/明确注入点的不同语义，保留原始记录和用户文件。
- [x] 独立 evaluation.py：严格二元标签、MAD 多通道归并、完整事件、覆盖率/排除原因。
- [x] precision/recall/F1/FPR、混淆计数；分母为零写 null，缺失评分不默认为正常。
- [x] 独立 experiments.py：固定前十个 normal 事件参考；参数/种子不按留出指标调优。
- [x] 真实 78 事件分类，以及 11 个留出正常事件测量副本的三个明确注入点比较。
- [x] 真实测量副本的时间缺陷校验、常数/正弦公式复跑、528 条真实时域特征。
- [x] Python/平台、依赖版本、原始/处理后 SHA、许可、完整划分、实际计时和局限记录。
- [x] 独立 reporting.py：当前数据快照、标准 JSON、转义 Markdown/简单 HTML；预览有界。
- [x] 未标注上传快照不含分类指标，未计算步骤为 null，旧检测指纹不符时拒绝生成。
- [x] Streamlit“实验与报告”：上传分析快照与独立内置实验，提交后执行，有界会话缓存。
- [x] 输入/映射/质量参数及已提交特征/检测变化清除旧快照；真实上传 AppTest 回归。
- [x] 复现脚本导出 23 文件，先检查所有目标、默认拒绝覆盖并使用排他创建。
- [x] 版本更新 0.0.5，更新使用指南/架构/示例/PRD 和实际 PHASE4_RESULT.md。
- [x] 完整 pytest、ruff、格式、依赖检查通过，原始 prompt.md 与 LP1 字节指纹不变。
- [x] 本阶段文件本地 Git 归档，保留未跟踪用户技能，不推送或发布。

### Phase 4 最终验收

2026-10-09，Windows AMD64，CPython 3.11.9；实际运行记录：

| 检查 | 实际结果 |
| --- | --- |
| 核心测试先行 | 实现前缺少 runlens.evaluation，预期失败；随后实现通过 |
| `python -m pytest` | **193 passed in 86.67s** |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 50 files already formatted |
| `python -m pip check` | No broken requirements found |
| `python -m runlens --version` | RunLens 0.0.5 |
| Phase 4 实验脚本 | 实际导出 23 文件，四组混淆矩阵、486 个逐单位预测 |
| 真实数据与需求原文 | LP1 / prompt.md SHA-256 与前阶段相同 |
| Linux/macOS CI | **未运行**，没有 Git 远程 |

保留原有 163 项；新增 30 项：评价 16、真实实验/脚本 4、报告 5、界面 5。
覆盖严格标签、空/无分母指标、评分缺失/重复/非有限、点归并、完整事件和覆盖率、
完整事件划分/参考不注入、相同种子预测、逐单位指标回算、来源与报告转义、覆盖保护、
实际真实上传的报告及结果失效。真实测量作为核心实验/回归背景，解析公式测试保留。
最终复核分开数据准备与特征计时，并在事件聚合前校验点预测的严格布尔类型；
新增文本 False 预测拒绝回归，修正后全套 193 项通过。未启动应用服务或执行人工视觉检查。

真实事件任务（78 事件，11 normal / 67 其他类）：MAD TP/FP/TN/FN=67/5/6/0，
precision 0.930556、recall 1、F1 0.964029、FPR 0.454545；
IF=67/11/0/0，precision 0.858974、recall 1、F1 0.924138、FPR 1。
正常真实背景明确注入任务（165 点，3 替换点）：MAD=3/9/153/0，precision 0.25、
recall 1、F1 0.4、FPR 0.055556；IF=3/70/92/0，precision 0.041096、recall 1、
F1 0.078947、FPR 0.432099。两任务不得混用单位或当作独立数据集。
四组覆盖率均为 100%，无排除；检测/评价时间来自实际运行而非估计。
固定协议参数、计时、数据来源、局限与复现见 [PHASE4_RESULT.md](examples/PHASE4_RESULT.md)。

IF 在当前参数下真实正常事件全部误报，MAD 也误报 5/11；保留此结果，不为了漂亮
指标调试留出标签。仅 11 个正常事件、单一划分及强注入不支持总体故障准确率结论。
真实 LP1 不含实测时钟，也不是 IMU；不报告其物理频谱。人工浏览器视觉检查未进行。
离线安装更新时 `--no-build-isolation` 缺少 bdist_wheel，改用标准隔离构建已成功安装；
没有修改运行依赖版本。后续为 Phase 5 完整边界/文档与课程报告提纲、实际 CI 验收，
CI 通过前不发布 v0.1.0。

## Phase 3（历史记录，已完成）

- [x] 阅读已有实现和要求，保存分阶段计划，保留用户技能及原有生成数据。
- [x] 独立 anomaly.py、不可变 DetectionConfig 与 DetectionResult。
- [x] MAD 参考中位数/鲁棒尺度、显式最小尺度、MAD=0 禁用和逐行状态。
- [x] 参考/检测区间强制不重叠，有限训练样本计数、参数/版本/来源记录。
- [x] IF 联合原始通道输入，参考拟合缩放和模型、随机种子、阈值与数值范围处理。
- [x] 相邻候选合并，正常/无效行及重复/逆序/异常间隔打断区间。
- [x] 候选区间 CSV、逐行分数 CSV、标准 JSON 配置/基准/计时导出。
- [x] Streamlit 检测表单、参考/检测范围、状态、候选选择和局部图/阈值。
- [x] “异常检测”与“信号浏览”保留质量断线并添加青色候选高亮。
- [x] scikit-learn 运行依赖安装，版本更新 0.0.4。
- [x] 核查 UCI 官方来源与 CC BY 4.0，保留 27 KB 原始 LP1 小样本及独立许可说明。
- [x] 真实记录原样/明确扰动副本回归；完整事件划分，构造时间轴明确标注。
- [x] 真实数据复现脚本、实际数量/计时、跨平台指令及局限文档。
- [x] 原始数据 SHA 检查、Git -text 属性保留原始字节；不运行下载包中程序。
- [x] 全套 pytest、ruff、格式和依赖检查通过；prompt.md 未改动。
- [x] 只将本阶段代码/小样本/文档/测试进行本地 Git 归档，不推送或发布。

### Phase 3 最终验收

2026-10-09，Windows，本项目 `.venv` 的 CPython 3.11.9：

| 检查 | 实际结果 |
| --- | --- |
| 核心测试先行 | 实现前因缺少 runlens.anomaly 失败，符合预期 |
| `python -m pytest` | **163 passed in 64.60s** |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 通过 |
| `python -m pip check` | No broken requirements found |
| `python -m runlens --version` | RunLens 0.0.4 |
| 真实数据复现脚本 | 实际生成原样/注入副本、候选/分数 CSV 与配置/汇总 JSON |
| 原始真实 fixture | 官方下载原始 SHA-256 不变，27,345 字节 |
| 原始 prompt.md | SHA-256 与前阶段一致，未改动 |
| Linux/macOS CI | **未运行**；未配置 Git 远程 |

原有 117 项测试保留通过；新增 46 项：检测器数值/特殊分布/无效值/参考隔离、
已知 IMU 尖峰、区间/高亮限制、CSV/JSON、界面交互、真实数据离线回归和
脚本覆盖保护。其中 8 项直接使用真实测量，另有真实 CSV 上传与示例脚本回归。
既检验原样实际输入，也验证显式注入尖峰/缺失值，不把不带真值的候选当准确率。

真实记录：UCI Robot Execution Failures LP1，88 个事件 / 1320 个六轴力/力矩行。
前十个 normal 事件参考（0–149），余下事件完整留出（150–1319）。
MAD 阈值 3.5、尺度下限 1：3720 条行×通道候选 / 548 区间；
IF auto、100 棵树、参考实际 150 行、种子 42：1012 个联合行候选 / 126 区间。
这只是候选数量，存在正常工况变化触发，不声称真实故障准确率。
第 150 行六轴值注入为 10000 后，两种方法均触发；原样该行未触发。
完整实际运行时间、参数与局限见 [PHASE3_RESULT.md](examples/PHASE3_RESULT.md)。

数据许可 [CC BY 4.0](THIRD_PARTY_NOTICES.md) 与项目 MIT 分开，原始 SHA：
`e146de5aeaffd864f0e57ce2fe0b58e98582c3e808e6c0e8deb9b25a54ef0cb5`。
此真实记录不是 IMU，且没有实测逐点时间戳；定位时钟明确构造，
不用于真实采样率/物理频率结论。EuRoC 官方端点连接或访问受限，本轮未完成该实验。

运行版本：RunLens 0.0.4、Streamlit 1.65.0、scikit-learn 1.9.1、SciPy 1.17.1、
Plotly 6.9.0、pandas 3.0.6、NumPy 2.4.6、pytest 8.4.2、ruff 0.16.10。
尚未进行人工浏览器视觉检查、完整分类指标或跨平台 CI 验收。

## Phase 2（历史记录，已完成）

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
- [x] Phase 3：MAD、候选区间、Isolation Forest 与拟合/检测分离、真实记录回归。
- [x] Phase 4：可复现实验、评价单位、方法比较、真实计时、结构化报告。
- [ ] Phase 5：完整边界测试、文档与课程报告提纲、CI 验收、v0.1.0。

## 当前环境与已知问题

- 默认 python 为 MSYS2 Python 3.14.5，缺少 pip/pytest 和分析依赖。
- 已下载并验证 Python Software Foundation 签名的官方 Python 3.11.9
  安装包，安装到被忽略的 `.tools/python311/`，创建 `.venv/`。
  原有 Python 与 PATH 保持原配置；IDE 应选择 `.venv/Scripts/python.exe`。
- 已安装并直接声明 Streamlit、pandas、NumPy、Plotly、SciPy、scikit-learn；
  analysis extra 保留为空兼容组，dev 组提供测试/检查工具。
- 未配置远程，不能触发 GitHub Actions。Linux/macOS 尚未验证。
- CSV 上限 20 MiB / 100000 行 / 64 列；图最多 20000 行 / 8 通道。
  超出绘图限制时需缩小范围，不自动抽稀。UI 表格和标记也有明确显示上限。
- 中位数间隔基准在多数间隔异常或分段采样率时可能不能代表期望频率。
- 窗口结果最多 50000 条窗口×通道记录、累计处理量最多 2000 万个信号值。
  采样相对容差默认 1e-6，放宽后是显式近似假设；谱能量估计不代表机械能。
- MAD/IF 逐点候选已实现，评分最多 500000 条；不直接使用窗口特征。
- 固定真实事件/注入点评价与分析报告已完成；尚未发布 v0.1.0。
- 后续测试优先真实机器人记录与明确注入副本，保留公式单元测试；
  独立事件按事件划分，无逐点真值不报告逐点准确率，无实测时钟不报告物理频率。

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

下一阶段建议：确认后进入 Phase 5，完善边界处理、文档与课程报告提纲。
实际三平台 CI 成功后再发布 v0.1.0；如获得带实测时间戳的日志，继续真实 IMU 验证。
