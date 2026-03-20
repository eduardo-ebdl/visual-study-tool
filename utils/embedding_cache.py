"""
Cache SQLite simples para embeddings de imagem CLIP.
"""

from __future__ import annotations

import pickle
import sqlite3
from typing import Optional

from config.settings import EMBEDDING_CACHE_PATH

def _connect() -> sqlite3.Connection:
    # 1) Abre DB de cache de embedding e garante que o schema existe.
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
    # 2) Lê blob de embedding em cache por chave.
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
    # 3) Escreve blob de embedding por chave.
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
