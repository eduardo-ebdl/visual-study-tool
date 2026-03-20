"""
Testes unitários para core/query_utils.py
Funções 100% puras sem dependências externas.
"""

import pytest
from core.query_utils import (
    subject_tokens,
    tokenize_text,
    dedupe_words,
    normalize_pose,
    normalize_negative,
    normalize_angle,
    build_query,
    build_clip_prompt,
    expand_subject,
    title_matches_subject,
    title_contains_blocklist,
    filter_photography_metadata,
)


class TestSubjectTokens:
    """Testa extração de tokens do subject."""

    def test_empty_subject(self):
        assert subject_tokens("") == []

    def test_short_tokens_filtered(self):
        # Tokens <= 2 chars são filtrados
        result = subject_tokens("a bo cat dog")
        assert result == ["cat", "dog"]

    def test_normal_subject(self):
        result = subject_tokens("Wolf Knight")
        assert sorted(result) == sorted(["wolf", "knight"])

    def test_compound_subject(self):
        result = subject_tokens("Cyberpunk Runner")
        assert sorted(result) == sorted(["cyberpunk", "runner"])


class TestTokenizeText:
    """Testa tokenização geral de texto."""

    def test_empty_text(self):
        assert tokenize_text("") == []

    def test_single_word(self):
        assert tokenize_text("hello") == ["hello"]

    def test_multiple_words(self):
        result = tokenize_text("hello world test")
        assert result == ["hello", "world", "test"]

    def test_special_chars_removed(self):
        result = tokenize_text("hello-world_test.ok")
        assert sorted(result) == sorted(["hello", "world", "test", "ok"])

    def test_numbers_preserved(self):
        result = tokenize_text("test123 456ok")
        assert sorted(result) == sorted(["test123", "456ok"])


class TestDedupeWords:
    """Testa remoção de duplicatas mantendo ordem."""

    def test_empty_list(self):
        assert dedupe_words([]) == []

    def test_no_duplicates(self):
        assert dedupe_words(["a", "b", "c"]) == ["a", "b", "c"]

    def test_with_duplicates(self):
        result = dedupe_words(["a", "b", "a", "c", "b"])
        assert result == ["a", "b", "c"]

    def test_order_preserved(self):
        result = dedupe_words(["wolf", "knight", "wolf", "epic"])
        assert result == ["wolf", "knight", "epic"]


class TestNormalizePose:
    """Testa normalização de pose removendo overlap com subject."""

    def test_empty_pose(self):
        assert normalize_pose("wolf", "") == ""

    def test_no_overlap(self):
        result = normalize_pose("wolf", "standing side profile")
        assert sorted(result.split()) == sorted(["standing", "side", "profile"])

    def test_with_overlap(self):
        result = normalize_pose("wolf knight", "wolf standing knight")
        assert sorted(result.split()) == ["standing"]

    def test_all_overlap(self):
        result = normalize_pose("standing pose", "standing pose")
        assert result == ""


class TestNormalizeNegative:
    """Testa normalização de negatives."""

    def test_empty_negative(self):
        assert normalize_negative("wolf", "") == ""

    def test_no_overlap(self):
        result = normalize_negative("wolf", "blurry watermark")
        assert sorted(result.split()) == ["blurry", "watermark"]

    def test_with_overlap(self):
        result = normalize_negative("wolf knight", "wolf blurry knight")
        assert result == "blurry"


class TestNormalizeAngle:
    """Testa normalização de angle."""

    def test_empty_angle(self):
        assert normalize_angle("wolf", "standing", "") == ""

    def test_no_overlap(self):
        result = normalize_angle("wolf", "standing", "front 3quarter")
        assert sorted(result.split()) == sorted(["front", "3quarter"])

    def test_overlap_subject(self):
        result = normalize_angle("wolf", "", "wolf front side")
        assert sorted(result.split()) == sorted(["front", "side"])

    def test_overlap_pose(self):
        result = normalize_angle("", "standing", "standing front")
        assert result == "front"

    def test_full_overlap(self):
        result = normalize_angle("wolf", "standing", "wolf standing")
        assert result == ""


