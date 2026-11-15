import re
from dataclasses import dataclass

from backend.schemas.study import StudyAction, StudyMistake, StudyState, StudyTopic, StudyTurn, StudyTurnRequest
from backend.services.course_manager import source_item
from backend.services.ingest import ChunkSource
from backend.services.llm_service import AIConfig, AIUnavailable


_MISTAKES: dict[StudyMistake, str] = {
    "confuses_intersection": "Bạn đang lấy phần giao. Phép hợp giữ cả phần tử chỉ thuộc một tập.",
    "confuses_nonfunctional": (
        "Bạn đang chọn các yêu cầu phi chức năng. Hãy tìm các hành động hoặc dịch vụ hệ thống cung cấp."
    ),
    "incomplete": "Các lựa chọn hiện tại đều đúng nhưng chưa đủ. Hãy kiểm tra lại dữ kiện còn bỏ sót.",
    "wrong_values": "Có giá trị hoặc lựa chọn chưa phù hợp. Hãy kiểm tra lại từng mục theo quy tắc trong bài.",
    "extra_values": "Bạn đã tìm đủ đáp án. Hãy bỏ các giá trị lặp hoặc dư.",
}


@dataclass(frozen=True)
class Exercise:
    prompt: str
    answer: tuple[int, ...]
    confused_answer: tuple[int, ...]


@dataclass(frozen=True)
class Lesson:
    topic: StudyTopic
    document_id: str
    misconception: StudyMistake
    diagnostic: Exercise
    exercises: tuple[Exercise, Exercise, Exercise]
    explanation: str
    hints: tuple[str, str]


def _union(a: tuple[int, ...], b: tuple[int, ...]) -> Exercise:
    left = ", ".join(map(str, a))
    right = ", ".join(map(str, b))
    return Exercise(
        f"Cho A = {{{left}}} và B = {{{right}}}. Nhập tất cả phần tử của A ∪ B, mỗi phần tử một lần.",
        tuple(sorted(set(a) | set(b))),
        tuple(sorted(set(a) & set(b))),
    )


def _classify(context: str, statements: tuple[str, ...], functional: tuple[int, ...]) -> Exercise:
    choices = "\n".join(f"{index}. {statement}" for index, statement in enumerate(statements, 1))
    other = tuple(index for index in range(1, len(statements) + 1) if index not in functional)
    return Exercise(f"{context} Nhập số thứ tự của tất cả yêu cầu chức năng.\n\n{choices}", functional, other)


