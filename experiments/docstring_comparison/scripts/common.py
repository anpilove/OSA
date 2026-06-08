"""Общие утилиты: загрузка конфигурации, патчи httpx/OpenAI для не-ASCII заголовков."""
from __future__ import annotations

import os
import sys
import yaml
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    """Подгружает .env из корня experiments/ если есть."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config() -> Dict[str, Any]:
    with (ROOT / "config.yaml").open() as f:
        return expand_env(yaml.safe_load(f))


def expand_env(value: Any) -> Any:
    """Expands ${VAR} and ${VAR:-default} in config values."""
    if isinstance(value, dict):
        return {k: expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env(v) for v in value]
    if not isinstance(value, str):
        return value

    def repl(match):
        expr = match.group(1)
        if ":-" in expr:
            name, default = expr.split(":-", 1)
            return os.environ.get(name, default)
        return os.environ.get(expr, "")

    import re

    return re.sub(r"\$\{([^}]+)\}", repl, value)


def resolve(p: str) -> Path:
    """Превращает относительный путь из config.yaml в абсолютный."""
    path = Path(p)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    return path


def patch_httpx_ascii() -> None:
    """Чистит User-Agent / заголовки от кириллицы — иначе httpx падает."""
    try:
        import httpx
        from httpx._models import Headers

        original = Headers.__init__

        def patched(self, headers=None, encoding=None):
            if isinstance(headers, dict):
                clean = {}
                for k, v in headers.items():
                    if isinstance(v, str):
                        cv = v.encode("ascii", "ignore").decode("ascii")
                        if cv:
                            clean[k] = cv
                    else:
                        clean[k] = v
                headers = clean
            original(self, headers, encoding)

        Headers.__init__ = patched
    except ImportError:
        pass


def force_utf8_io() -> None:
    """Принудительный UTF-8 для stdout/stderr."""
    os.environ.setdefault("LC_ALL", "en_US.UTF-8")
    os.environ.setdefault("LANG", "en_US.UTF-8")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8")


def bootstrap() -> Dict[str, Any]:
    """Стандартная инициализация: env + utf-8 + httpx-патч + конфиг."""
    load_env()
    force_utf8_io()
    patch_httpx_ascii()
    return load_config()
