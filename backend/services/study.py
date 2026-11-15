import re
from dataclasses import dataclass

from backend.schemas.study import StudyAction, StudyMistake, StudyState, StudyTopic, StudyTurn, StudyTurnRequest
from backend.services.course_manager import source_item
from backend.services.ingest import ChunkSource
from backend.services.llm_service import AIConfig, AIUnavailable


STUDY_COURSE = "software_testing"
STUDY_DOCUMENT = "testing_basics"

_MISTAKES: dict[StudyMistake, str] = {
    "one_partition": "Các giá trị bạn chọn cùng một lớp. Hãy xét lần lượt dưới khoảng, trong khoảng và trên khoảng cho phép.",
    "missing_partition": "Bạn chưa phủ đủ ba lớp. Hãy xét riêng dưới khoảng, trong khoảng và trên khoảng.",
    "only_endpoints": "Bạn đã tìm đúng hai đầu mút. Hãy kiểm tra thêm các giá trị kề mỗi đầu mút ở cả hai phía.",
    "missing_neighbors": "Bạn còn thiếu giá trị đúng biên hoặc kề biên. Hãy xét ngay trước, tại và ngay sau mỗi đầu mút.",
    "extra_values": "Bạn đã phủ các trường hợp cần thiết. Hãy bỏ giá trị lặp hoặc dư để còn đúng số giá trị được hỏi.",
}


@dataclass(frozen=True)
class Exercise:
    field: str
    lower: int
    upper: int

    def prompt(self, boundary: bool) -> str:
        task = (
            "Nhập sáu giá trị để kiểm thử cả hai biên theo bước 1."
            if boundary else
            "Nhập ba số đại diện, mỗi số thuộc một lớp tương đương khác nhau."
        )
        return (
            f"Trường {self.field} chỉ chấp nhận số nguyên từ {self.lower} đến {self.upper}, "
            f"tính cả hai đầu mút. {task}"
        )

    def answer(self, boundary: bool) -> tuple[int, ...]:
        if boundary:
            return (self.lower - 1, self.lower, self.lower + 1, self.upper - 1, self.upper, self.upper + 1)
        return (self.lower - 1, self.lower, self.upper + 1)


@dataclass(frozen=True)
class Lesson:
    topic: StudyTopic
    diagnostic: Exercise
    exercises: tuple[Exercise, Exercise, Exercise]
    explanation: str
    hints: tuple[str, str]


LESSONS = {
    "equivalence": Lesson(
        topic=StudyTopic(
            id="equivalence", title="Phân vùng tương đương",
            goal="Chia miền đầu vào và chọn đại diện cho từng lớp.", page=2,
        ),
        diagnostic=Exercise("tuổi đăng ký lớp", 21, 28),
        exercises=(
            Exercise("số lượng đặt", 5, 12),
            Exercise("số vé mua", 3, 9),
            Exercise("số quyển mượn", 6, 15),
        ),
        explanation=(
            "Hãy chia miền đầu vào theo cách hệ thống xử lý. Với một khoảng nguyên có hai đầu mút "
            "được chấp nhận, ba lớp gồm dưới khoảng, trong khoảng và trên khoảng. "
            "Chọn một giá trị đại diện cho mỗi lớp, rồi xác định lớp đó được chấp nhận hay bị từ chối.\n\n"
            "Ví dụ, nếu một đơn hàng nhận 10–20 sản phẩm, 8, 15 và 25 đại diện cho ba lớp. "
            "Chọn 10, 15 và 20 chỉ kiểm tra lớp hợp lệ dù đó là ba số khác nhau."
        ),
        hints=(
            "Trước khi chọn số, hãy nghĩ xem có bao nhiêu vùng trên trục số cần được kiểm tra.",
            "Chọn một số nhỏ hơn đầu dưới, một số trong khoảng và một số lớn hơn đầu trên.",
        ),
    ),
    "boundary": Lesson(
        topic=StudyTopic(
            id="boundary", title="Phân tích giá trị biên",
            goal="Chọn giá trị đúng biên và hai giá trị kề biên.", page=3,
        ),
        diagnostic=Exercise("điểm", 2, 20),
        exercises=(
            Exercise("số sản phẩm", 1, 10),
            Exercise("số ngày mượn", 4, 14),
            Exercise("nhiệt độ", -5, 5),
        ),
        explanation=(
            "Giá trị biên tập trung vào những chỗ quy tắc đổi từ chấp nhận sang từ chối hoặc ngược lại. "
            "Với số nguyên, thử ngay trước, tại và ngay sau từng đầu mút, cách nhau một đơn vị.\n\n"
            "Ví dụ, khoảng 20–50 cần thử 19, 20, 21 ở đầu dưới và 49, 50, 51 ở đầu trên. "
            "So với phân vùng tương đương, trọng tâm ở đây là phát hiện lỗi sai một đơn vị tại biên."
        ),
        hints=(
            "Có hai ranh giới cần kiểm tra. Đừng tập trung vào các số ở giữa khoảng.",
            "Ở mỗi đầu mút, hãy cộng và trừ 1 rồi giữ cả chính giá trị đầu mút đó.",
        ),
    ),
}

