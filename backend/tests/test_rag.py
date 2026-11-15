import json
from pathlib import Path
from types import SimpleNamespace

import pymupdf
import pytest

from backend.services.course_manager import CourseManager
from backend.services.ingest import ChunkSource, DocumentInfo, extract_pdf_chunks
from backend.services.llm_service import AIConfig, AIUnavailable
from backend.services.retrieval import CourseRetriever


def pdf_bytes(pages):
    with pymupdf.open() as pdf:
        for text in pages:
            page = pdf.new_page()
            page.insert_textbox(page.rect + (30, 30, -30, -30), text, fontsize=9)
        return pdf.tobytes()


def test_all_suggested_questions_have_grounded_evidence():
    root = Path(__file__).resolve().parents[2]
    manager = CourseManager(root)
    manager._ai = None

    from backend.services.course_manager import COURSE_SUGGESTED_QUESTIONS

    expected_pages = {
        "tin_hoc_dai_cuong": ({20}, {11}, {19, 22}, {13}),
        "software_testing": ({2}, {2, 3}, {1}, {3}),
        "algorithm_analysis": ({1}, {2}, {3}, {4}),
        "toan_roi_rac": ({4}, {2}, {9}, {21}),
        "thu_thap_phan_tich_yeu_cau": ({22, 30}, {29}, {15}, {2}),
    }

    for course_id, questions in COURSE_SUGGESTED_QUESTIONS.items():
        for question, expected in zip(questions, expected_pages[course_id], strict=True):
            response = manager.answer_question(course_id, question)
            pages = {source.page for source in response.sources}
            assert expected <= pages, (
                f"{course_id}: {question!r}; expected pages {sorted(expected)}, "
                f"got {sorted(pages)}"
            )


def test_chunks_overlap_without_crossing_pdf_pages():
    words = [f"word{i:03}" for i in range(180)]
    data = pdf_bytes([" ".join(words), "SECOND_PAGE_ONLY"])
    document = DocumentInfo("doc", "lecture.pdf", Path("lecture.pdf"), "project_demo")
    chunks = list(extract_pdf_chunks(document, data))
    first_page = [chunk for chunk in chunks if chunk.page == 1]
    assert len(first_page) == 2
    assert first_page[0].excerpt.split()[-25:] == first_page[1].excerpt.split()[:25]
    assert all("SECOND_PAGE_ONLY" not in chunk.excerpt for chunk in first_page)
    assert chunks[-1].page == 2
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)


def test_retrieval_returns_the_actual_pdf_page_and_respects_top_k():
    data = pdf_bytes(["Network sockets and datagrams", "Equivalence partitioning divides inputs into classes"])
    document = DocumentInfo("doc", "lecture.pdf", Path("lecture.pdf"), "project_demo")
    chunks = list(extract_pdf_chunks(document, data))
    retriever = CourseRetriever("testing", [document], chunks)
    result = retriever.search("Equivalence partitioning", limit=1)
    assert len(result) == 1
    assert result[0].page == 2
    assert result[0].document_id == "doc"
    assert result[0].excerpt in pymupdf.open(stream=data)[1].get_text().replace("\n", " ")
    assert retriever.search("zzzzzzzzzzzzzzzzzzzzzz") == []


def test_lookup_excerpt_retains_list_levels_labels_and_wrapped_lines():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((40, 55), "Requirements", fontsize=22)
        for x, y, text in (
            (40, 85, "3) Main requirement"),
            (61, 102, "- Describe the expected behavior"),
            (71, 116, "across several lines"),
            (61, 133, "- Describe its constraints"),
            (40, 160, "7) Verify the requirement"),
            (61, 177, "a) Record the evidence"),
        ):
            page.insert_text((x, y), text, fontsize=11)
        page.insert_text((page.rect.width - 30, page.rect.height - 30), "1", fontsize=8)
        data = pdf.tobytes()
    document = DocumentInfo("doc", "lecture.pdf", Path("lecture.pdf"), "project_demo")
    chunk, = extract_pdf_chunks(document, data)
    assert chunk.formatted_excerpt == (
        "### Requirements\n\n"
        "3) Main requirement\n"
        "   - Describe the expected behavior across several lines\n"
        "   - Describe its constraints\n"
        "7) Verify the requirement\n"
        "   - a) Record the evidence"
    )


