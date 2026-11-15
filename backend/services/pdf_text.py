"""Restore known Symbol font characters from PDF text extraction."""

import re


SYMBOLS = {
    "\uf0c6": "∅", "\uf0cd": "⊆", "\uf0cc": "⊂", "\uf0ce": "∈",
    "\uf0cf": "∉", "\uf0c7": "∩", "\uf0c8": "∪", "\uf022": "∀",
    "\uf024": "∃", "\uf0ac": "¬", "\uf0de": "⇒", "\uf0db": "⇔",
    "\uf0d7": "×",
}


def readable_pdf_text(text: str) -> str:
    for glyph, symbol in SYMBOLS.items():
        text = text.replace(glyph, symbol)
    return re.sub(r"[\ue000-\uf8ff]", "[ký hiệu cần xem PDF gốc]", text)
