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

from pydantic import TypeAdapter, ValidationError

from backend.schemas.chat import (
    AnswerStyle,
    ChatResponse,
    ChatMode,
    ChatStatus,
    ConversationModel,
    CourseItem,
    DocumentItem,
    MessageModel,
    SourceItem,
)
from backend.services.evidence import EVIDENCE_THRESHOLD, retrieval_query
from backend.services.ingest import (
    ChunkSource, DocumentInfo, extract_pdf_chunks, get_pdf_page_count, render_pdf_page_image,
)
from backend.services.retrieval import CourseRetriever
from backend.services.llm_service import AIConfig, AIUnavailable, get_provider_config
from backend.services.query import query_parts
from backend.services.pdf_text import format_academic_document_content, readable_pdf_text
from services.course_upload import (
    CourseNotFoundError, CourseUploadError, add_course, append_course_documents, validate_course_name,
)
from services.retrieval import read_manifest, valid_manifest_row


def format_math_latex(text: str) -> str:
    """Normalize extracted or AI-generated math symbols and expressions to standard LaTeX."""
    replacements = {
        "\uf0c6": r"$\emptyset$",
        "\uf0cd": r"$\subseteq$",
        "\uf0cc": r"$\subset$",
        "\uf0ce": r"$\in$",
        "\uf0c7": r"$\cap$",
        "\uf0c8": r"$\cup$",
        "\uf0d8": r"$\vee$",
        "\uf0d9": r"$\wedge$",
        "\uf0ac": r"$\neg$",
        "\uf0de": r"$\Rightarrow$",
        "\uf0db": r"$\Leftrightarrow$",
        "∅": r"$\emptyset$",
        "⊆": r"$\subseteq$",
        "⊂": r"$\subset$",
        "∈": r"$\in$",
        "∩": r"$\cap$",
        "∪": r"$\cup$",
        "≤": r"$\le$",
        "≥": r"$\ge$",
        "≠": r"$\ne$",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # 2^|S| or 2|S| -> $2^{|S|}$
    text = re.sub(r"(?<!\$)\b2\^\|S\|(?!\$)", r"$2^{|S|}$", text)
    text = re.sub(r"(bằng|là|bằng\s+với)\s+2\|S\|", r"\1 $2^{|S|}$", text)
    text = re.sub(r"(?<!\$)\b2\^([0-9a-zA-Z]+)\s*=\s*([0-9]+)(?!\$)", r"$2^{\1} = \2$", text)
    # Power set P(S) -> $\mathcal{P}(S)$
    text = re.sub(r"(?<!\$)\bP\(([A-Z])\)(?!\$)", r"$\\mathcal{P}(\1)$", text)
    # Clean up double wrapping
    text = re.sub(r"\${2,}([^$]+)\${2,}", r"$\1$", text)
    return text


def clean_excerpt_symbols(text: str) -> str:
    """Clean broken private-use glyphs in excerpts so they display as standard unicode."""
    replacements = {
        "\uf0c6": "∅",
        "\uf0cd": "⊆",
        "\uf0cc": "⊂",
        "\uf0ce": "∈",
        "\uf0c7": "∩",
        "\uf0c8": "∪",
        "\uf0d8": "∨",
        "\uf0d9": "∧",
        "\uf0ac": "¬",
        "\uf0de": "⇒",
        "\uf0db": "⇔",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


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
        "Hai vòng lặp độc lập chạy nối tiếp thì cộng hay nhân chi phí?",
        "Trường hợp cơ sở có vai trò gì trong hệ thức truy hồi của đệ quy?",
        "Vì sao sắp xếp trộn có độ phức tạp O(n log n)?",
    ],
    "toan_roi_rac": [
        "Mệnh đề là gì?",
        "Tập hợp là gì?",
        "Phép hợp và phép giao là gì?",
        "Đường một nét Euler là gì?",
    ],
    "thu_thap_phan_tich_yeu_cau": [
        "Yêu cầu chức năng khác yêu cầu phi chức năng như thế nào?",
        "Các kỹ thuật phổ biến để khám phá yêu cầu phần mềm?",
        "Biểu đồ Use Case dùng để mô hình hóa khía cạnh nào của hệ thống?",
        "Tài liệu hóa yêu cầu bằng ngôn ngữ tự nhiên có ưu điểm gì?",
    ],
}


