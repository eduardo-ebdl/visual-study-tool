"""
Sistema de download paralelo de imagens.
Responsável por baixar, validar e pré-processar imagens.
"""

import requests
from io import BytesIO
from PIL import Image, ImageOps
from typing import List, Tuple, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from utils.pretty_logger import log as pretty_log

from config.settings import HEADERS, DOWNLOAD_TIMEOUT, DEFAULT_IMAGE_SIZE, ACCEPTED_FORMATS

logger = logging.getLogger(__name__)


class ImageDownloader:
    """Gerenciador de download de imagens."""
    
    def __init__(self, timeout: int = DOWNLOAD_TIMEOUT, max_workers: int = 10):
        """
        Inicializa downloader.
        
        Args:
            timeout: Timeout para cada download (segundos)
            max_workers: Número máximo de threads paralelas
        """
        self.timeout = timeout
        self.max_workers = max_workers
        self.headers = HEADERS.copy()
    
    def download_single(self, url: str, resize_to: Optional[Tuple[int, int]] = None) -> Optional[Tuple[Image.Image, str]]:
        """
        Baixa uma única imagem.
        
        Args:
            url: URL da imagem
            resize_to: Tupla (width, height) para redimensionar, ou None
            
        Returns:
            Tupla (imagem_PIL, url) ou None se falhar
        """
        # Fetch, decode, normalize format, and optionally resize a single image.
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code != 200:
                logger.debug(f"Failed to download {url}: HTTP {response.status_code}")
                return None
            
            img = Image.open(BytesIO(response.content))
            
            if img.mode not in ACCEPTED_FORMATS:
                img = img.convert("RGB")
            
            if resize_to:
                img = ImageOps.fit(img, resize_to, method=Image.Resampling.LANCZOS)
            
            return (img, url)
            
        except requests.exceptions.Timeout:
            logger.debug(f"Timeout downloading {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"Request error for {url}: {str(e)}")
            return None
        except Exception as e:
            logger.debug(f"Error processing {url}: {str(e)}")
            return None
    
    def download_batch(
        self, 
        urls: List[str], 
        resize_to: Optional[Tuple[int, int]] = DEFAULT_IMAGE_SIZE,
        progress_callback: Optional[callable] = None
    ) -> List[Tuple[Image.Image, str]]:
        """
        Baixa múltiplas imagens em paralelo.
        
        Args:
            urls: Lista de URLs
            resize_to: Tamanho para redimensionar
            progress_callback: Função chamada a cada download (opcional)
            
        Returns:
            Lista de tuplas (imagem, url) bem-sucedidas
        """
        results = []
        total = len(urls)
        completed = 0
        
        pretty_log(f"Starting download of {total} images", "SYSTEM")
        
        # Run downloads in parallel and collect successful results.
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self.download_single, url, resize_to): url 
                for url in urls
            }
            
            for future in as_completed(future_to_url):
                completed += 1
                url = future_to_url[future]
                
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                        logger.debug(f"Downloaded {url}")
                except Exception as e:
                    logger.debug(f"Exception downloading {url}: {str(e)}")
                
                if progress_callback:
                    progress_callback(completed, total)
        
        success_rate = len(results) / total * 100 if total > 0 else 0
        pretty_log(
            f"Download complete: {len(results)}/{total} successful ({success_rate:.1f}%)",
            "SUCCESS",
        )
        
        return results
    
    def download_from_search_results(
        self, 
        search_results: List[Dict[str, str]],
        resize_to: Optional[Tuple[int, int]] = DEFAULT_IMAGE_SIZE,
        progress_callback: Optional[callable] = None
    ) -> List[Tuple[Image.Image, str, str]]:
        """
        Baixa imagens de resultados de busca formatados.
        
        Args:
            search_results: Lista de dicts com 'url' e 'source'
            resize_to: Tamanho para redimensionar
            progress_callback: Função de progresso
            
        Returns:
            Lista de tuplas (imagem, url, source)
        """
        urls = [result['url'] for result in search_results]
        sources = {result['url']: result['source'] for result in search_results}
        
        # Reuse batch downloader and reattach source metadata.
        downloaded = self.download_batch(urls, resize_to, progress_callback)
        
        results_with_source = [
            (img, url, sources.get(url, "unknown"))
            for img, url in downloaded
        ]
        
        return results_with_source


# Convenience helper for quick batch downloads.
def download_images(
    urls: List[str],
    resize_to: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    timeout: int = DOWNLOAD_TIMEOUT,
    max_workers: int = 10
) -> List[Tuple[Image.Image, str]]:
    """
    Função helper para download rápido.
    
    Args:
        urls: Lista de URLs
        resize_to: Tamanho de redimensionamento
        timeout: Timeout por imagem
        max_workers: Threads paralelas
        
    Returns:
        Lista de (imagem, url)
    """
    downloader = ImageDownloader(timeout=timeout, max_workers=max_workers)
    return downloader.download_batch(urls, resize_to)