@pytest.fixture
def manager(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "lecture.pdf").write_bytes(pdf_bytes(["Operating system manages resources and executes programs"]))
    (data / "manifest.csv").write_text(
        "course_id,document_id,document_name,path,license\n"
        "software_testing,lecture,lecture.pdf,lecture.pdf,project_demo\n", encoding="utf-8"
    )
    result = CourseManager(tmp_path)
    result._ai = None
    return result


def test_ai_refusal_is_not_changed_to_success(manager):
    manager._ai = SimpleNamespace(explain=lambda *_, **__: ("", []))
    response = manager.answer_question("software_testing", "Operating system")
    assert response.status == "insufficient_evidence"
    assert response.answer == ""
    assert response.sources[0].document_id == "lecture"


@pytest.mark.parametrize("question", ["!!!", "123456", "   ", "🙂🙂"])
def test_non_question_input_is_rejected(manager, question):
    assert manager.answer_question("software_testing", question).status == "invalid_input"


def test_intro_does_not_change_retrieved_sources(manager):
    short = manager.answer_question("software_testing", "Operating system")
    long = manager.answer_question("software_testing", "Mình đang học bài và chưa hiểu. Vậy Operating system")
    assert short.sources == long.sources


def test_answer_without_valid_citations_is_rejected(manager):
    manager._ai = SimpleNamespace(explain=lambda *_, **__: ("Unsupported answer", []))
    response = manager.answer_question("software_testing", "Operating system")
    assert response.status == "ai_unavailable"
    assert response.answer == ""


def test_provider_outage_is_reported(manager):
    def unavailable(*_, **__):
        raise AIUnavailable
    manager._ai = SimpleNamespace(explain=unavailable)
    response = manager.answer_question("software_testing", "Operating system")
    assert response.status == "ai_unavailable"
    assert response.sources[0].document_id == "lecture"
    assert response.message


def test_valid_ai_answer_keeps_retrieved_metadata(manager):
    manager._ai = SimpleNamespace(explain=lambda question, sources, **_: ("Manages resources", sources[:1]))
    response = manager.answer_question("software_testing", "Operating system")
    assert response.status == "success"
    assert response.mode == "ai"
    assert response.sources[0].document_id == "lecture"
    assert response.sources[0].page == 1
    assert response.sources[0].document_sha256


def test_ai_example_keeps_follow_up_separate_from_retrieval_topic(manager):
    requests = []

    def explain(question, sources, **options):
        requests.append((question, options))
        return "Ví dụ minh họa về cách hệ điều hành quản lý tài nguyên.", sources[:1]

    manager._ai = SimpleNamespace(explain=explain)
    response = manager.answer_question(
        "software_testing", "Cho ví dụ?", ["Operating system"], answer_style="example",
    )

    assert requests == [("Cho ví dụ?", {"answer_style": "example", "context_question": "Operating system"})]
    assert (response.status, response.mode, response.sources[0].page) == ("success", "ai", 1)


@pytest.mark.parametrize("source_ids", [["S999"], ["S1", "S999"], [], [123]])
def test_provider_cannot_invent_citations(monkeypatch, source_ids):
    from backend.services import llm_service
    from backend.services.ingest import ChunkSource

    reply = {"status": "success", "answer": "Answer", "source_ids": source_ids}
    raw = json.dumps({"choices": [{"message": {"content": json.dumps(reply)}}]}).encode()
    class Connection:
        def __init__(self, *args, **kwargs): pass
        def request(self, *args): pass
        def getresponse(self): return SimpleNamespace(status=200, read=lambda _: raw)
        def close(self): pass
    monkeypatch.setattr(llm_service, "HTTPSConnection", Connection)
    config = AIConfig("https://example.test/v1/chat/completions", "test-model", "test-key")
    source = ChunkSource("doc", "lecture.pdf", 2, "chunk", "Evidence")
    with pytest.raises(ValueError):
        config.explain("Question", [source])


def test_local_model_outage_returns_ai_unavailable_with_actionable_message(manager, monkeypatch):
    def unreachable(*_, **__):
        raise AIUnavailable("network")

    monkeypatch.setattr(AIConfig, "explain", unreachable)
    response = manager.answer_question(
        "software_testing",
        "Operating system",
        model_provider="local",
        model_name="qwen3.5:4b",
    )
    assert response.status == "ai_unavailable"
    assert response.mode == "ai"
    assert "Không thể kết nối đến máy chủ Local Model (Ollama tại http://127.0.0.1:11434)" in response.message
    assert response.answer == ""
    assert len(response.sources) > 0


