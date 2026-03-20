"""
Pytest fixtures compartilhadas para testes unitários.
"""

import pytest
import sqlite3
from pathlib import Path
from PIL import Image
import hashlib


@pytest.fixture
def tmp_download_dir(tmp_path):
    """Diretório temporário para downloads."""
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    return download_dir


@pytest.fixture
def sample_image():
    """Imagem PIL de teste: 256x256 RGB."""
    img = Image.new("RGB", (256, 256), color=(100, 150, 200))
    return img


@pytest.fixture
def sample_image_hash(sample_image):
    """Hash da imagem de teste."""
    img_bytes = sample_image.tobytes()
    return hashlib.md5(img_bytes).hexdigest()


@pytest.fixture
def mock_db(tmp_path):
    """Conexão SQLite em memória para testes."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))

    # Criar tabelas básicas
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_cache (
            key TEXT PRIMARY KEY,
            value TEXT,
            expires_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS embedding_cache (
            key TEXT PRIMARY KEY,
            embedding BLOB
        )
    """)
    conn.commit()

    yield conn
    conn.close()
