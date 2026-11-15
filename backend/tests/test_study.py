import json
from pathlib import Path
from shutil import copy2
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import llm_service
from backend.services.course_manager import CourseManager
from backend.services.llm_service import AIConfig


MATH_COURSE = "/api/study/toan_roi_rac"
REQUIREMENTS_COURSE = "/api/study/thu_thap_phan_tich_yeu_cau"
UNION = f"{MATH_COURSE}/union"
FUNCTIONAL = f"{REQUIREMENTS_COURSE}/functional"
DEMO_DOCUMENTS = ("discrete_math_study", "requirements_study")


@pytest.fixture
def client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    source_data = Path(__file__).resolve().parents[2] / "data"
    (data / "demo_licensed").mkdir(parents=True)
    for document in DEMO_DOCUMENTS:
        copy2(source_data / "demo_licensed" / f"{document}.pdf", data / "demo_licensed")
    header, *records = (source_data / "manifest.csv").read_text(encoding="utf-8").splitlines()
    selected = [record for record in records if record.split(",")[1] in DEMO_DOCUMENTS]
    (data / "manifest.csv").write_text("\n".join([header, *selected]) + "\n", encoding="utf-8")
    for name in ("ENDPOINT", "MODEL", "API_KEY"):
        monkeypatch.delenv(f"UNISTUDY_AI_{name}", raising=False)
    manager = CourseManager(tmp_path)
    monkeypatch.setattr(app.state, "course_manager", manager)
    with TestClient(app) as http:
        yield http


def session_fields(turn_result):
    return {key: turn_result[key] for key in ("session_id", "revision")}


def turn(client, path, action, previous=None, **fields):
    payload = {"action": action, **fields}
    if previous is not None:
        payload.update(session_fields(previous))
    result = client.post(path, json=payload)
    assert result.status_code == 200, result.json()
    return result.json()


def practice(client, path=UNION):
    explanation = turn(client, path, "explain")
    return turn(client, path, "practice", explanation)


@pytest.mark.parametrize(("course", "topic"), [(MATH_COURSE, "union"), (REQUIREMENTS_COURSE, "functional")])
def test_each_course_lists_its_licensed_lesson(client, course, topic):
    response = client.get(course)
    assert response.status_code == 200
    catalog = response.json()
    assert catalog["ai_configured"] is False
    assert [(item["id"], item["page"]) for item in catalog["topics"]] == [(topic, 1)]


@pytest.mark.parametrize(("path", "answer", "mistake", "feedback", "document_id"), [
    (UNION, "4", "confuses_intersection", "phần giao", "discrete_math_study"),
    (FUNCTIONAL, "2; 4", "confuses_nonfunctional", "phi chức năng", "requirements_study"),
])
def test_detects_each_misconception_and_cites_its_own_document(client, path, answer, mistake, feedback, document_id):
    first = turn(client, path, "view")
    assert first["state"]["step"] == "diagnose"
    assert first["lesson"] is None and first["sources"] == []
    result = turn(client, path, "submit", first, answer=answer)
    assert result["state"]["step"] == "explain"
    assert result["state"]["diagnosis"] == mistake
    assert feedback in result["feedback"]
    assert result["lesson"]
    assert {(item["document_id"], item["page"]) for item in result["sources"]} == {(document_id, 1)}
    assert client.get(f"/api/documents/{document_id}/page/1/pdf").headers["content-type"] == "application/pdf"


def test_identifies_a_correct_diagnostic_answer_without_marking_mastery(client):
    result = turn(client, UNION, "submit", answer="8 1 7 4")
    assert result["state"]["diagnosis"] == "correct"
    assert result["state"]["last_result"] is None


def test_copying_the_pdf_union_example_does_not_pass_diagnosis(client):
    copied_example = turn(client, UNION, "submit", answer="-2 4 9")
    assert copied_example["state"]["diagnosis"] != "correct"


def test_can_request_explanation_first_and_then_get_a_new_problem(client):
    explain = turn(client, UNION, "explain")
    assert explain["state"]["diagnosis"] is None
    assert "Phép hợp" in explain["lesson"]
    result = turn(client, UNION, "practice", explain)
    assert "{-3, 2, 5}" in result["prompt"]
    assert result["lesson"] is None and result["sources"] == []


@pytest.mark.parametrize(("path", "answer"), [
    (UNION, "6, -3, 5, 2"),
    (FUNCTIONAL, "4; 2"),
])
def test_first_unaided_correct_attempt_records_independent_result(client, path, answer):
    start = practice(client, path)
    result = turn(client, path, "submit", start, answer=answer)
    assert result["state"]["step"] == "review"
    assert result["state"]["last_result"] == "independent"
    assert result["lesson"] and result["sources"]


