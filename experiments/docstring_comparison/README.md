# Docstring Comparison Experiments

This module contains a reproducible experiment pipeline for comparing generated
Python docstrings from three documentation-generation variants:

- **OSA**: legacy Open-Source Advisor docstring pipeline.
- **OSA-C**: context-enhanced OSA variant with dependency-aware generation.
- **RepoAgent**: external documentation-generation baseline.

The pipeline was prepared for research experiments and paper results. It is kept
separate from the production `osa_tool` package because it contains benchmark
orchestration, model-judge evaluation and analysis scripts rather than end-user
library functionality.

## What The Module Does

The workflow:

1. Clones the target repository (`psf/requests` by default).
2. Creates separate working copies for OSA, OSA-C and RepoAgent.
3. Generates docstrings/documentation with each variant.
4. Extracts comparable docstring pairs.
5. Evaluates the pairs with G-Eval / LLM-as-Judge.
6. Produces reports with mean scores, standard deviations and paired t-tests.

Generated files are written to `data/` and `results/`. These directories are
ignored by git and can be regenerated.

## Structure

```text
docstring_comparison/
├── config.yaml
├── Makefile
├── requirements.txt
├── .env.example
└── scripts/
    ├── 00_clone_target.sh
    ├── 01_generate_osa.py
    ├── 02_generate_osa_c.py
    ├── 03_generate_repoagent.py
    ├── 04_extract_pairs.py
    ├── 05_evaluate_geval.py
    ├── 06_analyze.py
    ├── common.py
    └── g_eval_prompt.py
```

## Setup

```bash
cd experiments/docstring_comparison
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Put your OpenRouter/OpenAI-compatible key into `.env`:

```bash
OPENAI_API_KEY=...
```

## Repository Paths

The experiment needs local paths to OSA and RepoAgent. They can be configured in
`config.yaml` or through environment variables:

```bash
export OSA_LEGACY_REPO=/path/to/OSA
export OSA_C_REPO=/path/to/OSA
export REPOAGENT_REPO=/path/to/RepoAgent
```

When the module is stored inside the OSA repository, the default OSA path points
to the repository root. RepoAgent must be provided separately if `generate-ra`
is used.

## Quick Run

```bash
make clone
make generate-osa
make generate-osa-c
make generate-ra
make extract
make evaluate
make analyze
```

Or:

```bash
make generate
make all
```

`make all` runs `extract`, `evaluate` and `analyze`. It assumes generated
docstrings already exist in `data/`.

## Outputs

The main outputs are:

- `results/pairs/all_comparisons_<pair>.json`
- `results/metrics/all_metrics_<pair>.json`
- `results/reports/analysis_report_<pair>.txt`
- `results/reports/summary.txt`

The configured comparison pairs are:

- `osa_vs_osa_c`
- `osa_c_vs_ra`
- `osa_vs_ra`

## Notes

- The same LLM configuration is used across compared variants to focus the
  comparison on the generation pipeline rather than the model choice.
- G-Eval is used as an LLM-as-Judge protocol for clarity, completeness,
  accuracy, relevance and overall quality.
- `data/` and `results/` are intentionally not committed; they are generated
  artifacts.
