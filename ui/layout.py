"""
Construtor de layout Gradio para a Visual Study Tool.
"""

import gradio as gr

from config.ui_options import INTENTION_OPTIONS, ANGLE_OPTIONS
from ui.components import label_with_tip

def build_layout(css: str, theme: gr.themes.Base):
    with gr.Blocks(title="Visual Study Tool") as demo:
        with gr.Row(elem_id="main-layout"):
            # 1) Entradas da barra lateral e ações.
            with gr.Column(elem_id="sidebar", scale=0):
                gr.Markdown(
                    """
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
                         <span style="font-size: 1.3rem;">🐺</span>
                         <span style="font-weight: 700; font-size: 1.1rem; color: #e2e8f0;">Visual Study Tool</span>
                    </div>
                    """
                )

                # 2) Entrada de assunto.
                label_with_tip(
                    "Assunto",
                    "Assunto principal. Exemplo: cavaleiro lobo, corredor cyberpunk."
                )
                inp_subject = gr.Textbox(
                    label=None,
                    show_label=False,
                    placeholder="ex: Cavaleiro Lobo",
                    lines=1,
                    elem_classes="field-input"
                )

                # 3) Entrada de características.
                label_with_tip(
                    "Características",
                    "Opcional. Usado para priorizar resultados (pose, ação ou traços visuais). Exemplo: perfil lateral, corpo inteiro."
                )
                inp_pose = gr.Textbox(
                    label=None,
                    show_label=False,
                    placeholder="ex: De pé, perfil lateral",
                    lines=1,
                    elem_classes="field-input"
                )

                # 4) Seletor de ângulo de visualização.
                label_with_tip(
                    "Ângulo de Visão",
                    "Opcional. Guia ângulo de câmera/visualização. Exemplos: frontal, lateral, 3/4, de cima."
                )
                inp_angle = gr.Dropdown(
                    choices=[item["label"] for item in ANGLE_OPTIONS],
                    value="Any",
                    label=None,
                    show_label=False,
                    elem_id="angle-dropdown",
                    elem_classes=["field-input", "angle-dropdown"],
                )

                # 5) Seleção de intenção.
                label_with_tip(
                    "Intenção",
                    "Escolha pelo menos uma categoria. Estas definem o estilo da origem."
                )
                with gr.Column(elem_id="intention-select"):
                    intent_checks = []
                    for option in INTENTION_OPTIONS:
                        with gr.Row(elem_classes="intent-row"):
                            intent_checks.append(
                                gr.Checkbox(
                                    label=option["label"],
                                    value=False,
                                    elem_classes="intent-item"
                                )
                            )
                            gr.HTML(
                                f'<span class="tooltip intent-tooltip" data-tip="{option["tooltip"]}">?</span>',
                                elem_classes="intent-tooltip-wrap"
                            )

                # 6) Entrada de termos negativos.
                label_with_tip(
                    "Negativas",
                    "Opcional. Exclua termos que você não quer. Exemplo: desfocado, marca d'água, logo.",
                    optional=True
                )
                inp_impostors = gr.Textbox(
                    label=None,
                    show_label=False,
                    placeholder="O que evitar (opcional)",
                    lines=1,
                    max_lines=1,
                    elem_classes=["field-input", "field-optional"]
                )

                # 7) Ações primárias.
                with gr.Row(elem_id="actions-row"):
                    btn_search = gr.Button("Gerar novo conjunto", elem_id="btn-search")
                    btn_download = gr.DownloadButton("Exportar ZIP ⬇️", elem_id="btn-download", visible=False)

                label_with_tip(
                    "Escopo do ZIP",
                    "Escolha se deseja exportar apenas o lote mais recente ou tudo carregado.",
                    optional=True
                )
                zip_scope = gr.Radio(
                    choices=["Lote atual", "Todos os lotes"],
                    value="Lote atual",
                    show_label=False,
                    elem_classes="field-input",
                )

                label_with_tip(
                    "Visualizar Lote",
                    "Alterne entre lotes anteriores ou veja todos os resultados.",
                    optional=True
                )
                batch_selector = gr.Dropdown(
                    choices=["Todos os lotes"],
                    value="Todos os lotes",
                    show_label=False,
                    elem_classes="field-input",
                )

            # 8) Painel de conteúdo principal (status + galeria).
            with gr.Column(elem_id="content-area"):

                with gr.Row(elem_id="results-status", visible=False) as status_row:
                    status_box = gr.Markdown("", visible=False, elem_id="status-box")
                    mode_chip = gr.HTML("", visible=False, elem_id="mode-chip")

                out_gallery = gr.Gallery(
                    label="",
                    columns=4,
                    height="auto",
                    object_fit="contain",
                    allow_preview=True,
                    preview=False,
                    selected_index=None,
                    buttons=["download", "fullscreen"],
                    show_label=False,
                    visible=False,
                    elem_id="gallery-grid"
                )

                btn_load_more = gr.Button("Carregar mais", elem_id="btn-load-more", visible=False)

                with gr.Column(elem_classes="welcome-box", visible=False) as welcome_col:
                    gr.HTML(
                        """
                        <div class="welcome-hero">
                            <div class="welcome-title">Construa um conjunto de estudo visual limpo</div>
                            <div class="welcome-sub">
                                Comece com um assunto, adicione características, depois refine com uma intenção.
                            </div>
                        </div>
                        <div class="welcome-sub" style="margin-bottom: 6px;">
                            Tente: <span style="color:#cfe0ff;">lobo samurai</span>, <span style="color:#cfe0ff;">incineroar</span>, <span style="color:#cfe0ff;">lobo da neve</span>
                        </div>
                        <div class="skeleton-grid">
                            <div class="skeleton-card"></div>
                            <div class="skeleton-card"></div>
                            <div class="skeleton-card"></div>
                            <div class="skeleton-card"></div>
                            <div class="skeleton-card"></div>
                            <div class="skeleton-card"></div>
                        </div>
                        """
                    )

        shuffle_state = gr.State(0)
        gallery_state_comp = gr.State([])
        current_batch_state_comp = gr.State([])
        all_files_state_comp = gr.State([])
        seen_urls_state_comp = gr.State([])
        last_inputs_state_comp = gr.State({})
        batch_history_state_comp = gr.State([])

    refs = {
        "demo": demo,
        "status_row": status_row,
        "welcome_col": welcome_col,
        "status_box": status_box,
        "mode_chip": mode_chip,
        "out_gallery": out_gallery,
        "btn_search": btn_search,
        "btn_download": btn_download,
        "btn_load_more": btn_load_more,
        "inp_subject": inp_subject,
        "inp_pose": inp_pose,
        "inp_angle": inp_angle,
        "intent_checks": intent_checks,
        "inp_impostors": inp_impostors,
        "zip_scope": zip_scope,
        "batch_selector": batch_selector,
        "shuffle_state": shuffle_state,
        "gallery_state_comp": gallery_state_comp,
        "current_batch_state_comp": current_batch_state_comp,
        "all_files_state_comp": all_files_state_comp,
        "seen_urls_state_comp": seen_urls_state_comp,
        "last_inputs_state_comp": last_inputs_state_comp,
        "batch_history_state_comp": batch_history_state_comp,
    }

    return demo, refs
