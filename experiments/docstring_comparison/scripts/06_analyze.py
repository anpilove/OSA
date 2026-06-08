#!/usr/bin/env python3
"""Статистика по результатам G-Eval: средние, paired t-test, отчёты.

Читает results/metrics/all_metrics_<pair>.json,
пишет results/reports/analysis_report_<pair>.txt
       results/reports/summary.txt   (сводка по всем 3 парам)
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy import stats

from common import bootstrap

cfg = bootstrap()
ROOT = Path(__file__).resolve().parent.parent

CRITERIA = ("clarity", "completeness", "accuracy", "relevance", "overall")


@dataclass
class Stat:
    a_mean: float
    a_std: float
    b_mean: float
    b_std: float
    delta: float
    delta_pct: float
    p_value: float
    n: int

    @property
    def significant(self) -> bool:
        return self.p_value < 0.05


def extract_scores(metrics: List[dict], criterion: str) -> Tuple[List[float], List[float]]:
    a, b = [], []
    for m in metrics:
        c = m.get(criterion)
        if not c:
            continue
        sa = c.get("docstring_a_score")
        sb = c.get("docstring_b_score")
        if sa is None or sb is None:
            continue
        a.append(float(sa))
        b.append(float(sb))
    return a, b


def crit_stat(metrics: List[dict], criterion: str) -> Stat | None:
    a, b = extract_scores(metrics, criterion)
    if not a:
        return None
    a_arr, b_arr = np.array(a), np.array(b)
    delta = b_arr.mean() - a_arr.mean()
    pct = (delta / a_arr.mean() * 100) if a_arr.mean() else 0.0
    _, p = stats.ttest_rel(b_arr, a_arr)
    return Stat(
        a_mean=float(a_arr.mean()), a_std=float(a_arr.std()),
        b_mean=float(b_arr.mean()), b_std=float(b_arr.std()),
        delta=float(delta), delta_pct=float(pct),
        p_value=float(p), n=len(a),
    )


def render(pair_name: str, a_label: str, b_label: str, metrics: List[dict]) -> str:
    lines = []
    lines.append("=" * 78)
    lines.append(f"DOCSTRING G-EVAL  —  {pair_name}   (A={a_label}, B={b_label})")
    lines.append("=" * 78)
    lines.append("")

    for c in CRITERIA:
        s = crit_stat(metrics, c)
        if not s:
            continue
        marker = " ***" if s.significant else ""
        lines.append(f"### {c.capitalize()}  (n={s.n})")
        lines.append(f"  A ({a_label:<5}):  {s.a_mean:.3f} ± {s.a_std:.3f}")
        lines.append(f"  B ({b_label:<5}):  {s.b_mean:.3f} ± {s.b_std:.3f}")
        lines.append(f"  Δ      :  {s.delta:+.3f}  ({s.delta_pct:+.1f}%){marker}")
        lines.append(f"  p-value:  {s.p_value:.4f}")
        lines.append("")

    lines.append("*** = статистически значимо (p < 0.05, paired t-test)")
    return "\n".join(lines)


def reasoning_themes(metrics: List[dict]) -> Dict[str, int]:
    themes = defaultdict(int)
    keywords = {
        "parameters": ("parameter", "argument"),
        "context_helpers": ("context", "helper", "called"),
        "completeness": ("complete", "comprehensive"),
        "verbosity_negative": ("verbose", "redundant", "boilerplate"),
        "hallucination_negative": ("hallucinat", "incorrect", "wrong"),
    }
    for m in metrics:
        ov = (m.get("overall") or {}).get("reasoning", "").lower()
        for theme, kws in keywords.items():
            if any(k in ov for k in kws):
                themes[theme] += 1
    return dict(themes)


def main() -> int:
    metrics_dir = ROOT / "results" / "metrics"
    reports_dir = ROOT / "results" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary_lines = ["=" * 78, "СВОДКА: OSA / OSA-C / RepoAgent", "=" * 78, ""]

    for pair in cfg["pairs"]:
        mf = metrics_dir / f"all_metrics_{pair['name']}.json"
        if not mf.exists():
            print(f"✗ {mf} нет — пропускаю")
            continue
        metrics = json.loads(mf.read_text(encoding="utf-8"))
        report = render(pair["name"], pair["a"].upper(), pair["b"].upper(), metrics)
        report_file = reports_dir / f"analysis_report_{pair['name']}.txt"
        report_file.write_text(report)
        print(f"→ {report_file}")
        # сводка: средняя дельта overall
        s = crit_stat(metrics, "overall")
        if s:
            mark = " ***" if s.significant else ""
            summary_lines.append(
                f"{pair['name']:18s}  overall: A={s.a_mean:.3f}  B={s.b_mean:.3f}  "
                f"Δ={s.delta:+.3f} ({s.delta_pct:+.1f}%) p={s.p_value:.3f}{mark}"
            )

        # темы reasoning
        themes = reasoning_themes(metrics)
        themes_file = reports_dir / f"reasoning_themes_{pair['name']}.json"
        themes_file.write_text(json.dumps(themes, indent=2))

    summary_lines.append("")
    summary_lines.append("*** = p < 0.05")
    (reports_dir / "summary.txt").write_text("\n".join(summary_lines))
    print(f"\n→ {reports_dir / 'summary.txt'}")
    print("\n" + "\n".join(summary_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
