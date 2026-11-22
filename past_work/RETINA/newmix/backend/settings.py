"""Tiny .env loader (no dependency). Real environment variables always win over the file.

Secrets such as DEEPSEEK_API_KEY live in backend/.env, which is git-ignored.
Nothing in this module ever logs or returns a value, only loads them.
"""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent


def load_env() -> None:
    for path in (BACKEND_DIR / ".env", ROOT / ".env"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def db_path() -> Path:
    raw = get("SUITE_DB_PATH")
    return Path(raw).expanduser().resolve() if raw else ROOT / "var" / "suite.db"
