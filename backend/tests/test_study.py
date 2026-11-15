import json
from pathlib import Path
from shutil import copytree
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import llm_service
from backend.services.course_manager import CourseManager
from backend.services.llm_service import AIConfig


COURSE = "/api/study/software_testing"
EQUIVALENCE = f"{COURSE}/equivalence"
BOUNDARY = f"{COURSE}/boundary"


@pytest.fixture
def client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    source_data = Path(__file__).resolve().parents[2] / "data"
    copytree(source_data / "demo_licensed", data / "demo_licensed")
    (data / "manifest.csv").write_bytes((source_data / "manifest.csv").read_bytes())
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


def practice(client, path=EQUIVALENCE):
    explanation = turn(client, path, "explain")
    return turn(client, path, "practice", explanation)


def test_curriculum_lists_two_topics_with_licensed_sources(client):
    response = client.get(COURSE)
    assert response.status_code == 200
    catalog = response.json()
    assert catalog["ai_configured"] is False
    assert [(topic["id"], topic["page"]) for topic in catalog["topics"]] == [
        ("equivalence", 2), ("boundary", 3),
    ]
    assert client.get("/api/study/algorithm_analysis").json()["topics"] == []
    assert client.get("/api/study/unknown").status_code == 404


@pytest.mark.parametrize("answer", ["21, 24, 28", "2, 10, 20", "29, 35, 80"])
def test_diagnoses_three_values_in_same_partition_and_points_to_page_two(client, answer):
    first = turn(client, EQUIVALENCE, "view")
    assert first["state"]["step"] == "diagnose"
    assert "21 đến 28" in first["prompt"]
    assert first["lesson"] is None and first["sources"] == []
    result = turn(client, EQUIVALENCE, "submit", first, answer=answer)
    assert result["state"]["step"] == "explain"
    assert result["state"]["diagnosis"] == "one_partition"
    assert "cùng một lớp" in result["feedback"]
    assert "trong khoảng" in result["feedback"]
    assert result["lesson"]
    assert {(s["document_id"], s["page"]) for s in result["sources"]} == {("testing_basics", 2)}
    assert client.get("/api/documents/testing_basics/page/2/pdf").headers["content-type"] == "application/pdf"


def test_diagnoses_only_endpoints_and_cites_page_three(client):
    result = turn(client, BOUNDARY, "submit", answer="2; 20")
    assert result["state"]["diagnosis"] == "only_endpoints"
    assert "kề" in result["feedback"]
    assert {s["page"] for s in result["sources"]} == {3}


def test_identifies_a_correct_diagnostic_answer_without_marking_mastery(client):
    result = turn(client, EQUIVALENCE, "submit", answer="30 16 24")
    assert result["state"]["diagnosis"] == "correct"
    assert result["state"]["last_result"] is None


def test_copying_the_pdf_equivalence_example_does_not_pass_diagnosis(client):
    copied_example = turn(client, EQUIVALENCE, "submit", answer="16 30 70")
    assert copied_example["state"]["diagnosis"] != "correct"


def test_can_request_explanation_first_and_then_get_a_new_problem(client):
    explain = turn(client, EQUIVALENCE, "explain")
    assert explain["state"]["diagnosis"] is None
    assert "giá trị đại diện" in explain["lesson"]
    result = turn(client, EQUIVALENCE, "practice", explain)
    assert "5 đến 12" in result["prompt"]
    assert result["lesson"] is None and result["sources"] == []


@pytest.mark.parametrize(("path", "answer"), [
    (EQUIVALENCE, "13, 8, 4"),
    (BOUNDARY, "11; 10 9, 2 1 0"),
])
def test_first_unaided_correct_attempt_records_independent_result(client, path, answer):
    start = practice(client, path)
    result = turn(client, path, "submit", start, answer=answer)
    assert result["state"]["step"] == "review"
    assert result["state"]["last_result"] == "independent"
    assert result["lesson"] and result["sources"]


