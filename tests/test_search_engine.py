"""
Testes unitários para core/search_engine.py
Testes sem network - apenas lógica pura.
"""

import pytest
from core.search_engine import _clean_query


class TestCleanQuery:
    """Testa limpeza de query (remove tokens negativos)."""

    def test_empty_query(self):
        assert _clean_query("") == ""

    def test_none_query(self):
        result = _clean_query(None)
        assert result == ""

    def test_no_negative_tokens(self):
        result = _clean_query("wolf standing forest")
        assert result == "wolf standing forest"

    def test_remove_single_negative_token(self):
        result = _clean_query("wolf -blurry forest")
        assert result == "wolf forest"

    def test_remove_multiple_negative_tokens(self):
        result = _clean_query("wolf -blurry -watermark -small")
        assert result == "wolf"

    def test_negative_tokens_only(self):
        result = _clean_query("-blur -watermark -small")
        assert result == ""

    def test_mixed_tokens(self):
        result = _clean_query("beautiful wolf -ugly -bad standing side-profile")
        assert "beautiful" in result
        assert "wolf" in result
        assert "standing" in result
        assert "side-profile" in result
        assert "-ugly" not in result
        assert "-bad" not in result

    def test_preserve_order(self):
        result = _clean_query("a b -c d e -f g")
        assert result == "a b d e g"


class TestSearchEngineInterface:
    """Testa interface de engine de busca (sem network)."""

    def test_unsplash_engine_without_api_key(self):
        from core.search_engine import UnsplashEngine

        engine = UnsplashEngine(access_key="")
        assert engine.get_name() == "Unsplash"
        # Sem API key deve retornar []
        result = engine.search("wolf", max_results=10)
        assert result == []

    def test_pexels_engine_without_api_key(self):
        from core.search_engine import PexelsEngine

        engine = PexelsEngine(api_key="")
        assert engine.get_name() == "Pexels"
        # Sem API key deve retornar []
        result = engine.search("wolf", max_results=10)
        assert result == []

    def test_pixabay_engine_without_api_key(self):
        from core.search_engine import PixabayEngine

        engine = PixabayEngine(api_key="")
        assert engine.get_name() == "Pixabay"
        # Sem API key deve retornar []
        result = engine.search("wolf", max_results=10)
        assert result == []

    def test_duckduckgo_engine_name(self):
        from core.search_engine import DuckDuckGoEngine

        engine = DuckDuckGoEngine()
        assert engine.get_name() == "DuckDuckGo"

    def test_openverse_engine_name(self):
        from core.search_engine import OpenverseEngine

        engine = OpenverseEngine()
        assert engine.get_name() == "Openverse"

    def test_wikimedia_engine_name(self):
        from core.search_engine import WikimediaEngine

        engine = WikimediaEngine()
        assert engine.get_name() == "Wikimedia"


class TestSearchEngineReturn:
    """Testa formato de retorno de engines (sem fazer requests)."""

    def test_unsplash_returns_list_with_missing_key(self):
        from core.search_engine import UnsplashEngine

        engine = UnsplashEngine(access_key="")
        result = engine.search("wolf")
        assert isinstance(result, list)

    def test_pexels_returns_list_with_missing_key(self):
        from core.search_engine import PexelsEngine

        engine = PexelsEngine(api_key="")
        result = engine.search("wolf")
        assert isinstance(result, list)

    def test_pixabay_returns_list_with_missing_key(self):
        from core.search_engine import PixabayEngine

        engine = PixabayEngine(api_key="")
        result = engine.search("wolf")
        assert isinstance(result, list)


class TestCleanQueryEdgeCases:
    """Testa edge cases de _clean_query."""

    def test_whitespace_normalization(self):
        result = _clean_query("wolf  -blur   forest")
        assert "  " not in result  # Sem espaços duplos no resultado
        assert "wolf" in result
        assert "forest" in result

    def test_only_hyphenated_words(self):
        result = _clean_query("side-by-side full-body")
        assert "side-by-side" in result
        assert "full-body" in result

    def test_negative_at_start_middle_end(self):
        result = _clean_query("-bad wolf -ugly -small")
        assert result == "wolf"

    def test_token_with_number(self):
        result = _clean_query("wolf -blurry 4k portrait")
        assert "4k" in result
        assert "portrait" in result
        assert "-blurry" not in result
