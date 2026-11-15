from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

import pymupdf
import pytest

from services.chatbot_service import ChatbotService
from services.course_upload import CourseUploadError, add_course
from src.schemas import ChatRequest


def pdf_bytes(text):
    with pymupdf.open() as document:
        page = document.new_page()
        if text:
            page.insert_text((40, 60), text)
        return document.tobytes()


def test_first_upload_survives_reload_and_is_only_in_private_library(tmp_path):
    private = tmp_path / "data" / "local_course_pdfs"
    pdf = pdf_bytes("Network sockets and datagrams")

    course_id = add_course(private, "  Mạng   máy tính ", [("../network.pdf", pdf)])
    service = ChatbotService(private, private=True)
    course = next(course for course in service.courses() if course.course_id == course_id)
    source, = course.documents
    response = service.answer_question(ChatRequest("1", course_id, "Network sockets and datagrams"))

    assert course.course_name == "Mạng máy tính"
    assert source.document_name == "network.pdf"
    assert source.path.parent == private.resolve()
    assert source.path.name != source.document_name
    assert source.path.read_bytes() == pdf
    assert response.status == "success"
    assert response.sources[0].page == 1
    assert response.sources[0].document_sha256 == sha256(pdf).hexdigest()
    assert course_id not in {course.course_id for course in ChatbotService(private.parent).courses()}


def test_upload_preserves_legacy_manifest_and_rejects_duplicate_names(tmp_path):
    (tmp_path / "old.pdf").write_bytes(pdf_bytes("Computing fundamentals"))
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "course_id,document_id,document_name,path,license\n"
        "tin_hoc_dai_cuong,old,Old notes.pdf,old.pdf,local_only\n",
        encoding="utf-8",
    )
    files = [("notes.pdf", pdf_bytes("Linear algebra and matrices"))]
    with pytest.raises(CourseUploadError):
        add_course(tmp_path, "Tin học đại cương", files)
    course_id = add_course(tmp_path, "Đại số tuyến tính", files)
    before = manifest.read_bytes()
    with pytest.raises(CourseUploadError):
        add_course(tmp_path, " ĐẠI SỐ  TUYẾN TÍNH ", files)

    catalog = {course.course_id: course for course in ChatbotService(tmp_path, private=True).courses()}
    assert catalog["tin_hoc_dai_cuong"].documents[0].document_id == "old"
    assert catalog[course_id].course_name == "Đại số tuyến tính"
    assert manifest.read_bytes() == before
    assert len(list(tmp_path.glob("*.pdf"))) == 2


@pytest.mark.parametrize("invalid", [b"not a PDF", pdf_bytes("")])
def test_invalid_pdf_prevents_partial_upload(tmp_path, invalid):
    files = [("good.pdf", pdf_bytes("Linear algebra")), ("bad.pdf", invalid)]

    with pytest.raises(CourseUploadError):
        add_course(tmp_path, "Đại số", files)

    assert not (tmp_path / "manifest.csv").exists()
    assert not list(tmp_path.glob("*.pdf"))


def test_replace_failure_keeps_existing_manifest_and_removes_new_files(tmp_path, monkeypatch):
    files = [("notes.pdf", pdf_bytes("Linear algebra and matrices"))]
    add_course(tmp_path, "Đại số", files)
    manifest = tmp_path / "manifest.csv"
    before = manifest.read_bytes()
    paths = set(tmp_path.glob("*.pdf"))
    replace = Path.replace

    def fail_manifest_replace(path, target):
        if target == manifest:
            raise OSError("sensitive local path")
        return replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_manifest_replace)
    with pytest.raises(CourseUploadError) as error:
        add_course(tmp_path, "Giải tích", files)

    assert "sensitive" not in str(error.value)
    assert manifest.read_bytes() == before
    assert set(tmp_path.glob("*.pdf")) == paths


def test_simultaneous_uploads_preserve_both_courses(tmp_path):
    files = [("notes.pdf", pdf_bytes("Algebra and matrices"))]

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(add_course, tmp_path, "Đại số", files)
        second = executor.submit(add_course, tmp_path, "Giải tích", files)
        uploaded_ids = {first.result(), second.result()}

    assert uploaded_ids <= {course.course_id for course in ChatbotService(tmp_path, private=True).courses()}
