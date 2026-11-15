from fastapi import APIRouter, HTTPException, Request
from python_multipart.exceptions import FormParserError
from python_multipart.multipart import parse_options_header
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from backend.schemas.chat import CourseItem, CourseListResponse, DocumentListResponse
from services.course_upload import CourseNotFoundError, CourseUploadError, MAX_PDF_FILES, MAX_PDF_MB

router = APIRouter()
_MAX_PDF_BYTES = MAX_PDF_MB * 1024 * 1024
_MAX_UPLOAD_BYTES = MAX_PDF_FILES * _MAX_PDF_BYTES + 64 * 1024


class _UploadTooLarge(MultiPartException):
    pass


async def _read_upload(request: Request, *, with_name: bool) -> tuple[str, list[tuple[str, bytes]]]:
    media_type, _ = parse_options_header(request.headers.get("content-type"))
    if media_type.lower() != b"multipart/form-data":
        raise HTTPException(status_code=415, detail="Hãy tải tệp bằng biểu mẫu multipart.")

    async def limited_stream():
        bytes_received = 0
        async for chunk in request.stream():
            bytes_received += len(chunk)
            if bytes_received > _MAX_UPLOAD_BYTES:
                raise _UploadTooLarge("Upload too large")
            yield chunk

    try:
        form = await MultiPartParser(
            request.headers,
            limited_stream(),
            max_files=MAX_PDF_FILES,
            max_fields=int(with_name),
            max_part_size=1024,
        ).parse()
    except _UploadTooLarge:
        raise HTTPException(status_code=413, detail="Tổng dung lượng tải lên vượt giới hạn.") from None
    except (MultiPartException, FormParserError):
        raise HTTPException(status_code=400, detail=f"Biểu mẫu không hợp lệ. Hãy chọn tối đa {MAX_PDF_FILES} tệp PDF.") from None

    try:
        name = form.get("course_name", "") if with_name else ""
        uploads = form.getlist("files")
        if not isinstance(name, str) or not uploads or any(key not in {"course_name", "files"} for key in form):
            raise HTTPException(status_code=400, detail="Hãy nhập thông tin học phần và chọn tệp PDF.")
        files = []
        for upload in uploads:
            if not isinstance(upload, UploadFile) or not upload.filename:
                raise HTTPException(status_code=400, detail="Hãy chọn tệp PDF hợp lệ.")
            if upload.size is not None and upload.size > _MAX_PDF_BYTES:
                raise HTTPException(status_code=413, detail=f"Mỗi tệp PDF không được vượt quá {MAX_PDF_MB} MB.")
            data = await upload.read(_MAX_PDF_BYTES + 1)
            if len(data) > _MAX_PDF_BYTES:
                raise HTTPException(status_code=413, detail=f"Mỗi tệp PDF không được vượt quá {MAX_PDF_MB} MB.")
            files.append((upload.filename, data))
        return name, files
    finally:
        await form.close()


@router.get("/courses", response_model=CourseListResponse)
def get_courses(request: Request):
    course_manager = request.app.state.course_manager
    courses = course_manager.list_courses()
    return CourseListResponse(courses=courses)


@router.post("/courses", response_model=CourseItem, status_code=201)
async def post_course(request: Request):
    name, files = await _read_upload(request, with_name=True)
    try:
        return await run_in_threadpool(request.app.state.course_manager.add_course, name, files)
    except CourseUploadError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None


@router.get("/courses/{course_id}/documents", response_model=DocumentListResponse)
def get_course_documents(course_id: str, request: Request):
    course_manager = request.app.state.course_manager
    documents = course_manager.get_course_documents(course_id)
    if documents is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return DocumentListResponse(documents=documents)


@router.post("/courses/{course_id}/documents", response_model=DocumentListResponse, status_code=201)
async def post_course_documents(course_id: str, request: Request):
    course_manager = request.app.state.course_manager
    if course_manager.get_course_documents(course_id) is None:
        raise HTTPException(status_code=404, detail="Học phần không tồn tại.")
    _, files = await _read_upload(request, with_name=False)
    try:
        documents = await run_in_threadpool(course_manager.append_documents, course_id, files)
    except CourseNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except CourseUploadError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    return DocumentListResponse(documents=documents)
