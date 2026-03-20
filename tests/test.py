"""
Teste de todos os módulos e componentes refatorados.
"""

import sys
import os

# 1) Configura caminhos de importação para testes.
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """
    Testa se todos os módulos podem ser importados.
    """
    print("\n🔍 Testando imports...")
    
    try:
        from config import presets, settings
        print("✅ config.presets")
        print("✅ config.settings")
        from config import ui_options
        print("✅ config.ui_options")
        
        from core import search_engine, downloaders, vision_pipeline
        print("✅ core.search_engine")
        print("✅ core.downloaders")
        print("✅ core.vision_pipeline")
        from core import query_utils
        print("✅ core.query_utils")
        
        from utils import image_utils
        print("✅ utils.image_utils")
        from utils import file_utils
        print("✅ utils.file_utils")
        from ui import components
        print("✅ ui.components")
        from ui import layout
        print("✅ ui.layout")
        from core import search_pipeline
        print("✅ core.search_pipeline")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_presets():
    """
    Testa sistema de presets.
    """
    print("\n🎨 Testando presets...")
    
    try:
        from config.presets import PRESETS, list_presets, get_preset
        
        preset_names = list_presets()
        print(f"✅ {len(preset_names)} presets disponíveis")
        
        for name in preset_names:
            preset = get_preset(name)
            assert 'suffix' in preset
            assert 'clip_negatives' in preset
            print(f"✅ Preset '{name}' válido")
        
        return True
    except Exception as e:
        print(f"❌ Preset error: {e}")
        return False


def test_settings():
    """
    Testa configurações.
    """
    print("\n⚙️ Testando settings...")
    
    try:
        from config.settings import (
            DOWNLOAD_DIR, CLIP_MODEL_NAME, HEADERS,
            BASE_SIMILARITY_THRESHOLD, RANK_COLORS
        )
        
        print(f"✅ CLIP Model: {CLIP_MODEL_NAME}")
        print(f"✅ Download dir: {DOWNLOAD_DIR}")
        print(f"✅ Threshold: {BASE_SIMILARITY_THRESHOLD}")
        
        assert os.path.exists(DOWNLOAD_DIR)
        print(f"✅ Diretórios criados automaticamente")
        
        return True
    except Exception as e:
        print(f"❌ Settings error: {e}")
        return False


def test_search_engine():
    """
    Testa abstração de search engine.
    """
    print("\n🔎 Testando search engine...")
    
    try:
        from core.search_engine import DuckDuckGoEngine, get_default_searcher
        
        engine = get_default_searcher()
        print(f"✅ Engine criada: {engine.get_name()}")
        
        print("⏳ Testando busca real (5 resultados)...")
        results = engine.search("wolf", max_results=5)
        
        if results:
            print(f"✅ Busca funcionou: {len(results)} resultados")
            assert 'url' in results[0]
            assert 'source' in results[0]
            print("✅ Formato de resultados correto")
        else:
            print("⚠️ Busca não retornou resultados (pode ser rate limit)")
        
        return True
    except Exception as e:
        print(f"❌ Search engine error: {e}")
        return False


def test_downloaders():
    """
    Testa sistema de download.
    """
    print("\n📥 Testando downloaders...")
    
    try:
        from core.downloaders import ImageDownloader
        
        downloader = ImageDownloader(timeout=3, max_workers=2)
        print("✅ Downloader criado")
        
        test_url = "https://picsum.photos/200"
        print(f"⏳ Testando download: {test_url}")
        
        result = downloader.download_single(test_url, resize_to=(128, 128))
        
        if result:
            img, url = result
            print(f"✅ Download funcionou: {img.size}")
        else:
            print("⚠️ Download falhou (pode ser timeout ou bloqueio)")
        
        return True
    except Exception as e:
        print(f"❌ Downloader error: {e}")
        return False


def test_vision_pipeline():
    """
    Testa pipeline CLIP.
    """
    print("\n🧠 Testando vision pipeline...")
    
    try:
        from core.vision_pipeline import VisionPipeline
        from PIL import Image
        
        pipeline = VisionPipeline()
        print("✅ Pipeline criado")
        
        print("⏳ Carregando CLIP (pode demorar na primeira vez)...")
        model = pipeline.load_model(pipeline.primary_model_name)
        print(f"✅ Modelo carregado: {pipeline.primary_model_name}")
        
        text_emb = pipeline.encode_text("wolf")
        print(f"✅ Text embedding: shape {text_emb.shape}")
        
        cached_emb = pipeline.encode_text("wolf")
        assert cached_emb is text_emb
        print("✅ Cache de texto funcionando")
        
        wolf_emb = pipeline.encode_text("wolf")
        dog_emb = pipeline.encode_text("dog")
        sim = pipeline.compute_similarity(wolf_emb, dog_emb)
        print(f"✅ Similaridade wolf-dog: {sim:.3f}")
        
        return True
    except Exception as e:
        print(f"❌ Vision pipeline error: {e}")
        return False


