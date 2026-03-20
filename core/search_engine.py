"""
Abstração de engines de busca de imagens.
Permite adicionar múltiplas fontes (DDGS, Unsplash, Pexels, etc) facilmente.
"""

from abc import ABC, abstractmethod
import logging
from utils.pretty_logger import wrap_logger
import math
import random
import time
from typing import List, Dict, Optional
import requests
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from config.settings import (
    HEADERS,
    SEARCH_TIMEOUT,
    MAX_RESULTS_PER_ENGINE,
    UNSPLASH_ACCESS_KEY,
    UNSPLASH_SECRET_KEY,
    PEXELS_API_KEY,
    PIXABAY_API_KEY,
    OPENVERSE_API_KEY,
    ENABLE_MULTI_ENGINE,
    ENABLE_UNSPLASH,
    ENABLE_PEXELS,
    ENABLE_PIXABAY,
    ENABLE_OPENVERSE,
    ENABLE_WIKIMEDIA,
    ENABLE_DDG,
    ENABLE_DDG_FALLBACK,
)

logger = wrap_logger(logging.getLogger(__name__))

def _clean_query(query: str) -> str:
    """Remove tokens negativos para APIs que não suportam sintaxe avançada."""
    parts = []
    for token in (query or "").split():
        if token.startswith("-"):
            continue
        parts.append(token)
    return " ".join(parts).strip()


class SearchEngine(ABC):
    """Classe base abstrata para engines de busca."""
    
    @abstractmethod
    def search(self, query: str, max_results: int = 25, **kwargs) -> List[Dict[str, str]]:
        """
        Executa busca e retorna lista de URLs.
        
        Args:
            query: Texto de busca
            max_results: Número máximo de resultados
            **kwargs: Argumentos específicos da engine
            
        Returns:
            Lista de dicionários com formato:
            [
                {
                    'url': 'https://...',
                    'thumbnail': 'https://...',
                    'source': 'engine_name',
                    'title': '...',
                }
            ]
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Retorna nome da engine."""
        pass


