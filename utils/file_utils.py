"""
File and batch helpers for the Visual Study Tool.
"""

from typing import List, Tuple, Optional
import os
import shutil
import zipfile
from pathlib import Path

def setup_dirs(download_dir: Path, clear: bool = True) -> None:
    """Create download directory and optionally clear residual files."""
    # Ensure download directory exists; optionally clear previous files.
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
    """Create a ZIP only when there are valid files."""
    # Build a ZIP archive for the given file list.
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
    # Choose ZIP scope (current batch vs all batches).
    if scope == "All batches":
        return create_zip_pack(download_dir, all_files, zip_name="Reference_Pack_All.zip")
    return create_zip_pack(download_dir, current_files, zip_name="Reference_Pack.zip")


def dedupe_urls(values: List[object]) -> List[str]:
    """Return unique URL strings, skipping invalid items."""
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
    """Cap gallery/history to keep UI responsive and disk usage bounded."""
    # Trim oldest items and delete their files when over limit.
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
    """Cap batch history to avoid unbounded growth."""
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
