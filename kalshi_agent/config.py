"""Configuration loaded from environment variables.

Copy `.env.example` to `.env`, fill it in, and either `source` it or use a tool
like `python-dotenv` (loaded automatically below if installed).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Load a .env file if python-dotenv is available (optional convenience).
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is optional
    pass

# Repo root, so paths in .env can be relative.
ROOT = Path(__file__).resolve().parent.parent

# Kalshi API hosts. Production is the default; flip KALSHI_API_BASE to the demo
# host while you're testing so you never risk real money.
#   Production : https://api.elections.kalshi.com
#   Demo       : https://demo-api.kalshi.co
KALSHI_API_BASE = os.environ.get("KALSHI_API_BASE", "https://api.elections.kalshi.com")
KALSHI_API_PREFIX = "/trade-api/v2"


@dataclass(frozen=True)
class Settings:
    kalshi_api_base: str
    kalshi_api_prefix: str
    kalshi_key_id: str | None
    kalshi_private_key_path: str | None
    anthropic_api_key: str | None
    journal_db_path: str
    knowledge_dir: str
    model: str

    @property
    def kalshi_configured(self) -> bool:
        return bool(self.kalshi_key_id and self.kalshi_private_key_path)


def load_settings() -> Settings:
    return Settings(
        kalshi_api_base=KALSHI_API_BASE,
        kalshi_api_prefix=KALSHI_API_PREFIX,
        kalshi_key_id=os.environ.get("KALSHI_KEY_ID"),
        kalshi_private_key_path=os.environ.get("KALSHI_PRIVATE_KEY_PATH"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        journal_db_path=os.environ.get("KALSHI_JOURNAL_DB", str(ROOT / "journal.db")),
        knowledge_dir=os.environ.get("KALSHI_KNOWLEDGE_DIR", str(ROOT / "knowledge")),
        # Default to the most capable model; override with KALSHI_AGENT_MODEL.
        model=os.environ.get("KALSHI_AGENT_MODEL", "claude-opus-4-8"),
    )