_ALLOWED = {
    "diagnose": {"submit", "explain"},
    "explain": {"practice", "ai"},
    "practice": {"submit", "hint", "solution"},
    "review": {"retry"},
}


class InvalidStudyAction(ValueError):
    pass


def _read_integers(answer: str) -> list[int]:
    tokens = re.split(r"\s*[,;]\s*|\s+", answer.strip())
    if len(tokens) > 12 or any(not re.fullmatch(r"[+-]?[0-9]{1,6}", token) for token in tokens):
        raise ValueError("Nhập các số nguyên, ngăn cách bằng dấu phẩy, chấm phẩy hoặc khoảng trắng.")
    return [int(token) for token in tokens]


def _grade(exercise: Exercise, boundary: bool, answer: str) -> StudyMistake | None:
    values = _read_integers(answer)
    if boundary:
        expected = set(exercise.answer(boundary=True))
        if set(values) == {exercise.lower, exercise.upper}:
            return "only_endpoints"
        if not expected <= set(values):
            return "missing_neighbors"
    else:
        partitions = {
            -1 if value < exercise.lower else 1 if value > exercise.upper else 0
            for value in values
        }
        if len(partitions) == 1 and len(values) > 1:
            return "one_partition"
        if len(partitions) < 3:
            return "missing_partition"
    return "extra_values" if len(values) != (6 if boundary else 3) else None


def _transition(payload: StudyTurnRequest, lesson: Lesson, boundary: bool, previous: StudyState) -> StudyState:
    state = previous.model_copy()
    action: StudyAction = payload.action
    if action in {"open", "view"}:
        return state
    if action not in _ALLOWED[state.step]:
        raise InvalidStudyAction("Thao tác này không phù hợp với bước học hiện tại.")
    if action == "explain":
        state.step = "explain"
    elif action == "practice":
        state.step = "practice"
    elif action == "retry":
        state.variant = (state.variant + 1) % len(lesson.exercises)
        state.step = "practice"
        state.hint_level = 0
        state.practice_mistake = None
    elif action == "hint":
        if state.hint_level >= len(lesson.hints):
            raise InvalidStudyAction("Bạn đã mở tất cả gợi ý cho bài này.")
        state.hint_level += 1
    elif action == "solution":
        if state.practice_mistake is None and state.hint_level < len(lesson.hints):
            raise InvalidStudyAction("Hãy thử làm bài hoặc mở cả hai gợi ý trước khi xem lời giải.")
        state.last_result = "needs_practice"
        state.step = "review"
    elif action == "submit":
        diagnostic = state.step == "diagnose"
        exercise = lesson.diagnostic if diagnostic else lesson.exercises[state.variant]
        mistake = _grade(exercise, boundary, payload.answer)
        if mistake:
            state.mistake_count = min(state.mistake_count + 1, 999) if mistake == state.last_mistake else 1
            state.last_mistake = mistake
        if diagnostic:
            state.diagnosis = mistake or "correct"
            state.step = "explain"
        elif mistake:
            state.practice_mistake = mistake
        else:
            state.last_result = "needs_practice" if state.hint_level or state.practice_mistake else "independent"
            state.step = "review"
    return state


