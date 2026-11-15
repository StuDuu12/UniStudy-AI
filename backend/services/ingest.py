from collections.abc import Iterator
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

import pymupdf

from backend.services.evidence import normalize_text
from backend.services.pdf_text import PdfLine, format_pdf_blocks, pdf_layout_blocks
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
    formatted_excerpt: str = ""
    has_visual_content: bool = False


def extract_pdf_chunks(document: DocumentInfo, pdf_bytes: bytes, *, sort: bool = True) -> Iterator[ChunkSource]:
    with PDF_LOCK, pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        if not pdf.is_pdf or pdf.is_repaired or pdf.needs_pass:
            raise ValueError("PDF is invalid or requires a password")
        for page_number, page in enumerate(pdf, start=1):
            blocks = page.get_text("dict", sort=sort, flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
            lines = []
            for block in blocks["blocks"]:
                for line in block.get("lines", ()):
                    spans = line["spans"]
                    if not spans:
                        continue
                    parts = [spans[0]["text"]]
                    for left, right in zip(spans, spans[1:]):
                        if right["bbox"][0] - left["bbox"][2] > right["size"] * 0.15:
                            parts.append(" ")
                        parts.append(right["text"])
                    text = "".join(parts).strip()
                    if text:
                        lines.append(PdfLine(text, line["bbox"][0], line["bbox"][1], spans[0]["size"]))
            layout = pdf_layout_blocks(lines, page_number, page.rect.width, page.rect.height)
            heading = lines[0].text[:120] if lines else ""
            words = [word for line in lines for word in line.text.split()]
            # Dense rows of short entries can be a table flattened by PDF extraction.
            has_table_layout = len(lines) >= 16 and sum(len(line.text.split()) <= 2 for line in lines) >= len(lines) * 0.75
            has_visual_content = has_table_layout or any(
                (pymupdf.Rect(image["bbox"]) & page.rect).get_area() >= page.rect.get_area() * 0.02
                for image in page.get_image_info()
            )
            # Keep boundary context, while preserving one physical PDF page per chunk.
            step = _CHUNK_WORDS - _CHUNK_OVERLAP
            for start in range(0, len(words), step):
                excerpt = " ".join(words[start : start + _CHUNK_WORDS])
                if len(normalize_text(excerpt)) < 3:
                    continue
                chunk_number = start // step + 1
                yield ChunkSource(
                    document_id=document.document_id,
                    document_name=document.document_name,
                    page=page_number,
                    chunk_id=f"{document.document_id}_p{page_number}_c{chunk_number:02}",
                    excerpt=excerpt,
                    score=0.0,
                    document_sha256=document.sha256,
                    heading=heading,
                    formatted_excerpt=format_pdf_blocks(layout, start, start + _CHUNK_WORDS),
                    has_visual_content=has_visual_content,
                )
                if start + _CHUNK_WORDS >= len(words):
                    break


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    with PDF_LOCK, pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        return pdf.page_count


def render_pdf_page_image(
    pdf_bytes: bytes, page_number: int, *, max_edge: int = _MAX_PREVIEW_EDGE,
) -> bytes:
    with PDF_LOCK, pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        if not 1 <= page_number <= pdf.page_count:
            raise ValueError(f"Page {page_number} out of range (1..{pdf.page_count})")
        page = pdf[page_number - 1]
        rect = page.rect
        longest_edge = max(rect.width, rect.height)
        if rect.is_empty or not isfinite(longest_edge):
            raise ValueError("Invalid PDF page dimensions")
        scale = min(2.0, max_edge / longest_edge)
        return page.get_pixmap(matrix=pymupdf.Matrix(scale, scale)).tobytes("png")
