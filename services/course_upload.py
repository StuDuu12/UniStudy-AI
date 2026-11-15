import csv
import os
import unicodedata
from collections.abc import Collection, Iterator, Sequence
from contextlib import contextmanager, suppress
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from services.chatbot_service import COURSES, PRIVATE_COURSES
from services.retrieval import MANIFEST_COLUMNS, pdf_chunks, read_manifest, valid_manifest_row
from src.schemas import Document


MAX_PDF_MB = 20
MAX_PDF_FILES = 5
MAX_COURSE_NAME_LENGTH = 100
LOCAL_LICENSE = "local_only"


class CourseUploadError(Exception):
    pass


class CourseNotFoundError(CourseUploadError):
    pass


def validate_course_name(course_name: str) -> str:
    name = _clean_name(course_name)
    if not name or len(name) > MAX_COURSE_NAME_LENGTH:
        raise CourseUploadError(f"Hãy nhập tên học phần từ 1 đến {MAX_COURSE_NAME_LENGTH} ký tự.")
    return name


def add_course(
    data_dir: Path, course_name: str, files: Sequence[tuple[str, bytes]], *,
    active_course_names: Collection[str] | None = None,
) -> str:
    return _save_upload(data_dir, files, name=validate_course_name(course_name), active_course_names=active_course_names)


def append_course_documents(data_dir: Path, course_id: str, files: Sequence[tuple[str, bytes]]) -> None:
    _save_upload(data_dir, files, course_id=course_id)


def _save_upload(
    data_dir: Path, files: Sequence[tuple[str, bytes]], *, name: str = "", course_id: str | None = None,
    active_course_names: Collection[str] | None = None,
) -> str:
    if not 1 <= len(files) <= MAX_PDF_FILES:
        raise CourseUploadError(f"Hãy chọn từ 1 đến {MAX_PDF_FILES} tệp PDF.")

    uploads = []
    for index, (filename, contents) in enumerate(files, start=1):
        display_name = _clean_name(filename.replace("\\", "/").rsplit("/", 1)[-1])
        if not display_name.lower().endswith(".pdf"):
            raise CourseUploadError(f"Tệp {index}: chỉ chấp nhận định dạng PDF.")
        if not contents or len(contents) > MAX_PDF_MB * 1024 * 1024:
            raise CourseUploadError(f"Tệp {index}: PDF phải có dữ liệu và không quá {MAX_PDF_MB} MB.")
        stem = "".join("_" if char in '<>:"|?*' else char for char in display_name[:-4])
        display_name = f"{stem[:116].strip(' .') or 'Học liệu'}.pdf"
        document_id = uuid4().hex
        document = Document(document_id, display_name, Path(f"{document_id}.pdf"), LOCAL_LICENSE)
        try:
            searchable = sum(1 for _ in pdf_chunks(document, contents, sort=False))
        except (OSError, RuntimeError, ValueError):
            raise CourseUploadError(f"Tệp {index}: không đọc được PDF hoặc PDF có mật khẩu.") from None
        if not searchable:
            raise CourseUploadError(f"Tệp {index}: PDF chưa có lớp văn bản để tra cứu.")
        uploads.append((document, contents))

    try:
        data_dir = data_dir.parent.resolve() / data_dir.name
        if data_dir.resolve() != data_dir:
            raise OSError("Invalid private directory")
        data_dir.mkdir(parents=True, exist_ok=True)
        with _manifest_lock(data_dir):
            manifest = data_dir / "manifest.csv"
            rows = _existing_rows(manifest)
            catalog = dict(COURSES + PRIVATE_COURSES)
            known_names = {builtin_name.casefold() for builtin_name in catalog.values()}
            for row in rows:
                existing_name = _clean_name(row.get("course_name") or "")
                if row["license"].strip() == LOCAL_LICENSE and existing_name:
                    catalog.setdefault(row["course_id"].strip(), existing_name)
                    known_names.add(existing_name.casefold())
            if course_id is None:
                if active_course_names is not None:
                    known_names = {active_name.casefold() for active_name in active_course_names}
                if name.casefold() in known_names:
                    raise CourseUploadError("Tên học phần này đã có. Hãy chọn tên khác.")
                course_id = f"course_{uuid4().hex}"
            else:
                if course_id not in catalog:
                    raise CourseNotFoundError("Học phần không tồn tại.")
                name = catalog[course_id]
            _store_course(manifest, rows, course_id, name, uploads)
    except (OSError, RuntimeError, ValueError, csv.Error):
        raise CourseUploadError("Chưa lưu được học phần. Hãy kiểm tra kho học liệu rồi thử lại.") from None
    return course_id


def _clean_name(value: str) -> str:
    cleaned = "".join(char for char in value if char.isspace() or not unicodedata.category(char).startswith("C"))
    return unicodedata.normalize("NFC", " ".join(cleaned.split()))


@contextmanager
def _manifest_lock(data_dir: Path) -> Iterator[None]:
    lock_path = data_dir / ".upload.lock"
    if lock_path.resolve() != lock_path:
        raise OSError("Invalid lock file")
    with lock_path.open("a+b") as lock_file:
        if os.name == "nt":
            import msvcrt

            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file, fcntl.LOCK_EX)
        yield


def _existing_rows(manifest: Path) -> list[dict]:
    if manifest.resolve() != manifest:
        raise OSError("Invalid manifest path")
    try:
        rows = list(read_manifest(manifest))
    except FileNotFoundError:
        return []
    if not all(valid_manifest_row(row) for row in rows):
        raise ValueError("Invalid manifest rows")
    return rows


def _store_course(
    manifest: Path, rows: list[dict], course_id: str, name: str, uploads: list[tuple[Document, bytes]]
) -> None:
    created: list[Path] = []
    try:
        for document, contents in uploads:
            path = manifest.parent / document.path
            with path.open("xb") as file:
                created.append(path)
                file.write(contents)
                file.flush()
                os.fsync(file.fileno())
            rows.append({
                "course_id": course_id,
                "document_id": document.document_id,
                "document_name": document.document_name,
                "path": document.path.name,
                "license": document.license,
                "course_name": name,
            })

        with NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=manifest.parent, delete=False
        ) as file:
            staged = Path(file.name)
            created.append(staged)
            writer = csv.DictWriter(file, fieldnames=(*MANIFEST_COLUMNS, "course_name"))
            writer.writeheader()
            writer.writerows(rows)
            file.flush()
            os.fsync(file.fileno())
        staged.replace(manifest)
    except (OSError, ValueError, csv.Error):
        for path in created:
            with suppress(OSError):
                path.unlink(missing_ok=True)
        raise
