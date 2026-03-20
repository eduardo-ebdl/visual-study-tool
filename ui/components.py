"""
Reusable UI components.
"""

import gradio as gr

def label_with_tip(title: str, tip: str, optional: bool = False) -> gr.HTML:
    """Render a compact label with a hover-only tooltip."""
    # 1) Build the label with an optional pill and tooltip text.
    optional_html = '<span class="optional-pill">Optional</span>' if optional else ""
    return gr.HTML(
        f'<div class="field-label"><span class="field-title">{title}</span>'
        f'{optional_html}<span class="tooltip" data-tip="{tip}">?</span></div>'
    )
