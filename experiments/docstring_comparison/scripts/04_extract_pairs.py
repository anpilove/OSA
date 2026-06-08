#!/usr/bin/env python3
"""Извлекает docstring'и из трёх вариантов и строит файлы пар для оценки.

OSA / OSA-C — inline docstring в .py файлах (читаются через ast.get_docstring).
RepoAgent  — отдельный JSON .project_doc_record/project_hierarchy.json,
              ключ — относительный путь, внутри список объектов с name/md_content.

На выходе три файла в results/pairs/:
  all_comparisons_osa_vs_osa_c.json
  all_comparisons_osa_c_vs_ra.json
  all_comparisons_osa_vs_ra.json

Каждая запись:
{
  "file_path", "function_name", "class_name", "signature",
  "source_code",          # из A-варианта (без docstring)
  "osa_docstring",        # docstring A
  "osa_enhanced_docstring", # docstring B
  "line_number"
}
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from common import bootstrap, resolve

cfg = bootstrap()
ROOT = Path(__file__).resolve().parent.parent


# ---------- Извлечение из inline-docstring (OSA / OSA-C) ----------

@dataclass
class FunctionInfo:
    file_path: str
    function_name: str
    class_name: Optional[str]
    signature: str
    source_code: str
    docstring: Optional[str]
    line_number: int


def extract_function(node: ast.AST, source_lines: List[str], file_path: str,
                     class_name: Optional[str]) -> Optional[FunctionInfo]:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    docstring = ast.get_docstring(node)
    args = [a.arg for a in node.args.args]
    signature = f"def {node.name}({', '.join(args)}):"
    start = node.lineno - 1
    end = getattr(node, "end_lineno", node.lineno)
    source_code = "\n".join(source_lines[start:end])
    return FunctionInfo(
        file_path=file_path,
        function_name=node.name,
        class_name=class_name,
        signature=signature,
        source_code=source_code,
        docstring=docstring,
        line_number=node.lineno,
    )


def extract_inline(directory: Path) -> Dict[str, List[FunctionInfo]]:
    """Обходит .py файлы и собирает функции/методы (только с docstring)."""
    results: Dict[str, List[FunctionInfo]] = {}
    for py in directory.rglob("*.py"):
        if "test" in py.name.lower() or py.name == "__init__.py" and py.stat().st_size == 0:
            continue
        try:
            text = py.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(py))
            lines = text.splitlines()
        except Exception as e:
            print(f"  пропуск {py}: {e}")
            continue

        rel = str(py.relative_to(directory))
        funcs: List[FunctionInfo] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    info = extract_function(item, lines, rel, node.name)
                    if info and info.docstring:
                        funcs.append(info)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # пропускаем методы — их соберёт ветка ClassDef
                in_class = any(
                    isinstance(p, ast.ClassDef) and node in getattr(p, "body", [])
                    for p in ast.walk(tree)
                )
                if in_class:
                    continue
                info = extract_function(node, lines, rel, None)
                if info and info.docstring:
                    funcs.append(info)
        if funcs:
            results[rel] = funcs
    return results


# ---------- Извлечение из RepoAgent project_hierarchy.json ----------

DOCSTRING_RE = re.compile(
    r"\*\*(?P<name>[^\*]+)\*\*:\s*(?P<text>.+?)(?=\n\n\*\*|\Z)",
    re.DOTALL,
)


def _build_class_index(src_text: str) -> Dict[Tuple[int, str], Optional[str]]:
    """(line_no, function_name) -> class_name|None — достаёт из AST.

    Нужно потому что RepoAgent в hierarchy.json не пишет parent class.
    """
    idx: Dict[Tuple[int, str], Optional[str]] = {}
    try:
        tree = ast.parse(src_text)
    except SyntaxError:
        return idx
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    idx[(item.lineno, item.name)] = node.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            idx.setdefault((node.lineno, node.name), None)
    return idx


def extract_repoagent(hierarchy_file: Path, target_root: Path) -> Dict[str, List[FunctionInfo]]:
    """Парсит project_hierarchy.json. Ключи верхнего уровня — относительные
    пути файлов; внутри список объектов с name/type/md_content/code_start_line.
    Имена классов RepoAgent не сохраняет, поэтому достаём их из AST исходника.
    """
    if not hierarchy_file.exists():
        raise FileNotFoundError(
            f"Нет {hierarchy_file}. Запусти `make generate-ra` сначала."
        )
    raw = json.loads(hierarchy_file.read_text(encoding="utf-8"))
    results: Dict[str, List[FunctionInfo]] = {}

    for rel, entries in raw.items():
        py_path = target_root / rel
        try:
            src_text = py_path.read_text(encoding="utf-8")
            src_lines = src_text.splitlines()
        except FileNotFoundError:
            continue

        class_idx = _build_class_index(src_text)

        funcs: List[FunctionInfo] = []
        for entry in entries:
            etype = entry.get("type", "")
            if etype not in {"FunctionDef", "AsyncFunctionDef"}:
                continue
            name = entry.get("name") or ""
            if "." in name:
                # на всякий случай — если RepoAgent всё-таки положил Class.method
                _, name = name.split(".", 1)

            md = entry.get("md_content") or []
            md_text = "\n".join(md) if isinstance(md, list) else str(md)
            md_text = md_text.strip()
            # RepoAgent предваряет блок `**name**: …` — убираем шапку, чтобы
            # docstring начинался с описания (как в исходных prior-пар файлах).
            prefix = f"**{name}**:"
            if md_text.startswith(prefix):
                md_text = md_text[len(prefix):].lstrip()
            docstring = md_text or None
            if not docstring:
                continue

            line_no = entry.get("code_start_line") or 0
            end_line = entry.get("code_end_line") or line_no
            try:
                source_code = "\n".join(src_lines[line_no - 1:end_line])
            except Exception:
                source_code = ""

            class_name = class_idx.get((line_no, name))

            args_match = re.search(r"def\s+\w+\(([^)]*)\)", source_code)
            args = args_match.group(1) if args_match else ""
            signature = f"def {name}({args}):"

            funcs.append(FunctionInfo(
                file_path=rel,
                function_name=name,
                class_name=class_name,
                signature=signature,
                source_code=source_code,
                docstring=docstring,
                line_number=line_no,
            ))
        if funcs:
            results[rel] = funcs
    return results


# ---------- Парование ----------

def build_pairs(a_funcs: Dict[str, List[FunctionInfo]],
                b_funcs: Dict[str, List[FunctionInfo]]) -> List[dict]:
    pairs: List[dict] = []
    for rel, a_list in a_funcs.items():
        if rel not in b_funcs:
            continue
        b_lookup = {(f.class_name, f.function_name): f for f in b_funcs[rel]}
        for a in a_list:
            key = (a.class_name, a.function_name)
            if key not in b_lookup:
                continue
            b = b_lookup[key]
            if a.docstring == b.docstring:
                continue
            pairs.append({
                "file_path": rel,
                "function_name": a.function_name,
                "class_name": a.class_name,
                "signature": a.signature,
                "source_code": a.source_code,
                "osa_docstring": a.docstring,
                "osa_enhanced_docstring": b.docstring,
                "line_number": a.line_number,
            })
    return pairs


def load_variant(name: str) -> Tuple[Dict[str, List[FunctionInfo]], Path]:
    v = cfg["variants"][name]
    out_dir = resolve(v["output_dir"])
    if name == "ra":
        hierarchy = resolve(v["hierarchy_file"])
        return extract_repoagent(hierarchy, out_dir), out_dir
    return extract_inline(out_dir), out_dir


def main() -> int:
    print("→ Извлекаю docstring'и трёх вариантов")
    variants = {}
    for name in ("osa", "osa_c", "ra"):
        funcs, _ = load_variant(name)
        n_total = sum(len(v) for v in funcs.values())
        print(f"  {name:6s}: {len(funcs)} файлов, {n_total} функций")
        variants[name] = funcs

    out_dir = ROOT / "results" / "pairs"
    out_dir.mkdir(parents=True, exist_ok=True)

    for pair in cfg["pairs"]:
        a_name, b_name = pair["a"], pair["b"]
        pairs = build_pairs(variants[a_name], variants[b_name])
        out_file = out_dir / f"all_comparisons_{pair['name']}.json"
        out_file.write_text(json.dumps(pairs, indent=2, ensure_ascii=False))
        print(f"  {pair['name']:18s} -> {len(pairs):4d} пар  ({out_file.name})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
