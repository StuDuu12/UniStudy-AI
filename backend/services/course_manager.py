import csv
import os
import re
from collections import defaultdict
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from time import time_ns

from pydantic import TypeAdapter, ValidationError

from backend.schemas.chat import (
    ChatMode,
    ChatResponse,
    ChatStatus,
    ConversationModel,
    CourseItem,
    DocumentItem,
    MessageModel,
    SourceItem,
)
from backend.services.evidence import EVIDENCE_THRESHOLD, normalize_text, retrieval_query
from backend.services.ingest import ChunkSource, DocumentInfo, extract_pdf_chunks, get_pdf_page_count
from backend.services.llm_service import AIConfig, AIUnavailable
from backend.services.pdf_text import readable_pdf_text
from backend.services.query import query_parts
from backend.services.retrieval import CourseRetriever
from services.course_upload import CourseUploadError, add_course, append_course_documents
from services.retrieval import read_manifest, valid_manifest_row


COURSE_DISPLAY_NAMES = {
    "tin_hoc_dai_cuong": "Tin học đại cương",
    "software_testing": "Kiểm thử phần mềm",
    "algorithm_analysis": "Phân tích thuật toán",
    "toan_roi_rac": "Toán rời rạc",
    "thu_thap_phan_tich_yeu_cau": "Thu thập và phân tích yêu cầu",
}

COURSE_SUGGESTED_QUESTIONS = {
    "tin_hoc_dai_cuong": [
        "Hệ điều hành có những chức năng gì?",
        "Cấu trúc cơ bản của máy tính gồm những thành phần nào?",
        "Phần mềm hệ thống khác phần mềm ứng dụng ở điểm nào?",
        "Các thao tác định dạng văn bản cơ bản trong Word là gì?",
    ],
    "software_testing": [
        "Phân vùng tương đương là gì?",
        "Phân vùng tương đương khác phân tích giá trị biên ở đâu?",
        "Một ca kiểm thử hộp đen cần ghi những thông tin nào?",
        "Nên thử những giá trị biên nào cho ô điểm nguyên từ 0 đến 100?",
    ],
    "algorithm_analysis": [
        "Big O là gì và biểu diễn cận trên như thế nào?",
        "Quy tắc tuần tự khi phân tích thời gian tính là gì?",
        "Trường hợp cơ sở có vai trò gì trong hệ thức truy hồi của đệ quy?",
        "Vì sao sắp xếp trộn có độ phức tạp O(n log n)?",
    ],
    "toan_roi_rac": [
        "Định nghĩa mệnh đề trong logic mệnh đề là gì?",
        "Các phép toán tập hợp cơ bản gồm những phép toán nào?",
        "Đại số Boole có những tính chất và tiên đề cơ bản nào?",
        "Định nghĩa đồ thị liên thông và đường đi Euler?",
    ],
    "thu_thap_phan_tich_yeu_cau": [
        "Yêu cầu chức năng khác yêu cầu phi chức năng như thế nào?",
        "Các kỹ thuật phổ biến để khám phá yêu cầu phần mềm?",
        "Biểu đồ Use Case dùng để mô hình hóa khía cạnh nào của hệ thống?",
        "Tại sao cần tài liệu hóa yêu cầu bằng ngôn ngữ tự nhiên rõ ràng?",
    ],
}

_AI_ISSUES = {
    "credentials": "Dịch vụ AI từ chối khóa hoặc quyền truy cập. Hãy kiểm tra cấu hình AI.",
    "model": "Model AI đã cấu hình chưa khả dụng với tài khoản này.",
    "quota": "Dịch vụ AI đang giới hạn số lượt gọi hoặc hạn mức của tài khoản.",
    "format": "AI trả phản hồi chưa đúng định dạng hoặc trích dẫn không hợp lệ.",
    "network": "Kết nối tới AI bị gián đoạn hoặc quá thời gian chờ.",
}


def _source_item(source: ChunkSource) -> SourceItem:
    return SourceItem(
        chunk_id=source.chunk_id,
        document_id=source.document_id,
        document_name=source.document_name,
        page=source.page,
        excerpt=readable_pdf_text(source.excerpt),
        score=round(source.score, 3) if source.score else None,
        document_sha256=source.document_sha256,
    )


@dataclass(frozen=True)
class _Catalog:
    courses: dict[str, CourseItem]
    documents: dict[str, list[DocumentItem]]
    document_map: dict[str, DocumentInfo]
    retrievers: dict[str, CourseRetriever]