def test_image_utils():
    """
    Testa utilitários de imagem.
    """
    print("\n🖼️ Testando image utils...")
    
    try:
        from utils.image_utils import (
            get_domain, add_podium_border, get_rank_medal
        )
        from PIL import Image
        
        domain = get_domain("https://www.example.com/image.jpg")
        assert domain == "example.com"
        print("✅ get_domain funcionando")
        
        medal = get_rank_medal(0)
        assert medal == "🥇"
        print("✅ get_rank_medal funcionando")
        
        img = Image.new("RGB", (100, 100), color="red")
        bordered = add_podium_border(img, 0)
        assert bordered.size[0] > 100
        print("✅ add_podium_border funcionando")
        
        return True
    except Exception as e:
        print(f"❌ Image utils error: {e}")
        return False


def test_query_utils():
    """
    Testa utilitários de query/texto.
    """
    print("\n🧾 Testando query utils...")

    try:
        from core.query_utils import (
            subject_tokens, tokenize_text, dedupe_words,
            normalize_pose, normalize_negative, normalize_angle,
            build_query, build_clip_prompt, expand_subject,
        )

        tokens = subject_tokens("Wolf Samurai")
        assert "wolf" in tokens
        assert "samurai" in tokens
        assert tokenize_text("A-B") == ["a", "b"]
        assert dedupe_words(["a", "a", "b"]) == ["a", "b"]
        assert normalize_pose("wolf", "wolf pose") == "pose"
        assert normalize_negative("wolf", "wolf dog") == "dog"
        assert normalize_angle("wolf", "front", "front view") == "view"
        assert "test" in build_query("test", "", "-x")
        assert "quality" in build_clip_prompt("x", "quality")
        assert expand_subject("lynx")[0] == "lynx"
        print("✅ query utils ok")
        return True
    except Exception as e:
        print(f"❌ Query utils error: {e}")
        return False


def test_file_utils():
    """
    Testa utilitários de arquivos/batches.
    """
    print("\n🧱 Testando file utils...")

    try:
        from utils.file_utils import dedupe_urls, cap_gallery
        deduped = dedupe_urls(["a", "a", 1, None, "b"])
        assert deduped == ["a", "b"]
        gallery, files = cap_gallery([("a", "1"), ("b", "2")], ["a", "b"], 1)
        assert len(gallery) == 1
        assert len(files) == 1
        print("✅ file utils ok")
        return True
    except Exception as e:
        print(f"❌ File utils error: {e}")
        return False


def test_integration():
    """
    Teste de integração básico."""
    print("\n🔗 Testando integração...")
    
    try:
        from core.search_engine import get_default_searcher
        from core.downloaders import ImageDownloader
        from core.vision_pipeline import VisionPipeline
        
        print("⏳ Executando mini-pipeline...")
        
        searcher = get_default_searcher()
        results = searcher.search("cat", max_results=3)
        print(f"✅ Busca: {len(results)} resultados")
        
        if not results:
            print("⚠️ Sem resultados, pulando resto do teste")
            return True
        
        downloader = ImageDownloader()
        urls = [r['url'] for r in results[:2]]
        downloaded = downloader.download_batch(urls)
        print(f"✅ Download: {len(downloaded)} imagens")
        
        if not downloaded:
            print("⚠️ Download falhou, pulando resto")
            return True
        
        pipeline = VisionPipeline()
        images = [img for img, _ in downloaded]
        scores = pipeline.score_images(images, "cat sitting")
        print(f"✅ Scoring: {len(scores)} scores")
        print(f"   Scores: {[f'{s:.2f}' for s in scores]}")
        
        print("✅ Integração funcionando!")
        return True
        
    except Exception as e:
        print(f"❌ Integration error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Executa todos os testes.
    """
    print("=" * 60)
    print("🧪 CP-001 VALIDATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Presets", test_presets),
        ("Settings", test_settings),
        ("Search Engine", test_search_engine),
        ("Downloaders", test_downloaders),
        ("Vision Pipeline", test_vision_pipeline),
        ("Image Utils", test_image_utils),
        ("Query Utils", test_query_utils),
        ("File Utils", test_file_utils),
        ("Integration", test_integration),
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ {name} failed with exception: {e}")
            results[name] = False
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("=" * 60)
    print(f"Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("TESTES VALIDADOS COM SUCESSO!")
    else:
        print("⚠️ Alguns testes falharam. Revise os erros acima.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
