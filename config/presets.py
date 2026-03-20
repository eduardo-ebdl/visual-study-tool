"""
Presets de busca para diferentes tipos de estudo visual.
Separamos o que vai para a BUSCA (DuckDuckGo) do que vai para a IA (CLIP).
"""

# 1) Preset definitions used by search, filtering, and scoring.
PRESETS = {
    "🐾 Animal Study (Wildlife)": {
        "search_query": "wild animal photography", 
        "suffix": "wildlife photography",
        "quality_prompt": "wildlife photography full body portrait biological reference dslr sharp focus anatomy",
        "clip_negatives": "human, person, woman, man, girl, boy, face, model, makeup, fashion, werewolf, anthro, clothes",
        "hard_negatives": [
            "cartoon", "illustration", "mascot", "costume", "pet", "collar", "leash"
        ],
        "clip_weights": {
            "clip-ViT-B-32": 0.4,
            "clip-ViT-B-16": 0.6
        },
        "style_filter": True,
        "integrity_threshold": 0.23,
        "min_display_score": 22.0,
        "pose_weight": 0.3,
        "criteria": [
            ("biological accuracy", 0.4),
            ("neutral background", 0.3),
            ("sharp focus", 0.3)
        ],
        "description": "Fotografias reais de animais para estudo anatômico e referência biológica"
    },
    
    "👤 Human Study (Portrait)": {
        "search_query": "", 
        "suffix": "",
        "quality_prompt": "realistic photo sharp focus high detail reference",
        "clip_negatives": "illustration, cartoon, anime, 3d render, cgi, painting, sketch, watermark, text",
        "hard_negatives": [
            "illustration", "cartoon", "anime", "3d render", "cgi", "painting", "sketch", "drawing"
        ],
        "clip_weights": {
            "clip-ViT-B-32": 0.6,
            "clip-ViT-B-16": 0.4
        },
        "style_filter": True,
        "integrity_threshold": 0.2,
        "min_display_score": 18.0,
        "pose_weight": 0.28,
        "criteria": [
            ("sharp focus", 0.4),
            ("natural lighting", 0.3),
            ("high detail", 0.3)
        ],
        "description": "Fotografia real do subject com alta nitidez e detalhe"
    },
    
    "🎨 Inspiration / Concept": {
        "search_query": "concept art illustration", 
        "suffix": "concept art",
        "quality_prompt": "digital art character design concept art trending on artstation dynamic lighting",
        "clip_negatives": "low quality, jpeg artifacts, bad anatomy, simple background, watermark, text, 3d, render, cgi, model",
        "hard_negatives": [
            "photo", "photography", "stock photo"
        ],
        "clip_weights": {
            "clip-ViT-B-32": 0.7,
            "clip-ViT-B-16": 0.3
        },
        "style_filter": False,
        "integrity_threshold": 0.19,
        "min_display_score": 18.0,
        "pose_weight": 0.2,
        "criteria": [
            ("artistic composition", 0.4),
            ("dynamic lighting", 0.3),
            ("color theory", 0.3)
        ],
        "description": "Arte conceitual e ilustrações para inspiração criativa"
    },
    
    "🦴 3D Reference / Sculpt": {
        "search_query": "3d render model", 
        "suffix": "3d render grey background",
        "quality_prompt": "3d render zbrush clay render neutral background ambient occlusion",
        "clip_negatives": "2d, drawing, sketch, noise, textured, painting, watermark, text",
        "hard_negatives": [
            "photo", "photography", "illustration", "cartoon"
        ],
        "clip_weights": {
            "clip-ViT-B-32": 0.7,
            "clip-ViT-B-16": 0.3
        },
        "style_filter": False,
        "integrity_threshold": 0.2,
        "min_display_score": 18.0,
        "pose_weight": 0.2,
        "criteria": [
            ("3d model volumetric", 0.5),
            ("neutral lighting", 0.3),
            ("clean geometry", 0.2)
        ],
        "description": "Renders 3D e esculturas digitais para referência de volume e forma"
    },
    
    "🔧 Debug Mode": {
        "search_query": "", 
        "suffix": "",
        "quality_prompt": "high quality image",
        "clip_negatives": "",
        "hard_negatives": [],
        "clip_weights": {
            "clip-ViT-B-32": 1.0
        },
        "style_filter": False,
        "criteria": [],
        "description": "Modo de debug sem filtros adicionais"
    }
}


def get_preset(name: str) -> dict:
    """Retorna configuração de um preset."""
    # 2) Safe fallback if a preset key is missing.
    if name not in PRESETS:
        return PRESETS["🔧 Debug Mode"]
    return PRESETS[name]


def list_presets() -> list:
    """Retorna lista de nomes de presets disponíveis."""
    return list(PRESETS.keys())


def get_preset_description(name: str) -> str:
    """Retorna descrição de um preset."""
    return get_preset(name).get("description", "Sem descrição")