def study_turn(
    lesson: Lesson, payload: StudyTurnRequest, previous: StudyState, chunks: list[ChunkSource], ai: AIConfig | None,
) -> StudyTurn:
    boundary = lesson.topic.id == "boundary"
    state = _transition(payload, lesson, boundary, previous)
    response = StudyTurn(state=state)
    exercise = lesson.exercises[state.variant]
    if state.step == "diagnose":
        response.prompt = lesson.diagnostic.prompt(boundary)
    elif state.step == "explain":
        response.lesson = lesson.explanation
        response.sources = [source_item(chunk) for chunk in chunks]
        if state.diagnosis == "correct":
            response.feedback = "Bạn đã chọn đủ các giá trị cần kiểm tra. Hãy áp dụng lại với dữ kiện mới."
        elif state.diagnosis:
            response.feedback = _MISTAKES[state.diagnosis]
    elif state.step == "practice":
        response.prompt = exercise.prompt(boundary)
        if state.practice_mistake:
            response.feedback = _MISTAKES[state.practice_mistake]
        if state.hint_level:
            response.hint = lesson.hints[state.hint_level - 1]
    else:
        label = "Bộ giá trị cần thử" if boundary else "Một bộ giá trị đại diện hợp lệ"
        values = ", ".join(str(value) for value in exercise.answer(boundary))
        response.lesson = f"{label} là {values}.\n\n{lesson.explanation}"
        response.sources = [source_item(chunk) for chunk in chunks]
        response.feedback = (
            "Bạn đã làm đúng ngay lần đầu mà không cần gợi ý."
            if state.last_result == "independent"
            else "Hãy thử một bộ dữ kiện khác để kiểm tra xem bạn đã tự làm được chưa."
        )
        if state.last_mistake and state.mistake_count >= 2 and state.last_result != "independent":
            response.feedback += f" {_MISTAKES[state.last_mistake]}"

    if payload.action == "ai":
        _add_ai_explanation(response, lesson, chunks, ai)
    return response


def _add_ai_explanation(
    response: StudyTurn, lesson: Lesson, chunks: list[ChunkSource], ai: AIConfig | None,
) -> None:
    if ai is None:
        response.ai_status = "not_configured"
        response.ai_message = "Chưa cấu hình mô hình trên máy chủ. Bạn vẫn có thể đọc giải thích và làm bài."
        return
    question = (
        f"Hướng dẫn một sinh viên luyện kỹ năng {lesson.topic.title}. "
        "Giải thích phương pháp theo từng bước, dùng số liệu tự tạo khác ví dụ trong học liệu. "
        "Kết thúc bằng một câu hỏi gợi suy nghĩ. Chỉ dùng học liệu để giải thích kiến thức."
    )
    if response.feedback:
        question += f" Phản hồi chẩn đoán đã xác định: {response.feedback}"
    try:
        answer, cited = ai.explain(question, chunks, answer_style="detailed", require_inline_citations=True)
    except AIUnavailable as error:
        response.ai_status = "unavailable"
        response.ai_message = {
            "credentials": "Nhà cung cấp từ chối thông tin xác thực.",
            "quota": "Nhà cung cấp đang giới hạn lượt gọi hoặc hết hạn mức.",
            "model": "Mô hình đã cấu hình chưa khả dụng.",
        }.get(error.reason, "Không thể kết nối hoặc nhận phản hồi từ mô hình.")
    except ValueError:
        response.ai_status = "unavailable"
        response.ai_message = "Phản hồi AI sai định dạng hoặc dẫn nguồn không hợp lệ."
    else:
        if answer:
            response.ai_status = "used"
            response.ai_answer = answer
            response.ai_sources = [source_item(chunk) for chunk in cited]
        else:
            response.ai_status = "insufficient_evidence"
            response.ai_message = "AI chưa tìm được đủ căn cứ để giải thích thêm."
