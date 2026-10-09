"""Minimal command-line entry point for installation verification."""

import argparse

from runlens import __version__


def main() -> None:
    """Show project information or the installed version."""
    parser = argparse.ArgumentParser(
        prog="runlens",
        description="RunLens — robot time-series analysis toolkit (Phase 0).",
        epilog="Start the initialization page with: python -m streamlit run app.py",
    )
    parser.add_argument("--version", action="version", version=f"RunLens {__version__}")
    parser.parse_args()
    parser.print_help()


if __name__ == "__main__":
    main()
