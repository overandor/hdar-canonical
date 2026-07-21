"""Canonical worker module — part of the HDAR demo workspace.

This file is sealed into the capsule and restored on Host B.
It is not executed directly by the pipeline; it serves as a
content-addressed source artifact that must survive transport.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_records(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text().strip().split("\n")
        if line.strip()
    ]


def filter_valid(records: list[dict]) -> tuple[list[dict], list[dict]]:
    valid, rejected = [], []
    for r in records:
        if not r.get("id") or not r.get("category") or "value" not in r:
            rejected.append({"id": r.get("id", "unknown"), "reason": "missing_fields"})
        elif not isinstance(r["value"], (int, float)) or r["value"] < 0:
            rejected.append({"id": r["id"], "reason": "invalid_value"})
        else:
            valid.append(r)
    return valid, rejected


def aggregate(valid: list[dict]) -> dict:
    from collections import defaultdict
    by_cat: dict[str, list[float]] = defaultdict(list)
    for r in valid:
        by_cat[r["category"]].append(r["value"])
    stats = {}
    for cat, vals in sorted(by_cat.items()):
        stats[cat] = {
            "count": len(vals),
            "sum": round(sum(vals), 4),
            "mean": round(sum(vals) / len(vals), 4),
            "min": min(vals),
            "max": max(vals),
            "median": sorted(vals)[len(vals) // 2],
        }
    return stats
