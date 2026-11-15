import re
import unicodedata
from pathlib import Path

from services.llm_service import AIConfig, AIUnavailable
from services.retrieval import CourseIndex, normalize_search_text
from src.schemas import MAX_QUESTION_LENGTH, ChatRequest, ChatResponse, Course


COURSES = (
    ("software_testing", "Kiểm thử phần mềm"),
    ("algorithm_analysis", "Phân tích thuật toán"),
)
PRIVATE_COURSES = (
    ("tin_hoc_dai_cuong", "Tin học đại cương"),
    ("toan_roi_rac", "Toán rời rạc"),
    ("thu_thap_phan_tich_yeu_cau", "Thu thập và phân tích yêu cầu"),
)
EVIDENCE_THRESHOLD = 0.20
AMBIGUOUS_QUESTION = re.compile(
    r"(?:(?:hãy )?(?:giải thích|nói rõ|phân tích) (?:về )?(?:cái này|cái đó|cái kia|nó|phần này|đoạn này)"
    r"(?: (?:giúp mình|giúp tôi|với|đi))?|(?:vậy )?còn (?:cái này|cái kia|trường hợp này|trường hợp kia|trường hợp đó)"
    r"(?: thì sao)?)"
)
SOURCE_REQUEST = re.compile(
    r"^(?:(?:hay|vui long|ban|giup minh|giup toi) )*"
    r"(?:trich|tra cuu|tim (?:trang|doan|nguon|muc|chuong|tai lieu|phan|trong tai lieu)"
    r"|(?:cho (?:minh |toi )?xem|mo) (?:trang|doan|nguon|tai lieu|phan))\b"
    r"|\b(?:khong (?:can )?giai thich|khong (?:can )?(?:dung |goi )?ai|chi can (?:trang|nguon|doan))\b"
)
EXPLANATION_REQUEST = re.compile(
    r"\b(?:giai thich|dien giai|tom tat|so sanh|vi sao|tai sao|la gi|the nao|lam sao|khi nao|"
    r"lam gi|tac dung gi|lenh nao|vi du|huong dan)\b"
    r"|\bkhac\b.*\b(?:o dau|o diem nao)\b|^(?:cach|chung minh)\b"
)


def _answer_mode(question: str) -> str:
    wording = re.sub(r"\W+", " ", normalize_search_text(question)).strip()
    if SOURCE_REQUEST.search(wording):
        return "lookup"
    return "ai" if EXPLANATION_REQUEST.search(wording) else "lookup"


class ChatbotService:
    def __init__(self, data_dir: Path, *, private: bool = False):
        self._catalog = dict(PRIVATE_COURSES if private else COURSES)
        self._index = CourseIndex(data_dir, private=private)
        if private:
            for course_id, course_name in self._index.course_names.items():
                self._catalog.setdefault(course_id, course_name)
        project_dir = data_dir.parent.parent if private else data_dir.parent
        ai = AIConfig.load(project_dir / ".env")
        self._ai = ai if ai and (not private or ai.is_local) else None

    @property
    def ai_available(self) -> bool:
        return self._ai is not None

    @property
    def issues(self) -> tuple[str, ...]:
        return self._index.issues

    def courses(self) -> tuple[Course, ...]:
        return tuple(
            Course(course_id, name, self._index.documents(course_id)) for course_id, name in self._catalog.items()
        )

    def answer_question(self, request: ChatRequest) -> ChatResponse:
        automatic = request.mode == "auto"
        mode = "lookup" if automatic else request.mode

        def notice(status: str, message: str) -> ChatResponse:
            return ChatResponse(request.request_id, status, mode, message=message)

        if (
            request.mode not in ("auto", "lookup", "ai")
            or not isinstance(request.course_id, str)
            or request.course_id not in self._catalog
        ):
            return notice("invalid_input", "Hãy chọn học phần và chế độ hợp lệ.")
        if not isinstance(request.question, str) or not request.question.strip():
            return notice("invalid_input", "Hãy nhập câu hỏi về học phần.")
        question = unicodedata.normalize("NFC", " ".join(request.question.split()))
        if len(request.question) > MAX_QUESTION_LENGTH:
            return notice("invalid_input", f"Câu hỏi tối đa {MAX_QUESTION_LENGTH} ký tự.")
        if not any(character.isalnum() for character in question):
            return notice("invalid_input", "Hãy nhập câu hỏi về học phần.")
        if not self._index.documents(request.course_id):
            return notice("no_documents", "Học phần này chưa có tài liệu sẵn sàng.")
        # ponytail: explicit Vietnamese follow-up phrases for this demo corpus.
        if AMBIGUOUS_QUESTION.fullmatch(question.casefold().strip(" ?!.,…")):
            return notice("needs_clarification", "Bạn có thể nêu rõ khái niệm hoặc chương cần hỏi không?")

        sources = tuple(
            source for source in self._index.search(request.course_id, question)
            if source.score >= EVIDENCE_THRESHOLD
        )
        insufficient = "Chưa tìm thấy căn cứ phù hợp trong học liệu đã nạp."
        if not sources:
            return notice("insufficient_evidence", insufficient)

        def excerpts(message: str = "") -> ChatResponse:
            return ChatResponse(request.request_id, "success", "lookup", "Các đoạn học liệu liên quan", message, sources)

        if automatic:
            mode = _answer_mode(question)
        if mode == "lookup":
            return excerpts()
        if self._ai is None:
            if automatic:
                return excerpts("AI chưa được cấu hình. Bạn có thể đối chiếu các đoạn trích và trang nguồn bên dưới.")
            return notice("ai_unavailable", "Chế độ AI chưa được cấu hình. Bạn có thể dùng Tra cứu học liệu.")

        try:
            answer, cited_sources = self._ai.explain(question, sources)
        except (AIUnavailable, ValueError) as error:
            if automatic:
                return excerpts("AI tạm thời chưa trả lời được. Bạn có thể đối chiếu các đoạn trích và trang nguồn bên dưới.")
            if isinstance(error, AIUnavailable):
                return notice("ai_unavailable", "Chưa kết nối được chế độ AI. Bạn có thể dùng Tra cứu học liệu.")
            return notice("error", "Phản hồi AI không hợp lệ. Hãy thử lại hoặc chuyển sang Tra cứu học liệu.")
        if not answer:
            return notice("insufficient_evidence", insufficient)
        return ChatResponse(request.request_id, "success", "ai", answer, sources=cited_sources)
