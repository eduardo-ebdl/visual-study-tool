"""
Utilitários para processamento de busca e texto.
"""

from typing import List
import re

# Expansões mínimas para melhorar busca em termos específicos.
SUBJECT_SYNONYMS = {
    "ocelot": ["leopardus pardalis", "neotropical cat", "wildcat"],
    "lynx": ["bobcat", "caracal"],
    "puma": ["cougar", "mountain lion"],
}

WILDLIFE_NEGATIVE_MAP = {
    "ocelot": ["tiger", "leopard", "jaguar", "cheetah", "cat", "house cat", "domestic cat"],
    "wolf": ["dog", "husky", "german shepherd", "coyote", "fox"],
    "fox": ["dog", "wolf", "coyote"],
    "tiger": ["lion", "leopard", "jaguar", "cheetah"],
    "leopard": ["jaguar", "cheetah", "tiger"],
}

PHOTO_METADATA_BLOCKLIST = {
    "photo",
    "photograph",
    "photography",
    "camera",
    "lens",
    "dslr",
    "film",
    "polaroid",
    "album",
    "gallery",
    "photographer",
    "photo frame",
    "photos",
    "studio",
}


def subject_tokens(subject: str) -> List[str]:
    tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", subject.lower()) if len(t) > 2]
    return tokens


def tokenize_text(text: str) -> List[str]:
    return [t for t in re.split(r"[^a-zA-Z0-9]+", text.lower()) if t]


def dedupe_words(tokens: List[str]) -> List[str]:
    seen = set()
    ordered = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def normalize_pose(subject: str, pose: str) -> str:
    if not pose:
        return ""
    subject_tokens = set(tokenize_text(subject))
    pose_tokens = dedupe_words(tokenize_text(pose))
    filtered = [token for token in pose_tokens if token not in subject_tokens]
    return " ".join(filtered).strip()


def normalize_negative(subject: str, negative: str) -> str:
    if not negative:
        return ""
    subject_tokens = set(tokenize_text(subject))
    neg_tokens = dedupe_words(tokenize_text(negative))
    filtered = [token for token in neg_tokens if token not in subject_tokens]
    return " ".join(filtered).strip()


def normalize_angle(subject: str, pose: str, angle: str) -> str:
    if not angle:
        return ""
    subject_tokens = set(tokenize_text(subject))
    pose_tokens = set(tokenize_text(pose))
    angle_tokens = dedupe_words(tokenize_text(angle))
    filtered = [token for token in angle_tokens if token not in subject_tokens and token not in pose_tokens]
    return " ".join(filtered).strip()


def build_query(subject: str, query_suffix: str, generic_negatives: str) -> str:
    parts = dedupe_words(tokenize_text(f"{subject} {query_suffix}"))
    query = " ".join(parts) if parts else subject
    return f"{query} {generic_negatives}".strip()


def build_clip_prompt(subject: str, quality_prompt: str) -> str:
    parts = dedupe_words(tokenize_text(f"{subject} {quality_prompt}"))
    return " ".join(parts) if parts else subject


def expand_subject(subject: str) -> List[str]:
    # Expande subject com sinônimos conhecidos e remove duplicatas.
    key = (subject or "").strip().lower()
    expansions = [subject]
    for extra in SUBJECT_SYNONYMS.get(key, []):
        expansions.append(extra)
    seen = set()
    ordered = []
    for item in expansions:
        if not item:
            continue
        key_item = item.lower().strip()
        if key_item in seen:
            continue
        seen.add(key_item)
        ordered.append(item)
    return ordered


def title_matches_subject(title: str, tokens: List[str]) -> bool:
    if not title:
        return False
    title_lower = title.lower()
    return any(token in title_lower for token in tokens)


def title_contains_blocklist(title: str) -> bool:
    if not title:
        return False
    title_lower = title.lower()
    return any(term in title_lower for term in PHOTO_METADATA_BLOCKLIST)


def filter_photography_metadata(items: List[dict], subject_tokens_list: List[str]) -> List[dict]:
    if not subject_tokens_list:
        return items
    filtered = []
    for item in items:
        title = item.get("title", "") or ""
        if not title:
            filtered.append(item)
            continue
        if title_matches_subject(title, subject_tokens_list):
            filtered.append(item)
            continue
        if title_contains_blocklist(title):
            continue
        filtered.append(item)
    return filtered
