#!/usr/bin/env python3
"""
generate_task_master.py

Builds a single master CSV summarizing every task in WebArena's config_files/
directory: which site(s) it targets, whether it's single-site or cross-site,
how it gets evaluated, and its full intent text.

Usage:
    python3 scripts/generate_task_master.py
    python3 scripts/generate_task_master.py --config-dir config_files --output webarena_task_master.csv
    python3 scripts/generate_task_master.py --num-tasks 812

Run this from the root of the webarena repo (or pass --config-dir explicitly).
"""

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Categorize WebArena tasks by site, cross-site status, and eval type."
    )
    parser.add_argument(
        "--config-dir",
        type=str,
        default="config_files",
        help="Directory containing the per-task JSON configs (default: config_files)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="webarena_task_master.csv",
        help="Output CSV path (default: webarena_task_master.csv)",
    )
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=812,
        help="Number of task IDs to scan, 0..N-1 (default: 812, the official WebArena set)",
    )
    return parser.parse_args()


def load_task_config(config_dir: Path, task_id: int) -> dict | None:
    """Load a single task's config JSON. Returns None if missing or malformed."""
    config_path = config_dir / f"{task_id}.json"
    try:
        with open(config_path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def build_row(task_id: int, config: dict) -> dict:
    """Turn one task's config into a flat CSV row."""
    sites = config.get("sites", [])
    eval_types = config.get("eval", {}).get("eval_types", [])
    return {
        "task_id": task_id,
        "category": "cross-site" if len(sites) > 1 else "single-site",
        "num_sites": len(sites),
        "sites": "+".join(sites),
        "eval_types": "+".join(eval_types),
        "intent": config.get("intent", ""),
        "require_login": config.get("require_login", ""),
        "require_reset": config.get("require_reset", ""),
    }


def main() -> None:
    args = parse_args()
    config_dir = Path(args.config_dir)

    rows = []
    for task_id in range(args.num_tasks):
        config = load_task_config(config_dir, task_id)
        if config is None:
            continue
        rows.append(build_row(task_id, config))

    rows.sort(key=lambda r: r["task_id"])

    fieldnames = [
        "task_id", "category", "num_sites", "sites",
        "eval_types", "intent", "require_login", "require_reset",
    ]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    single_site = sum(1 for r in rows if r["category"] == "single-site")
    cross_site = sum(1 for r in rows if r["category"] == "cross-site")

    print(f"Total tasks:     {len(rows)}")
    print(f"Single-site:     {single_site}")
    print(f"Cross-site:      {cross_site}")
    print(f"Saved to:        {args.output}")


if __name__ == "__main__":
    main()
