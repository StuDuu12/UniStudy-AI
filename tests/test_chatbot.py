import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from services import chatbot_service
from services.chatbot_service import ChatbotService
from src.schemas import ChatRequest, Document, Source


@pytest.fixture
def demo_service(tmp_path, monkeypatch):
    for key in ("ENDPOINT", "MODEL", "API_KEY"):
        monkeypatch.delenv(f"UNISTUDY_AI_{key}", raising=False)

    class DemoIndex:
        issues = ()
        course_names = {}

        def __init__(self, data_dir, *, private=False):
            pass

        def documents(self, course_id):
            if course_id == "software_testing":
                return (Document("testing", "Kiểm thử.pdf", tmp_path / "test.pdf", "project_demo"),)
            return ()

        def search(self, course_id, question, limit=3):
            if "tương đương" in question or "tuong duong" in question:
                return (Source("testing", "Kiểm thử.pdf", 2, "testing_p2_c1", "Chia dữ liệu thành các lớp tương đương.", 0.6),)
            return ()

    monkeypatch.setattr(chatbot_service, "CourseIndex", DemoIndex)
    return tmp_path / "data"


@pytest.fixture
def provider(monkeypatch):
    calls = []
    result = {"http": 200, "body": {"status": "success", "answer": "Chia đầu vào thành các lớp.", "source_ids": ["S1"]}}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            calls.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            payload = {"choices": [{"message": {"content": json.dumps(result["body"])}}]}
            self.send_response(result["http"])
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        monkeypatch.setenv("UNISTUDY_AI_ENDPOINT", f"http://127.0.0.1:{server.server_port}/v1/chat/completions")
        monkeypatch.setenv("UNISTUDY_AI_MODEL", "test-model")
        try:
            yield calls, result
        finally:
            server.shutdown()
            thread.join()


def ask(service, question="Phân vùng tương đương là gì?", mode="lookup", course="software_testing"):
    return service.answer_question(ChatRequest("req-1", course, question, mode))


def test_offline_validation_and_no_source_states(demo_service):
    service = ChatbotService(demo_service)
    assert not service.ai_available
    result = ask(service)
    assert (result.request_id, result.status, result.sources[0].page) == ("req-1", "success", 2)
    assert ask(service, "  ").status == "invalid_input"
    assert ask(service, "a" * 1001).status == "invalid_input"
    assert ask(service, mode="other").status == "invalid_input"
    assert ask(service, "Vậy còn trường hợp kia?").status == "needs_clarification"
    assert ask(service, "Học phí bao nhiêu?").status == "insufficient_evidence"
    assert ask(service, course="algorithm_analysis").status == "no_documents"
    assert ask(service, course="unknown").status == "invalid_input"
    assert ask(service, mode="ai").status == "ai_unavailable"


def test_ai_only_calls_provider_with_evidence_and_uses_verified_sources(demo_service, provider):
    calls, _ = provider
    service = ChatbotService(demo_service)
    assert service.ai_available
    assert ask(service).status == "success"
    assert ask(service, "Học phí bao nhiêu?", "ai").status == "insufficient_evidence"
    assert calls == []
    result = ask(service, mode="ai")
    assert (result.status, result.answer) == ("success", "Chia đầu vào thành các lớp.")
    assert (result.sources[0].document_id, result.sources[0].page) == ("testing", 2)
    payload = json.loads(calls[0]["messages"][1]["content"])
    assert payload["evidence"][0]["id"] == "S1"


def test_auto_routes_by_question_and_calls_ai_only_with_evidence(demo_service, provider):
    calls, _ = provider
    service = ChatbotService(demo_service)
    for question in (
        "Phân vùng tương đương ở trang nào?",
        "Trích nguyên văn định nghĩa phân vùng tương đương.",
        "Tìm đoạn nói về phân vùng tương đương là gì.",
        "Phân vùng tương đương là gì? Không dùng AI.",
    ):
        response = ask(service, question, "auto")
        assert (response.status, response.mode, response.sources[0].page) == ("success", "lookup", 2)
    assert ask(service, "Học phí là gì?", "auto").status == "insufficient_evidence"
    assert not calls

    for question in (
        "Phân vùng tương đương là gì?",
        "Phan vung tuong duong la gi?",
        "Giải thích phân vùng tương đương và cho biết ở trang nào.",
    ):
        response = ask(service, question, "auto")
        assert (response.status, response.mode, response.sources[0].page) == ("success", "ai", 2)
    assert len(calls) == 3


def test_auto_falls_back_when_ai_is_not_configured(demo_service):
    response = ask(ChatbotService(demo_service), mode="auto")
    assert (response.status, response.mode, response.sources[0].page) == ("success", "lookup", 2)
    assert response.message


@pytest.mark.parametrize(
    ("http", "body", "status"),
    [
        (200, {"status": "insufficient_evidence", "answer": "", "source_ids": []}, "insufficient_evidence"),
        (200, {"status": "success", "answer": "Sai nguồn", "source_ids": ["S999"]}, "error"),
        (429, {}, "ai_unavailable"),
    ],
)
def test_ai_refusal_and_failures(demo_service, provider, http, body, status):
    _, result = provider
    result.update(http=http, body=body)
    response = ask(ChatbotService(demo_service), mode="ai")
    assert response.status == status
    assert response.sources == ()
    assert response.message

    automatic = ask(ChatbotService(demo_service), mode="auto")
    if status == "insufficient_evidence":
        assert automatic.status == status
        assert automatic.sources == ()
    else:
        assert (automatic.status, automatic.mode, automatic.sources[0].page) == ("success", "lookup", 2)
        assert automatic.message


def test_private_library_blocks_remote_ai(demo_service, monkeypatch):
    monkeypatch.setenv("UNISTUDY_AI_ENDPOINT", "https://example.invalid/v1/chat/completions")
    monkeypatch.setenv("UNISTUDY_AI_MODEL", "test-model")
    monkeypatch.setenv("UNISTUDY_AI_API_KEY", "test-key")
    assert ChatbotService(demo_service).ai_available
    private = ChatbotService(demo_service / "local_course_pdfs", private=True)
    assert not private.ai_available
    assert [course.course_id for course in private.courses()] == [
        "tin_hoc_dai_cuong", "toan_roi_rac", "thu_thap_phan_tich_yeu_cau"
    ]
