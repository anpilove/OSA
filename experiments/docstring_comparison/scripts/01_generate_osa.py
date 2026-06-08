#!/usr/bin/env python3
"""Генерация docstring через OSA legacy (ветка main).

Переключает локальный клон OSA на main, импортирует его, и прогоняет
осу против data/requests_osa. Docstring'и пишутся inplace.
"""
from __future__ import annotations

import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

from common import bootstrap, resolve

cfg = bootstrap()


def checkout_branch(repo: Path, branch: str) -> str:
    """Переключает репо на нужную ветку, возвращает предыдущую."""
    prev = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    if prev != branch:
        print(f"→ checkout {branch} (было: {prev})")
        subprocess.run(["git", "checkout", branch], cwd=repo, check=True)
    return prev


def run_osa(target: Path, model: str, base_url: str) -> None:
    """Прогоняет OSA через её CLI main()."""
    from osa_tool.run import main

    sys.argv = [
        "osa_tool.run",
        "--no-fork", "--no-pull-request",
        "-r", str(target),
        "--api", "openai",
        "--base-url", base_url,
        "--model", model,
        "--mode", "auto",
        "--docstring",
    ]
    main()


def main() -> int:
    osa_repo = resolve(cfg["variants"]["osa"]["repo_path"])
    target = resolve(cfg["variants"]["osa"]["output_dir"])
    branch = cfg["variants"]["osa"]["branch"]
    model = cfg["llm"]["model"]
    base_url = cfg["llm"]["base_url"]

    if not target.exists():
        print(f"✗ {target} не существует. Запусти `make clone`.", file=sys.stderr)
        return 1

    sys.path.insert(0, str(osa_repo))
    prev = checkout_branch(osa_repo, branch)

    try:
        print(f"→ Запуск OSA legacy ({branch}) на {target}")
        run_osa(target, model, base_url)
    finally:
        if prev and prev != branch:
            print(f"→ восстанавливаю ветку {prev}")
            subprocess.run(["git", "checkout", prev], cwd=osa_repo, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
