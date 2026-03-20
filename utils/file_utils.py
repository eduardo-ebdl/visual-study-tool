"""
Utilitários para arquivos e lotes de imagens.
"""

from typing import List, Tuple, Optional
import os
import shutil
import zipfile
from pathlib import Path

def setup_dirs(download_dir: Path, clear: bool = True) -> None:
    """Cria diretório e opcionalmente limpa arquivos residuais."""
    # Garante que diretório existe e opcionalmente remove arquivos antigos
    os.makedirs(download_dir, exist_ok=True)
    if not clear:
        return
    for entry in os.scandir(download_dir):
        try:
            if entry.is_file():
                os.remove(entry.path)
            else:
                shutil.rmtree(entry.path)
        except OSError:
            pass


def create_zip_pack(download_dir: Path, clean_files: List[str], zip_name: str = "Reference_Pack.zip") -> Optional[str]:
    """Cria ZIP somente quando há arquivos válidos."""
    # Constrói arquivo ZIP com os arquivos fornecidos
    if not clean_files:
        return None
    zip_path = os.path.join(download_dir, zip_name)
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        for i, file_path in enumerate(clean_files):
            if os.path.exists(file_path):
                zipf.write(file_path, arcname=f"reference_{i+1:02d}.jpg")
    return zip_path


def build_zip_for_scope(
    download_dir: Path,
    scope: str,
    current_files: List[str],
    all_files: List[str],
) -> Optional[str]:
    # Escolhe escopo do ZIP (lote atual ou todos os lotes)
    if scope == "All batches":
        return create_zip_pack(download_dir, all_files, zip_name="Reference_Pack_All.zip")
    return create_zip_pack(download_dir, current_files, zip_name="Reference_Pack.zip")


def dedupe_urls(values: List[object]) -> List[str]:
    """Retorna URLs únicas, ignorando itens inválidos."""
    seen = set()
    deduped = []
    for item in values or []:
        if not isinstance(item, str):
            continue
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def cap_gallery(
    gallery: List[Tuple[str, str]],
    all_files: List[str],
    max_items: int,
) -> Tuple[List[Tuple[str, str]], List[str]]:
    """Limita galeria para manter UI responsiva e disco otimizado."""
    # Remove itens antigos e seus arquivos quando ultrapassa limite
    if len(gallery) <= max_items:
        return gallery, all_files
    overflow = len(gallery) - max_items
    files_to_remove = all_files[:overflow]
    for file_path in files_to_remove:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
    return gallery[overflow:], all_files[overflow:]


def cap_batch_history(
    history: List[List[Tuple[str, str]]],
    max_items: int,
) -> List[List[Tuple[str, str]]]:
    """Limita histórico de lotes para evitar crescimento sem limite."""
    total = sum(len(batch) for batch in history)
    while history and total > max_items:
        removed = history.pop(0)
        total -= len(removed)
        for path, _ in removed:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
    return history
