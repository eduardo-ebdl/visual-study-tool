"""
Testes unitários para core/vision_pipeline.py
Testes sem carregar CLIP models - apenas lógica pura.
"""

import pytest
from core.vision_pipeline import VisionPipeline


class TestVisionPipelineNormalizeWeights:
    """Testa normalização de pesos do modelo."""

    def test_none_weights(self):
        pipeline = VisionPipeline()
        result = pipeline._normalize_weights(None)
        assert pipeline.primary_model_name in result
        assert result[pipeline.primary_model_name] == 1.0

    def test_empty_dict_weights(self):
        pipeline = VisionPipeline()
        result = pipeline._normalize_weights({})
        assert pipeline.primary_model_name in result
        assert result[pipeline.primary_model_name] == 1.0

    def test_positive_weights_normalization(self):
        pipeline = VisionPipeline()
        weights = {"model_a": 2.0, "model_b": 2.0}
        result = pipeline._normalize_weights(weights)
        assert abs(result["model_a"] - 0.5) < 0.0001
        assert abs(result["model_b"] - 0.5) < 0.0001

    def test_single_weight(self):
        pipeline = VisionPipeline()
        weights = {"model_a": 5.0}
        result = pipeline._normalize_weights(weights)
        assert abs(result["model_a"] - 1.0) < 0.0001

    def test_zero_weights_fallback(self):
        pipeline = VisionPipeline()
        weights = {"model_a": 0, "model_b": 0}
        result = pipeline._normalize_weights(weights)
        assert pipeline.primary_model_name in result

    def test_negative_weights_ignored(self):
        pipeline = VisionPipeline()
        weights = {"model_a": -1.0, "model_b": 2.0}
        result = pipeline._normalize_weights(weights)
        # Negative weights são ignorados
        assert "model_a" not in result
        assert abs(result["model_b"] - 1.0) < 0.0001

    def test_mixed_positive_zero_weights(self):
        pipeline = VisionPipeline()
        weights = {"model_a": 3.0, "model_b": 0, "model_c": 3.0}
        result = pipeline._normalize_weights(weights)
        # model_b com peso 0 é ignorado
        assert "model_b" not in result
        assert abs(result["model_a"] - 0.5) < 0.0001
        assert abs(result["model_c"] - 0.5) < 0.0001


class TestVisionPipelineInit:
    """Testa inicialização do pipeline."""

    def test_default_init(self):
        pipeline = VisionPipeline()
        assert pipeline.primary_model_name is not None
        assert pipeline.secondary_model_name is not None
        assert isinstance(pipeline.models, dict)
        assert len(pipeline.text_cache) == 0
        assert len(pipeline.image_cache) == 0

    def test_custom_weights_init(self):
        custom_weights = {"model_x": 0.7, "model_y": 0.3}
        pipeline = VisionPipeline(default_model_weights=custom_weights)
        assert pipeline.default_model_weights == custom_weights

    def test_secondary_disabled_init(self):
        pipeline = VisionPipeline(secondary_enabled=False)
        assert pipeline.secondary_enabled is False


class TestVisionPipelineClear:
    """Testa limpeza de cache."""

    def test_clear_cache_empties_text_cache(self):
        pipeline = VisionPipeline()
        # Simular adição ao cache
        pipeline.text_cache[("model", "text")] = [1.0, 2.0, 3.0]
        assert len(pipeline.text_cache) > 0

        pipeline.clear_cache()
        assert len(pipeline.text_cache) == 0

    def test_clear_cache_keeps_image_cache(self):
        """clear_cache limpa apenas text_cache, não image_cache."""
        pipeline = VisionPipeline()
        pipeline.text_cache[("model", "text")] = [1.0]
        pipeline.image_cache[("model", "hash")] = [2.0]

        pipeline.clear_cache()
        assert len(pipeline.text_cache) == 0
        # image_cache não é limpo por clear_cache
        assert len(pipeline.image_cache) == 1


class TestVisionPipelineWeightEdgeCases:
    """Testa edge cases de normalização de pesos."""

    def test_very_small_weights(self):
        pipeline = VisionPipeline()
        weights = {"model_a": 0.0001, "model_b": 0.0001}
        result = pipeline._normalize_weights(weights)
        assert abs(result["model_a"] - 0.5) < 0.0001
        assert abs(result["model_b"] - 0.5) < 0.0001

    def test_very_large_weights(self):
        pipeline = VisionPipeline()
        weights = {"model_a": 1e10, "model_b": 1e10}
        result = pipeline._normalize_weights(weights)
        assert abs(result["model_a"] - 0.5) < 0.0001
        assert abs(result["model_b"] - 0.5) < 0.0001

    def test_imbalanced_weights(self):
        pipeline = VisionPipeline()
        weights = {"model_a": 1.0, "model_b": 99.0}
        result = pipeline._normalize_weights(weights)
        assert abs(result["model_a"] - 0.01) < 0.0001
        assert abs(result["model_b"] - 0.99) < 0.0001
