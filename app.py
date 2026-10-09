"""RunLens Phase 0 startup page; analytical features arrive in later phases."""

import streamlit as st

from runlens import __version__


def main() -> None:
    """Render a small, runnable initialization page."""
    st.set_page_config(page_title="RunLens", page_icon="📈", layout="wide")
    st.title("RunLens")
    st.caption(f"Robot Time-Series Analysis Toolkit · v{__version__}")
    st.info("Phase 0 · 项目初始化：Python 包和启动页已建立。")
    st.write("下一阶段将支持 CSV 导入、时间戳与通道选择、信号查看和基础质量检查。")
    st.write(
        "当前版本尚未提供数据分析功能。安装与测试方法见 README.md 和中文用户指南。"
    )


if __name__ == "__main__":
    main()
