"""
Search pipeline and UI update helpers.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import time
import random
import os

import gradio as gr

from config.presets import PRESETS
from config.ui_options import INTENTION_OPTIONS, ANGLE_OPTIONS, ANGLE_MAP
from config.settings import (
    DOWNLOAD_DIR,
    BASE_SIMILARITY_THRESHOLD,
    MIN_DISPLAY_SCORE,
    SCORE_DISPLAY_MULTIPLIER,
    SEARCH_POOL_SIZE,
    DOWNLOAD_BATCH_SIZE,
    DISPLAY_BATCH_SIZE,
    SOURCE_WEIGHT_ALPHA,
    SEARCH_CACHE_ENABLED,
    MAX_GALLERY_ITEMS,
    ENABLE_DDG,
    ENABLE_DDG_QUALITY_FALLBACK,
    DDG_MATCH_MIN,
    FEATURE_WEIGHT_MULTIPLIER,
)
from core.search_engine import DuckDuckGoEngine
from core.query_utils import (
    WILDLIFE_NEGATIVE_MAP,
    subject_tokens,
    tokenize_text,
    normalize_pose,
    normalize_negative,
    normalize_angle,
    build_query,
    build_clip_prompt,
    expand_subject,
    title_matches_subject,
    filter_photography_metadata,
)
from utils.search_cache import make_cache_key, get_cached_results, set_cached_results
from utils.pretty_logger import log as pretty_log
from utils.file_utils import (
    setup_dirs,
    build_zip_for_scope,
    dedupe_urls,
    cap_gallery,
    cap_batch_history,
)
from utils.image_utils import compute_image_hash, images_are_similar, save_image


@dataclass
class PipelineDeps:
    search_engine: object
    downloader: object
    vision_pipeline: object
    source_weights: Dict[str, float]


@dataclass
class UIRefs:
    status_row: gr.Component
    welcome_col: gr.Component
    out_gallery: gr.Component
    status_box: gr.Component
    mode_chip: gr.Component
    btn_download: gr.Component
    btn_search: gr.Component
    btn_load_more: gr.Component
    gallery_state_comp: gr.Component
    current_batch_state_comp: gr.Component
    all_files_state_comp: gr.Component
    seen_urls_state_comp: gr.Component
    last_inputs_state_comp: gr.Component
    batch_history_state_comp: gr.Component
    batch_selector: gr.Component


DEPS: Optional[PipelineDeps] = None
UI: Optional[UIRefs] = None


def init_pipeline(deps: PipelineDeps) -> None:
    global DEPS
    DEPS = deps


def set_ui_refs(refs: UIRefs) -> None:
    global UI
    UI = refs


def _ui_error(message: str):
    """Standard UI updates for errors."""
    return {
        UI.status_row: gr.update(visible=True),
        UI.welcome_col: gr.update(visible=False),
        UI.out_gallery: gr.update(visible=False, value=None, selected_index=None, preview=False),
        UI.status_box: gr.update(value=message, visible=True),
        UI.mode_chip: gr.update(value="", visible=False),
        UI.btn_download: gr.update(value=None, visible=False, interactive=False),
        UI.btn_search: gr.update(value="Generate New Set", interactive=True, visible=True),
        UI.btn_load_more: gr.update(visible=False, interactive=False),
        UI.gallery_state_comp: [],
        UI.current_batch_state_comp: [],
        UI.all_files_state_comp: [],
        UI.seen_urls_state_comp: [],
        UI.last_inputs_state_comp: {},
    }


def _ui_error_keep(message: str, gallery_value: List[Tuple[str, str]]):
    """Error UI that keeps existing gallery/state (used for load more)."""
    return {
        UI.status_row: gr.update(visible=True),
        UI.welcome_col: gr.update(visible=False),
        UI.out_gallery: gr.update(
            visible=bool(gallery_value),
            value=gallery_value,
            selected_index=None,
            preview=False,
        ),
        UI.status_box: gr.update(value=message, visible=True),
        UI.mode_chip: gr.update(visible=bool(gallery_value)),
        UI.btn_search: gr.update(value="Generate New Set", interactive=True, visible=True),
        UI.btn_load_more: gr.update(visible=bool(gallery_value), interactive=bool(gallery_value)),
    }


def _ui_stage(message: str):
    """UI updates for multi-step progress during search."""
    return {
        UI.status_row: gr.update(visible=True),
        UI.welcome_col: gr.update(visible=False),
        UI.out_gallery: gr.update(visible=False, value=None, selected_index=None, preview=False),
        UI.status_box: gr.update(value=message, visible=True),
        UI.mode_chip: gr.update(visible=False),
        UI.btn_download: gr.update(value=None, visible=False, interactive=False),
        UI.btn_search: gr.update(value="Loading...", interactive=False, visible=True),
        UI.btn_load_more: gr.update(visible=False, interactive=False),
    }


def ui_loading():
    """Immediate loading state."""
    return _ui_stage("Searching...")


def _make_last_inputs(
    subject: str,
    pose: str,
    angle_label: str,
    intent_photo: bool,
    intent_wildlife: bool,
    intent_art: bool,
    intent_3d: bool,
    impostors: str,
) -> Dict[str, object]:
    return {
        "subject": subject,
        "pose": pose,
        "angle_label": angle_label,
        "intent_flags": [intent_photo, intent_wildlife, intent_art, intent_3d],
        "impostors": impostors,
    }


def _resolve_preset_keys(selected_labels: List[str]) -> List[str]:
    """Map UI labels to preset keys by substring match."""
    keys = []
    for option in INTENTION_OPTIONS:
        label = option["label"]
        substring = option["match"]
        if label not in selected_labels:
            continue
        for key in PRESETS.keys():
            if substring in key:
                keys.append(key)
                break
    return keys


def _mode_label(selected_labels: List[str]) -> str:
    if not selected_labels:
        return '<span class="mode-chip-item"><span class="mode-icon">•</span><span class="mode-text">No mode</span></span>'

    icon_map = {
        "Photography (General)": "📷",
        "Wildlife Photography": "🐾",
        "2D Illustration Art": "🎨",
        "3D Clay / Model Renders": "🧱",
    }
    parts = []
    for label in selected_labels:
        icon = icon_map.get(label, "•")
        parts.append(
            f'<span class="mode-chip-item"><span class="mode-icon">{icon}</span><span class="mode-text">{label}</span></span>'
        )
    return '<span class="mode-chip-sep">+</span>'.join(parts)


def _collect_intentions(*flags: bool) -> List[str]:
    """Collect selected intention labels from checkbox flags."""
    selected = []
    for flag, option in zip(flags, INTENTION_OPTIONS):
        if flag:
            selected.append(option["label"])
    return selected


def _get_engine_signature(searcher) -> str:
    if hasattr(searcher, "engines"):
        names = [e.get_name() for e in searcher.engines if hasattr(e, "get_name")]
        return "|".join(names)
    if hasattr(searcher, "get_name"):
        return searcher.get_name()
    return searcher.__class__.__name__


def search_and_process(
    subject,
    pose,
    angle_label,
    intent_photo,
    intent_wildlife,
    intent_art,
    intent_3d,
    impostors,
    shuffle_seed=0,
    zip_scope="Current batch",
    gallery_state=None,
    all_files_state=None,
    seen_urls_state=None,
    batch_history_state=None,
    append_mode: bool = False,
):
    """Main pipeline: search, download, score, and render results."""
    if DEPS is None or UI is None:
        raise RuntimeError("Pipeline not initialized")

    search_engine = DEPS.search_engine
    downloader = DEPS.downloader
    vision_pipeline = DEPS.vision_pipeline
    source_weights = DEPS.source_weights

    subject = (subject or "").strip()
    pose = (pose or "").strip()
    pose = normalize_pose(subject, pose)
    angle_choice = ANGLE_MAP.get(angle_label, ANGLE_OPTIONS[0])
    angle_query = normalize_angle(subject, pose, angle_choice.get("query", ""))
    angle_clip = normalize_angle(subject, pose, angle_choice.get("clip", ""))
    impostors = (impostors or "").strip()
    impostors = normalize_negative(subject, impostors)
    preset_labels = _collect_intentions(
        intent_photo,
        intent_wildlife,
        intent_art,
        intent_3d
    )
    is_art_or_3d = bool(intent_art or intent_3d)

    # 1) Validate input required for search.
    if not subject:
        if append_mode:
            yield _ui_error_keep("Subject is required.", gallery_state or [])
        else:
            yield _ui_error("Subject is required.")
        return

    # 2) Validate intention selection (presets drive search + scoring).
    if not preset_labels:
        if append_mode:
            yield _ui_error_keep("Select at least one intention.", gallery_state or [])
        else:
            yield _ui_error("Select at least one intention.")
        return

    # 3) Prepare workspace and resolve preset keys.
    should_clear = not append_mode and not (gallery_state or batch_history_state)
    setup_dirs(DOWNLOAD_DIR, clear=should_clear)
    start_time = time.time()
    preset_keys = _resolve_preset_keys(preset_labels)
    if not preset_keys:
        if append_mode:
            yield _ui_error_keep("Invalid intention selection.", gallery_state or [])
        else:
            yield _ui_error("Invalid intention selection.")
        return

    # 4) Search: pull a wider pool for better final ranking.
    yield _ui_stage("Searching...")
    generic_negatives = "-clipart -logo -icon -stock"
    lower_subject = subject.lower()
    lower_pose = pose.lower()
    if "pokemon" in lower_subject or "pokemon" in lower_pose:
        generic_negatives = f"{generic_negatives} -card -cards -tcg -trading -booster -pack"

    def _search_with_retry(query: str, style_filter: bool, limit: int, engine_override=None):
        last_error = ""
        for attempt in range(2):
            try:
                active_engine = engine_override or search_engine
                if SEARCH_CACHE_ENABLED:
                    engine_signature = _get_engine_signature(active_engine)
                    cache_key = make_cache_key(
                        query=query,
                        type_filter='photo' if style_filter else None,
                        limit=limit,
                        engine_signature=engine_signature,
                    )
                    cached = get_cached_results(cache_key)
                    if cached:
                        pretty_log("Search cache hit", "INFO")
                        return cached, ""
                results = active_engine.search(
                    query=query,
                    max_results=limit,
                    type_filter='photo' if style_filter else None
                )
                if results:
                    if SEARCH_CACHE_ENABLED:
                        set_cached_results(cache_key, results)
                    return results, ""
                last_error = "empty"
            except Exception as e:
                last_error = str(e)
                pretty_log(f"Search failed: {e}", "ERROR")
            if attempt == 0:
                time.sleep(1.2)
        return [], last_error

    def _search_for_subject(term: str, engine_override=None):
        feature_part = pose if pose else ""
        extra_terms = []
        lower_subject = (term or "").lower()
        if "pokemon" in lower_subject or "pokemon" in lower_pose:
            extra_terms.append("pokemon")
            if is_art_or_3d:
                extra_terms.append("fan art")
        search_term = f"{term} {feature_part} {' '.join(extra_terms)} {angle_query}".strip()
        raw = []
        last_err = ""
        if len(preset_keys) == 1:
            preset = PRESETS[preset_keys[0]]
            query = build_query(search_term, preset['search_query'], generic_negatives)
            raw, last_err = _search_with_retry(query, preset['style_filter'], SEARCH_POOL_SIZE, engine_override)
        else:
            per_preset_limit = max(10, int(SEARCH_POOL_SIZE / len(preset_keys)))
            per_preset_results = []
            for key in preset_keys:
                preset = PRESETS.get(key, {})
                query = build_query(search_term, preset.get('search_query', ''), generic_negatives)
                results, err = _search_with_retry(
                    query,
                    preset.get('style_filter', False),
                    per_preset_limit,
                    engine_override,
                )
                if err:
                    last_err = err
                per_preset_results.append(results)
            merged = []
            seen_urls = set()
            while any(per_preset_results) and len(merged) < SEARCH_POOL_SIZE:
                for results in per_preset_results:
                    if not results:
                        continue
                    item = results.pop(0)
                    url = item.get("url")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    merged.append(item)
                    if len(merged) >= SEARCH_POOL_SIZE:
                        break
            raw = merged
        return raw, last_err

    raw_results = []
    last_error = ""
    subject_variants = expand_subject(subject)

    if ENABLE_DDG and is_art_or_3d:
        ddg_engine = DuckDuckGoEngine()
        raw_results, last_error = _search_for_subject(subject_variants[0], ddg_engine)
        if not raw_results:
            raw_results, last_error = _search_for_subject(subject_variants[0])
    else:
        raw_results, last_error = _search_for_subject(subject_variants[0])

    subject_tokens_primary = subject_tokens(subject)
    title_matches = [r for r in raw_results if title_matches_subject(r.get("title", ""), subject_tokens_primary)]
    if len(title_matches) < 5 and len(subject_variants) > 1:
        for alt in subject_variants[1:]:
            pretty_log(f"Search fallback using subject variant: {alt}", "INFO")
            extra_results, err = _search_for_subject(alt, DuckDuckGoEngine() if (ENABLE_DDG and is_art_or_3d) else None)
            if err:
                last_error = err
            raw_results.extend(extra_results)
            if len(raw_results) >= SEARCH_POOL_SIZE * 2:
                break

    # 5) Deduplicate and group results by source for balanced mixing.
    seen = set()
    search_results = []
    for r in raw_results:
        url = r.get('url')
        if not url or url in seen:
            continue
        seen.add(url)
        search_results.append(r)

    exclude_urls = set(dedupe_urls(seen_urls_state or []))
    if exclude_urls:
        search_results = [r for r in search_results if r.get("url") not in exclude_urls]
    subject_tokens_list = subject_tokens(subject)
    for alt in expand_subject(subject)[1:]:
        subject_tokens_list.extend(subject_tokens(alt))
    subject_tokens_list = sorted(set(subject_tokens_list))
    source_groups = {}
    for r in search_results:
        source = r.get("source", "unknown")
        source_groups.setdefault(source, []).append(r)

    photo_general_only = len(preset_keys) == 1 and "Human Study (Portrait)" in preset_keys[0]
    wildlife_only = len(preset_keys) == 1 and "Animal Study (Wildlife)" in preset_keys[0]
    enforce_metadata_match = photo_general_only or wildlife_only
    if photo_general_only and subject_tokens_list:
        for source, items in source_groups.items():
            filtered = filter_photography_metadata(items, subject_tokens_list)
            if len(filtered) != len(items):
                pretty_log(
                    f"Metadata filter removed {len(items) - len(filtered)} items from {source}",
                    "INFO",
                )
            source_groups[source] = filtered

    if subject_tokens_list:
        for source, items in source_groups.items():
            matches = [r for r in items if title_matches_subject(r.get("title", ""), subject_tokens_list)]
            titled = [r for r in items if r.get("title")]
            if enforce_metadata_match and not matches and len(titled) >= 8:
                pretty_log(f"Dropping source {source} (0 subject matches in metadata)", "WARN")
                source_groups[source] = []
                continue
            if matches:
                min_matches = max(3, int(len(items) * 0.2))
                if len(matches) >= min_matches:
                    source_groups[source] = matches
                else:
                    non_matches = [r for r in items if r not in matches]
                    source_groups[source] = matches + non_matches

    source_counts = {source: len(items) for source, items in source_groups.items()}
    balanced_results = []
    source_pick_counts = {source: 0 for source in source_groups.keys()}
    sources = list(source_groups.keys())
    while sources and len(balanced_results) < SEARCH_POOL_SIZE:
        next_sources = []
        for _ in range(len(sources)):
            if not sources:
                break
            source = max(
                sources,
                key=lambda s: (source_weights.get(s, 1.0) / (1 + source_pick_counts.get(s, 0))),
            )
            items = source_groups.get(source, [])
            if items:
                balanced_results.append(items.pop(0))
                source_pick_counts[source] = source_pick_counts.get(source, 0) + 1
                if len(balanced_results) >= SEARCH_POOL_SIZE:
                    break
            if items:
                next_sources.append(source)
            else:
                sources = [s for s in sources if s != source]
        if next_sources:
            sources = list(dict.fromkeys(next_sources))

    if balanced_results:
        search_results = balanced_results
        if search_results:
            random.Random(shuffle_seed).shuffle(search_results)
        pretty_log(
            "Search source pool: " + ", ".join(f"{k}={v}" for k, v in source_counts.items()),
            "INFO",
        )

    if ENABLE_DDG and ENABLE_DDG_QUALITY_FALLBACK:
        engine_signature = _get_engine_signature(search_engine)
        if "DuckDuckGo" not in engine_signature and subject_tokens_list:
            match_count = sum(
                1 for r in search_results if title_matches_subject(r.get("title", ""), subject_tokens_list)
            )
            if match_count < DDG_MATCH_MIN:
                ddg_engine = DuckDuckGoEngine()
                ddg_results, ddg_err = _search_for_subject(subject_variants[0], ddg_engine)
                if ddg_err:
                    last_error = ddg_err
                seen_urls = {r.get("url") for r in search_results if r.get("url")}
                for item in ddg_results:
                    url = item.get("url")
                    if not url or url in seen_urls:
                        continue
                    search_results.append(item)
                    seen_urls.add(url)
                    if len(search_results) >= SEARCH_POOL_SIZE:
                        break

    if ENABLE_DDG and is_art_or_3d:
        engine_signature = _get_engine_signature(search_engine)
        if "DuckDuckGo" not in engine_signature:
            ddg_engine = DuckDuckGoEngine()
            ddg_results, ddg_err = _search_for_subject(subject_variants[0], ddg_engine)
            if ddg_err:
                last_error = ddg_err
            seen_urls = {r.get("url") for r in search_results if r.get("url")}
            for item in ddg_results:
                url = item.get("url")
                if not url or url in seen_urls:
                    continue
                search_results.append(item)
                seen_urls.add(url)
                if len(search_results) >= SEARCH_POOL_SIZE:
                    break

    if not search_results:
        if "ratelimit" in last_error.lower():
            if append_mode:
                yield _ui_error_keep("Search rate-limited. Please try again in a moment.", gallery_state or [])
            else:
                yield _ui_error("Search rate-limited. Please try again in a moment.")
        else:
            if append_mode:
                yield _ui_error_keep("No results found.", gallery_state or [])
            else:
                yield _ui_error("No results found.")
        return

    # 6) Download the top N URLs for scoring.
    yield _ui_stage("Downloading...")
    url_to_source = {r["url"]: r.get("source", "unknown") for r in search_results}
    urls = [r['url'] for r in search_results[:DOWNLOAD_BATCH_SIZE]]
    downloaded = downloader.download_batch(urls)

    if not downloaded:
        if append_mode:
            yield _ui_error_keep("Download failed.", gallery_state or [])
        else:
            yield _ui_error("Download failed.")
        return

    # 7) Deduplicate identical images across sources.
    deduped = []
    seen_hashes = []
    for img, url in downloaded:
        img_hash = compute_image_hash(img)
        if img_hash:
            if any(images_are_similar(img_hash, seen, threshold=3) for seen in seen_hashes):
                continue
            seen_hashes.append(img_hash)
        deduped.append((img, url))

    images_pil: List = [img for img, _ in deduped]
    final_urls: List[str] = [url for _, url in deduped]

    # 8) Build prompts and run integrity filter.
    yield _ui_stage("Scoring...")
    hard_negatives = []
    for key in preset_keys:
        hard_negatives.extend(PRESETS[key].get("hard_negatives", []))
        if "Animal Study (Wildlife)" in key:
            for token in tokenize_text(subject):
                hard_negatives.extend(WILDLIFE_NEGATIVE_MAP.get(token, []))
    hard_negatives = sorted(set([neg for neg in hard_negatives if neg]))
    hard_neg_text = ", ".join(hard_negatives) if hard_negatives else ""

    if len(preset_keys) == 1:
        preset = PRESETS[preset_keys[0]]
        neg_prompt = preset["clip_negatives"]
        if hard_neg_text:
            neg_prompt = f"{neg_prompt}, {hard_neg_text}"
        if impostors:
            neg_prompt = f"{neg_prompt}, {impostors}"
    else:
        neg_prompt = "watermark, text, logo, low quality, jpeg artifacts"
        if hard_neg_text:
            neg_prompt = f"{neg_prompt}, {hard_neg_text}"
        if impostors:
            neg_prompt = f"{neg_prompt}, {impostors}"

    integrity_thresholds = [
        PRESETS[key].get("integrity_threshold", BASE_SIMILARITY_THRESHOLD)
        for key in preset_keys
    ]
    integrity_threshold = max(integrity_thresholds) if integrity_thresholds else BASE_SIMILARITY_THRESHOLD
    if is_art_or_3d:
        integrity_threshold *= 0.75
    display_thresholds = [
        PRESETS[key].get("min_display_score", MIN_DISPLAY_SCORE)
        for key in preset_keys
    ]
    display_threshold = min(display_thresholds) if display_thresholds else MIN_DISPLAY_SCORE

    valid_imgs, valid_urls, _ = vision_pipeline.filter_by_integrity(
        images=images_pil,
        urls=final_urls,
        subject=subject,
        negative_prompt=neg_prompt,
        threshold=integrity_threshold
    )

    if downloaded:
        total_by_source = {}
        for _, url in downloaded:
            source = url_to_source.get(url, "unknown")
            total_by_source[source] = total_by_source.get(source, 0) + 1

        passed_by_source = {}
        for url in valid_urls:
            source = url_to_source.get(url, "unknown")
            passed_by_source[source] = passed_by_source.get(source, 0) + 1

        pretty_log(
            "Passed by source: " + ", ".join(f"{k}={v}" for k, v in passed_by_source.items()),
            "INFO",
        )

        for source, total in total_by_source.items():
            if total <= 0:
                continue
            passed = passed_by_source.get(source, 0)
            ratio = passed / total
            previous = source_weights.get(source, ratio)
            source_weights[source] = (1 - SOURCE_WEIGHT_ALPHA) * previous + SOURCE_WEIGHT_ALPHA * ratio
        if source_weights:
            pretty_log(
                "Updated source weights: " + ", ".join(f"{k}={v:.2f}" for k, v in source_weights.items()),
                "INFO",
            )

    if not valid_imgs:
        if append_mode:
            yield _ui_error_keep("AI filtered all images.", gallery_state or [])
        else:
            yield _ui_error("AI filtered all images.")
        return

    if len(preset_keys) == 1:
        preset = PRESETS[preset_keys[0]]
        full_prompt = build_clip_prompt(subject, preset["quality_prompt"])
        criteria = list(preset.get("criteria", []))
        pose_weight = preset.get("pose_weight", 0.25) * FEATURE_WEIGHT_MULTIPLIER
        if pose:
            criteria.append((pose, pose_weight))
        if angle_clip:
            criteria.append((angle_clip, min(0.2, pose_weight)))
        scores = vision_pipeline.score_images(
            valid_imgs,
            base_prompt=full_prompt,
            criteria=criteria,
            model_weights=preset.get("clip_weights"),
        )
    else:
        all_scores = []
        for key in preset_keys:
            preset = PRESETS[key]
            full_prompt = build_clip_prompt(subject, preset["quality_prompt"])
            criteria = list(preset.get("criteria", []))
            pose_weight = preset.get("pose_weight", 0.25) * FEATURE_WEIGHT_MULTIPLIER
            if pose:
                criteria.append((pose, pose_weight))
            if angle_clip:
                criteria.append((angle_clip, min(0.2, pose_weight)))
            preset_scores = vision_pipeline.score_images(
                valid_imgs,
                base_prompt=full_prompt,
                criteria=criteria,
                model_weights=preset.get("clip_weights"),
            )
            all_scores.append(preset_scores)
        scores = [max(score_set) for score_set in zip(*all_scores)]

    # 9) Rank and export results.
    yield _ui_stage("Finalizing...")
    ranked_data = sorted(
        zip(scores, valid_imgs, valid_urls),
        key=lambda x: x[0],
        reverse=True
    )

    gallery_output: List[Tuple[str, str]] = []
    clean_files: List[str] = []
    batch_urls: List[str] = []
    rank_count = 0
    batch_id = len(batch_history_state or []) + 1

    for score, img, url in ranked_data:
        if rank_count >= DISPLAY_BATCH_SIZE:
            break
        disp_score = min(score * SCORE_DISPLAY_MULTIPLIER, 99.9)
        if disp_score < display_threshold:
            continue

        clean_path = os.path.join(DOWNLOAD_DIR, f"ref_{batch_id:03d}_{rank_count:02d}.jpg")
        if not save_image(img, clean_path):
            continue
        clean_files.append(clean_path)

        tags = vision_pipeline.generate_smart_tags(
            img,
            subject,
            pose,
            top_k=4,
            threshold=0.2
        )
        tag_text = " - ".join(tags) if tags else ""
        source = url_to_source.get(url, "unknown")
        label = tag_text or subject
        label = f"{label}\nSource: {source}"

        gallery_output.append((clean_path, label))
        if url:
            batch_urls.append(str(url))
        rank_count += 1

    if not gallery_output:
        if append_mode:
            yield _ui_error_keep("No images passed the quality threshold.", gallery_state or [])
        else:
            yield _ui_error("No images passed the quality threshold.")
        return

    # 10) Update batch history and UI outputs.
    merged_gallery = (gallery_state or []) + gallery_output
    merged_files = (all_files_state or []) + clean_files
    merged_gallery, merged_files = cap_gallery(merged_gallery, merged_files, MAX_GALLERY_ITEMS)

    batch_history = list(batch_history_state or [])
    batch_history.append(gallery_output)
    batch_history = cap_batch_history(batch_history, MAX_GALLERY_ITEMS)

    zip_path = build_zip_for_scope(DOWNLOAD_DIR, zip_scope, clean_files, merged_files)
    elapsed = time.time() - start_time

    batch_choices = ["All batches"] + [f"Batch {i+1}" for i in range(len(batch_history))]
    batch_value = batch_choices[-1] if batch_choices else "All batches"

    yield {
        UI.status_row: gr.update(visible=True),
        UI.welcome_col: gr.update(visible=False),
        UI.out_gallery: gr.update(value=merged_gallery, visible=True, selected_index=None, preview=False),
        UI.status_box: gr.update(value=f"Found {len(gallery_output)} results in {elapsed:.1f}s", visible=True),
        UI.mode_chip: gr.update(value=_mode_label(preset_labels), visible=True),
        UI.btn_download: gr.update(value=zip_path, visible=True, interactive=bool(zip_path)),
        UI.btn_search: gr.update(value="Generate New Set", interactive=True, visible=True),
        UI.btn_load_more: gr.update(value="Load more", interactive=True, visible=True),
        UI.gallery_state_comp: merged_gallery,
        UI.current_batch_state_comp: clean_files,
        UI.all_files_state_comp: merged_files,
        UI.seen_urls_state_comp: dedupe_urls((seen_urls_state or []) + batch_urls),
        UI.last_inputs_state_comp: _make_last_inputs(
            subject,
            pose,
            angle_label,
            intent_photo,
            intent_wildlife,
            intent_art,
            intent_3d,
            impostors,
        ),
        UI.batch_history_state_comp: batch_history,
        UI.batch_selector: gr.update(choices=batch_choices, value=batch_value),
    }
