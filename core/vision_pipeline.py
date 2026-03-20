"""
Pipeline de visão computacional.
Responsável por embeddings CLIP, filtros e scoring.
"""

from sentence_transformers import SentenceTransformer, util
from PIL import Image
from typing import List, Tuple, Dict, Optional
import logging
from utils.pretty_logger import wrap_logger

from config.settings import (
    CLIP_PRIMARY_MODEL_NAME,
    CLIP_SECONDARY_MODEL_NAME,
    CLIP_SECONDARY_ENABLED,
    CLIP_SECONDARY_WINDOW,
    CLIP_DEFAULT_MODEL_WEIGHTS,
    BASE_SIMILARITY_THRESHOLD,
    INTEGRITY_MARGIN,
    INTEGRITY_MIN_KEEP,
    INTEGRITY_MIN_KEEP_RATIO,
    EMBEDDING_CACHE_ENABLED,
)
from utils.image_utils import compute_image_hash
from utils.embedding_cache import get_cached_embedding, set_cached_embedding

logger = wrap_logger(logging.getLogger(__name__))


class VisionPipeline:
    """Pipeline de processamento de visão computacional."""

    def __init__(
        self,
        primary_model_name: str = CLIP_PRIMARY_MODEL_NAME,
        secondary_model_name: str = CLIP_SECONDARY_MODEL_NAME,
        secondary_enabled: bool = CLIP_SECONDARY_ENABLED,
        secondary_window: Tuple[float, float] = CLIP_SECONDARY_WINDOW,
        default_model_weights: Optional[Dict[str, float]] = None,
    ):
        """
        Inicializa pipeline.

        Args:
            primary_model_name: Nome do modelo CLIP principal
            secondary_model_name: Nome do modelo CLIP secundário
            secondary_enabled: Habilita ensemble leve no score
            secondary_window: Faixa de score para re-score
            default_model_weights: Pesos padrão dos modelos
        """
        self.primary_model_name = primary_model_name
        self.secondary_model_name = secondary_model_name
        self.secondary_enabled = secondary_enabled
        self.secondary_window = secondary_window
        self.default_model_weights = default_model_weights or CLIP_DEFAULT_MODEL_WEIGHTS
        self.models = {}
        # Keep lightweight in-memory caches for embeddings.
        self.text_cache = {}
        self.image_cache = {}
        self.embedding_cache_enabled = EMBEDDING_CACHE_ENABLED
        logger.info(
            "VisionPipeline initialized with primary=%s secondary=%s",
            primary_model_name,
            secondary_model_name,
        )

    def load_model(self, model_name: str):
        """Carrega modelo CLIP (lazy loading)."""
        # Lazy-load CLIP models to reduce startup cost.
        if model_name not in self.models:
            logger.info("Loading CLIP model: %s", model_name)
            self.models[model_name] = SentenceTransformer(model_name)
            logger.info("CLIP model loaded: %s", model_name)
        return self.models[model_name]

    def encode_text(self, text: str, model_name: Optional[str] = None) -> any:
        """
        Encode texto para embedding (com cache por modelo).

        Args:
            text: Texto para encodar
            model_name: Modelo a usar

        Returns:
            Embedding do texto
        """
        name = model_name or self.primary_model_name
        cache_key = (name, text)
        if cache_key not in self.text_cache:
            model = self.load_model(name)
            self.text_cache[cache_key] = model.encode(text)
            logger.debug("Cached text embedding: %s...", text[:50])
        return self.text_cache[cache_key]

    def encode_texts(self, texts: List[str], model_name: Optional[str] = None) -> any:
        """
        Encode múltiplos textos (sem cache individual).

        Args:
            texts: Lista de textos
            model_name: Modelo a usar

        Returns:
            Array de embeddings
        """
        name = model_name or self.primary_model_name
        model = self.load_model(name)
        return model.encode(texts)

    def encode_images(self, images: List[Image.Image], model_name: Optional[str] = None) -> any:
        """
        Encode imagens para embeddings.

        Args:
            images: Lista de imagens PIL
            model_name: Modelo a usar

        Returns:
            Array de embeddings
        """
        name = model_name or self.primary_model_name
        model = self.load_model(name)
        if not self.embedding_cache_enabled:
            return model.encode(images)

        embeddings = [None] * len(images)
        missing_images = []
        missing_indices = []
        missing_keys = []

        for idx, img in enumerate(images):
            img_hash = compute_image_hash(img)
            if not img_hash:
                missing_images.append(img)
                missing_indices.append(idx)
                missing_keys.append("")
                continue
            cache_key = f"{name}:{img_hash}"
            cached = self.image_cache.get(cache_key)
            if cached is None:
                cached = get_cached_embedding(cache_key)
            if cached is not None:
                embeddings[idx] = cached
            else:
                missing_images.append(img)
                missing_indices.append(idx)
                missing_keys.append(cache_key)

        if missing_images:
            new_embeddings = model.encode(missing_images)
            for i, cache_key, emb in zip(missing_indices, missing_keys, new_embeddings):
                embeddings[i] = emb
                if cache_key:
                    self.image_cache[cache_key] = emb
                    set_cached_embedding(cache_key, emb)

        return embeddings

    def compute_similarity(self, emb1, emb2) -> float:
        """
        Calcula similaridade cosine entre embeddings.

        Args:
            emb1: Embedding 1
            emb2: Embedding 2

        Returns:
            Score de similaridade (0-1)
        """
        return float(util.cos_sim(emb1, emb2)[0][0])

    def filter_by_integrity(
        self,
        images: List[Image.Image],
        urls: List[str],
        subject: str,
        negative_prompt: str,
        threshold: float = BASE_SIMILARITY_THRESHOLD,
        margin: float = INTEGRITY_MARGIN,
    ) -> Tuple[List[Image.Image], List[str], List[int]]:
        """
        Filtro de integridade: remove imagens que parecem mais com o negativo.

        Args:
            images: Lista de imagens
            urls: Lista de URLs correspondentes
            subject: Assunto principal (positivo)
            negative_prompt: O que evitar
            threshold: Threshold base de similaridade
            margin: Margem de segurança

        Returns:
            Tupla (imagens_válidas, urls_válidas, índices_válidos)
        """
        # Integrity filter uses only the primary model for speed.
        subject_emb = self.encode_text(subject, self.primary_model_name)
        negative_emb = self.encode_text(negative_prompt, self.primary_model_name)
        img_embeddings = self.encode_images(images, self.primary_model_name)

        valid_indices = []
        scores_subject = []
        scores_negative = []
        scores_delta = []

        for i in range(len(images)):
            score_subject = self.compute_similarity(img_embeddings[i], subject_emb)
            score_negative = self.compute_similarity(img_embeddings[i], negative_emb)
            delta = score_subject - score_negative
            scores_subject.append(score_subject)
            scores_negative.append(score_negative)
            scores_delta.append(delta)

            if score_subject > threshold:
                if score_subject > (score_negative + margin):
                    valid_indices.append(i)

        if scores_subject:
            avg_subject = sum(scores_subject) / len(scores_subject)
            avg_negative = sum(scores_negative) / len(scores_negative)
            avg_delta = sum(scores_delta) / len(scores_delta)
            logger.info(
                "Integrity stats: subject(min/avg/max)=%.3f/%.3f/%.3f | "
                "negative(min/avg/max)=%.3f/%.3f/%.3f | "
                "delta(min/avg/max)=%.3f/%.3f/%.3f",
                min(scores_subject), avg_subject, max(scores_subject),
                min(scores_negative), avg_negative, max(scores_negative),
                min(scores_delta), avg_delta, max(scores_delta),
            )

        # Adaptive fallback to keep a minimum viable batch.
        min_keep = max(INTEGRITY_MIN_KEEP, int(len(images) * INTEGRITY_MIN_KEEP_RATIO))
        if len(valid_indices) < min_keep:
            logger.warning(
                "Integrity filter too strict (%s/%s). Applying adaptive fallback.",
                len(valid_indices),
                len(images),
            )
            candidate_indices = [i for i, delta in enumerate(scores_delta) if delta > 0]
            if not candidate_indices:
                candidate_indices = list(range(len(images)))
            candidate_indices.sort(
                key=lambda i: (scores_delta[i], scores_subject[i]),
                reverse=True,
            )
            valid_indices = candidate_indices[:min_keep]

        valid_images = [images[i] for i in valid_indices]
        valid_urls = [urls[i] for i in valid_indices]

        logger.info("Integrity filter: %s/%s passed", len(valid_images), len(images))

        return valid_images, valid_urls, valid_indices

    def _normalize_weights(self, weights: Optional[Dict[str, float]]) -> Dict[str, float]:
        if not weights:
            return {self.primary_model_name: 1.0}
        total = sum(value for value in weights.values() if value and value > 0)
        if total <= 0:
            return {self.primary_model_name: 1.0}
        return {key: value / total for key, value in weights.items() if value and value > 0}

    def _score_with_model(
        self,
        images: List[Image.Image],
        base_prompt: str,
        criteria: List[Tuple[str, float]],
        model_name: str,
    ) -> List[float]:
        base_emb = self.encode_text(base_prompt, model_name)
        img_embeddings = self.encode_images(images, model_name)
        criteria_embs = [
            (self.encode_text(criterion_text, model_name), weight)
            for criterion_text, weight in criteria
        ]

        scores = []
        for i in range(len(images)):
            score = self.compute_similarity(img_embeddings[i], base_emb)
            if score > 0.20:
                for crit_emb, weight in criteria_embs:
                    crit_score = self.compute_similarity(img_embeddings[i], crit_emb)
                    score += (crit_score * weight * 0.5)
            scores.append(score)
        return scores

    def score_images(
        self,
        images: List[Image.Image],
        base_prompt: str,
        criteria: Optional[List[Tuple[str, float]]] = None,
        model_weights: Optional[Dict[str, float]] = None,
        secondary_window: Optional[Tuple[float, float]] = None,
    ) -> List[float]:
        """
        Calcula scores para imagens baseado em critérios.

        Args:
            images: Lista de imagens
            base_prompt: Prompt base de busca
            criteria: Lista de (critério_texto, peso)
            model_weights: Pesos por modelo (opcional)
            secondary_window: Faixa de score para re-score

        Returns:
            Lista de scores
        """
        if criteria is None:
            criteria = []

        weights = self._normalize_weights(model_weights or self.default_model_weights)

        # Score images with the primary model.
        primary_scores = self._score_with_model(
            images,
            base_prompt,
            criteria,
            self.primary_model_name,
        )

        if not self.secondary_enabled:
            return primary_scores

        secondary_weight = weights.get(self.secondary_model_name, 0.0)
        if secondary_weight <= 0:
            return primary_scores

        # Re-score borderline cases with the secondary model and blend.
        window = secondary_window or self.secondary_window
        min_score, max_score = window
        borderline_indices = [
            i for i, score in enumerate(primary_scores) if min_score <= score <= max_score
        ]

        if not borderline_indices:
            return primary_scores

        try:
            images_borderline = [images[i] for i in borderline_indices]
            secondary_scores = self._score_with_model(
                images_borderline,
                base_prompt,
                criteria,
                self.secondary_model_name,
            )
        except Exception as exc:
            logger.warning("Secondary model failed, using primary only: %s", exc)
            return primary_scores

        primary_weight = weights.get(self.primary_model_name, 1.0)
        pair_total = primary_weight + secondary_weight
        if pair_total <= 0:
            pair_total = 1.0

        for idx, secondary_score in zip(borderline_indices, secondary_scores):
            blended = (
                primary_scores[idx] * primary_weight + secondary_score * secondary_weight
            ) / pair_total
            primary_scores[idx] = blended

        return primary_scores

    def generate_smart_tags(
        self,
        image: Image.Image,
        subject: str,
        pose: str,
        top_k: int = 4,
        threshold: float = 0.23,
    ) -> List[str]:
        """
        Gera tags automáticas baseadas na imagem.

        Args:
            image: Imagem PIL
            subject: Assunto principal
            pose: Pose/detalhe
            top_k: Número de tags
            threshold: Threshold mínimo

        Returns:
            Lista de tags
        """
        # Generate simple tags via text-image similarity ranking.
        tech_tags = [
            "side profile", "front view", "three-quarter view",
            "close-up", "full body", "macro detail",
            "cinematic light", "neutral light", "dark moody",
            "sharp focus", "blurred background", "mouth open",
            "action pose", "biting", "teeth", "fangs", "aggressive",
        ]

        user_tags = [t.strip().lower() for t in f"{subject} {pose}".split() if len(t) > 3]

        candidates = list(set(user_tags + tech_tags))

        model = self.load_model(self.primary_model_name)
        img_emb = model.encode([image])[0]
        text_emb = self.encode_texts(candidates, self.primary_model_name)

        similarities = util.cos_sim(img_emb.reshape(1, -1), text_emb)[0]

        scored_tags = [(float(sim), tag) for sim, tag in zip(similarities, candidates)]
        scored_tags.sort(key=lambda x: x[0], reverse=True)

        top_tags = [tag for score, tag in scored_tags[:top_k] if score > threshold]

        return top_tags

    def clear_cache(self):
        """Limpa cache de embeddings de texto."""
        self.text_cache.clear()
        logger.info("Text embedding cache cleared")
