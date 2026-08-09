#!/usr/bin/env python3
"""Generate a conservative project handoff document from local evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".next"}
INTERESTING = {"README.md", "AGENTS.md", "pyproject.toml", "package.json", "requirements.txt", "Cargo.toml", "go.mod", "docker-compose.yml", "Dockerfile"}
SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|password|secret|private[_-]?key)\s*[:=]\s*[^\s,;]+")


def run_git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    if result.returncode != 0:
        return "unavailable"
    value = (result.stdout or result.stderr).strip()
    return value or "clean/empty"


def safe_excerpt(path: Path, max_chars: int = 1200) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError:
        return "unreadable"
    return SECRET_RE.sub(r"\1=<redacted>", text)


def project_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(files):
            path = Path(current) / name
            if path.is_symlink():
                continue
            found.append(path.relative_to(root))
            if len(found) >= 200:
                return found
    return found


def todo_lines(root: Path, files: list[Path]) -> list[str]:
    hits: list[str] = []
    for rel in files:
        if rel.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".md", ".yml", ".yaml", ".toml"}:
            continue
        try:
            lines = (root / rel).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for index, line in enumerate(lines, 1):
            if re.search(r"\b(TODO|FIXME|XXX)\b", line, re.IGNORECASE):
                hits.append(f"`{rel}:{index}`: {line.strip()[:180]}")
                if len(hits) >= 30:
                    return hits
    return hits


def usage_text(snapshot: dict[str, Any] | None, evaluation: dict[str, Any] | None) -> str:
    if not snapshot or not evaluation:
        return "No verified usage snapshot was supplied. Quota-trigger evidence is unavailable."
    fields = [
        f"- Provider: `{evaluation.get('provider', 'unknown')}`",
        f"- Window: `{evaluation.get('window', 'unspecified')}`",
        f"- Remaining: `{evaluation.get('remaining_percent')}%`",
        f"- Threshold: `< {evaluation.get('threshold_percent')}%`",
        f"- Captured at: `{evaluation.get('captured_at') or 'not supplied'}`",
        f"- Source: `{evaluation.get('source') or 'not supplied'}`",
        f"- Calculation: `{evaluation.get('calculation')}`",
    ]
    return "\n".join(fields)


def generate(root: Path, output: Path, snapshot: dict[str, Any] | None = None, evaluation: dict[str, Any] | None = None) -> Path:
    root = root.resolve()
    files = project_files(root)
    interesting = [p for p in files if p.name in INTERESTING][:20]
    todos = todo_lines(root, files)
    display_output = output if output.is_absolute() else root / output
    display_output.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Project Handoff",
        "",
        f"> Generated at {datetime.now(timezone.utc).isoformat()} from local repository evidence.",
        "> Treat this file as a continuation aid; verify commands and assumptions before changing production systems.",
        "",
        "## Quota trigger evidence",
        "",
        usage_text(snapshot, evaluation),
        "",
        "## Project identity",
        "",
        f"- Root: `{root}`",
        f"- Project name: `{root.name}`",
        f"- Git branch: `{run_git(root, 'branch', '--show-current')}`",
        f"- Git commit: `{run_git(root, 'rev-parse', '--short', 'HEAD')}`",
        f"- Working tree: `{run_git(root, 'status', '--short')}`",
        "",
        "## Files to inspect first",
        "",
    ]
    if interesting:
        lines.extend(f"- `{path}`" for path in interesting)
    else:
        lines.append("- No standard project manifest or README was found; inspect the file tree below.")
    lines.extend(["", "## Repository snapshot", "", f"- Files discovered (capped at 200): `{len(files)}`", ""])
    for rel in files[:80]:
        lines.append(f"- `{rel}`")
    lines.extend(["", "## Evidence excerpts", ""])
    if interesting:
        for rel in interesting[:5]:
            lines.extend([f"### `{rel}`", "", "```text", safe_excerpt(root / rel), "```", ""])
    else:
        lines.append("No standard evidence files were available for an excerpt.")
    lines.extend(["", "## Pending markers", ""])
    lines.extend(todos or ["No TODO/FIXME markers were found in the scanned text files."])
    lines.extend([
        "",
        "## Validation and continuation",
        "",
        "- Commands run by this generator: local read-only file scan and, when available, `git branch`, `git rev-parse`, and `git status`.",
        "- Tests/build/deployment were not run by this generator; record exact verified commands here before relying on them.",
        "- Next agent: read the repository instructions, confirm the current branch and working-tree changes, then continue from the pending work above.",
        "- Unverified assumptions: this baseline does not infer product behavior, deployment health, credentials, or quota availability.",
        "",
    ])
    display_output.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return display_output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output", default="HANDOFF.md")
    parser.add_argument("--usage-json")
    args = parser.parse_args()

    snapshot = None
    evaluation = None
    if args.usage_json:
        snapshot = json.loads(Path(args.usage_json).read_text(encoding="utf-8-sig"))
        from check_usage import evaluate

        evaluation = evaluate(snapshot, 5.0)
    output = generate(Path(args.project_root), Path(args.output), snapshot, evaluation)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
