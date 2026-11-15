from hashlib import sha256
from math import isfinite
from pathlib import Path

import pymupdf
import streamlit as st

from services.retrieval import PDF_LOCK


_MAX_PREVIEW_EDGE = 1440


class PdfChangedError(ValueError):
    pass


def render_pdf_preview(path: Path, expected_sha256: str, page_number: int) -> bytes:
    pdf_bytes = path.read_bytes()
    if sha256(pdf_bytes).hexdigest() != expected_sha256:
        raise PdfChangedError
    return _render_page(expected_sha256, page_number, pdf_bytes)


@st.cache_data(show_spinner=False, max_entries=16)
def _render_page(digest: str, page_number: int, _pdf_bytes: bytes) -> bytes:
    # The caller verifies the digest before consulting this cache.
    with PDF_LOCK, pymupdf.open(stream=_pdf_bytes, filetype="pdf") as pdf:
        if not 1 <= page_number <= pdf.page_count:
            raise ValueError("PDF page out of range")
        page = pdf[page_number - 1]
        rect = page.rect
        longest_edge = max(rect.width, rect.height)
        if rect.is_empty or not isfinite(longest_edge):
            raise ValueError("Invalid PDF page dimensions")
        scale = min(2, _MAX_PREVIEW_EDGE / longest_edge)
        return page.get_pixmap(matrix=pymupdf.Matrix(scale, scale)).tobytes("png")
