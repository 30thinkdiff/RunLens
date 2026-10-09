# Phase 5 实际验收记录

2026-10-09，RunLens 0.0.6。本地 Windows AMD64 / CPython 3.11.9 已验收，
GitHub 仓库 origin 已连接；三平台 CI 和 v0.1.0 发布尚待实际执行。

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
课程与技术材料见 [课程提纲](../docs/COURSE_REPORT_OUTLINE.md)、
[技术交底提纲](../docs/TECHNICAL_DISCLOSURE_OUTLINE.md)。
