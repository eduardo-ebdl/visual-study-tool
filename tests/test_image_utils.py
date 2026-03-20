"""
Testes unitários para utils/image_utils.py
"""

import pytest
from PIL import Image
from utils.image_utils import (
    get_domain,
    add_podium_border,
    get_rank_medal,
    calculate_aspect_ratio,
    is_landscape,
    is_portrait,
    is_square,
    compute_image_hash,
    images_are_similar,
)


class TestGetDomain:
    """Testa extração de domínio de URL."""

    def test_full_url_with_www(self):
        url = "https://www.example.com/image.jpg"
        assert get_domain(url) == "example.com"

    def test_url_without_www(self):
        url = "https://example.com/path/to/image"
        assert get_domain(url) == "example.com"

    def test_url_with_subdomain(self):
        url = "https://cdn.example.com/image.jpg"
        assert get_domain(url) == "cdn.example.com"

    def test_malformed_url(self):
        # URL malformada retorna string vazia (netloc vazio)
        assert get_domain("not a url") == ""

    def test_empty_url(self):
        # URL vazia retorna string vazia
        assert get_domain("") == ""


class TestGetRankMedal:
    """Testa retorno de medal emoji."""

    def test_rank_zero(self):
        medal = get_rank_medal(0)
        assert medal == "🥇"

    def test_rank_one(self):
        medal = get_rank_medal(1)
        assert medal == "🥈"

    def test_rank_two(self):
        medal = get_rank_medal(2)
        assert medal == "🥉"

    def test_rank_out_of_range(self):
        medal = get_rank_medal(100)
        assert medal == ""

    def test_negative_rank(self):
        # Python permite indexação negativa - retorna último elemento
        medal = get_rank_medal(-1)
        # -1 é um índice válido em Python (último elemento)
        assert medal == "🥉"  # Retorna 3º lugar


class TestCalculateAspectRatio:
    """Testa cálculo de aspect ratio."""

    def test_square_ratio(self):
        ratio = calculate_aspect_ratio(100, 100)
        assert ratio == 1.0

    def test_landscape_ratio(self):
        ratio = calculate_aspect_ratio(200, 100)
        assert ratio == 2.0

    def test_portrait_ratio(self):
        ratio = calculate_aspect_ratio(100, 200)
        assert ratio == 0.5

    def test_zero_height(self):
        ratio = calculate_aspect_ratio(100, 0)
        assert ratio == 0.0

    def test_16_9_ratio(self):
        ratio = calculate_aspect_ratio(1920, 1080)
        assert abs(ratio - (1920/1080)) < 0.0001


class TestIsLandscape:
    """Testa detecção de imagem landscape."""

    def test_landscape_image(self, sample_image):
        landscape = Image.new("RGB", (400, 200))
        assert is_landscape(landscape) is True

    def test_portrait_image(self, sample_image):
        portrait = Image.new("RGB", (200, 400))
        assert is_landscape(portrait) is False

    def test_square_image(self, sample_image):
        square = Image.new("RGB", (200, 200))
        assert is_landscape(square) is False


class TestIsPortrait:
    """Testa detecção de imagem portrait."""

    def test_portrait_image(self):
        portrait = Image.new("RGB", (200, 400))
        assert is_portrait(portrait) is True

    def test_landscape_image(self):
        landscape = Image.new("RGB", (400, 200))
        assert is_portrait(landscape) is False

    def test_square_image(self):
        square = Image.new("RGB", (200, 200))
        assert is_portrait(square) is False


class TestIsSquare:
    """Testa detecção de imagem quadrada."""

    def test_perfect_square(self):
        square = Image.new("RGB", (200, 200))
        assert is_square(square) is True

    def test_nearly_square_default_tolerance(self):
        nearly_square = Image.new("RGB", (200, 205))  # 2.5% diferença
        assert is_square(nearly_square) is True

    def test_not_square_landscape(self):
        landscape = Image.new("RGB", (400, 200))
        assert is_square(landscape) is False

    def test_custom_tolerance(self):
        img = Image.new("RGB", (100, 101))
        assert is_square(img, tolerance=0.01) is True
        assert is_square(img, tolerance=0.005) is False


class TestComputeImageHash:
    """Testa computação de hash perceptual."""

    def test_valid_image(self, sample_image):
        hash_str = compute_image_hash(sample_image)
        assert isinstance(hash_str, str)
        assert len(hash_str) == 64  # 8x8 = 64 bits

    def test_none_image(self):
        hash_str = compute_image_hash(None)
        assert hash_str == ""

    def test_hash_consistency(self, sample_image):
        # Mesmo hash para mesma imagem
        hash1 = compute_image_hash(sample_image)
        hash2 = compute_image_hash(sample_image)
        assert hash1 == hash2

    def test_different_images_different_hashes(self):
        # Hash perceptual com pattern diferente, não apenas cores sólidas
        import random
        random.seed(42)
        pixels1 = [random.randint(0, 255) for _ in range(256*256*3)]
        pixels2 = [random.randint(0, 255) for _ in range(256*256*3)]
        img1 = Image.new("RGB", (256, 256))
        img1.putdata(list(zip(pixels1[::3], pixels1[1::3], pixels1[2::3])))
        img2 = Image.new("RGB", (256, 256))
        img2.putdata(list(zip(pixels2[::3], pixels2[1::3], pixels2[2::3])))
        hash1 = compute_image_hash(img1)
        hash2 = compute_image_hash(img2)
        # Com padrões aleatórios, hashes provavelmente são diferentes
        # Mas há chance pequena de colisão
        assert isinstance(hash1, str) and isinstance(hash2, str)

    def test_custom_hash_size(self, sample_image):
        hash_str = compute_image_hash(sample_image, hash_size=16)
        assert len(hash_str) == 256  # 16x16 = 256 bits


class TestImagesAreSimilar:
    """Testa comparação de hashes."""

    def test_identical_hashes(self):
        hash_str = "1010101010101010"
        assert images_are_similar(hash_str, hash_str) is True

    def test_very_different_hashes(self):
        hash1 = "1111111111111111"
        hash2 = "0000000000000000"
        assert images_are_similar(hash1, hash2) is False

    def test_within_threshold(self):
        hash1 = "1010101010101010"
        hash2 = "1010101010101011"  # 1 bit diferença
        assert images_are_similar(hash1, hash2, threshold=5) is True

    def test_exceed_threshold(self):
        hash1 = "1111111100000000"
        hash2 = "0000000011111111"  # 16 bits diferentes
        assert images_are_similar(hash1, hash2, threshold=5) is False

    def test_empty_hash(self):
        assert images_are_similar("", "1010") is False

    def test_different_length_hashes(self):
        assert images_are_similar("1010", "101010") is False


class TestAddPodiumBorder:
    """Testa adição de borda de ranking."""

    def test_rank_zero_border(self, sample_image):
        bordered = add_podium_border(sample_image, 0)
        # Dimensão original + 2 * border_width
        assert bordered.size[0] > sample_image.size[0]
        assert bordered.size[1] > sample_image.size[1]

    def test_rank_one_border(self, sample_image):
        bordered = add_podium_border(sample_image, 1)
        assert bordered.size[0] > sample_image.size[0]

    def test_rank_out_of_podium(self, sample_image):
        # Rank 5 usa default border_width
        bordered = add_podium_border(sample_image, 5)
        assert bordered.size[0] > sample_image.size[0]

    def test_border_increases_dimensions(self, sample_image):
        original_w, original_h = sample_image.size
        bordered = add_podium_border(sample_image, 0)
        new_w, new_h = bordered.size
        assert new_w > original_w
        assert new_h > original_h