def test_wrong_attempt_feedback_and_recurrence_are_preserved_on_resume(client):
    start = practice(client)
    wrong = turn(client, EQUIVALENCE, "submit", start, answer="5 7 12")
    assert wrong["state"]["step"] == "practice"
    assert "cùng một lớp" in wrong["feedback"]
    assert wrong["lesson"] is None
    wrong_again = turn(client, EQUIVALENCE, "submit", wrong, answer="6 8 11")
    assert wrong_again["state"]["mistake_count"] == 2
    app.state.course_manager = CourseManager(app.state.course_manager.project_root)
    resumed = turn(client, EQUIVALENCE, "view", wrong_again)
    assert resumed == wrong_again
    corrected = turn(client, EQUIVALENCE, "submit", resumed, answer="4 7 13")
    assert corrected["state"]["last_result"] == "needs_practice"


def test_two_progressive_hints_and_guided_completion(client):
    start = practice(client, BOUNDARY)
    first = turn(client, BOUNDARY, "hint", start)
    second = turn(client, BOUNDARY, "hint", first)
    assert (first["state"]["hint_level"], second["state"]["hint_level"]) == (1, 2)
    assert first["hint"] != second["hint"]
    assert "0, 1, 2, 9, 10, 11" not in second["hint"]
    extra = client.post(BOUNDARY, json={"action": "hint", **session_fields(second)})
    assert extra.status_code == 409
    correct = turn(client, BOUNDARY, "submit", second, answer="0 1 2 9 10 11")
    assert correct["state"]["last_result"] == "needs_practice"


def test_solution_is_gated_and_review_uses_new_data(client):
    start = practice(client)
    assert client.post(EQUIVALENCE, json={"action": "solution", **session_fields(start)}).status_code == 409
    wrong = turn(client, EQUIVALENCE, "submit", start, answer="5 6 7")
    review = turn(client, EQUIVALENCE, "solution", wrong)
    assert review["state"]["last_result"] == "needs_practice"
    assert "4, 5, 13" in review["lesson"]
    retry = turn(client, EQUIVALENCE, "retry", review)
    assert retry["state"]["step"] == "practice"
    assert retry["state"]["last_result"] == "needs_practice"
    assert "3 đến 9" in retry["prompt"]
    assert retry["state"]["hint_level"] == 0 and retry["feedback"] is None
    correct = turn(client, EQUIVALENCE, "submit", retry, answer="2 6 10")
    assert correct["state"]["last_result"] == "independent"


@pytest.mark.parametrize("answer", [" ", "abc", "4.5 6 13", "4,,7,13", "1 2 3 4 5 6 7 8 9 10 11 12 13"])
def test_invalid_numeric_input_does_not_consume_an_attempt(client, answer):
    start = practice(client)
    invalid = client.post(EQUIVALENCE, json={"action": "submit", **session_fields(start), "answer": answer})
    assert invalid.status_code == 422
    correct = turn(client, EQUIVALENCE, "submit", start, answer="4 7 13")
    assert correct["state"]["last_result"] == "independent"


def test_duplicate_values_do_not_count_as_coverage(client):
    start = practice(client)
    result = turn(client, EQUIVALENCE, "submit", start, answer="4 7 13 13")
    assert result["state"]["step"] == "practice"
    assert result["state"]["practice_mistake"] == "extra_values"


def test_forged_review_state_and_unknown_topic_are_rejected(client):
    assert client.post(EQUIVALENCE, json={"action": "practice"}).status_code == 409
    forged = client.post(EQUIVALENCE, json={
        "action": "view", "state": {"step": "review", "last_result": "independent"},
    })
    assert forged.status_code == 422
    assert "4, 5, 13" not in forged.text
    assert client.post(f"{COURSE}/made-up", json={"action": "view"}).status_code == 404


def test_stale_or_cross_topic_sessions_cannot_change_progress(client):
    start = practice(client)
    changed = turn(client, EQUIVALENCE, "hint", start)
    stale = client.post(EQUIVALENCE, json={"action": "submit", **session_fields(start), "answer": "4 7 13"})
    assert stale.status_code == 409
    assert turn(client, EQUIVALENCE, "view", start) == changed
    assert client.post(BOUNDARY, json={"action": "view", **session_fields(start)}).status_code == 404


