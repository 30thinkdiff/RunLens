# 真实数据下载与 RunLens 试用

核查日期：2026-10-10。下面只列官方来源；下载大包由使用者选择，不自动下载整套图像。
已检查网页或下载响应不等于已完整下载、校验和跑完该数据集。大型 ZIP/TAR 需先解压，
RunLens 当前上传的是 CSV，不能直接上传压缩包或 ROS bag。

## 建议从 TUM VI room1 开始

真实六轴加速度/角速度，名义 200 Hz；官方提供 EuRoC 格式，适合当前导入映射。
数据与说明：[TUM VI 官方页面](https://cvg.cit.tum.de/data/datasets/visual-inertial-dataset)。
选择 Euroc/DSO 512×512 版本，图像较小；IMU 不因图像分辨率降低而变成模拟数据。

- [room1 TAR 直接下载](https://vision.in.tum.de/tumvi/exported/euroc/512_16/dataset-room1_512_16.tar)
- [全部 EuRoC 格式序列目录](https://vision.in.tum.de/tumvi/exported/euroc/512_16/)

Windows 原生 HTTPS HEAD 实际返回 200，application/x-tar，1,707,110,400 字节（约 1.59 GiB）。
本机 Python 标准库检查遇到证书链问题，Windows 证书验证成功；不建议关闭证书校验。
解压后寻找 `mav0/imu0/data.csv`，保留表头与大整数时间戳，时间单位选 **ns**。
选择三个角速度和三个加速度通道；不要选相机帧列表或把时间列当信号。
数据许可 CC BY 4.0，引用官方页面和论文。

## EuRoC MAV：真实无人机 IMU

- [官方介绍与最新入口](https://projects.asl.ethz.ch/datasets/euroc-mav/)
- [ETH Research Collection 下载页](https://www.research-collection.ethz.ch/entities/researchdata/bcaf173e-5dac-484b-bc37-faf97a594f1f)

ETH 官方已说明数据文件迁移至 Research Collection；不要只依赖旧 robotics.ethz.ch 链接。
本次 Windows HEAD 验证新下载页返回 200；没有完整下载各压缩包。先选 MH_01_easy 或
V1_01_easy 的 ASL/EuRoC 文件格式，而不是 bag；解压后使用 `mav0/imu0/data.csv`。
IMU 名义 200 Hz；时间列通常 `#timestamp [ns]`，六通道为 angular velocity / acceleration，
在网页中手动选择实际表头，时间单位 **ns**。下载时查看对应文件的许可和引用要求，
本项目不把第三方数据归入 MIT，也不在未经核对许可时再分发。

## UCI Robot Execution Failures：小型真实机器人力/力矩

- [官方说明](https://archive.ics.uci.edu/dataset/138/robot+execution+failures)
- [完整 ZIP 直接下载](https://archive.ics.uci.edu/static/public/138/robot+execution+failures.zip)

官方约 58 KB；实际 GET 返回 200，前缀为 ZIP 魔数。包含 LP1–LP5 和说明，每事件 15 点
六轴力/力矩。`.data` 不是普通 CSV，不能直接上传；项目已支持 LP1 适配与真实实验复现。
使用 `examples/analyze_anomalies.py` 导出 LP1 分析 CSV，参数见 `--help` 和 examples/README.md。
例如：`python examples/analyze_anomalies.py --output examples/generated/try-real-lp1`，
再上传输出的原始测量 CSV；时间列 `synthetic_time_s`，单位 s，选择 Fx/Fy/Fz/Tx/Ty/Tz。
未核对转换器对 LP2–LP5 的支持，不能假设可直接混用。数据没有实测逐点时钟，构造的
显示时间要明确标注，不用于物理频谱；事件标签也不是逐点故障真值。许可 CC BY 4.0。
ZIP 中的 a.out 是历史可执行文件，试用只需读取数据和说明，无需运行它。

## UZH-FPV：剧烈运动背景

- [官方序列与下载表](https://fpv.ifi.uzh.ch/datasets/)
- [Indoor forward 3 DAVIS ZIP](https://download.ifi.uzh.ch/rpg/web/datasets/uzh-fpv-newer-versions/v3/indoor_forward_3_davis_with_gt.zip)

真实竞速四旋翼 IMU 和相机数据。上列包实际返回 206，ZIP 头正确，总大小
415,378,875 字节（约 396 MiB），仅检查前 512 字节；没有下载整包。
选 ZIP 文本版本，按包内 IMU 文件说明整理为含数值时间列和六轴通道的 CSV；
不能直接导入 rosbag，也不要凭列序猜时间单位。单位按实际说明选择 s 或 ns。
适合观察正常剧烈运动引起的统计告警，不能把大幅运动自动当作硬件故障。
数据许可 CC BY-NC-SA 3.0，适用于非商业研究试用；未来产品用途要单独核对许可。

## 导入前截取与设置

CSV 上限 20 MiB / 100000 行 / 64 列；图最多 20000 行 / 8 通道。
长序列先取连续前 20000 行用于试用，不改变原文件，不随机抽样或打乱时间。
以下示例只创建副本，所有列按字符串读取，避免纳秒时间戳经浮点转化丢失精度。
把输入路径改为解压后实际位置，输出放在被 Git 忽略的 `data/`。

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; import pandas as pd; src=Path('data/room1/mav0/imu0/data.csv'); dst=Path('data/room1_imu_20000.csv'); assert not dst.exists(), '输出已存在，请另选文件名'; frame=pd.read_csv(src, dtype=str, keep_default_na=False, nrows=20000); frame.to_csv(dst, index=False, encoding='utf-8', mode='x')"
```

打开 RunLens → CSV 上传 → 时间列与六轴映射 → 明确时间单位 → 质量检查 → 信号浏览。
频谱拒绝不规则采样时先查看质量证据，不随意放宽容差来“做出频谱”。
MAD/IF 选择互不重叠的参考/检测区间；参考应是已知正常且工况接近的片段。
这些 IMU 数据的运动轨迹真值不能作为传感器故障标签，未提供故障真值时只观察候选，
不报告故障检测准确率。
