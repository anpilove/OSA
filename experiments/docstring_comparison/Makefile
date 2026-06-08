.PHONY: help install clone generate generate-osa generate-osa-c generate-ra extract evaluate analyze all clean

help:
	@echo "OSA / OSA-C / RepoAgent experiments"
	@echo ""
	@echo "  make install        — установить зависимости"
	@echo "  make clone          — склонировать requests в data/"
	@echo "  make generate       — сгенерировать docstring всеми тремя инструментами"
	@echo "  make extract        — построить 3 файла пар в results/pairs/"
	@echo "  make evaluate       — прогнать G-Eval по 3 парам"
	@echo "  make analyze        — статистика и отчёты в results/reports/"
	@echo "  make all            — extract + evaluate + analyze"
	@echo "  make clean          — стереть results/ (data/ остаётся)"

install:
	pip install -r requirements.txt

clone:
	bash scripts/00_clone_target.sh

generate-osa:
	python scripts/01_generate_osa.py

generate-osa-c:
	python scripts/02_generate_osa_c.py

generate-ra:
	python scripts/03_generate_repoagent.py

generate: generate-osa generate-osa-c generate-ra

extract:
	python scripts/04_extract_pairs.py

evaluate:
	python scripts/05_evaluate_geval.py

analyze:
	python scripts/06_analyze.py

all: extract evaluate analyze

clean:
	rm -rf results/pairs/* results/metrics/* results/reports/*