# Engine DuckDuckGo (sem chave de API).
class DuckDuckGoEngine(SearchEngine):
    """Engine de busca usando DuckDuckGo."""
    
    def __init__(self):
        self.name = "DuckDuckGo"
    
    def search(self, query: str, max_results: int = 25, type_filter: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Busca imagens no DuckDuckGo.
        
        Args:
            query: Texto de busca
            max_results: Número máximo de resultados
            type_filter: 'photo', 'clipart', 'gif', 'transparent', 'line' ou None
            
        Returns:
            Lista de resultados formatados
        """
        logger.info(f"[{self.name}] Searching: {query} (max: {max_results})")
        max_results = min(max_results, 40)

        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.images(
                        query,
                        max_results=max_results,
                        type_image=type_filter
                    ))

                formatted_results = []
                for result in results:
                    formatted_results.append({
                        'url': result['image'],
                        'thumbnail': result.get('thumbnail', result['image']),
                        'source': self.name,
                        'title': result.get('title', ''),
                    })

                logger.info(f"[{self.name}] Found {len(formatted_results)} results")
                return formatted_results
            except Exception as e:
                message = str(e)
                lower_msg = message.lower()
                logger.error(f"[{self.name}] Error: {message}")
                if "ratelimit" in lower_msg or "403" in lower_msg:
                    wait_s = 1.2 + (attempt * 1.3) + random.random() * 0.4
                    logger.warning(f"[{self.name}] Rate limited, retrying in {wait_s:.1f}s")
                    time.sleep(wait_s)
                    max_results = max(20, int(max_results * 0.7))
                    continue
                return []

        return []
    def get_name(self) -> str:
        return self.name


# Engines com API (Unsplash, Pexels, Pixabay).

class UnsplashEngine(SearchEngine):
    """Engine de busca usando Unsplash API (CP-008)."""

    def __init__(self, access_key: Optional[str] = None):
        self.name = "Unsplash"
        self.access_key = access_key or ""

    def search(self, query: str, max_results: int = 25, **kwargs) -> List[Dict[str, str]]:
        if not self.access_key:
            logger.warning(f"[{self.name}] Missing API key")
            return []

        clean_query = _clean_query(query)
        per_page = min(max_results, 30)
        total_pages = max(1, math.ceil(max_results / per_page))
        total_pages = min(total_pages, 3)
        headers = {
            "Authorization": f"Client-ID {self.access_key}",
            "User-Agent": HEADERS.get("User-Agent", "Mozilla/5.0"),
        }

        results_out: List[Dict[str, str]] = []
        for page in range(1, total_pages + 1):
            params = {"query": clean_query, "per_page": per_page, "page": page}
            try:
                response = requests.get(
                    "https://api.unsplash.com/search/photos",
                    headers=headers,
                    params=params,
                    timeout=SEARCH_TIMEOUT,
                )
                if response.status_code == 429:
                    logger.warning(f"[{self.name}] Rate limited (429)")
                    break
                response.raise_for_status()
                payload = response.json()
                for item in payload.get("results", []):
                    urls = item.get("urls", {})
                    url = urls.get("regular") or urls.get("full") or urls.get("raw")
                    if not url:
                        continue
                    thumb = urls.get("small") or urls.get("thumb") or url
                    title = item.get("alt_description") or item.get("description") or ""
                    results_out.append(
                        {
                            "url": url,
                            "thumbnail": thumb,
                            "source": self.name,
                            "title": title,
                        }
                    )
                    if len(results_out) >= max_results:
                        break
            except requests.RequestException as exc:
                logger.error(f"[{self.name}] Error: {exc}")
                break

            if len(results_out) >= max_results:
                break
            if total_pages > 1:
                time.sleep(0.2)

        logger.info(f"[{self.name}] Found {len(results_out)} results")
        return results_out

    def get_name(self) -> str:
        return self.name


class PexelsEngine(SearchEngine):
    """Engine de busca usando Pexels API (CP-009)."""

    def __init__(self, api_key: Optional[str] = None):
        self.name = "Pexels"
        self.api_key = api_key or ""

    def search(self, query: str, max_results: int = 25, **kwargs) -> List[Dict[str, str]]:
        if not self.api_key:
            logger.warning(f"[{self.name}] Missing API key")
            return []

        clean_query = _clean_query(query)
        per_page = min(max_results, 80)
        total_pages = max(1, math.ceil(max_results / per_page))
        total_pages = min(total_pages, 3)
        headers = {
            "Authorization": self.api_key,
            "User-Agent": HEADERS.get("User-Agent", "Mozilla/5.0"),
        }

        results_out: List[Dict[str, str]] = []
        for page in range(1, total_pages + 1):
            params = {"query": clean_query, "per_page": per_page, "page": page}
            try:
                response = requests.get(
                    "https://api.pexels.com/v1/search",
                    headers=headers,
                    params=params,
                    timeout=SEARCH_TIMEOUT,
                )
                if response.status_code == 429:
                    logger.warning(f"[{self.name}] Rate limited (429)")
                    break
                response.raise_for_status()
                payload = response.json()
                for item in payload.get("photos", []):
                    src = item.get("src", {})
                    url = src.get("large") or src.get("original") or src.get("medium")
                    if not url:
                        continue
                    thumb = src.get("tiny") or src.get("small") or url
                    title = item.get("alt") or ""
                    results_out.append(
                        {
                            "url": url,
                            "thumbnail": thumb,
                            "source": self.name,
                            "title": title,
                        }
                    )
                    if len(results_out) >= max_results:
                        break
            except requests.RequestException as exc:
                logger.error(f"[{self.name}] Error: {exc}")
                break

            if len(results_out) >= max_results:
                break
            if total_pages > 1:
                time.sleep(0.2)

        logger.info(f"[{self.name}] Found {len(results_out)} results")
        return results_out

    def get_name(self) -> str:
        return self.name


# Engine Pixabay.

class PixabayEngine(SearchEngine):
    """Engine de busca usando Pixabay API (CP-009)."""

    def __init__(self, api_key: Optional[str] = None):
        self.name = "Pixabay"
        self.api_key = api_key or ""

    def search(self, query: str, max_results: int = 25, type_filter: Optional[str] = None, **kwargs) -> List[Dict[str, str]]:
        if not self.api_key:
            logger.warning(f"[{self.name}] Missing API key")
            return []

        clean_query = _clean_query(query)
        per_page = min(max_results, 200)
        total_pages = max(1, math.ceil(max_results / per_page))
        total_pages = min(total_pages, 3)

        results_out: List[Dict[str, str]] = []
        for page in range(1, total_pages + 1):
            params = {
                "key": self.api_key,
                "q": clean_query,
                "per_page": per_page,
                "page": page,
            }
            if type_filter == "photo":
                params["image_type"] = "photo"
            try:
                response = requests.get(
                    "https://pixabay.com/api/",
                    params=params,
                    timeout=SEARCH_TIMEOUT,
                )
                if response.status_code == 429:
                    logger.warning(f"[{self.name}] Rate limited (429)")
                    break
                response.raise_for_status()
                payload = response.json()
                for item in payload.get("hits", []):
                    url = item.get("largeImageURL") or item.get("webformatURL")
                    if not url:
                        continue
                    thumb = item.get("previewURL") or item.get("webformatURL") or url
                    title = item.get("tags") or ""
                    results_out.append(
                        {
                            "url": url,
                            "thumbnail": thumb,
                            "source": self.name,
                            "title": title,
                        }
                    )
                    if len(results_out) >= max_results:
                        break
            except requests.RequestException as exc:
                logger.error(f"[{self.name}] Error: {exc}")
                break

            if len(results_out) >= max_results:
                break
            if total_pages > 1:
                time.sleep(0.2)

        logger.info(f"[{self.name}] Found {len(results_out)} results")
        return results_out

    def get_name(self) -> str:
        return self.name


# Free engines (no API key required).

class OpenverseEngine(SearchEngine):
    """Engine using Openverse (optional API token)."""

    def __init__(self, access_token: Optional[str] = None):
        self.name = "Openverse"
        self.access_token = access_token or ""

    def search(self, query: str, max_results: int = 25, **kwargs) -> List[Dict[str, str]]:
        clean_query = _clean_query(query)
        per_page = min(max_results, 50)
        total_pages = max(1, math.ceil(max_results / per_page))
        total_pages = min(total_pages, 2)

        results_out: List[Dict[str, str]] = []
        for page in range(1, total_pages + 1):
            params = {
                "q": clean_query,
                "page_size": per_page,
                "page": page,
                "mature": "false",
            }
            try:
                headers = None
                if self.access_token:
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                response = requests.get(
                    "https://api.openverse.engineering/v1/images",
                    headers=headers,
                    params=params,
                    timeout=SEARCH_TIMEOUT,
                )
                if response.status_code == 401:
                    logger.warning(f"[{self.name}] Unauthorized (401). Disable or set API key.")
                    break
                response.raise_for_status()
                payload = response.json()
                for item in payload.get("results", []):
                    url = item.get("url") or item.get("thumbnail")
                    if not url:
                        continue
                    mime = item.get("mime_type") or item.get("mimetype") or ""
                    if mime and not mime.startswith("image/"):
                        continue
                    thumb = item.get("thumbnail") or url
                    title = item.get("title") or ""
                    results_out.append(
                        {
                            "url": url,
                            "thumbnail": thumb,
                            "source": self.name,
                            "title": title,
                        }
                    )
                    if len(results_out) >= max_results:
                        break
            except requests.RequestException as exc:
                logger.error(f"[{self.name}] Error: {exc}")
                break

            if len(results_out) >= max_results:
                break
            if total_pages > 1:
                time.sleep(0.2)

        logger.info(f"[{self.name}] Found {len(results_out)} results")
        return results_out

    def get_name(self) -> str:
        return self.name


class WikimediaEngine(SearchEngine):
    """Engine using Wikimedia Commons (no API key)."""

    def __init__(self):
        self.name = "Wikimedia"

    def search(self, query: str, max_results: int = 25, **kwargs) -> List[Dict[str, str]]:
        clean_query = _clean_query(query)
        per_page = min(max_results, 50)
        total_pages = max(1, math.ceil(max_results / per_page))
        total_pages = min(total_pages, 2)

        results_out: List[Dict[str, str]] = []
        for page in range(1, total_pages + 1):
            params = {
                "action": "query",
                "format": "json",
                "formatversion": 2,
                "generator": "search",
                "gsrsearch": f"filetype:bitmap {clean_query}",
                "gsrnamespace": 6,
                "gsrlimit": per_page,
                "gsroffset": (page - 1) * per_page,
                "prop": "imageinfo",
                "iiprop": "url|mime",
                "iiurlwidth": 400,
            }
            try:
                response = requests.get(
                    "https://commons.wikimedia.org/w/api.php",
                    headers=HEADERS,
                    params=params,
                    timeout=SEARCH_TIMEOUT,
                )
                if response.status_code == 403:
                    logger.warning(f"[{self.name}] Forbidden (403).")
                    break
                response.raise_for_status()
                payload = response.json()
                pages = payload.get("query", {}).get("pages", [])
                if isinstance(pages, dict):
                    pages = list(pages.values())
                for item in pages:
                    imageinfo = (item.get("imageinfo") or [])
                    if not imageinfo:
                        continue
                    info = imageinfo[0]
                    mime = info.get("mime", "")
                    if mime and not mime.startswith("image/"):
                        continue
                    if mime == "image/svg+xml":
                        continue
                    url = info.get("url")
                    if not url:
                        continue
                    thumb = info.get("thumburl") or url
                    title = (item.get("title") or "").replace("File:", "")
                    results_out.append(
                        {
                            "url": url,
                            "thumbnail": thumb,
                            "source": self.name,
                            "title": title,
                        }
                    )
                    if len(results_out) >= max_results:
                        break
            except requests.RequestException as exc:
                logger.error(f"[{self.name}] Error: {exc}")
                break

            if len(results_out) >= max_results:
                break
            if total_pages > 1:
                time.sleep(0.2)

        logger.info(f"[{self.name}] Found {len(results_out)} results")
        return results_out

    def get_name(self) -> str:
        return self.name


# Multi-engine orchestration helpers.

class MultiEngineSearcher:
    """
    Orquestrador de múltiplas engines de busca.
    Permite buscar em várias fontes e fazer merge dos resultados.
    """
    
    def __init__(self, engines: List[SearchEngine]):
        self.engines = engines
        logger.info(f"Initialized with {len(engines)} engines: {[e.get_name() for e in engines]}")
    
    def search(self, query: str, max_results: int = 25, **kwargs) -> List[Dict[str, str]]:
        """
        Busca em todas as engines e retorna resultados combinados.
        
        Args:
            query: Texto de busca
            max_results_per_engine: Máximo por engine
            **kwargs: Passado para cada engine
            
        Returns:
            Lista combinada de resultados
        """
        max_results_per_engine = kwargs.pop("max_results_per_engine", None)
        if not max_results_per_engine:
            max_results_per_engine = max_results or MAX_RESULTS_PER_ENGINE
        max_results_total = kwargs.pop("max_results_total", None)
        all_results = []
        seen_urls = set()
        
        for engine in self.engines:
            try:
                results = engine.search(query, max_results_per_engine, **kwargs)
                for item in results:
                    url = item.get("url")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    all_results.append(item)
                    if max_results_total and len(all_results) >= max_results_total:
                        break
            except Exception as e:
                logger.error(f"Engine {engine.get_name()} failed: {str(e)}")
                continue
            if max_results_total and len(all_results) >= max_results_total:
                break
        
        logger.info(f"Total results from all engines: {len(all_results)}")
        return all_results
    
    def add_engine(self, engine: SearchEngine):
        """Adiciona nova engine ao orquestrador."""
        self.engines.append(engine)
        logger.info(f"Added engine: {engine.get_name()}")
    
    def remove_engine(self, engine_name: str):
        """Remove engine por nome."""
        self.engines = [e for e in self.engines if e.get_name() != engine_name]
        logger.info(f"Removed engine: {engine_name}")

    def get_name(self) -> str:
        return "MultiEngine(" + ",".join([e.get_name() for e in self.engines]) + ")"


class FallbackSearcher:
    """Try primary searcher; if empty, fallback to another engine."""

    def __init__(self, primary: SearchEngine, fallback: SearchEngine):
        self.primary = primary
        self.fallback = fallback

    def search(self, query: str, max_results: int = 25, **kwargs) -> List[Dict[str, str]]:
        results = self.primary.search(query, max_results, **kwargs)
        if results:
            return results
        logger.warning("Primary searcher returned no results. Using fallback.")
        return self.fallback.search(query, max_results, **kwargs)

    def get_name(self) -> str:
        return f"Fallback({self.primary.get_name()} -> {self.fallback.get_name()})"


# Factory helpers for default engine wiring.

def get_default_searcher() -> SearchEngine:
    """Return the default searcher, using multi-engine when enabled."""
    engines: List[SearchEngine] = []
    if ENABLE_UNSPLASH and UNSPLASH_ACCESS_KEY:
        engines.append(UnsplashEngine(UNSPLASH_ACCESS_KEY))
    if ENABLE_PEXELS and PEXELS_API_KEY:
        engines.append(PexelsEngine(PEXELS_API_KEY))
    if ENABLE_PIXABAY and PIXABAY_API_KEY:
        engines.append(PixabayEngine(PIXABAY_API_KEY))
    if ENABLE_OPENVERSE:
        engines.append(OpenverseEngine(OPENVERSE_API_KEY))
    if ENABLE_WIKIMEDIA:
        engines.append(WikimediaEngine())

    if ENABLE_MULTI_ENGINE and engines:
        if len(engines) == 1:
            return engines[0]
        primary = MultiEngineSearcher(engines)
        if ENABLE_DDG and ENABLE_DDG_FALLBACK:
            return FallbackSearcher(primary, DuckDuckGoEngine())
        if ENABLE_DDG and not ENABLE_DDG_FALLBACK:
            primary.add_engine(DuckDuckGoEngine())
        return primary
    if ENABLE_DDG:
        return DuckDuckGoEngine()
    return MultiEngineSearcher(engines)


def get_multi_searcher(
    enable_unsplash: bool = False,
    enable_pexels: bool = False,
    enable_pixabay: bool = False,
    enable_openverse: bool = True,
    enable_wikimedia: bool = True,
    enable_ddg: bool = True,
) -> MultiEngineSearcher:
    """Create a multi-engine searcher with selected sources."""
    engines: List[SearchEngine] = []

    if enable_unsplash and UNSPLASH_ACCESS_KEY:
        engines.append(UnsplashEngine(UNSPLASH_ACCESS_KEY))
    if enable_pexels and PEXELS_API_KEY:
        engines.append(PexelsEngine(PEXELS_API_KEY))
    if enable_pixabay and PIXABAY_API_KEY:
        engines.append(PixabayEngine(PIXABAY_API_KEY))
    if enable_openverse:
        engines.append(OpenverseEngine(OPENVERSE_API_KEY))
    if enable_wikimedia:
        engines.append(WikimediaEngine())
    if enable_ddg:
        engines.append(DuckDuckGoEngine())

    return MultiEngineSearcher(engines)
