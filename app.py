"""
Visual Study Tool - Ferramenta de referência visual para artistas e designers.
"""

import gradio as gr
import logging
from logging.handlers import RotatingFileHandler
from typing import List, Tuple, Dict
from pathlib import Path

from config.settings import DOWNLOAD_DIR, LOGS_DIR, LOG_LEVEL
from core.search_engine import get_default_searcher
from core.downloaders import ImageDownloader
from core.vision_pipeline import VisionPipeline
from core.search_pipeline import (
    init_pipeline,
    set_ui_refs,
    UIRefs,
    PipelineDeps,
    search_and_process,
    ui_loading,
)
from ui.layout import build_layout
from utils.pretty_logger import log as pretty_log
from utils.file_utils import build_zip_for_scope


def setup_logging():
    """Configura logging em console e arquivo."""
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    if getattr(root, "_configured", False):
        return
    root.setLevel(log_level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    log_path = LOGS_DIR / "app.log"
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root.handlers = []
    root.addHandler(console_handler)
    root.addHandler(file_handler)
    root._configured = True


setup_logging()
pretty_log("Logger configurado e pronto para capturar execuções.", "SYSTEM")

search_engine = get_default_searcher()
downloader = ImageDownloader()
vision_pipeline = VisionPipeline()
source_weights: Dict[str, float] = {}

init_pipeline(PipelineDeps(
    search_engine=search_engine,
    downloader=downloader,
    vision_pipeline=vision_pipeline,
    source_weights=source_weights,
))

CSS_PATH = Path(__file__).with_name("ui.css")
css = CSS_PATH.read_text(encoding="utf-8")
theme = gr.themes.Soft(primary_hue="blue", neutral_hue="slate")
demo, refs = build_layout(css, theme)

set_ui_refs(UIRefs(
    status_row=refs["status_row"],
    welcome_col=refs["welcome_col"],
    out_gallery=refs["out_gallery"],
    status_box=refs["status_box"],
    mode_chip=refs["mode_chip"],
    btn_download=refs["btn_download"],
    btn_search=refs["btn_search"],
    btn_load_more=refs["btn_load_more"],
    gallery_state_comp=refs["gallery_state_comp"],
    current_batch_state_comp=refs["current_batch_state_comp"],
    all_files_state_comp=refs["all_files_state_comp"],
    seen_urls_state_comp=refs["seen_urls_state_comp"],
    last_inputs_state_comp=refs["last_inputs_state_comp"],
    batch_history_state_comp=refs["batch_history_state_comp"],
    batch_selector=refs["batch_selector"],
))


def _bump_seed(seed: int) -> int:
    """Incrementa seed para embaralhar ordem de busca."""
    return (seed or 0) + 1


def _load_more(
    last_inputs: Dict[str, object],
    shuffle_seed: int,
    zip_scope_value: str,
    gallery_state_value: List[Tuple[str, str]],
    all_files_value: List[str],
    seen_urls_value: List[str],
    batch_history_value: List[List[Tuple[str, str]]],
):
    """Carrega mais resultados usando os parâmetros anteriores."""
    if not last_inputs:
        yield {
            refs["status_row"]: gr.update(visible=True),
            refs["welcome_col"]: gr.update(visible=False),
            refs["status_box"]: gr.update(value="Execute uma busca antes de carregar mais.", visible=True),
        }
        return

    subject = last_inputs.get("subject", "")
    pose = last_inputs.get("pose", "")
    angle_label = last_inputs.get("angle_label", "Any")
    intent_flags = last_inputs.get("intent_flags", [False, False, False, False])
    impostors = last_inputs.get("impostors", "")

    yield from search_and_process(
        subject,
        pose,
        angle_label,
        intent_flags[0],
        intent_flags[1],
        intent_flags[2],
        intent_flags[3],
        impostors,
        shuffle_seed,
        zip_scope_value,
        gallery_state_value,
        all_files_value,
        seen_urls_value,
        batch_history_value,
        append_mode=True,
    )


def _refresh_zip(scope: str, current_files: List[str], all_files: List[str]):
    """Reconstrói ZIP baseado no escopo selecionado."""
    zip_path = build_zip_for_scope(DOWNLOAD_DIR, scope, current_files, all_files)
    return gr.update(value=zip_path, visible=bool(zip_path), interactive=bool(zip_path))


def _view_batch(selection: str, batch_history: List[List[Tuple[str, str]]], merged_gallery: List[Tuple[str, str]]):
    """Alterna visualização entre batches de resultados."""
    if not selection or selection == "All batches":
        return gr.update(value=merged_gallery, visible=bool(merged_gallery), selected_index=None, preview=False)
    if selection.startswith("Batch "):
        try:
            index = int(selection.split(" ")[1]) - 1
        except (ValueError, IndexError):
            index = -1
        if 0 <= index < len(batch_history):
            batch = batch_history[index]
            return gr.update(value=batch, visible=bool(batch), selected_index=None, preview=False)
    return gr.update(value=merged_gallery, visible=bool(merged_gallery), selected_index=None, preview=False)


with demo:
    refs["btn_search"].click(
        fn=_bump_seed,
        inputs=[refs["shuffle_state"]],
        outputs=[refs["shuffle_state"]]
    ).then(
        fn=ui_loading,
        inputs=[],
        outputs=[
            refs["status_row"],
            refs["welcome_col"],
        refs["out_gallery"],
        refs["status_box"],
        refs["mode_chip"],
        refs["btn_download"],
        refs["btn_search"],
        refs["btn_load_more"],
        ]
    ).then(
        fn=search_and_process,
        inputs=[
            refs["inp_subject"],
            refs["inp_pose"],
            refs["inp_angle"],
            *refs["intent_checks"],
            refs["inp_impostors"],
            refs["shuffle_state"],
            refs["zip_scope"],
            refs["gallery_state_comp"],
            refs["all_files_state_comp"],
            refs["seen_urls_state_comp"],
            refs["batch_history_state_comp"],
        ],
        outputs=[
            refs["status_row"],
            refs["welcome_col"],
        refs["out_gallery"],
        refs["status_box"],
        refs["mode_chip"],
        refs["btn_download"],
        refs["btn_search"],
        refs["btn_load_more"],
            refs["gallery_state_comp"],
            refs["current_batch_state_comp"],
            refs["all_files_state_comp"],
            refs["seen_urls_state_comp"],
            refs["last_inputs_state_comp"],
            refs["batch_history_state_comp"],
            refs["batch_selector"],
        ]
    )

    refs["btn_load_more"].click(
        fn=_bump_seed,
        inputs=[refs["shuffle_state"]],
        outputs=[refs["shuffle_state"]]
    ).then(
        fn=_load_more,
        inputs=[
            refs["last_inputs_state_comp"],
            refs["shuffle_state"],
            refs["zip_scope"],
            refs["gallery_state_comp"],
            refs["all_files_state_comp"],
            refs["seen_urls_state_comp"],
            refs["batch_history_state_comp"],
        ],
        outputs=[
        refs["status_row"],
        refs["welcome_col"],
        refs["out_gallery"],
        refs["status_box"],
        refs["mode_chip"],
        refs["btn_download"],
        refs["btn_search"],
        refs["btn_load_more"],
            refs["gallery_state_comp"],
            refs["current_batch_state_comp"],
            refs["all_files_state_comp"],
            refs["seen_urls_state_comp"],
            refs["last_inputs_state_comp"],
            refs["batch_history_state_comp"],
            refs["batch_selector"],
        ]
    )

    refs["zip_scope"].change(
        fn=_refresh_zip,
        inputs=[refs["zip_scope"], refs["current_batch_state_comp"], refs["all_files_state_comp"]],
        outputs=[refs["btn_download"]],
    )

    refs["batch_selector"].change(
        fn=_view_batch,
        inputs=[refs["batch_selector"], refs["batch_history_state_comp"], refs["gallery_state_comp"]],
        outputs=[refs["out_gallery"]],
    )


if __name__ == "__main__":
    demo.queue()
    demo.launch(
        inbrowser=True,
        css=css,
        theme=theme,
        allowed_paths=[str(DOWNLOAD_DIR)]
    )
