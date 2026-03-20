"""
Utilitários para processamento de imagens.
Funções helpers para manipulação, análise e export.
"""

from PIL import Image, ImageOps
from urllib.parse import urlparse
from typing import Tuple
import os

from config.settings import (
    RANK_COLORS, 
    RANK_BORDER_WIDTH, 
    RANK_MEDALS,
    EXPORT_QUALITY
)

def get_domain(url: str) -> str:
    """
    Extrai domínio de uma URL.
    
    Args:
        url: URL completa
        
    Returns:
        Domínio sem 'www.'
        
    Examples:
        >>> get_domain("https://www.example.com/image.jpg")
        'example.com'
    """
    try:
        domain = urlparse(url).netloc
        return domain.replace("www.", "")
    except:
        return "web"

def add_podium_border(img: Image.Image, rank: int) -> Image.Image:
    """
    Adiciona borda colorida baseada no ranking.
    
    Args:
        img: Imagem PIL
        rank: Posição no ranking (0 = primeiro)
        
    Returns:
        Imagem com borda
    """
    # Pick border color based on rank.
    if rank in RANK_COLORS:
        color = RANK_COLORS[rank]
    else:
        color = RANK_COLORS["default"]
    
    # Pick border width based on rank.
    if rank < 3:
        border_width = RANK_BORDER_WIDTH["podium"]
    else:
        border_width = RANK_BORDER_WIDTH["regular"]
    
    bordered_img = ImageOps.expand(img, border=border_width, fill=color)
    
    return bordered_img

def get_rank_medal(rank: int) -> str:
    """
    Retorna emoji de medalha para o rank.
    
    Args:
        rank: Posição no ranking (0 = primeiro)
        
    Returns:
        Emoji de medalha ou string vazia
    """
    if rank < len(RANK_MEDALS):
        return RANK_MEDALS[rank]
    return ""

def save_image(img: Image.Image, filepath: str, quality: int = EXPORT_QUALITY) -> bool:
    """
    Salva imagem com configurações otimizadas.
    
    Args:
        img: Imagem PIL
        filepath: Caminho de destino
        quality: Qualidade JPEG (1-100)
        
    Returns:
        True se sucesso, False se falha
    """
    try:
        # Ensure destination exists before saving.
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        img.save(filepath, quality=quality, optimize=True)
        return True
    except Exception as e:
        print(f"Error saving image to {filepath}: {str(e)}")
        return False

def resize_image(
    img: Image.Image, 
    size: Tuple[int, int], 
    method=Image.Resampling.LANCZOS
) -> Image.Image:
    """
    Redimensiona imagem mantendo aspect ratio.
    
    Args:
        img: Imagem PIL
        size: Tupla (width, height)
        method: Método de resampling
        
    Returns:
        Imagem redimensionada
    """
    return ImageOps.fit(img, size, method=method)

def get_image_dimensions(img: Image.Image) -> Tuple[int, int]:
    """
    Retorna dimensões da imagem.
    
    Args:
        img: Imagem PIL
        
    Returns:
        Tupla (width, height)
    """
    return img.size

def calculate_aspect_ratio(width: int, height: int) -> float:
    """
    Calcula aspect ratio.
    
    Args:
        width: Largura
        height: Altura
        
    Returns:
        Ratio width/height
    """
    if height == 0:
        return 0.0
    return width / height

def is_landscape(img: Image.Image) -> bool:
    """
    Verifica se imagem é landscape.
    """
    width, height = img.size
    return width > height

def is_portrait(img: Image.Image) -> bool:
    """
    Verifica se imagem é portrait.
    """
    width, height = img.size
    return height > width

def is_square(img: Image.Image, tolerance: float = 0.05) -> bool:
    """
    Verifica se imagem é aproximadamente quadrada.
    
    Args:
        img: Imagem PIL
        tolerance: Tolerância para considerar quadrado (0.05 = 5%)
    """
    width, height = img.size
    ratio = abs(width - height) / max(width, height)
    return ratio <= tolerance

# Perceptual hash helpers for deduplication.
def compute_image_hash(img: Image.Image, hash_size: int = 8) -> str:
    """
    Calculate a simple average hash for quick deduplication.
    """
    if img is None:
        return ""
    small = img.convert("L").resize((hash_size, hash_size), Image.Resampling.BILINEAR)
    pixels = list(small.getdata())
    avg = sum(pixels) / len(pixels)
    return "".join("1" if p > avg else "0" for p in pixels)

def images_are_similar(hash1: str, hash2: str, threshold: int = 5) -> bool:
    """
    Compare two hashes using Hamming distance.
    """
    if not hash1 or not hash2 or len(hash1) != len(hash2):
        return False
    distance = sum(ch1 != ch2 for ch1, ch2 in zip(hash1, hash2))
    return distance <= threshold