class TestBuildQuery:
    """Testa construção de query string."""

    def test_empty_inputs(self):
        result = build_query("", "", "")
        assert result == ""

    def test_subject_only(self):
        result = build_query("wolf", "", "")
        assert result == "wolf"

    def test_with_suffix(self):
        result = build_query("wolf", "standing", "")
        assert sorted(result.split()) == sorted(["wolf", "standing"])

    def test_with_negatives(self):
        result = build_query("wolf", "standing", "-blurry -watermark")
        assert "wolf" in result
        assert "-blurry" in result

    def test_dedupe(self):
        result = build_query("wolf wolf", "standing standing", "")
        assert sorted(result.split()) == sorted(["wolf", "standing"])


class TestBuildClipPrompt:
    """Testa construção de prompt CLIP."""

    def test_subject_only(self):
        assert build_clip_prompt("wolf", "") == "wolf"

    def test_with_quality(self):
        result = build_clip_prompt("wolf", "hd quality cinematic")
        assert "wolf" in result
        assert "quality" in result

    def test_dedupe(self):
        result = build_clip_prompt("wolf wolf", "quality quality")
        assert result.count("wolf") == 1
        assert result.count("quality") == 1


class TestExpandSubject:
    """Testa expansão de subject com sinônimos."""

    def test_subject_without_synonym(self):
        result = expand_subject("unknown")
        assert result == ["unknown"]

    def test_subject_with_synonym(self):
        result = expand_subject("ocelot")
        assert result[0] == "ocelot"
        assert "leopardus pardalis" in result

    def test_case_insensitive(self):
        result = expand_subject("OCELOT")
        assert len(result) > 1

    def test_empty_subject(self):
        result = expand_subject("")
        # Função filtra strings vazias
        assert result == []


class TestTitleMatchesSubject:
    """Testa matching de title com subject tokens."""

    def test_empty_title(self):
        assert title_matches_subject("", ["wolf"]) is False

    def test_match_case_insensitive(self):
        assert title_matches_subject("A Beautiful WOLF Portrait", ["wolf"]) is True

    def test_no_match(self):
        assert title_matches_subject("A Beautiful Cat", ["wolf"]) is False

    def test_partial_token_match(self):
        # Busca substring, não word boundary
        assert title_matches_subject("amazing wolf-like creature", ["wolf"]) is True

    def test_empty_tokens(self):
        assert title_matches_subject("Some Title", []) is False


class TestTitleContainsBlocklist:
    """Testa blocklist de termos fotográficos."""

    def test_empty_title(self):
        assert title_contains_blocklist("") is False

    def test_photo_blocklisted(self):
        assert title_contains_blocklist("Beautiful Photography Moment") is True

    def test_camera_blocklisted(self):
        assert title_contains_blocklist("Camera Lens Test") is True

    def test_not_blocklisted(self):
        assert title_contains_blocklist("Digital Art Wolf") is False

    def test_case_insensitive(self):
        assert title_contains_blocklist("PHOTOGRAPHY GUIDE") is True


class TestFilterPhotographyMetadata:
    """Testa filtragem de metadados fotográficos."""

    def test_empty_items(self):
        assert filter_photography_metadata([], ["wolf"]) == []

    def test_empty_tokens(self):
        items = [{"title": "Photo 1"}, {"title": "Photo 2"}]
        # Sem tokens, nada é filtrado por blocklist
        assert len(filter_photography_metadata(items, [])) == 2

    def test_filter_photo_metadata(self):
        items = [
            {"title": "Wolf Portrait"},
            {"title": "Photography Setup"},
            {"title": "Wolf Art"},
        ]
        result = filter_photography_metadata(items, ["wolf"])
        # "Wolf Portrait" e "Wolf Art" passam (match subject)
        # "Photography Setup" é filtrado (photography é blocklist)
        assert len(result) == 2

    def test_missing_title(self):
        items = [{"url": "http://example.com"}]
        # Sem title, item passa
        assert len(filter_photography_metadata(items, ["wolf"])) == 1

    def test_subject_match_overrides_blocklist(self):
        items = [
            {"title": "Wolf Photography Masterclass"}
        ]
        result = filter_photography_metadata(items, ["wolf"])
        # Wolf match overrides photography blocklist
        assert len(result) == 1
