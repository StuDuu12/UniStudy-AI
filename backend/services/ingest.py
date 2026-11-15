from collections.abc import Iterator
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

import pymupdf

from backend.services.evidence import normalize_text
from services.retrieval import PDF_LOCK

_CHUNK_WORDS = 135
_CHUNK_OVERLAP = 25
_MAX_PREVIEW_EDGE = 1440


@dataclass(frozen=True)
class DocumentInfo:
    document_id: str
    document_name: str
    path: Path
    license: str
    page_count: int = 0
    sha256: str = ""


@dataclass(frozen=True)
class ChunkSource:
    document_id: str
    document_name: str
    page: int
    chunk_id: str
    excerpt: str
    score: float = 0.0
    document_sha256: str = ""
    heading: str = ""


def extract_pdf_chunks(document: DocumentInfo, pdf_bytes: bytes, *, sort: bool = True) -> Iterator[ChunkSource]:
    with PDF_LOCK, pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        if not pdf.is_pdf or pdf.is_repaired or pdf.needs_pass:
            raise ValueError("PDF is invalid or requires a password")
        step = _CHUNK_WORDS - _CHUNK_OVERLAP
        for page_number, page in enumerate(pdf, start=1):
            page_text = page.get_text(sort=sort)
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            heading = lines[0][:120] if lines else ""
            words = page_text.split()
            for chunk_number, start in enumerate(range(0, len(words), step), start=1):
                excerpt = " ".join(words[start : start + _CHUNK_WORDS])
                if len(normalize_text(excerpt)) < 3:
                    continue
                yield ChunkSource(
                    document_id=document.document_id,
                    document_name=document.document_name,
                    page=page_number,
                    chunk_id=f"{document.document_id}_p{page_number}_c{chunk_number:02}",
                    excerpt=excerpt,
                    score=0.0,
                    document_sha256=document.sha256,
                    heading=heading,
                )
                if start + _CHUNK_WORDS >= len(words):
                    break


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    with PDF_LOCK, pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        return pdf.page_count


def render_pdf_page_image(pdf_bytes: bytes, page_number: int) -> bytes:
    with PDF_LOCK, pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        if not 1 <= page_number <= pdf.page_count:
            raise ValueError(f"Page {page_number} out of range (1..{pdf.page_count})")
        page = pdf[page_number - 1]
        rect = page.rect
        longest_edge = max(rect.width, rect.height)
        if rect.is_empty or not isfinite(longest_edge):
            raise ValueError("Invalid PDF page dimensions")
        scale = min(2.0, _MAX_PREVIEW_EDGE / longest_edge)
        return page.get_pixmap(matrix=pymupdf.Matrix(scale, scale)).tobytes("png")
