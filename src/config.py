"""
Centralised configuration for the AI Support & TAM Tooling system.

Loads environment variables and provides typed access to all settings.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
KB_DIR = PROJECT_ROOT / "knowledge-base"
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(PROJECT_ROOT / "chroma_db"))

# --- LLM ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.1-70b-versatile")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))
SEED = int(os.getenv("SEED", "42"))

# --- Embedding ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --- RAG ---
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_COLLECTION_NAME = "knowledge_base"

# --- Data loaders ---
_tickets_cache = None
_accounts_cache = None


def load_tickets() -> list[dict]:
    """Load and cache tickets from data/tickets.json."""
    global _tickets_cache
    if _tickets_cache is None:
        with open(DATA_DIR / "tickets.json", "r") as f:
            _tickets_cache = json.load(f)
    return _tickets_cache


def load_accounts() -> list[dict]:
    """Load and cache accounts from data/accounts.json."""
    global _accounts_cache
    if _accounts_cache is None:
        with open(DATA_DIR / "accounts.json", "r") as f:
            _accounts_cache = json.load(f)
    return _accounts_cache


def get_account_map() -> dict[str, dict]:
    """Build a lookup dict from account_id -> account record."""
    return {a["account_id"]: a for a in load_accounts()}


def get_ticket_by_id(ticket_id: str) -> dict | None:
    """Look up a single ticket by its ticket_id."""
    for t in load_tickets():
        if t["ticket_id"] == ticket_id:
            return t
    return None


def get_account_tickets(account_id: str, days: int = 90) -> list[dict]:
    """Get tickets for a specific account within the last N days."""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return [
        t
        for t in load_tickets()
        if t["account_id"] == account_id
        and datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) > cutoff
    ]
