"""
UI option definitions.
"""

# 1) Intention options shown in the UI (labels mapped to preset names).
INTENTION_OPTIONS = [
    {
        "label": "Photography (General)",
        "match": "Human Study (Portrait)",
        "tooltip": "Real photos of the subject. Humans and animals allowed."
    },
    {
        "label": "Wildlife Photography",
        "match": "Animal Study (Wildlife)",
        "tooltip": "Real animals in nature. No humans, fantasy, or stylized art."
    },
    {
        "label": "2D Illustration Art",
        "match": "Inspiration / Concept",
        "tooltip": "2D concept art, illustration, painterly or stylized work."
    },
    {
        "label": "3D Clay / Model Renders",
        "match": "3D Reference / Sculpt",
        "tooltip": "3D renders, sculpts, clay or neutral background models."
    },
]

ANGLE_OPTIONS = [
    {"label": "Any", "query": "", "clip": ""},
    {"label": "Front", "query": "front view", "clip": "front view"},
    {"label": "Side", "query": "side view", "clip": "side view"},
    {"label": "3/4", "query": "three quarter view", "clip": "three quarter view"},
    {"label": "Top", "query": "top view", "clip": "top view"},
    {"label": "Back", "query": "back view", "clip": "back view"},
    {"label": "Bottom", "query": "bottom view", "clip": "bottom view"},
]

ANGLE_MAP = {item["label"]: item for item in ANGLE_OPTIONS}
