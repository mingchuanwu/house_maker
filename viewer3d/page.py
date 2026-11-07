"""Assemble the single-file viewer page: the HTML template with its CSS, scripts and the model payload inlined."""

import html
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def build_page(payload: dict) -> str:
    data = json.dumps(payload, separators=(',', ':')).replace('</', '<\\/')
    page = (HERE / 'viewer.html').read_text(encoding='utf-8')
    return (page.replace('/*__TITLE__*/', html.escape(payload.get('title', 'house')))
                .replace('/*__CSS__*/', (HERE / 'viewer.css').read_text(encoding='utf-8'))
                .replace('/*__CORE__*/', (HERE / 'viewer_core.js').read_text(encoding='utf-8'))
                .replace('/*__APP__*/', (HERE / 'viewer_app.js').read_text(encoding='utf-8'))
                .replace('/*__DATA__*/', data))
