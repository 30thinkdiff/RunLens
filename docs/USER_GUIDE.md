# RunLens 中文使用指南

## 当前能做什么

Phase 0 提供可安装的 Python 包、版本命令和 Streamlit 初始化页。
CSV 导入、曲线、质量检查、特征、检测及导出从后续阶段开始实现。
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
初始化页显示版本和阶段说明；终端 Ctrl+C 停止服务。
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
后续开发用 `.[analysis,dev]` 安装完整分析依赖。

## Git 与阶段推进

仓库已初始化，保留现有分支和用户文件。`.gitignore` 排除环境、缓存、
私有配置以及 `data/`、`reports/`；不要把真实实验数据或密钥直接提交。
本地提交不等于公开发布。本轮只完成 Phase 0，确认后再开发 Phase 1。

三平台 CI 配置不是已通过的证据。实际测试结果与尚未验证内容见
[TASKS.md](../TASKS.md)。
