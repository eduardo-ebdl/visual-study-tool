"""
Definições de opções de UI.
"""

# 1) Opções de intenção mostradas na UI (labels mapeados para nomes de preset).
INTENTION_OPTIONS = [
    {
        "label": "Fotografia (Geral)",
        "match": "Human Study (Portrait)",
        "tooltip": "Fotos reais do assunto. Humanos e animais permitidos."
    },
    {
        "label": "Fotografia de Fauna",
        "match": "Animal Study (Wildlife)",
        "tooltip": "Animais reais na natureza. Sem humanos, fantasia ou arte estilizada."
    },
    {
        "label": "Arte de Ilustração 2D",
        "match": "Inspiration / Concept",
        "tooltip": "Conceito 2D, ilustração, trabalho pictórico ou estilizado."
    },
    {
        "label": "Renders 3D / Escultura",
        "match": "3D Reference / Sculpt",
        "tooltip": "Renders 3D, esculturas, argila ou modelos com fundo neutro."
    },
]

ANGLE_OPTIONS = [
    {"label": "Qualquer", "query": "", "clip": ""},
    {"label": "Frontal", "query": "front view", "clip": "front view"},
    {"label": "Lateral", "query": "side view", "clip": "side view"},
    {"label": "3/4", "query": "three quarter view", "clip": "three quarter view"},
    {"label": "De cima", "query": "top view", "clip": "top view"},
    {"label": "Traseira", "query": "back view", "clip": "back view"},
    {"label": "De baixo", "query": "bottom view", "clip": "bottom view"},
]

ANGLE_MAP = {item["label"]: item for item in ANGLE_OPTIONS}
