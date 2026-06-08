#!/usr/bin/env python3
"""G-Eval (LLM-as-Judge) для всех 3 пар сравнения.

Читает results/pairs/all_comparisons_<pair>.json,
пишет results/metrics/all_metrics_<pair>.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

import openai
from tqdm import tqdm

from common import bootstrap
from g_eval_prompt import SYSTEM_PROMPT, build_comparison_prompt

cfg = bootstrap()
ROOT = Path(__file__).resolve().parent.parent


@dataclass
class EvaluationResult:
    file_path: str
    function_name: str
    class_name: Optional[str]
    osa_docstring: str
    osa_enhanced_docstring: str
    clarity: Dict[str, float]
    completeness: Dict[str, float]
    accuracy: Dict[str, float]
    relevance: Dict[str, float]
    overall: Dict[str, float]


class Judge:
    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise SystemExit("OPENAI_API_KEY не задан (см. .env.example)")
        self.client = openai.OpenAI(api_key=api_key, base_url=cfg["llm"]["base_url"])
        self.model = cfg["llm"]["model"]
        self.temperature = cfg["llm"]["judge_temperature"]
        self.retries = cfg["geval"]["retries"]

    def call(self, prompt: str) -> Optional[str]:
        for attempt in range(self.retries):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                )
                return resp.choices[0].message.content
            except Exception as e:
                if attempt == self.retries - 1:
                    print(f"  судья упал: {e}")
                    return None
        return None

    @staticmethod
    def parse(response: str) -> Optional[Dict]:
        try:
            txt = response
            if "```json" in txt:
                txt = txt.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in txt:
                txt = txt.split("```", 1)[1].split("```", 1)[0]
            return json.loads(txt.strip())
        except (json.JSONDecodeError, IndexError) as e:
            print(f"  не распарсил ответ судьи: {e}")
            return None

    def evaluate(self, pair: Dict) -> Optional[EvaluationResult]:
        prompt = build_comparison_prompt(
            function_name=pair["function_name"],
            function_signature=pair["signature"],
            source_code=pair["source_code"],
            docstring_a=pair["osa_docstring"] or "",
            docstring_b=pair["osa_enhanced_docstring"] or "",
            file_path=pair.get("file_path", ""),
            class_name=pair.get("class_name"),
        )
        raw = self.call(prompt)
        if not raw:
            return None
        scores = self.parse(raw)
        if not scores:
            return None
        empty = {"docstring_a_score": 0.0, "docstring_b_score": 0.0, "reasoning": "missing"}
        return EvaluationResult(
            file_path=pair["file_path"],
            function_name=pair["function_name"],
            class_name=pair.get("class_name"),
            osa_docstring=pair["osa_docstring"] or "",
            osa_enhanced_docstring=pair["osa_enhanced_docstring"] or "",
            clarity=scores.get("clarity", empty),
            completeness=scores.get("completeness", empty),
            accuracy=scores.get("accuracy", empty),
            relevance=scores.get("relevance", empty),
            overall=scores.get("overall", empty),
        )


def evaluate_file(judge: Judge, pair_file: Path, out_file: Path, rate_limit: int) -> None:
    pairs = json.loads(pair_file.read_text(encoding="utf-8"))
    print(f"\n=== {pair_file.name} ({len(pairs)} пар) ===")

    results: List[dict] = []
    with ThreadPoolExecutor(max_workers=rate_limit) as ex:
        futures = {ex.submit(judge.evaluate, p): p for p in pairs}
        for fut in tqdm(as_completed(futures), total=len(futures), desc="  G-Eval"):
            r = fut.result()
            if r:
                results.append(asdict(r))

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"  → {out_file} ({len(results)} оценок)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", help="только указанная пара (osa_vs_osa_c / osa_c_vs_ra / osa_vs_ra)")
    args = parser.parse_args()

    judge = Judge()
    rate_limit = cfg["geval"]["rate_limit"]
    pair_dir = ROOT / "results" / "pairs"
    metrics_dir = ROOT / "results" / "metrics"

    for pair in cfg["pairs"]:
        if args.pair and pair["name"] != args.pair:
            continue
        pf = pair_dir / f"all_comparisons_{pair['name']}.json"
        if not pf.exists():
            print(f"✗ {pf} не найден, запусти `make extract`")
            continue
        evaluate_file(judge, pf, metrics_dir / f"all_metrics_{pair['name']}.json", rate_limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
