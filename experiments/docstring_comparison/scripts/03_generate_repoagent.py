#!/usr/bin/env python3
"""Генерация документации через RepoAgent.

В отличие от OSA, RepoAgent не пишет docstring внутрь .py файлов.
Он создаёт markdown_docs/ и .project_doc_record/project_hierarchy.json
рядом с целевым репозиторием. extract_pairs.py читает из этого JSON.
"""
from __future__ import annotations

import sys
from pathlib import Path

from common import bootstrap, resolve

cfg = bootstrap()


def main() -> int:
    ra_repo = resolve(cfg["variants"]["ra"]["repo_path"])
    target = resolve(cfg["variants"]["ra"]["output_dir"])
    model = cfg["llm"]["model"]
    base_url = cfg["llm"]["base_url"]
    temperature = cfg["llm"]["temperature"]

    if not target.exists():
        print(f"✗ {target} не существует. Запусти `make clone`.", file=sys.stderr)
        return 1

    sys.path.insert(0, str(ra_repo))

    from repo_agent.settings import SettingsManager
    from repo_agent.runner import Runner

    print(f"→ Запуск RepoAgent на {target}")
    SettingsManager.initialize_with_params(
        target_repo=str(target),
        hierarchy_name=".project_doc_record",
        markdown_docs_name="markdown_docs",
        ignore_list=[],
        language="English",
        log_level="INFO",
        model=model,
        temperature=temperature,
        request_timeout=60,
        openai_base_url=base_url,
        max_thread_count=4,
    )
    Runner().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
