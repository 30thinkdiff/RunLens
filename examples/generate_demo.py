"""Generate labeled Synthetic Data without external downloads."""

import argparse
import json
from pathlib import Path

from runlens.demo import generate_demo


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate RunLens Synthetic Data and injection labels."
    )
    parser.add_argument("--output", type=Path, default=Path("examples") / "generated")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--sample-rate", type=float, default=100.0)
    parser.add_argument("--vibration", action="store_true")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly replace existing example outputs.",
    )
    args = parser.parse_args()
    paths = [
        args.output / name
        for name in (
            "synthetic_imu.csv",
            "synthetic_labels.csv",
            "synthetic_metadata.json",
        )
    ]
    if not args.overwrite and any(path.exists() for path in paths):
        parser.error(
            "Output exists. Use another --output directory "
            "or explicitly pass --overwrite."
        )
    demo = generate_demo(
        seed=args.seed,
        sample_count=args.samples,
        sample_rate=args.sample_rate,
        vibration=args.vibration,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    mode = "w" if args.overwrite else "x"
    with paths[0].open(mode, encoding="utf-8", newline="") as stream:
        demo.data.to_csv(stream, index=False)
    with paths[1].open(mode, encoding="utf-8", newline="") as stream:
        demo.labels.to_csv(stream, index=False)
    with paths[2].open(mode, encoding="utf-8") as stream:
        json.dump(demo.metadata, stream, ensure_ascii=False, indent=2)
    print(
        f"Synthetic Data: {len(demo.data)} rows, "
        f"{len(demo.labels)} injection reference labels."
    )
    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
