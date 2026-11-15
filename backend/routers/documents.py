from hashlib import sha256
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse

from backend.schemas.chat import DocumentItem
from backend.services.ingest import render_pdf_page_image

router = APIRouter()


@router.get("/documents/{document_id}/info", response_model=DocumentItem)
def get_document_details(document_id: str, request: Request):
    course_manager = request.app.state.course_manager
    doc = course_manager.get_document_info(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentItem(
        document_id=doc.document_id,
        document_name=doc.document_name,
        page_count=doc.page_count,
    )


@router.get("/documents/{document_id}/page/{page}")
def get_document_page_preview(
    document_id: str,
    page: int,
    request: Request,
    expected_hash: Annotated[str | None, Query(alias="sha256", pattern=r"^[0-9a-f]{64}$")] = None,
):
    course_manager = request.app.state.course_manager
    doc = course_manager.get_document_info(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        pdf_bytes = doc.path.read_bytes()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    except OSError:
        raise HTTPException(status_code=500, detail="Cannot render page preview") from None
    if sha256(pdf_bytes).hexdigest() != (expected_hash or doc.sha256):
        raise HTTPException(status_code=409, detail="Tệp PDF đã thay đổi. Hãy hỏi lại để lấy nguồn mới.")

    try:
        image_bytes = render_pdf_page_image(pdf_bytes, page)
        return Response(content=image_bytes, media_type="image/png")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Cannot render page preview")


@router.get("/documents/{document_id}")
def get_document_file(document_id: str, request: Request):
    course_manager = request.app.state.course_manager
    doc = course_manager.get_document_info(document_id)
    if not doc or not doc.path.is_file():
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(
        path=doc.path,
        filename=doc.document_name,
        media_type="application/pdf",
        content_disposition_type="inline",
    )


@router.get("/documents/{document_id}/page/{page}/pdf")
def get_document_single_page_pdf(document_id: str, page: int, request: Request):
    import pymupdf
    from urllib.parse import quote

    course_manager = request.app.state.course_manager
    doc = course_manager.get_document_info(document_id)
    if not doc or not doc.path.is_file():
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        with pymupdf.open(str(doc.path)) as src_pdf:
            if not 1 <= page <= src_pdf.page_count:
                raise HTTPException(status_code=400, detail=f"Trang {page} vượt quá tổng số trang (1..{src_pdf.page_count})")
            single_page_doc = pymupdf.open()
            single_page_doc.insert_pdf(src_pdf, from_page=page - 1, to_page=page - 1)
            pdf_bytes = single_page_doc.tobytes()

        safe_filename = quote(f"{doc.document_name}_trang_{page}.pdf")
        headers = {
            "Content-Disposition": f"inline; filename*=utf-8''{safe_filename}",
        }
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot extract page PDF: {e}")