def test_wrong_attempt_feedback_and_recurrence_are_preserved_on_resume(client):
    start = practice(client)
    wrong = turn(client, UNION, "submit", start, answer="2")
    assert wrong["state"]["step"] == "practice"
    assert "phần giao" in wrong["feedback"]
    assert wrong["lesson"] is None
    wrong_again = turn(client, UNION, "submit", wrong, answer="2, 2")
    assert wrong_again["state"]["mistake_count"] == 2
    app.state.course_manager = CourseManager(app.state.course_manager.project_root)
    resumed = turn(client, UNION, "view", wrong_again)
    assert resumed == wrong_again
    corrected = turn(client, UNION, "submit", resumed, answer="-3 2 5 6")
    assert corrected["state"]["last_result"] == "needs_practice"


def test_two_progressive_hints_and_guided_completion(client):
    start = practice(client, FUNCTIONAL)
    first = turn(client, FUNCTIONAL, "hint", start)
    second = turn(client, FUNCTIONAL, "hint", first)
    assert (first["state"]["hint_level"], second["state"]["hint_level"]) == (1, 2)
    assert first["hint"] != second["hint"]
    assert "hành động" in second["hint"] and "2, 4" not in second["hint"]
    extra = client.post(FUNCTIONAL, json={"action": "hint", **session_fields(second)})
    assert extra.status_code == 409
    correct = turn(client, FUNCTIONAL, "submit", second, answer="2 4")
    assert correct["state"]["last_result"] == "needs_practice"


def test_solution_is_gated_and_review_uses_new_data(client):
    start = practice(client)
    assert client.post(UNION, json={"action": "solution", **session_fields(start)}).status_code == 409
    wrong = turn(client, UNION, "submit", start, answer="-3 5 7")
    review = turn(client, UNION, "solution", wrong)
    assert review["state"]["last_result"] == "needs_practice"
    assert "-3, 2, 5, 6" in review["lesson"]
    retry = turn(client, UNION, "retry", review)
    assert retry["state"]["step"] == "practice"
    assert retry["state"]["last_result"] == "needs_practice"
    assert "{2, 9}" in retry["prompt"]
    assert retry["state"]["hint_level"] == 0 and retry["feedback"] is None
    correct = turn(client, UNION, "submit", retry, answer="-2 2 9 11")
    assert correct["state"]["last_result"] == "independent"


@pytest.mark.parametrize("answer", [" ", "abc", "4.5 6 13", "4,,7,13", "1 2 3 4 5 6 7 8 9 10 11 12 13"])
def test_invalid_numeric_input_does_not_consume_an_attempt(client, answer):
    start = practice(client)
    invalid = client.post(UNION, json={"action": "submit", **session_fields(start), "answer": answer})
    assert invalid.status_code == 422
    correct = turn(client, UNION, "submit", start, answer="-3 2 5 6")
    assert correct["state"]["last_result"] == "independent"


def test_duplicate_values_do_not_count_as_coverage(client):
    start = practice(client)
    result = turn(client, UNION, "submit", start, answer="-3 2 5 6 6")
    assert result["state"]["step"] == "practice"
    assert result["state"]["practice_mistake"] == "extra_values"


def test_forged_review_state_and_unknown_topic_are_rejected(client):
    assert client.post(UNION, json={"action": "practice"}).status_code == 409
    forged = client.post(UNION, json={
        "action": "view", "state": {"step": "review", "last_result": "independent"},
    })
    assert forged.status_code == 422
    assert "-3, 2, 5, 6" not in forged.text
    assert client.post(f"{MATH_COURSE}/made-up", json={"action": "view"}).status_code == 404


def test_stale_or_cross_topic_sessions_cannot_change_progress(client):
    start = practice(client)
    changed = turn(client, UNION, "hint", start)
    stale = client.post(UNION, json={"action": "submit", **session_fields(start), "answer": "-3 2 5 6"})
    assert stale.status_code == 409
    assert turn(client, UNION, "view", start) == changed
    assert client.post(FUNCTIONAL, json={"action": "view", **session_fields(start)}).status_code == 404


def test_reopening_a_preallocated_session_recovers_a_lost_first_response(client):
    session_id = str(uuid4())
    first = turn(client, UNION, "open", session_id=session_id)
    second_tab = turn(client, UNION, "open", session_id=session_id)
    assert first == second_tab and first["state"]["step"] == "diagnose"
    first_send = client.post(UNION, json={
        "action": "submit", **session_fields(first), "answer": "4",
    })
    assert first_send.status_code == 200
    # The browser already had this ID even if it could not read first_send.
    resumed = turn(client, UNION, "open", session_id=session_id)
    assert resumed["state"]["step"] == "explain" and resumed["revision"] == first["revision"] + 1
    assert client.post(FUNCTIONAL, json={"action": "open", "session_id": session_id}).status_code == 404


def test_unknown_session_never_starts_over_or_reveals_solution(client):
    response = client.post(UNION, json={
        "action": "view", "session_id": "842f73ec-4791-4e97-87ef-72b28cb63e34",
    })
    assert response.status_code == 404
    assert "-3, 2, 5, 6" not in response.text