def test_reopening_a_preallocated_session_recovers_a_lost_first_response(client):
    session_id = str(uuid4())
    first = turn(client, EQUIVALENCE, "open", session_id=session_id)
    second_tab = turn(client, EQUIVALENCE, "open", session_id=session_id)
    assert first == second_tab and first["state"]["step"] == "diagnose"
    first_send = client.post(EQUIVALENCE, json={
        "action": "submit", **session_fields(first), "answer": "22 24 26",
    })
    assert first_send.status_code == 200
    # The browser already had this ID even if it could not read first_send.
    resumed = turn(client, EQUIVALENCE, "open", session_id=session_id)
    assert resumed["state"]["step"] == "explain" and resumed["revision"] == first["revision"] + 1
    assert client.post(BOUNDARY, json={"action": "open", "session_id": session_id}).status_code == 404


def test_unknown_session_never_starts_over_or_reveals_solution(client):
    response = client.post(EQUIVALENCE, json={
        "action": "view", "session_id": "842f73ec-4791-4e97-87ef-72b28cb63e34",
    })
    assert response.status_code == 404
    assert "4, 5, 13" not in response.text


def test_unwritable_progress_is_reported_and_a_retry_can_start(client):
    db_path = app.state.course_manager.data_dir / "study_progress.sqlite3"
    db_path.mkdir()
    response = client.post(EQUIVALENCE, json={"action": "explain"})
    assert response.status_code == 503
    assert "tiến độ" in response.json()["detail"]
    db_path.rmdir()
    result = turn(client, EQUIVALENCE, "explain")
    assert result["session_id"] and result["revision"] == 1


def test_missing_or_private_demo_sources_cannot_be_used(client):
    manager = app.state.course_manager
    private = manager.data_dir / "local_course_pdfs"
    private.mkdir()
    (private / "software_testing.pdf").write_bytes(
        (manager.data_dir / "demo_licensed" / "software_testing.pdf").read_bytes()
    )
    (private / "manifest.csv").write_text(
        "course_id,document_id,document_name,path,license\n"
        "software_testing,testing_basics,software_testing.pdf,software_testing.pdf,local_only\n",
        encoding="utf-8",
    )
    (manager.data_dir / "manifest.csv").unlink()
    app.state.course_manager = CourseManager(manager.project_root)
    assert app.state.course_manager.get_document_info("testing_basics").license == "local_only"
    assert client.get(COURSE).json()["topics"] == []
    assert client.post(EQUIVALENCE, json={"action": "ai"}).status_code == 404


def test_unconfigured_api_preserves_lesson_and_progress(client):
    explain = turn(client, EQUIVALENCE, "explain")
    result = turn(client, EQUIVALENCE, "ai", explain)
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
    explain = turn(client, EQUIVALENCE, "submit", answer="21 24 28")
    result = turn(client, EQUIVALENCE, "ai", explain)
    assert result["ai_status"] == expected
    assert result["lesson"] == explain["lesson"] and result["state"] == explain["state"]
    assert {s["page"] for s in result["sources"]} == {2}
    if expected == "used":
        assert result["ai_answer"] == "Giải thích theo tài liệu [1]."
        assert result["ai_sources"][0]["chunk_id"] == result["sources"][0]["chunk_id"]
    else:
        assert result["ai_answer"] is None and result["ai_sources"] == []
    assert len(requests) == 1
    model_input = json.loads(requests[0]["messages"][1]["content"])
    assert "cùng một lớp" in model_input["question"]
    assert "21 24 28" not in model_input["question"]
    assert "5 đến 12" not in model_input["question"]


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
    explain = turn(client, BOUNDARY, "explain")
    result = turn(client, BOUNDARY, "ai", explain)
    assert result["ai_status"] == "unavailable"
    assert result["ai_message"] and "test-key" not in str(result)
    assert turn(client, BOUNDARY, "practice", result)["state"]["step"] == "practice"
