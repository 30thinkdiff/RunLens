# Phase 5 实际验收记录

2026-10-09，RunLens 0.0.6。本地 Windows AMD64 / CPython 3.11.9 已验收，
GitHub 仓库 origin 已连接；0.0.6 首轮三平台 CI 已实际成功。
0.1.0 已重新通过本地与三平台检查，正式标签和发布页已创建，核心 wheel 已上传。

| 检查 | 实际结果 |
| --- | --- |
| 完整 pytest | **219 passed in 92.04s**，JUnit 保存到 generated/phase5/junit.xml |
| ruff / format | All checks passed / 58 files already formatted |
| pip check / version | No broken requirements found / RunLens 0.0.6 |
| wheel | 独立 -I 进程直接导入 wheel 内模块并执行真实流程 |
| 真实 wheel 流程 | 1320 行、528 条时域特征、7020 条评分、报告 schema 2 |
| 固定实验 | 实际导出 23 文件；四组混淆计数与 Phase 4 相同 |
| 原始数据/需求 | LP1 与 prompt.md SHA-256 保持不变 |
| 人工视觉检查 | 未执行，AppTest 是无浏览器交互验证 |

新增 26 项测试：20 项输入/文件边界、5 项真实记录来源一致性、1 项核心升级后的
页面失效。先验证缺口可复现，再实现修复。完整检查另发现结果失效时报告未同步清除；
修正后专项与完整测试通过。配置拒绝错误类型/布尔数值/非有限参数，冻结列表配置。
文件实际读取最多上限加一字节，拒绝文本流。来源覆盖质量、特征、检测及空特征；
规范化 LF 指纹跨平台稳定，相同字节改变映射也拒绝旧结果。报告 schema 更新为 2。

wheel SHA-256（0.0.6）：
`773e49e983ab066c5b77119ffb64ce782bcb0fe7ec2f07e55cedaf1b9ad324af`。
该检查使用现有第三方依赖，不能当作全新空环境安装。wheel 仅含核心；网页与 fixture
从完整 Git 源码使用。生成物在 ignored 的 `generated/phase5/`，不覆盖 Phase 4。

| 任务 | 方法 | TP / FP / TN / FN | Precision | Recall | F1 | FPR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 78 个真实事件 | MAD | 67 / 5 / 6 / 0 | 0.930556 | 1 | 0.964029 | 0.454545 |
| 78 个真实事件 | IF | 67 / 11 / 0 / 0 | 0.858974 | 1 | 0.924138 | 1 |
| 165 个明确注入背景点 | MAD | 3 / 9 / 153 / 0 | 0.25 | 1 | 0.4 | 0.055556 |
| 165 个明确注入背景点 | IF | 3 / 70 / 92 / 0 | 0.041096 | 1 | 0.078947 | 0.432099 |

四组覆盖率 1，无排除；检测参数和固定划分没有重新调优。两项任务共享正常背景，
不代表独立数据集。真实正常事件仅 11 个；IF 全部误报，MAD 误报 5 个。LP1 为六轴
力/力矩，示例时钟构造，不是实测 IMU，不报告物理频谱或总体硬件故障准确率。
固定协议和许可见 [PHASE4_RESULT.md](PHASE4_RESULT.md)、[第三方说明](../THIRD_PARTY_NOTICES.md)。

复现命令、平台证据与发布清单见 [VALIDATION.md](../docs/VALIDATION.md)。
首次实际 CI 的 Windows/Ubuntu/macOS 三 job 均成功。历史清理后旧运行已移除，
首轮计时保留为历史记录，现行证据采用清理后重新执行的 CI。
实际下载三个平台 artifact 验证：每份 JUnit 219 项、0 失败/错误/跳过，四组计数及
覆盖率与本地一致；JUnit 耗时 Windows 79.602s、Ubuntu 78.624s、macOS 63.526s。
实际环境 Windows CPython 3.11.9 AMD64、Linux 3.11.17 x86_64、Darwin 3.11.9 arm64，
运行直接依赖与 requirements-verified.txt 一致。记录的是本次 runner 范围，不代表
所有系统发行版与架构；跨系统速度差不能解释为算法性能改进。
最终 v0.1.0 发布页附该版本实际 CI 与准确标签提交，不能移用首轮版本的验收结论。

0.1.0 本地重新验收：**219 passed in 83.25s**，ruff/格式/pip check 通过，版本命令
输出 RunLens 0.1.0；独立 wheel 实测流程仍为 1320 行、528 特征、7020 评分、schema 2，
固定真实实验重新导出 23 文件，计数一致。0.1.0 wheel SHA-256：
`6e9ad00dbd240a8e992dde06b9f4f7fa55406133cf9b0a7393afc4446b8d084e`。
此处为历史清理后替换发布附件的最新指纹；核心模块保持不变，替换的是公开说明元数据。
正式标签在该版本自身三平台 CI 成功后创建；最终记录见
[发布页](https://github.com/30thinkdiff/RunLens/releases/tag/v0.1.0)。

## 正式发布最终证据

[v0.1.0](https://github.com/30thinkdiff/RunLens/releases/tag/v0.1.0) 已公开发布，
清理后标签精确指向 `b54e129a03a02d1a69a02525d26f90b322a5afb0`。
该版本 [CI 37955842348](https://github.com/30thinkdiff/RunLens/actions/runs/37955842348)
三 job 均 success；实际下载三个产物，每平台 219 项测试且失败/错误/跳过 0。
报告版本均为 0.1.0，四组混淆计数、覆盖率与规范化数据身份跨平台一致。

| 发布平台 | CPython / 架构 | JUnit 秒数 | 实际结果 |
| --- | --- | --- | --- |
| Windows | 3.11.9 / AMD64 | 86.688 | 219 passed |
| Ubuntu | 3.11.17 / x86_64 | 79.272 | 219 passed |
| macOS | 3.11.9 / arm64 | 64.772 | 219 passed |

GitHub Release ID 408064518；附件
[runlens-0.1.0-py3-none-any.whl](https://github.com/30thinkdiff/RunLens/releases/download/v0.1.0/runlens-0.1.0-py3-none-any.whl)。
安装方式、准确 CI 与已知误报/时钟限制均随发布说明提供；不发布 PyPI。
原发布后的历史记录计时保留；用户授权清理提示词后，标签与分支均已重写，
重写后的标签另行通过三平台验收。旧运行和 SHA 链接不再公开保存。
全新远程镜像克隆及实际 GitHub 源码 ZIP 均不含本地任务提示词。开发者本地文件保留并忽略。
用户确认以新下载/克隆不包含文件为目标，不申请服务器缓存清理。
课程与技术材料见 [课程提纲](../docs/COURSE_REPORT_OUTLINE.md)、
[技术交底提纲](../docs/TECHNICAL_DISCLOSURE_OUTLINE.md)。
