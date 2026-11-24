"""Settings, read from environment variables (and .env if present)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

APP_VERSION = "0.1.0"


@dataclass(frozen=True)
class Settings:
    raw_dir: Path = ROOT / "data" / "raw"
    index_dir: Path = ROOT / "data" / "index"
    audit_dir: Path = ROOT / "data" / "audit"
    results_dir: Path = ROOT / "data" / "results"
    model_cache: Path = ROOT / "data" / "models"
    provider: str = os.getenv("GXP_PROVIDER", "offline")
    embeddings: str = os.getenv("GXP_EMBEDDINGS", "fastembed")
    embedding_model: str = os.getenv("GXP_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    top_k: int = int(os.getenv("GXP_TOP_K", "8"))
    llm_tools: bool = os.getenv("GXP_LLM_TOOLS", "0") == "1"  # get_section tool round for the LLM (off: 1 call per case)
    public_demo: bool = os.getenv("GXP_PUBLIC_DEMO", "0") == "1"  # public hosted demo: show the data and audit-log notices


_override: Settings | None = None  # set by tests via use_settings(); never in normal runs


def get_settings() -> Settings:
    return _override or Settings()


def use_settings(settings: Settings | None) -> None:
    """Replace the settings for the whole app (tests use this to force the offline classifier and
    temporary folders). Patching the dataclass defaults does NOT work: a dataclass captures its
    defaults when the class is created, which once let tests reach Gemini and the real audit log."""
    global _override
    _override = settings
