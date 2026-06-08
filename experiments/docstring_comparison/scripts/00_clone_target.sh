#!/usr/bin/env bash
# Клонирует целевой репозиторий (psf/requests) в data/requests
# Затем создаёт три копии — по одной на каждый генератор docstring.
set -euo pipefail
cd "$(dirname "$0")/.."

REPO_URL=${REPO_URL:-https://github.com/psf/requests}
TARGET=data/requests

mkdir -p data
if [ ! -d "$TARGET" ]; then
  git clone "$REPO_URL" "$TARGET"
else
  echo "→ $TARGET уже существует, пропускаю clone"
fi

# Три рабочих копии — генераторы пишут docstring inplace
for v in osa osa_c ra; do
  dst="data/requests_${v}"
  if [ -d "$dst" ]; then
    echo "→ $dst уже существует, пропускаю"
    continue
  fi
  echo "→ копирую $TARGET в $dst"
  cp -r "$TARGET" "$dst"
done

echo "Готово. Дальше: make generate-osa / generate-osa-c / generate-ra"