LESSONS = {
    "toan_roi_rac": Lesson(
        topic=StudyTopic(
            id="union", title="Phép hợp và phép giao",
            goal="Phân biệt điều kiện thuộc ít nhất một tập và thuộc đồng thời hai tập.", page=1,
        ),
        document_id="discrete_math_study",
        misconception="confuses_intersection",
        diagnostic=_union((1, 4, 7), (4, 8)),
        exercises=(
            _union((-3, 2, 5), (2, 6)),
            _union((2, 9), (-2, 9, 11)),
            _union((-5, 0, 3), (0, 10)),
        ),
        explanation=(
            "Phép hợp giữ mọi phần tử thuộc A hoặc B (kể cả thuộc cả hai), mỗi phần tử ghi một lần. "
            "Phép giao chỉ giữ phần tử có mặt trong cả hai tập.\n\n"
            "Ví dụ, với A = {3, 5} và B = {5, 10}, hợp là {3, 5, 10} và giao là {5}. "
            "Số 3 nằm trong hợp dù nó không thuộc B."
        ),
        hints=(
            "Một phần tử chỉ thuộc một trong hai tập có được đưa vào hợp không?",
            "Lấy toàn bộ phần tử của A rồi thêm các phần tử có trong B mà chưa xuất hiện.",
        ),
    ),
    "thu_thap_phan_tich_yeu_cau": Lesson(
        topic=StudyTopic(
            id="functional", title="Yêu cầu chức năng và phi chức năng",
            goal="Phân biệt hành vi hệ thống với tiêu chí chất lượng và ràng buộc.", page=1,
        ),
        document_id="requirements_study",
        misconception="confuses_nonfunctional",
        diagnostic=_classify(
            "Một hệ thống đặt lịch có bốn yêu cầu.",
            (
                "Sinh viên có thể hủy lịch đã đặt.",
                "Thời gian phản hồi của trang kết quả không vượt quá 2 giây.",
                "Hệ thống gửi xác nhận sau khi đặt lịch.",
                "Dịch vụ phải sẵn sàng ít nhất 99,9% mỗi tháng.",
            ),
            (1, 3),
        ),
        exercises=(
            _classify(
                "Một ứng dụng quản lý phòng học có bốn yêu cầu.",
                (
                    "Thời gian tải danh sách phòng không vượt quá 2 giây.",
                    "Giảng viên có thể đặt một phòng còn trống.",
                    "Ứng dụng hỗ trợ 200 người dùng đồng thời.",
                    "Hệ thống gửi thông báo khi yêu cầu đặt phòng được duyệt.",
                ),
                (2, 4),
            ),
            _classify(
                "Một cổng đăng ký học phần có bốn yêu cầu.",
                (
                    "Sinh viên có thể rút học phần đã đăng ký.",
                    "Cổng đăng ký duy trì độ sẵn sàng 99,9% mỗi tháng.",
                    "Hệ thống hiển thị danh sách học phần đã đăng ký.",
                    "Trang danh sách tải trong tối đa 3 giây.",
                ),
                (1, 3),
            ),
            _classify(
                "Một hệ thống mượn thiết bị có bốn yêu cầu.",
                (
                    "Người dùng nhận biên nhận khi trả thiết bị.",
                    "Nhân viên có thể lập phiếu mượn.",
                    "Tra cứu phản hồi trong tối đa 1 giây.",
                    "Dữ liệu phải được lưu trữ tại Việt Nam.",
                ),
                (1, 2),
            ),
        ),
        explanation=(
            "Yêu cầu chức năng mô tả hành vi hoặc dịch vụ mà hệ thống cung cấp. "
            "Yêu cầu phi chức năng mô tả chất lượng hoặc ràng buộc cần đáp ứng.\n\n"
            "Ví dụ, cho phép người dùng tải một hóa đơn là hành vi chức năng. "
            "Tạo hóa đơn trong tối đa 3 giây là tiêu chí hiệu năng có thể kiểm tra."
        ),
        hints=(
            "Xem từng câu mô tả hệ thống làm gì hay làm tốt đến mức nào.",
            "Tìm các hành động hoặc dịch vụ cho người dùng. Tốc độ và sức tải là tiêu chí chất lượng.",
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


def _grade(exercise: Exercise, misconception: StudyMistake, answer: str) -> StudyMistake | None:
    values = _read_integers(answer)
    submitted = set(values)
    expected = set(exercise.answer)
    if submitted == expected and len(values) == len(expected):
        return None
    if submitted == set(exercise.confused_answer):
        return misconception
    if submitted < expected:
        return "incomplete"
    return "extra_values" if expected <= submitted else "wrong_values"


def _transition(payload: StudyTurnRequest, lesson: Lesson, previous: StudyState) -> StudyState:
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
        mistake = _grade(exercise, lesson.misconception, payload.answer)
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
    state = _transition(payload, lesson, previous)
    response = StudyTurn(state=state)
    exercise = lesson.exercises[state.variant]
    if state.step == "diagnose":
        response.prompt = lesson.diagnostic.prompt
    elif state.step == "explain":
        response.lesson = lesson.explanation
        response.sources = [source_item(chunk) for chunk in chunks]
        if state.diagnosis == "correct":
            response.feedback = "Bạn đã chọn đủ các giá trị cần kiểm tra. Hãy áp dụng lại với dữ kiện mới."
        elif state.diagnosis:
            response.feedback = _MISTAKES[state.diagnosis]
    elif state.step == "practice":
        response.prompt = exercise.prompt
        if state.practice_mistake:
            response.feedback = _MISTAKES[state.practice_mistake]
        if state.hint_level:
            response.hint = lesson.hints[state.hint_level - 1]
    else:
        values = ", ".join(str(value) for value in exercise.answer)
        response.lesson = f"Đáp án là {values}.\n\n{lesson.explanation}"
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
        "Giải thích phương pháp theo từng bước, dùng ví dụ tự tạo khác ví dụ trong học liệu. "
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
