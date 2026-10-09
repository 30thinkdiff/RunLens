# RunLens 任务与验证状态

当前阶段：**Phase 0 — 环境与项目初始化（已完成本地验收）**。
等待用户确认 Phase 1，不提前实现后续算法。

## Phase 0

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

- [ ] Phase 1：CSV 导入/映射、相对时间、质量检查、Plotly 曲线、合成数据与标签。
- [ ] Phase 2：窗口特征、三轴模长、FFT/Welch、特征 CSV 导出。
- [ ] Phase 3：MAD、候选区间、Isolation Forest 与拟合/评估分离。
- [ ] Phase 4：可复现实验、评价单位、方法比较、真实计时、结构化报告。
- [ ] Phase 5：完整边界测试、文档与课程报告提纲、CI 验收、v0.1.0。

## 环境与已知问题

- 默认 python 为 MSYS2 Python 3.14.5，缺少 pip/pytest 和分析依赖。
- 已下载并验证 Python Software Foundation 签名的官方 Python 3.11.9
  安装包，安装到被忽略的 `.tools/python311/`，创建 `.venv/`。
  原有 Python 与 PATH 保持原配置；IDE 应选择 `.venv/Scripts/python.exe`。
- Phase 0 只安装 Streamlit 和开发工具；analysis 可选依赖组已声明但未安装。
  Streamlit 间接安装的分析库不表示后续分析模块已实现或已验证。
- 未配置远程，不能触发 GitHub Actions。Linux/macOS 尚未验证。
- Phase 0 不提供 CSV 分析或演示数据，不发布 v0.1.0。

## 验证记录

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

下一阶段建议：用户确认后实施 CSV 导入、显式列/时间单位映射、精确相对时间、
基础质量报告与 Plotly 曲线，并提供固定种子的 Synthetic Data 和边界测试。