class ConversationConflict(Exception):
    pass


class ConversationStorageError(Exception):
    pass


_CONVERSATIONS = TypeAdapter(list[ConversationModel])


def _merge_messages(persisted: list[MessageModel], incoming: list[MessageModel]) -> list[MessageModel]:
    by_id: dict[str, MessageModel] = {}
    for branch in (persisted, incoming):
        pending_question = None
        for message in branch:
            if message.sender == "user":
                pending_question = message.id
            else:
                reply_to = message.reply_to or pending_question
                message = message.model_copy(update={"reply_to": reply_to})
                if reply_to == pending_question:
                    pending_question = None
            by_id.setdefault(message.id, message)

    turns = []
    replies: dict[str, list[MessageModel]] = defaultdict(list)
    for message in sorted(by_id.values(), key=lambda item: item.created_at or 0):
        parent = by_id.get(message.reply_to) if message.reply_to else None
        if message.sender == "assistant" and parent and parent.sender == "user":
            replies[parent.id].append(message)
        else:
            turns.append(message)
    return [message for turn in turns for message in (turn, *replies[turn.id])]


class CourseManager:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.data_dir = (project_root / "data").resolve()
        self.local_dir = self.data_dir / "local_course_pdfs"
        self._upload_lock = Lock()
        self._conversation_lock = Lock()
        self._catalog = self._load_catalog()
        self._ai = AIConfig.load(self.project_root / ".env")

    def _synthesize_answer(self, sources: list[ChunkSource], *, multipart: bool) -> str:
        excerpts = [
            f"Theo giáo trình **{source.document_name}** (Trang {source.page}):\n\n> {source.excerpt}"
            for source in (sources if multipart else sources[:1])
        ]
        if multipart:
            excerpts.insert(0, "Các đoạn liên quan dưới đây có thể chưa bao phủ mọi ý trong câu hỏi.")
        return "\n\n".join(excerpts)

    def _lookup_sources(
        self, retriever: CourseRetriever, query: str, *, contextual: bool = False, limit: int | None = None
    ) -> list[ChunkSource]:
        direct_limit = limit
        if direct_limit is None:
            part_count = 1 if contextual else len(query_parts(query))
            direct_limit = min(6, max(3, part_count))
            if re.search(r"\b(?:gom|nhung phep|cac phep|tinh chat|tien de)\b", normalize_text(query)):
                direct_limit = 6
        sources = retriever.search(query, direct_limit, minimum_score=EVIDENCE_THRESHOLD, contextual=contextual)
        if limit is not None or direct_limit != 6:
            return sources

        # A numbered section or list may span several pages of the same PDF.
        anchors = sources[:3]
        seen = {source.chunk_id for source in sources}
        for same_heading in (True, False):
            for anchor in anchors:
                if same_heading and not re.match(r"^\d+\.\s", anchor.heading):
                    continue
                for candidate in retriever.chunks:
                    if candidate.document_id != anchor.document_id or candidate.chunk_id in seen:
                        continue
                    matches = (
                        candidate.heading == anchor.heading if same_heading else abs(candidate.page - anchor.page) == 1
                    )
                    if matches:
                        sources.append(replace(candidate, score=0.0))
                        seen.add(candidate.chunk_id)
                        if len(sources) == 12:
                            return sources
        return sources

    def _load_catalog(self) -> _Catalog:
        names = dict(COURSE_DISPLAY_NAMES)
        documents: dict[str, list[DocumentInfo]] = defaultdict(list)
        chunks: dict[str, list[ChunkSource]] = defaultdict(list)
        document_map: dict[str, DocumentInfo] = {}

        for base_dir, license_type in ((self.data_dir, "project_demo"), (self.local_dir, "local_only")):
            manifest = base_dir / "manifest.csv"
            try:
                if base_dir.resolve() != base_dir or manifest.resolve() != manifest:
                    continue
                for row in read_manifest(manifest):
                    if not valid_manifest_row(row) or row["license"].strip() != license_type:
                        continue
                    course_id = row["course_id"].strip()
                    name = (row.get("course_name") or "").strip()
                    if course_id not in names and (license_type != "local_only" or not name):
                        continue
                    names.setdefault(course_id, name)
                    document_id = row["document_id"].strip()
                    if document_id in document_map:
                        continue
                    loaded = self._load_document(base_dir, row)
                    if loaded is None:
                        continue
                    document, excerpts = loaded
                    documents[course_id].append(document)
                    chunks[course_id].extend(excerpts)
                    document_map[document_id] = document
            except (OSError, RuntimeError, ValueError, csv.Error):
                continue

        courses = {
            course_id: CourseItem(
                course_id=course_id,
                course_name=name,
                document_count=len(documents[course_id]),
                status="ready" if documents[course_id] else "empty",
                suggested_questions=COURSE_SUGGESTED_QUESTIONS.get(course_id, []),
            )
            for course_id, name in names.items()
        }
        document_lists = {
            course_id: [
                DocumentItem(document_id=doc.document_id, document_name=doc.document_name, page_count=doc.page_count)
                for doc in course_documents
            ]
            for course_id, course_documents in documents.items()
        }
        retrievers = {
            course_id: CourseRetriever(course_id, documents[course_id], excerpts)
            for course_id, excerpts in chunks.items()
            if excerpts
        }
        return _Catalog(courses, document_lists, document_map, retrievers)

    def _load_document(self, base_dir: Path, row: dict) -> tuple[DocumentInfo, list[ChunkSource]] | None:
        relative = Path(row["path"].strip())
        if relative.anchor or relative.suffix.lower() != ".pdf":
            return None
        try:
            path = (base_dir / relative).resolve()
            if not path.is_relative_to(base_dir) or path.suffix.lower() != ".pdf" or not path.is_file():
                return None
            if base_dir == self.data_dir and path.is_relative_to(self.local_dir.resolve()):
                return None
            pdf_bytes = path.read_bytes()
            page_count = get_pdf_page_count(pdf_bytes)
            if not page_count:
                return None
            document = DocumentInfo(
                document_id=row["document_id"].strip(),
                document_name=row["document_name"].strip(),
                path=path,
                license=row["license"].strip(),
                page_count=page_count,
                sha256=sha256(pdf_bytes).hexdigest(),
            )
            return document, list(extract_pdf_chunks(document, pdf_bytes, sort=True))
        except (OSError, RuntimeError, ValueError):
            return None

    def add_course(self, name: str, files: Sequence[tuple[str, bytes]]) -> CourseItem:
        with self._upload_lock:
            course_id = add_course(self.local_dir, name, files)
            self._catalog = self._load_catalog()
            course = self._catalog.courses.get(course_id)
            if course is None:
                raise CourseUploadError("Đã lưu học liệu nhưng chưa thể mở học phần. Hãy tải lại trang.")
            return course

    def append_documents(self, course_id: str, files: Sequence[tuple[str, bytes]]) -> list[DocumentItem]:
        with self._upload_lock:
            append_course_documents(self.local_dir, course_id, files)
            self._catalog = self._load_catalog()
            return self._catalog.documents[course_id]

    def list_courses(self) -> list[CourseItem]:
        return list(self._catalog.courses.values())

    def get_course_documents(self, course_id: str) -> list[DocumentItem] | None:
        return self._catalog.documents.get(course_id)

    def get_document_info(self, document_id: str) -> DocumentInfo | None:
        return self._catalog.document_map.get(document_id)

    def get_conversations(self, course_id: str | None = None) -> list[ConversationModel]:
        with self._conversation_lock:
            data = self._read_conversations()
        data.sort(key=lambda item: item.updated_at, reverse=True)
        if course_id:
            return [c for c in data if c.course_id == course_id]
        return data

    def save_conversation(self, conversation: ConversationModel) -> ConversationModel:
        with self._conversation_lock:
            data = self._read_conversations()
            index = next((i for i, c in enumerate(data) if c.id == conversation.id), None)
            if index is not None:
                persisted = data[index]
                if persisted.course_id != conversation.course_id:
                    raise ConversationConflict
                latest = conversation if conversation.updated_at > persisted.updated_at else persisted
                conversation = latest.model_copy(update={
                    "title": persisted.title if persisted.title_version > 0 else latest.title,
                    "title_version": persisted.title_version,
                    "messages": _merge_messages(persisted.messages, conversation.messages),
                })
                data[index] = conversation
            else:
                conversation = conversation.model_copy(update={
                    "title_version": 0,
                    "messages": _merge_messages([], conversation.messages),
                })
                data.insert(0, conversation)
            self._write_conversations(data)
            return conversation

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._conversation_lock:
            data = self._read_conversations()
            new_data = [c for c in data if c.id != conversation_id]
            if len(new_data) != len(data):
                self._write_conversations(new_data)
                return True
            return False

    def rename_conversation(self, conversation_id: str, new_title: str) -> ConversationModel | None:
        title = new_title.strip()
        with self._conversation_lock:
            data = self._read_conversations()
            for index, persisted in enumerate(data):
                if persisted.id != conversation_id:
                    continue
                updated = persisted.model_copy(update={
                    "title": title,
                    "title_version": max(persisted.title_version + 1, time_ns() // 1_000_000),
                })
                data[index] = updated
                self._write_conversations(data)
                return updated
            return None

    def _read_conversations(self) -> list[ConversationModel]:
        file_path = self.data_dir / "conversations.json"
        try:
            return _CONVERSATIONS.validate_json(file_path.read_bytes())
        except FileNotFoundError:
            return []
        except (OSError, ValidationError):
            raise ConversationStorageError from None

    def _write_conversations(self, data: list[ConversationModel]) -> None:
        file_path = self.data_dir / "conversations.json"
        staged = None
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(dir=self.data_dir, delete=False) as file:
                staged = Path(file.name)
                file.write(_CONVERSATIONS.dump_json(data, indent=2))
                file.flush()
                os.fsync(file.fileno())
            staged.replace(file_path)
        except OSError:
            raise ConversationStorageError from None
        finally:
            if staged is not None:
                with suppress(OSError):
                    staged.unlink(missing_ok=True)

    def answer_question(
        self, course_id: str, question: str, previous_questions: Sequence[str] = ()
    ) -> ChatResponse:
        def notice(status: ChatStatus, message: str) -> ChatResponse:
            return ChatResponse(status=status, answer="", mode="lookup", message=message)

        catalog = self._catalog
        if course_id not in catalog.courses:
            return notice("error", "Học phần không tồn tại.")
        if not any(character.isalpha() for character in question):
            return notice("invalid_input", "Vui lòng nhập câu hỏi.")
        if not catalog.documents[course_id]:
            return notice("no_documents", "Học phần này chưa có tài liệu khả dụng.")
        resolved = retrieval_query(question, previous_questions)
        if resolved is None:
            return notice("needs_clarification", "Bạn có thể nêu rõ khái niệm hoặc bài đang muốn hỏi không?")
        query, context_question = resolved
        contextual = query != context_question

        retriever = catalog.retrievers.get(course_id)
        if retriever is None:
            return notice("no_documents", "Chưa có dữ liệu tìm kiếm cho học phần này.")
        sources = self._lookup_sources(retriever, query, contextual=contextual)
        if not sources:
            return notice("insufficient_evidence", "Chưa tìm thấy căn cứ đủ phù hợp trong tài liệu đã nạp.")

        status: ChatStatus = "success"
        mode: ChatMode = "lookup"
        message = None
        if self._ai:
            mode = "ai"
            evidence = sources
            if not getattr(self._ai, "is_local", False):
                # Keep adjacent uploaded passages available for lookup and loopback AI.
                local_document_ids = {
                    document.document_id for document in retriever.documents if document.license == "local_only"
                }
                evidence = [
                    source for source in sources if source.score > 0 or source.document_id not in local_document_ids
                ]
            try:
                answer, cited = self._ai.explain(query, evidence)
                if answer:
                    cited_ids = {source.chunk_id for source in cited}
                    if not cited_ids or not cited_ids <= {source.chunk_id for source in evidence}:
                        raise ValueError("Invalid answer citations")
                    sources = [source for source in sources if source.chunk_id in cited_ids]
                else:
                    status = "insufficient_evidence"
                    message = (
                        "AI chưa xác nhận đủ căn cứ cho câu hỏi. "
                        "Bạn có thể đối chiếu các đoạn liên quan bên dưới hoặc hỏi cụ thể hơn."
                    )
            except (AIUnavailable, ValueError) as error:
                reason = error.reason if isinstance(error, AIUnavailable) else "format"
                status = "ai_unavailable"
                answer = ""
                message = _AI_ISSUES.get(reason, "Dịch vụ AI tạm thời không phản hồi.")
                message += " Bạn vẫn có thể xem các nguồn PDF đã tìm được bên dưới."
        else:
            answer = self._synthesize_answer(sources, multipart=not contextual and len(query_parts(query)) > 1)

        return ChatResponse(
            status=status,
            answer=readable_pdf_text(answer),
            mode=mode,
            context_question=context_question,
            message=message,
            sources=[_source_item(source) for source in sources],
        )