def test_unwritable_progress_is_reported_and_a_retry_can_start(client):
    db_path = app.state.course_manager.data_dir / "study_progress.sqlite3"
    db_path.mkdir()
    response = client.post(UNION, json={"action": "explain"})
    assert response.status_code == 503
    assert "tiến độ" in response.json()["detail"]
    db_path.rmdir()
    result = turn(client, UNION, "explain")
    assert result["session_id"] and result["revision"] == 1


def test_missing_or_private_demo_sources_cannot_be_used(client):
    manager = app.state.course_manager
    private = manager.data_dir / "local_course_pdfs"
    private.mkdir()
    (private / "discrete_math_study.pdf").write_bytes(
        (manager.data_dir / "demo_licensed" / "discrete_math_study.pdf").read_bytes()
    )
    (private / "manifest.csv").write_text(
        "course_id,document_id,document_name,path,license\n"
        "toan_roi_rac,discrete_math_study,discrete_math_study.pdf,discrete_math_study.pdf,local_only\n",
        encoding="utf-8",
    )
    (manager.data_dir / "manifest.csv").unlink()
    app.state.course_manager = CourseManager(manager.project_root)
    assert app.state.course_manager.get_document_info("discrete_math_study").license == "local_only"
    assert client.get(MATH_COURSE).json()["topics"] == []
    assert client.post(UNION, json={"action": "ai"}).status_code == 404


def test_unconfigured_api_preserves_lesson_and_progress(client):
    explain = turn(client, UNION, "explain")
    result = turn(client, UNION, "ai", explain)
    assert result["ai_status"] == "not_configured"
    assert result["ai_answer"] is None
    assert result["lesson"] == explain["lesson"] and result["state"] == explain["state"]


@pytest.mark.parametrize(("provider_reply", "expected"), [
    ({"status": "success", "answer": "Giải thích theo tài liệu [S1].", "source_ids": ["S1"]}, "used"),
    ({"status": "success", "answer": "Nguồn sai [S99].", "source_ids": ["S99"]}, "unavailable"),
    ({"status": "success", "answer": "Không dẫn trong bài.", "source_ids": ["S1"]}, "unavailable"),
    ({"status": "insufficient_evidence", "answer": "", "source_ids": []}, "insufficient_evidence"),
])
def test_api_enrichment_checks_citations_and_falls_back(client, monkeypatch, provider_reply, expected):
    requests = []
    raw = json.dumps({"choices": [{"message": {"content": json.dumps(provider_reply)}}]}).encode()

    class Connection:
        def __init__(self, *_args, **_kwargs):
            pass

        def request(self, _method, _path, body, _headers):
            requests.append(json.loads(body))

        def getresponse(self):
            return SimpleNamespace(status=200, read=lambda _: raw)

        def close(self):
            pass

    monkeypatch.setattr(llm_service, "HTTPSConnection", Connection)
    app.state.course_manager._ai = AIConfig("https://example.test/v1/chat/completions", "test-model", "test-key")
    explain = turn(client, UNION, "submit", answer="4, 4")
    result = turn(client, UNION, "ai", explain)
    assert result["ai_status"] == expected
    assert result["lesson"] == explain["lesson"] and result["state"] == explain["state"]
    assert {s["page"] for s in result["sources"]} == {1}
    if expected == "used":
        assert result["ai_answer"] == "Giải thích theo tài liệu [1]."
        assert result["ai_sources"][0]["chunk_id"] == result["sources"][0]["chunk_id"]
    else:
        assert result["ai_answer"] is None and result["ai_sources"] == []
    assert len(requests) == 1
    model_input = json.loads(requests[0]["messages"][1]["content"])
    assert "phần giao" in model_input["question"]
    assert "4, 4" not in model_input["question"]
    assert "{-3, 2, 5}" not in model_input["question"]


@pytest.mark.parametrize("status", [401, 429, 503])
def test_provider_failures_preserve_the_study_flow(client, monkeypatch, status):
    class Connection:
        def __init__(self, *_args, **_kwargs):
            pass

        def request(self, *_args):
            pass

        def getresponse(self):
            return SimpleNamespace(status=status)

        def close(self):
            pass

    monkeypatch.setattr(llm_service, "HTTPSConnection", Connection)
    monkeypatch.setattr(llm_service, "sleep", lambda _: None)
    app.state.course_manager._ai = AIConfig("https://example.test/v1/chat/completions", "test-model", "test-key")
    explain = turn(client, FUNCTIONAL, "explain")
    result = turn(client, FUNCTIONAL, "ai", explain)
    assert result["ai_status"] == "unavailable"
    assert result["ai_message"] and "test-key" not in str(result)
    assert turn(client, FUNCTIONAL, "practice", result)["state"]["step"] == "practice"
