import csv
import unicodedata
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, replace
from hashlib import sha256
from io import StringIO
from pathlib import Path
from threading import Lock

import pymupdf
from scipy.sparse import spmatrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.schemas import Document, Source


MANIFEST_COLUMNS = ("course_id", "document_id", "document_name", "path", "license")
PDF_LOCK = Lock()
_CHUNK_WORDS = 135


@dataclass(frozen=True)
class _IndexedCourse:
    documents: tuple[Document, ...]
    chunks: tuple[Source, ...]
    vectorizer: TfidfVectorizer
    matrix: spmatrix


class CourseIndex:
    def __init__(self, data_dir: Path, *, private: bool = False):
        issues: list[str] = []
        documents: dict[str, list[Document]] = defaultdict(list)
        chunks: dict[str, list[Source]] = defaultdict(list)
        seen_ids: set[tuple[str, str]] = set()
        self.course_names: dict[str, str] = {}

        allowed_license = "local_only" if private else "project_demo"
        for line, course_id, course_name, document in _manifest_documents(data_dir.resolve(), allowed_license, issues):
            key = (course_id, document.document_id)
            if key in seen_ids:
                issues.append(f"Dòng {line}: mã tài liệu bị trùng trong học phần.")
                continue
            try:
                pdf_bytes = document.path.read_bytes()
                document = replace(document, sha256=sha256(pdf_bytes).hexdigest())
                document_chunks = tuple(pdf_chunks(document, pdf_bytes, sort=not private))
            except (OSError, RuntimeError, ValueError):
                issues.append(f"Dòng {line}: không đọc được tệp PDF.")
                continue
            if not document_chunks:
                issues.append(f"Dòng {line}: PDF không có văn bản để tra cứu.")
                continue
            seen_ids.add(key)
            if course_name:
                self.course_names.setdefault(course_id, course_name)
            documents[course_id].append(document)
            chunks[course_id].extend(document_chunks)

        self.issues = tuple(issues)
        self._courses: dict[str, _IndexedCourse] = {}
        for course_id, course_chunks in chunks.items():
            vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), preprocessor=normalize_search_text)
            matrix = vectorizer.fit_transform(
                chunk.excerpt + " " + " ".join(chunk.excerpt.split()[:30]) for chunk in course_chunks
            )
            self._courses[course_id] = _IndexedCourse(
                tuple(documents[course_id]), tuple(course_chunks), vectorizer, matrix
            )

    def documents(self, course_id: str) -> tuple[Document, ...]:
        course = self._courses.get(course_id)
        return course.documents if course else ()

    def search(self, course_id: str, question: str, limit: int = 3) -> tuple[Source, ...]:
        course = self._courses.get(course_id)
        if not course or limit <= 0:
            return ()
        import re
        query_text = re.sub(
            r"^(?:tìm\s+(?:kiếm\s+|hiểu\s+)?(?:trang\s+(?:về\s+)?)?|tìm\s+trang\s+(?:về\s+)?|cho\s+(?:tôi|mình)?\s*biết\s+)",
            "",
            question,
            flags=re.IGNORECASE,
        ).strip() or question
        query = course.vectorizer.transform([query_text])
        scores = cosine_similarity(query, course.matrix)[0]
        ranked = sorted(enumerate(scores), key=lambda item: -item[1])
        return tuple(
            replace(course.chunks[index], score=min(float(score), 1.0))
            for index, score in ranked[:limit]
            if score > 0
        )


def read_manifest(manifest: Path) -> csv.DictReader:
    with manifest.open(encoding="utf-8-sig", newline="") as file:
        contents = file.read()
    rows = csv.DictReader(StringIO(contents, newline=""), strict=True)
    columns = rows.fieldnames or []
    expected = set(MANIFEST_COLUMNS)
    if len(columns) != len(set(columns)) or set(columns) not in (expected, expected | {"course_name"}):
        raise ValueError("Invalid manifest columns")
    return rows


def valid_manifest_row(row: dict) -> bool:
    return None not in row and all(row.get(column) and row[column].strip() for column in MANIFEST_COLUMNS)


def _manifest_documents(
    data_dir: Path, allowed_license: str, issues: list[str]
) -> Iterator[tuple[int, str, str, Document]]:
    try:
        private_dir = (data_dir / "local_course_pdfs").resolve() if allowed_license == "project_demo" else None
        manifest = (data_dir / "manifest.csv").resolve()
        if not manifest.is_relative_to(data_dir) or not manifest.is_file():
            issues.append("Không tìm thấy manifest.csv hợp lệ trong thư mục học liệu.")
            return
        rows = read_manifest(manifest)
        for row in rows:
            line = rows.line_num
            if not valid_manifest_row(row):
                issues.append(f"Dòng {line}: dữ liệu danh mục học liệu không hợp lệ.")
                continue
            if row["license"].strip() != allowed_license:
                issues.append(f"Dòng {line}: quyền sử dụng tài liệu không khớp kho học liệu.")
                continue
            path = _pdf_path(data_dir, row["path"].strip())
            if path is None:
                issues.append(f"Dòng {line}: đường dẫn PDF không hợp lệ hoặc tệp không tồn tại.")
                continue
            if private_dir is not None and path.is_relative_to(private_dir):
                issues.append(f"Dòng {line}: kho demo không được dùng PDF thuộc kho riêng.")
                continue
            yield line, row["course_id"].strip(), (row.get("course_name") or "").strip(), Document(
                document_id=row["document_id"].strip(),
                document_name=row["document_name"].strip(),
                path=path,
                license=allowed_license,
            )
    except (OSError, RuntimeError, UnicodeError, csv.Error):
        issues.append("Không đọc được manifest.csv hoặc tệp có định dạng CSV không hợp lệ.")
    except ValueError:
        issues.append("manifest.csv thiếu cột bắt buộc hoặc có cột không hợp lệ.")


def _pdf_path(data_dir: Path, value: str) -> Path | None:
    relative_path = Path(value)
    if relative_path.anchor or relative_path.suffix.lower() != ".pdf":
        return None
    try:
        path = (data_dir / relative_path).resolve()
        if path.is_relative_to(data_dir) and path.suffix.lower() == ".pdf" and path.is_file():
            return path
    except (OSError, RuntimeError, ValueError):
        return None
    return None


def pdf_chunks(document: Document, pdf_bytes: bytes, *, sort: bool) -> Iterator[Source]:
    with PDF_LOCK, pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        if not pdf.is_pdf or pdf.is_repaired or pdf.needs_pass:
            raise ValueError("PDF is invalid or requires a password")
        for page_number, page in enumerate(pdf, start=1):
            words = page.get_text(sort=sort).split()
            for start in range(0, len(words), _CHUNK_WORDS):
                excerpt = " ".join(words[start : start + _CHUNK_WORDS])
                if len(normalize_search_text(excerpt)) < 3:
                    continue
                chunk_number = start // _CHUNK_WORDS + 1
                yield Source(
                    document_id=document.document_id,
                    document_name=document.document_name,
                    page=page_number,
                    chunk_id=f"{document.document_id}_p{page_number}_c{chunk_number:02}",
                    excerpt=excerpt,
                    score=0.0,
                    document_sha256=document.sha256,
                )


def normalize_search_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text).casefold().replace("đ", "d")
    decomposed = unicodedata.normalize("NFKD", normalized)
    return "".join(character for character in decomposed if not unicodedata.combining(character))
