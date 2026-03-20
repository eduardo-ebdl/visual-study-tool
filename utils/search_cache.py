import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

from config.settings import CACHE_DIR, SEARCH_CACHE_TTL_SECONDS

CACHE_DB = Path(CACHE_DIR) / "search_cache.sqlite"

def _connect():
    # 1) Open cache DB and ensure schema exists.
    conn = sqlite3.connect(str(CACHE_DB))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS search_cache (
            cache_key TEXT PRIMARY KEY,
            created_at INTEGER NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    return conn

def make_cache_key(query: str, type_filter: Optional[str], limit: int, engine_signature: str) -> str:
    # 2) Build a stable hash key for a search request.
    payload = {
        "q": query,
        "t": type_filter or "",
        "l": int(limit),
        "s": engine_signature,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def get_cached_results(cache_key: str, ttl_seconds: int = SEARCH_CACHE_TTL_SECONDS) -> Optional[List[dict]]:
    # 3) Read cached results and drop expired entries.
    now = int(time.time())
    with _connect() as conn:
        row = conn.execute(
            "SELECT created_at, payload FROM search_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if not row:
            return None
        created_at, payload = row
        if now - created_at > ttl_seconds:
            conn.execute("DELETE FROM search_cache WHERE cache_key = ?", (cache_key,))
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            conn.execute("DELETE FROM search_cache WHERE cache_key = ?", (cache_key,))
            return None

def set_cached_results(cache_key: str, results: List[dict]) -> None:
    # 4) Persist results to the cache store.
    now = int(time.time())
    payload = json.dumps(results)
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO search_cache (cache_key, created_at, payload) VALUES (?, ?, ?)",
            (cache_key, now, payload),
        )
