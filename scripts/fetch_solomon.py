"""Download Solomon RC1/RC2 benchmark instances.

Source: https://github.com/jonzhaocn/VRPTW-ACO-python/tree/master/solomon-100
Format is compatible with `vrptw_clean.load_datasets`.

Usage:
    uv run python scripts/fetch_solomon.py
    uv run python scripts/fetch_solomon.py --dest data/solomon
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

BASE_URL = "https://raw.githubusercontent.com/jonzhaocn/VRPTW-ACO-python/master/solomon-100"
INSTANCES = [f"rc10{i}" for i in range(1, 9)] + [f"rc20{i}" for i in range(1, 9)]


def download_one(client: httpx.Client, name: str, dest_dir: Path) -> Path:
    out_path = dest_dir / f"{name}.txt"
    if out_path.exists() and out_path.stat().st_size > 0:
        return out_path

    url = f"{BASE_URL}/{name}.txt"
    resp = client.get(url, timeout=30.0)
    resp.raise_for_status()
    out_path.write_text(resp.text, encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", default="data/solomon", help="Output directory")
    args = parser.parse_args()

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    with httpx.Client(follow_redirects=True) as client:
        for name in INSTANCES:
            try:
                path = download_one(client, name, dest)
                print(f"  ok  {path}")
            except httpx.HTTPError as exc:
                print(f"  fail {name}: {exc}", file=sys.stderr)
                return 1

    print(f"\nDone. {len(INSTANCES)} instances in {dest.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
