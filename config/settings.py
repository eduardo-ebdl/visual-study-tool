"""
Configurações globais do Visual Study Tool.
Centralize todas as constantes e configurações do sistema.
"""

import os
from pathlib import Path

def _load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a .env file into os.environ."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

# 1) Paths and .env loading.
BASE_DIR = Path(__file__).parent.parent

_load_env_file(BASE_DIR / ".env")

DOWNLOAD_DIR = BASE_DIR / "app_downloads"
CACHE_DIR = BASE_DIR / "cache_db"
LOGS_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "models"

# 2) Ensure working directories exist.
for directory in [DOWNLOAD_DIR, CACHE_DIR, LOGS_DIR, MODELS_DIR]:
    directory.mkdir(exist_ok=True, parents=True)


# 3) AI model configuration.
CLIP_PRIMARY_MODEL_NAME = "clip-ViT-B-32"
CLIP_MODEL_NAME = CLIP_PRIMARY_MODEL_NAME
CLIP_SECONDARY_MODEL_NAME = "clip-ViT-B-16"
CLIP_SECONDARY_ENABLED = os.getenv("CLIP_SECONDARY_ENABLED", "true").lower() == "true"
CLIP_SECONDARY_WINDOW = (0.16, 0.28)
CLIP_DEFAULT_MODEL_WEIGHTS = {
    CLIP_PRIMARY_MODEL_NAME: 0.7,
    CLIP_SECONDARY_MODEL_NAME: 0.3,
}
CLIP_BATCH_SIZE = 32

YOLO_MODEL_PATH = MODELS_DIR / "yolov8n.pt"
SPECIES_MODEL_PATH = MODELS_DIR / "species_resnet18.pth"


# 4) Search configuration and sizing.
MAX_RESULTS_PER_ENGINE = 25

SEARCH_POOL_SIZE = int(os.getenv("SEARCH_POOL_SIZE", "120"))
DOWNLOAD_BATCH_SIZE = int(os.getenv("DOWNLOAD_BATCH_SIZE", "60"))
DISPLAY_BATCH_SIZE = int(os.getenv("DISPLAY_BATCH_SIZE", "60"))

SOURCE_WEIGHT_ALPHA = float(os.getenv("SOURCE_WEIGHT_ALPHA", "0.4"))

SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "8"))

DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "3"))

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
}

SEARCH_CACHE_ENABLED = os.getenv("SEARCH_CACHE_ENABLED", "true").lower() == "true"
SEARCH_CACHE_TTL_SECONDS = int(os.getenv("SEARCH_CACHE_TTL_SECONDS", str(24 * 60 * 60)))

EMBEDDING_CACHE_ENABLED = os.getenv("EMBEDDING_CACHE_ENABLED", "true").lower() == "true"
EMBEDDING_CACHE_PATH = CACHE_DIR / "embeddings.sqlite"

# 5) API keys and engine toggles.
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
UNSPLASH_SECRET_KEY = os.getenv("UNSPLASH_SECRET_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
OPENVERSE_API_KEY = os.getenv("OPENVERSE_API_KEY", "")

ENABLE_UNSPLASH = bool(UNSPLASH_ACCESS_KEY)
ENABLE_PEXELS = bool(PEXELS_API_KEY)
ENABLE_PIXABAY = bool(PIXABAY_API_KEY)
ENABLE_OPENVERSE = os.getenv("ENABLE_OPENVERSE", "false").lower() == "true"
ENABLE_WIKIMEDIA = os.getenv("ENABLE_WIKIMEDIA", "true").lower() == "true"
ENABLE_DDG = os.getenv("ENABLE_DDG", "true").lower() == "true"
ENABLE_DDG_FALLBACK = os.getenv("ENABLE_DDG_FALLBACK", "true").lower() == "true"
ENABLE_DDG_QUALITY_FALLBACK = os.getenv("ENABLE_DDG_QUALITY_FALLBACK", "true").lower() == "true"
DDG_MATCH_MIN = int(os.getenv("DDG_MATCH_MIN", "4"))


# 6) Image processing defaults.
_default_size_raw = os.getenv("DEFAULT_IMAGE_SIZE", "512,512")
try:
    _parts = [int(p.strip()) for p in _default_size_raw.split(",") if p.strip()]
    if len(_parts) >= 2:
        DEFAULT_IMAGE_SIZE = (_parts[0], _parts[1])
    elif len(_parts) == 1:
        DEFAULT_IMAGE_SIZE = (_parts[0], _parts[0])
    else:
        DEFAULT_IMAGE_SIZE = (512, 512)
except ValueError:
    DEFAULT_IMAGE_SIZE = (512, 512)

EXPORT_QUALITY = 95

ACCEPTED_FORMATS = ['RGB']


# 7) Scoring and filtering thresholds.
BASE_SIMILARITY_THRESHOLD = float(os.getenv("BASE_SIMILARITY_THRESHOLD", "0.18"))

INTEGRITY_MARGIN = float(os.getenv("INTEGRITY_MARGIN", "0.02"))
INTEGRITY_MIN_KEEP = int(os.getenv("INTEGRITY_MIN_KEEP", "12"))
INTEGRITY_MIN_KEEP_RATIO = float(os.getenv("INTEGRITY_MIN_KEEP_RATIO", "0.2"))

MIN_DISPLAY_SCORE = float(os.getenv("MIN_DISPLAY_SCORE", "20.0"))

SCORE_DISPLAY_MULTIPLIER = float(os.getenv("SCORE_DISPLAY_MULTIPLIER", "250"))

FEATURE_WEIGHT_MULTIPLIER = float(os.getenv("FEATURE_WEIGHT_MULTIPLIER", "1.6"))


# 8) UI configuration.
RANK_COLORS = {
    0: "#FFD700",
    1: "#C0C0C0",
    2: "#CD7F32",
    "default": "#F5F5F5"
}

RANK_BORDER_WIDTH = {
    "podium": 12,
    "regular": 4
}

RANK_MEDALS = ["🥇", "🥈", "🥉"]


# 9) Cache configuration.
CACHE_EXPIRATION_DAYS = 7

MAX_CACHE_SIZE_MB = 500


# 10) Logging configuration.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


# 11) Development flags.
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"

SAVE_DEBUG_IMAGES = DEBUG_MODE

VERBOSE = DEBUG_MODE


# 12) Future feature toggles.
ENABLE_PERSON_DETECTOR = False

ENABLE_SPECIES_CLASSIFIER = False

ENABLE_WATERMARK_DETECTOR = False

ENABLE_MULTI_ENGINE = os.getenv("ENABLE_MULTI_ENGINE", "true").lower() == "true"

MAX_GALLERY_ITEMS = int(os.getenv("MAX_GALLERY_ITEMS", "180"))