def _selected_page_images(sources: Sequence[ChunkSource], documents: dict[str, DocumentInfo]) -> dict[str, bytes]:
    images = {}
    seen = set()
    for source in sources:
        page_key = (source.document_id, source.page)
        if not source.has_visual_content or page_key in seen:
            continue
        seen.add(page_key)
        document = documents.get(source.document_id)
        if document is None or document.sha256 != source.document_sha256:
            continue
        try:
            pdf = document.path.read_bytes()
            if sha256(pdf).hexdigest() != document.sha256:
                continue
            image = render_pdf_page_image(pdf, source.page, max_edge=1200)
        except (OSError, RuntimeError, ValueError):
            continue
        if len(image) <= 500_000:
            images[source.chunk_id] = image
            if len(images) == 2:
                break
    return images


def source_item(source: ChunkSource) -> SourceItem:
    formatted = format_academic_document_content(source.formatted_excerpt or source.excerpt) if (source.formatted_excerpt or source.excerpt) else None
    return SourceItem(
        chunk_id=source.chunk_id, document_id=source.document_id,
        document_name=source.document_name, page=source.page,
        excerpt=readable_pdf_text(source.excerpt),
        score=round(source.score, 3) if source.score else None,
        document_sha256=source.document_sha256,
        formatted_excerpt=formatted,
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


class CourseCatalogStorageError(Exception):
    pass


_CONVERSATIONS = TypeAdapter(list[ConversationModel])
_COURSE_OVERRIDES = TypeAdapter(dict[str, str | None])


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
        self._course_overrides = self._read_course_overrides()
        self._catalog = self._load_catalog()
        self._ai = AIConfig.load(self.project_root / ".env")

    def _synthesize_answer(self, query: str, sources: list[ChunkSource]) -> str:
        if not sources:
            return "Đã tìm thấy các đoạn học liệu liên quan."
        selected = sources if len(query_parts(query)) > 1 else sources[:1]
        sections = []
        for s in selected:
            structured = format_academic_document_content(s.formatted_excerpt or s.excerpt)
            sections.append(f"Theo giáo trình **{s.document_name}** (Trang {s.page}):\n\n{structured}")
        prefix = "Dưới đây là nội dung trích xuất từ giáo trình đối chiếu với câu hỏi:\n\n" if len(sections) > 1 else ""
        return prefix + "\n\n---\n\n".join(sections)

    def _load_catalog(self) -> _Catalog:
        names = {course_id: name for course_id, name in COURSE_DISPLAY_NAMES.items()
                 if self._course_overrides.get(course_id, name) is not None}
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
                    if self._course_overrides.get(course_id, name) is None:
                        continue
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
                course_name=self._course_overrides.get(course_id) or name,
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
            course_id = add_course(
                self.local_dir, name, files,
                active_course_names=[course.course_name for course in self._catalog.courses.values()],
            )
            self._catalog = self._load_catalog()
            course = self._catalog.courses.get(course_id)
            if course is None:
                raise CourseUploadError("Đã lưu học liệu nhưng chưa thể mở học phần. Hãy tải lại trang.")
            return course

    def append_documents(self, course_id: str, files: Sequence[tuple[str, bytes]]) -> list[DocumentItem]:
        with self._upload_lock:
            if course_id not in self._catalog.courses:
                raise CourseNotFoundError("Học phần không tồn tại.")
            append_course_documents(self.local_dir, course_id, files)
            self._catalog = self._load_catalog()
            return self._catalog.documents[course_id]

    def rename_course(self, course_id: str, course_name: str) -> CourseItem:
        with self._upload_lock:
            catalog = self._catalog
            course = catalog.courses.get(course_id)
            if course is None:
                raise CourseNotFoundError("Học phần không tồn tại.")
            name = validate_course_name(course_name)
            if any(other.course_id != course_id and other.course_name.casefold() == name.casefold()
                   for other in catalog.courses.values()):
                raise CourseUploadError("Tên học phần này đã có. Hãy chọn tên khác.")
            updated = course.model_copy(update={"course_name": name})
            self._write_course_overrides({**self._course_overrides, course_id: name})
            self._catalog = replace(catalog, courses={**catalog.courses, course_id: updated})
            return updated

    def delete_course(self, course_id: str) -> None:
        with self._upload_lock:
            catalog = self._catalog
            if course_id not in catalog.courses:
                raise CourseNotFoundError("Học phần không tồn tại.")
            courses = catalog.courses.copy()
            documents = catalog.documents.copy()
            document_map = catalog.document_map.copy()
            retrievers = catalog.retrievers.copy()
            courses.pop(course_id)
            for document in documents.pop(course_id, []):
                document_map.pop(document.document_id, None)
            retrievers.pop(course_id, None)
            # A null override keeps the course out of future catalog loads.
            self._write_course_overrides({**self._course_overrides, course_id: None})
            self._catalog = _Catalog(courses, documents, document_map, retrievers)

    def _read_course_overrides(self) -> dict[str, str | None]:
        path = self.data_dir / "course_overrides.json"
        try:
            if path.resolve() != path:
                raise OSError("Invalid course metadata path")
            return _COURSE_OVERRIDES.validate_json(path.read_bytes())
        except FileNotFoundError:
            return {}
        except (OSError, ValidationError):
            raise CourseCatalogStorageError("Không thể đọc thông tin học phần đã lưu.") from None

    def _write_course_overrides(self, overrides: dict[str, str | None]) -> None:
        path = self.data_dir / "course_overrides.json"
        staged = None
        try:
            if path.resolve() != path:
                raise OSError("Invalid course metadata path")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(dir=self.data_dir, delete=False) as file:
                staged = Path(file.name)
                file.write(_COURSE_OVERRIDES.dump_json(overrides, indent=2))
                file.flush()
                os.fsync(file.fileno())
            staged.replace(path)
        except OSError:
            raise CourseCatalogStorageError("Không thể lưu thay đổi học phần.") from None
        finally:
            if staged is not None:
                with suppress(OSError):
                    staged.unlink(missing_ok=True)
        self._course_overrides = overrides

    def list_courses(self) -> list[CourseItem]:
        return list(self._catalog.courses.values())

    def get_course_documents(self, course_id: str) -> list[DocumentItem] | None:
        return self._catalog.documents.get(course_id)

    def get_document_info(self, document_id: str) -> DocumentInfo | None:
        return self._catalog.document_map.get(document_id)

    def get_formatted_excerpt(self, document_id: str, page: int, chunk_id: str, digest: str) -> str | None:
        for retriever in self._catalog.retrievers.values():
            for chunk in retriever.chunks:
                if (chunk.document_id, chunk.page, chunk.chunk_id, chunk.document_sha256) == (
                    document_id, page, chunk_id, digest
                ):
                    return chunk.formatted_excerpt or None
        return None

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
                conversation = latest.model_copy(update={"messages": _merge_messages(persisted.messages, conversation.messages)})
                data[index] = conversation
            else:
                conversation = conversation.model_copy(update={"messages": _merge_messages([], conversation.messages)})
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
        title = new_title.strip() or new_title
        with self._conversation_lock:
            data = self._read_conversations()
            index = next((i for i, c in enumerate(data) if c.id == conversation_id), None)
            if index is None:
                return None
            updated = data[index].model_copy(update={"title": title})
            data[index] = updated
            self._write_conversations(data)
            return updated

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
        self,
        course_id: str,
        question: str,
        previous_questions: Sequence[str] = (),
        model_provider: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
        answer_style: AnswerStyle = "auto",
    ) -> ChatResponse:
        def notice(status: ChatStatus, message: str) -> ChatResponse:
            return ChatResponse(
                status=status,
                answer="",
                mode="lookup",
                message=message,
                model_name=model_name,
                model_provider=model_provider,
            )

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

        retriever = catalog.retrievers.get(course_id)
        if retriever is None:
            return notice("no_documents", "Chưa có dữ liệu tìm kiếm cho học phần này.")
        ai_config, error_reason = get_provider_config(model_provider, api_key, self._ai, model_name=model_name)
        prior_topic = context_question if context_question != question.strip() else None
        retrieval_text = prior_topic or query
        limit = min(6, max(3, len(query_parts(retrieval_text))))
        concepts = []
        if isinstance(ai_config, AIConfig) and ai_config.supports_rag_enrichment and len(question.split()) >= 10:
            try:
                concepts = ai_config.search_terms(question, catalog.courses[course_id].course_name, prior_topic)
            except (AIUnavailable, ValueError):
                # The optional search request must not block lexical retrieval.
                pass
        if re.search(r"gồm|bao gồm|những phép|cac phep|các phép|tính chất|tiên đề", query, re.IGNORECASE):
            limit = 6
        if ai_config and answer_style != "auto":
            limit = 6
        sources = [
            source for source in retriever.search(
                retrieval_text, limit=max(limit, min(6, len(concepts) * 2)), concepts=concepts,
            )
            if source.score >= EVIDENCE_THRESHOLD
        ]
        if not sources:
            message = "Không tìm thấy tài liệu phù hợp trong giáo trình cho câu hỏi này. Bạn hãy đặt câu hỏi liên quan đến nội dung bài giảng của môn học."
            if model_provider and model_name != "lookup":
                message += " Hệ thống chưa gọi mô hình vì thiếu đoạn nguồn phù hợp."
            return notice("insufficient_evidence", message)
        if limit == 6 or len(concepts) >= 2:
            # Slides often split one list across adjacent physical pages. Include bounded
            # context without pretending that adjacent pages have a similarity score.
            anchors = sources[:min(3, len(concepts))] if concepts else sources[:3]
            context_limit = min(10, len(sources) + 4) if concepts else 12
            seen = {source.chunk_id for source in sources}
            # Carry section headings from PDF ingestion: a definition and its laws
            # frequently span several slides under the same numbered heading.
            for anchor in anchors:
                if limit != 6 or not re.match(r"^\d+\.\s", anchor.heading):
                    continue
                for candidate in retriever.chunks:
                    if (candidate.document_id == anchor.document_id
                            and candidate.heading == anchor.heading
                            and candidate.chunk_id not in seen and len(sources) < context_limit):
                        sources.append(replace(candidate, score=0.0))
                        seen.add(candidate.chunk_id)
            seen_pages = {(source.document_id, source.page) for source in sources}
            for anchor in anchors:
                for candidate in retriever.chunks:
                    page_key = (candidate.document_id, candidate.page)
                    if (candidate.document_id == anchor.document_id
                            and abs(candidate.page - anchor.page) == 1
                            and page_key not in seen_pages and len(sources) < context_limit):
                        sources.append(replace(candidate, score=0.0))
                        seen_pages.add(page_key)

        ai_answer = ""
        cited_sources = sources
        mode: ChatMode = "lookup"
        response_status: ChatStatus = "success"
        response_message = None

        if error_reason == "missing_key":
            provider_title = "Google Gemini" if model_provider == "gemini" else "OpenAI ChatGPT"
            return ChatResponse(
                status="ai_unavailable",
                answer="",
                mode="lookup",
                context_question=context_question,
                message=f"Chưa có API Key cho {provider_title}. Vui lòng nhập API Key ở menu chuyển đổi mô hình (ngay thanh hỏi) để kích hoạt giải thích bằng AI.",
                sources=[source_item(s) for s in sources],
                model_name=model_name,
                model_provider=model_provider,
            )

        if ai_config:
            try:
                visual = {}
                if isinstance(ai_config, AIConfig) and ai_config.supports_rag_enrichment:
                    images = _selected_page_images(sources, catalog.document_map)
                    if images:
                        visual["page_images"] = images
                raw_ans, cited = ai_config.explain(
                    question, sources, answer_style=answer_style, context_question=prior_topic, **visual,
                )
                if not raw_ans:
                    response_status = "insufficient_evidence"
                    response_message = "AI chưa xác nhận đủ căn cứ cho toàn bộ câu hỏi. Các đoạn liên quan vẫn có ở dưới để bạn đối chiếu hoặc hỏi hẹp hơn."
                    mode = "ai"
                    cited_sources = sources
                    # Preserve the model's refusal, but don't hide retrieved documents.
                    return ChatResponse(
                        status=response_status, answer="", mode=mode,
                        context_question=context_question, message=response_message,
                        sources=[source_item(s) for s in sources],
                    )
                cited_ids = list(dict.fromkeys(c.chunk_id for c in cited))
                evidence_by_id = {s.chunk_id: s for s in sources}
                if not cited_ids or any(key not in evidence_by_id for key in cited_ids):
                    raise ValueError("Invalid answer citations")
                ai_answer = raw_ans
                mode = "ai"
                cited_sources = [evidence_by_id[key] for key in cited_ids]
            except (AIUnavailable, ValueError) as error:
                reason = error.reason if isinstance(error, AIUnavailable) else "format"
                is_local = (model_provider == "local") or getattr(ai_config, "is_local", False)
                if is_local and not model_provider and not model_name and reason in {"network", "model"}:
                    response_message = "Ollama chưa khả dụng. Câu trả lời được tạo từ phần tra cứu giáo trình."
                elif is_local:
                    response_status = "ai_unavailable"
                    mode = "ai"
                    response_message = (
                        "Không thể kết nối đến máy chủ Local Model (Ollama tại http://127.0.0.1:11434). "
                        'Hãy khởi động Ollama và bảo đảm mô hình đã chọn đã được tải về, hoặc chọn "Tra cứu giáo trình (Offline)" trên thanh công cụ.'
                    )
                    if reason == "model":
                        response_message = (
                            f"Ollama chưa có mô hình {ai_config.model}. "
                            'Chọn một mô hình đã cài hoặc dùng "Tra cứu giáo trình (Offline)".'
                        )
                    elif reason == "format":
                        response_message = "Mô hình Ollama trả định dạng hoặc trích dẫn chưa hợp lệ. Bạn có thể xem các đoạn nguồn bên dưới."
                    ai_answer = ""
                else:
                    provider_label = "Gemini" if model_provider == "gemini" else ("ChatGPT" if model_provider == "chatgpt" else "AI")
                    response_message = {
                        "credentials": f"Dịch vụ {provider_label} từ chối API Key hoặc quyền truy cập. Vui lòng kiểm tra lại API Key.",
                        "model": f"Mô hình {provider_label} đã cấu hình chưa khả dụng.",
                        "quota": f"Tài khoản {provider_label} đang hết hạn mức (Quota exceeded) hoặc bị giới hạn số lượt gọi.",
                        "format": "AI trả phản hồi chưa đúng định dạng hoặc trích dẫn không hợp lệ.",
                        "network": f"Kết nối tới {provider_label} bị gián đoạn hoặc quá thời gian chờ.",
                        "timeout": (
                            f"{provider_label} chưa trả lời trong thời gian chờ. "
                            "Bạn có thể thử lại hoặc chọn Gemini 3.5 Flash-Lite để phản hồi nhanh hơn."
                        ),
                    }.get(reason, f"Dịch vụ {provider_label} tạm thời không phản hồi.")
                    response_status = "ai_unavailable"
                    response_message += " Bạn vẫn có thể xem các nguồn PDF đã tìm được bên dưới."
                    mode = "ai"
                    ai_answer = ""

        if not ai_answer and response_status == "success":
            ai_answer = self._synthesize_answer(query, sources)
            mode = "lookup"

        # Keep synthesized answer structure intact without destroying line breaks
        formatted_answer = ai_answer
        active_model = getattr(ai_config, "model", model_name) if mode == "ai" else "lookup"

        return ChatResponse(
            status=response_status,
            answer=formatted_answer,
            mode=mode,
            context_question=context_question,
            message=response_message,
            sources=[source_item(source) for source in cited_sources],
            model_name=active_model,
            model_provider=model_provider or "local",
        )