def test_out_of_scope_query_returns_insufficient_evidence():
    root = Path(__file__).resolve().parents[2]
    course_manager = CourseManager(root)
    response = course_manager.answer_question("thu_thap_phan_tich_yeu_cau", "Hôm nay ăn gì?")
    assert response.status == "insufficient_evidence"
    assert response.message == "Không tìm thấy tài liệu phù hợp trong giáo trình cho câu hỏi này. Bạn hãy đặt câu hỏi liên quan đến nội dung bài giảng của môn học."
    assert response.sources == []


@pytest.mark.parametrize("model_name", ["lookup", None])
def test_requirements_elicitation_techniques_ranks_page_29_top(model_name, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    course_manager = CourseManager(root)
    course_manager._ai = AIConfig("http://127.0.0.1:11434/v1/chat/completions", "test-model", "")

    def unreachable(*_, **__):
        if model_name == "lookup":
            pytest.fail("Explicit lookup must skip the model")
        raise AIUnavailable("network")

    monkeypatch.setattr(AIConfig, "explain", unreachable)
    response = course_manager.answer_question(
        "thu_thap_phan_tich_yeu_cau",
        "Các kỹ thuật phổ biến để khám phá yêu cầu phần mềm?",
        model_name=model_name,
    )
    assert response.status == "success"
    assert response.mode == "lookup"
    assert response.sources[0].page == 29
    assert response.sources[0].score == 1.0
    assert "Các kỹ thuật điều tra" in response.answer
    assert "Các kỹ thuật sáng tạo" in response.answer
    assert "Các kỹ thuật lấy tài liệu làm trung tâm" in response.answer
    assert "Các kỹ thuật quan sát" in response.answer
    assert "Các kỹ thuật hỗ trợ" in response.answer


def test_out_of_scope_questions_with_overlapping_words_are_rejected(monkeypatch):
    def unexpected_model_call(*_, **__):
        pytest.fail("An out-of-scope question reached the model without supporting passages")

    monkeypatch.setattr(AIConfig, "explain", unexpected_model_call)
    root = Path(__file__).resolve().parents[2]
    manager = CourseManager(root)
    for question in (
        "Lịch đăng ký học phần học kỳ tới bắt đầu ngày nào?",
        "Học kỳ này trường mình đăng ký học phần ngày nào?",
        "Biểu đồ Use Case dùng để mô hình hóa khía cạnh nào của hệ thống?",
        "Thủ đô của Nhật Bản là gì?",
    ):
        result = manager.answer_question("toan_roi_rac", question, model_provider="local", model_name="qwen2.5:1.5b")
        assert (result.status, result.answer, result.sources) == ("insufficient_evidence", "", []), question


def test_missing_local_model_is_identified(manager, monkeypatch):
    def model_not_found(*_, **__):
        raise AIUnavailable("model")

    monkeypatch.setattr(AIConfig, "explain", model_not_found)
    result = manager.answer_question(
        "software_testing", "Operating system", model_provider="local", model_name="missing-test-model",
    )
    assert result.status == "ai_unavailable"
    assert "missing-test-model" in result.message



@pytest.mark.parametrize(("question", "lecture_pages", "expected_pages", "concepts"), [
    (
        "Mình mới học Toán rời rạc và hay nhầm giữa “thuộc” với “là tập con”. "
        "Nếu A = {1, 2}, thì 1 và {1} liên hệ với A như thế nào?",
        {
            2: "Ký hiệu phần tử của tập hợp: a là một phần tử khi a thuộc tập hợp A.",
            4: "Khái niệm cơ bản. Tập con: A là tập con của B khi mọi phần tử của A đều thuộc B.",
        },
        {2, 4},
        ("ký hiệu phần tử tập hợp", "tập con khái niệm"),
    ),
    (
        "Cho tập vũ trụ U = {1, 2, 3, 4, 5}, A = {1, 2, 3}, B = {2, 4}. "
        "Hãy tìm A − B và phần bù của A trong U. Giải thích vì sao hai kết quả khác nhau.",
        {
            10: "Phép hiệu của hai tập hợp giữ các phần tử thuộc A mà không thuộc B.",
            19: "Phần bù của tập hợp A trong tập vũ trụ U gồm mọi phần tử của U không thuộc A.",
        },
        {10, 19},
        ("phép hiệu tập hợp", "phần bù tập hợp"),
    ),
    (
        "Lập bảng chân trị của p → q và giải thích khi nào mệnh đề kéo theo sai.",
        {
            9: "Phép suy ra: Mệnh đề p suy ra q nhận giá trị F khi p là T và q là F.",
            11: "Bảng giá trị chân lý: p q p→q T T T T F F F T T F F T.",
        },
        {9, 11},
        ("phép suy ra", "bảng giá trị chân lý p q T F"),
    ),
])
def test_discrete_math_application_retrieves_each_required_rule(question, lecture_pages, expected_pages, concepts):
    document = DocumentInfo("lecture", "lecture.pdf", Path("lecture.pdf"), "project_demo")
    excerpts = {
        **lecture_pages,
        25: "Tương đương logic. Lập bảng giá trị chân lý của mệnh đề. Hãy giải thích vì sao kết quả khác nhau.",
        26: "Tổ hợp chập k từ n phần tử. Cho A = {1, 2, 3, 4, 5} và B = {2, 4}.",
        36: "Đồ thị con. Ví dụ về phần tử của đồ thị và tập con của tập đỉnh.",
    }
    chunks = [
        ChunkSource("lecture", document.document_name, page, str(page), excerpt)
        for page, excerpt in excerpts.items()
    ]
    retriever = CourseRetriever("toan_roi_rac", [document], chunks)
    assert expected_pages <= {source.page for source in retriever.search(question, limit=3, concepts=concepts)}



def test_new_course_can_retrieve_multiple_concepts_with_rewritten_terms():
    document = DocumentInfo("new", "new.pdf", Path("new.pdf"), "project_demo")
    excerpts = [
        "Boundary value analysis tests data at, just below, and just above each boundary.",
        "Equivalence partitioning divides inputs that should behave alike into classes.",
        "Account registration sends a welcome message with setup instructions.",
    ]
    chunks = [ChunkSource("new", "new.pdf", page, str(page), text) for page, text in enumerate(excerpts, 1)]
    retriever = CourseRetriever("new_course", [document], chunks)
    results = retriever.search(
        "How do I group similar inputs, and which values near the edge should I check?",
        limit=2,
        concepts=("equivalence partitioning", "boundary value analysis"),
    )
    assert [source.page for source in results] == [2, 1]


def test_query_parts_keeps_request_when_example_contains_many_commas():
    from backend.services.query import query_parts

    parts = query_parts(
        "Cho dữ liệu X = {1, 2, {3, 4}, 5, 6, 7, 8}. "
        "Hãy trình bày cách kiểm tra dữ liệu biên và giải thích mục đích.",
    )
    assert any("kiem tra du lieu bien" in part for part in parts)
    assert all(not any(character.isdigit() for character in part) for part in parts)



@pytest.mark.parametrize("planning_succeeds", [True, False])
def test_hosted_rag_keeps_the_full_question_and_falls_back_to_lexical_search(manager, monkeypatch, planning_succeeds):
    question = "Mình đang thử giải thích một số nội dung theo bài học trên lớp. Operating system"
    calls = []

    def plan(_config, original, _course_name, prior):
        assert original == question and prior is None
        calls.append("plan")
        if not planning_succeeds:
            raise AIUnavailable("timeout")
        return ["operating system"]

    def answer(_config, original, sources, **_options):
        assert original == question and sources[0].page == 1
        calls.append("answer")
        return "Explained from the lecture.", sources[:1]

    monkeypatch.setattr(AIConfig, "search_terms", plan)
    monkeypatch.setattr(AIConfig, "explain", answer)
    response = manager.answer_question("software_testing", question, model_provider="gemini", api_key="test-key")
    assert response.status == "success"
    assert calls == ["plan", "answer"]


def test_a_new_example_uses_the_previous_topic_if_the_operation_is_implicit(manager):
    previous = "Operating system"
    question = "Vậy nếu có thêm hai chương trình chạy cùng lúc thì kết quả là gì?"
    response = manager.answer_question("software_testing", question, [previous], model_name="lookup")
    assert response.status == "success"
    assert response.context_question == previous
    assert response.sources[0].page == 1
