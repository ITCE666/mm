#!/usr/bin/env python3
"""Normalize a provider usage snapshot and optionally generate a handoff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_snapshot(source: str) -> dict[str, Any]:
    if source == "-":
        raw = sys.stdin.read()
    else:
        # PowerShell's default Set-Content may emit a UTF-8 BOM.
        raw = Path(source).read_text(encoding="utf-8-sig")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("usage snapshot must be a JSON object")
    return value


def number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def remaining_percent(snapshot: dict[str, Any]) -> tuple[float | None, str]:
    direct = number(snapshot.get("remaining_percent"))
    if direct is not None:
        return direct, "remaining_percent"

    limit = number(snapshot.get("limit"))
    remaining = number(snapshot.get("remaining"))
    if limit is not None and remaining is not None and limit > 0:
        return remaining / limit * 100, "remaining/limit"

    used = number(snapshot.get("used"))
    if limit is not None and used is not None and limit > 0:
        return (limit - used) / limit * 100, "used/limit"

    used_percent = number(snapshot.get("used_percent"))
    if used_percent is not None:
        return 100 - used_percent, "used_percent"

    return None, "missing remaining_percent or a supported numerator/limit pair"


def evaluate(snapshot: dict[str, Any], threshold: float) -> dict[str, Any]:
    percent, method = remaining_percent(snapshot)
    provider = str(snapshot.get("provider") or "unknown")
    window = str(snapshot.get("window") or "unspecified")
    result: dict[str, Any] = {
        "provider": provider,
        "window": window,
        "threshold_percent": threshold,
        "remaining_percent": None if percent is None else round(percent, 4),
        "calculation": method,
        "captured_at": snapshot.get("captured_at"),
        "source": snapshot.get("source"),
        "status": "unknown",
        "should_handoff": False,
    }
    if percent is None:
        result["reason"] = method
        return result

    if percent < 0 or percent > 100:
        result["reason"] = "remaining percentage must be between 0 and 100"
        return result

    result["status"] = "low" if percent < threshold else "ok"
    result["should_handoff"] = result["status"] == "low"
    result["reason"] = f"remaining {percent:.2f}% is {'below' if percent < threshold else 'at or above'} {threshold:.2f}%"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="-", help="JSON file path, or - for stdin")
    parser.add_argument("--threshold", type=float, default=5.0)
    parser.add_argument("--project-root", help="Generate a handoff when status is low")
    parser.add_argument("--handoff-output", help="Output path for the generated handoff")
    args = parser.parse_args()

    if not 0 < args.threshold <= 100:
        parser.error("--threshold must be greater than 0 and at most 100")
    try:
        snapshot = load_snapshot(args.input)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "unknown", "should_handoff": False, "reason": str(exc)}, ensure_ascii=False))
        return 2

    result = evaluate(snapshot, args.threshold)
    if result["should_handoff"] and args.project_root and args.handoff_output:
        from generate_handoff import generate

        output = generate(Path(args.project_root), Path(args.handoff_output), snapshot, result)
        result["handoff_output"] = str(output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
