"""
Lightweight SQLite cache for CLIP image embeddings.
"""

from __future__ import annotations

import pickle
import sqlite3
from typing import Optional

from config.settings import EMBEDDING_CACHE_PATH

def _connect() -> sqlite3.Connection:
    # 1) Open embedding cache DB and ensure schema exists.
    conn = sqlite3.connect(EMBEDDING_CACHE_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            key TEXT PRIMARY KEY,
            value BLOB
        )
        """
    )
    return conn


def get_cached_embedding(key: str):
    # 2) Read cached embedding blob by key.
    if not key:
        return None
    try:
        conn = _connect()
        row = conn.execute("SELECT value FROM embeddings WHERE key = ?", (key,)).fetchone()
        return pickle.loads(row[0]) if row else None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def set_cached_embedding(key: str, value) -> None:
    # 3) Write embedding blob by key.
    if not key or value is None:
        return
    try:
        conn = _connect()
        conn.execute(
            "INSERT OR REPLACE INTO embeddings (key, value) VALUES (?, ?)",
            (key, pickle.dumps(value)),
        )
        conn.commit()
    except Exception:
        return
    finally:
        try:
            conn.close()
        except Exception:
            pass
