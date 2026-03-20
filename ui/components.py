"""
Componentes reutilizáveis de UI.
"""

import gradio as gr

def label_with_tip(title: str, tip: str, optional: bool = False) -> gr.HTML:
    """Renderiza um label compacto com tooltip ao passar o mouse."""
    # 1) Constrói o label com um pill opcional e texto de tooltip.
    optional_html = '<span class="optional-pill">Opcional</span>' if optional else ""
    return gr.HTML(
        f'<div class="field-label"><span class="field-title">{title}</span>'
        f'{optional_html}<span class="tooltip" data-tip="{tip}">?</span></div>'
    )
