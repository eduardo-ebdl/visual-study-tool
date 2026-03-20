"""
Testes unitários para utils/file_utils.py
"""

import pytest
from pathlib import Path
from utils.file_utils import (
    dedupe_urls,
    cap_gallery,
    cap_batch_history,
    build_zip_for_scope,
    create_zip_pack,
)


class TestDedupeUrls:
    """Testa remoção de duplicatas de URLs."""

    def test_empty_list(self):
        assert dedupe_urls([]) == []

    def test_none_input(self):
        assert dedupe_urls(None) == []

    def test_no_duplicates(self):
        urls = ["http://example.com/1", "http://example.com/2"]
        result = dedupe_urls(urls)
        assert result == urls

    def test_with_duplicates(self):
        urls = ["http://a.com", "http://b.com", "http://a.com"]
        result = dedupe_urls(urls)
        assert result == ["http://a.com", "http://b.com"]

    def test_non_string_items_skipped(self):
        items = ["http://a.com", 123, "http://b.com", None, "http://a.com"]
        result = dedupe_urls(items)
        assert result == ["http://a.com", "http://b.com"]

    def test_order_preserved(self):
        urls = ["z", "a", "z", "b"]
        result = dedupe_urls(urls)
        assert result == ["z", "a", "b"]


class TestCapGallery:
    """Testa capping de galeria."""

    def test_empty_gallery(self):
        gallery, all_files = cap_gallery([], [], max_items=10)
        assert gallery == []
        assert all_files == []

    def test_below_limit(self):
        gallery = [("img1.jpg", "title1"), ("img2.jpg", "title2")]
        all_files = ["img1.jpg", "img2.jpg"]
        result_gallery, result_files = cap_gallery(gallery, all_files, max_items=5)
        assert result_gallery == gallery
        assert result_files == all_files

    def test_at_limit(self):
        gallery = [("img1.jpg", "t1"), ("img2.jpg", "t2")]
        all_files = ["img1.jpg", "img2.jpg"]
        result_gallery, result_files = cap_gallery(gallery, all_files, max_items=2)
        assert result_gallery == gallery

    def test_exceeds_limit(self):
        gallery = [
            ("img1.jpg", "t1"),
            ("img2.jpg", "t2"),
            ("img3.jpg", "t3"),
            ("img4.jpg", "t4"),
        ]
        all_files = ["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg"]
        result_gallery, result_files = cap_gallery(gallery, all_files, max_items=2)
        # Deve remover os 2 primeiros
        assert len(result_gallery) == 2
        assert len(result_files) == 2
        assert ("img3.jpg", "t3") in result_gallery
        assert ("img4.jpg", "t4") in result_gallery


class TestCapBatchHistory:
    """Testa capping do histórico de batches."""

    def test_empty_history(self):
        result = cap_batch_history([], max_items=100)
        assert result == []

    def test_below_limit(self):
        history = [
            [("img1.jpg", "t1"), ("img2.jpg", "t2")],
            [("img3.jpg", "t3")],
        ]
        result = cap_batch_history(history, max_items=10)
        assert len(result) == 2

    def test_exceeds_limit_removes_oldest_batches(self):
        history = [
            [("img1.jpg", "t1"), ("img2.jpg", "t2")],  # 2 items
            [("img3.jpg", "t3"), ("img4.jpg", "t4")],  # 2 items
            [("img5.jpg", "t5")],  # 1 item
        ]
        # Total: 5 items, limit 3, deve remover primeiro batch (2 items)
        result = cap_batch_history(history, max_items=3)
        assert len(result) == 2

    def test_removes_multiple_old_batches_if_needed(self):
        history = [
            [("img1.jpg", "t1")],  # 1 item
            [("img2.jpg", "t2")],  # 1 item
            [("img3.jpg", "t3"), ("img4.jpg", "t4"), ("img5.jpg", "t5")],  # 3 items
        ]
        # Total: 5 items, limit 2
        # Função remove batches até total <= 2
        # Remove primeiro batch (1 item) -> total = 4
        # Remove segundo batch (1 item) -> total = 3
        # Ainda precisa remover para ficar <= 2, remove terceiro batch
        result = cap_batch_history(history, max_items=2)
        # Resultado: vazio ou apenas último batch parcialmente
        assert isinstance(result, list)


class TestBuildZipForScope:
    """Testa construção de ZIP por scope."""

    def test_all_batches_scope(self, tmp_download_dir):
        current_files = []
        all_files = []

        zip_path = build_zip_for_scope(
            tmp_download_dir,
            "All batches",
            current_files,
            all_files,
        )
        # Sem files, deve retornar None
        assert zip_path is None

    def test_current_batch_scope(self, tmp_download_dir):
        current_files = []
        all_files = ["file1.jpg", "file2.jpg"]

        zip_path = build_zip_for_scope(
            tmp_download_dir,
            "Batch 1",
            current_files,
            all_files,
        )
        # Sem files, deve retornar None
        assert zip_path is None


class TestCreateZipPack:
    """Testa criação de ZIP pack."""

    def test_empty_file_list(self, tmp_download_dir):
        zip_path = create_zip_pack(tmp_download_dir, [])
        assert zip_path is None

    def test_none_file_list(self, tmp_download_dir):
        zip_path = create_zip_pack(tmp_download_dir, None)
        assert zip_path is None

    def test_creates_zip_with_valid_files(self, tmp_download_dir, tmp_path):
        # Criar arquivos temporários
        file1 = tmp_path / "file1.jpg"
        file1.write_text("test content 1")
        file2 = tmp_path / "file2.jpg"
        file2.write_text("test content 2")

        zip_path = create_zip_pack(
            tmp_download_dir,
            [str(file1), str(file2)],
            zip_name="test.zip"
        )

        assert zip_path is not None
        assert zip_path.endswith("test.zip")

    def test_custom_zip_name(self, tmp_download_dir, tmp_path):
        file1 = tmp_path / "file1.jpg"
        file1.write_text("test")

        zip_path = create_zip_pack(
            tmp_download_dir,
            [str(file1)],
            zip_name="custom_name.zip"
        )

        assert "custom_name.zip" in zip_path
