from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import State

from backend.main import app
from backend.services.course_manager import CourseManager

client = TestClient(app)


@pytest.fixture(autouse=True)
def seeded_manager(tmp_path, monkeypatch):
    data = tmp_path / "data"
    private = data / "local_course_pdfs"
    private.mkdir(parents=True)
    seed_document(
        private, "tin_hoc_dai_cuong", "local_only", "operating_system.pdf",
        "He dieu hanh co nhung chuc nang gi?\nQuan ly tai nguyen va thuc hien chuong trinh.",
    )
    seed_document(data, "software_testing", "project_demo", "seed-testing.pdf", "Software testing fundamentals")
    # Replace the state object so pytest can restore it without dynamic-attribute hooks.
    monkeypatch.setattr(app, "state", State({"course_manager": CourseManager(tmp_path)}))


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_courses():
    response = client.get("/api/courses")
    assert response.status_code == 200
    data = response.json()
    assert "courses" in data
    course_ids = [c["course_id"] for c in data["courses"]]
    assert "tin_hoc_dai_cuong" in course_ids
    thdc = next(c for c in data["courses"] if c["course_id"] == "tin_hoc_dai_cuong")
    assert len(thdc["suggested_questions"]) > 0
    assert "Hệ điều hành có những chức năng gì?" in thdc["suggested_questions"]
    assert "software_testing" in course_ids
    for course in data["courses"]:
        assert "course_name" in course
        assert "document_count" in course
        assert "status" in course


def test_rename_course_keeps_identity_and_sources_after_restart(tmp_path, monkeypatch):
    course_id = "tin_hoc_dai_cuong"
    route = f"/api/courses/{course_id}"
    response = client.patch(route, json={"course_name": "  Nhập môn   tin học  "})
    assert response.status_code == 200
    assert response.json()["course_name"] == "Nhập môn tin học"
    assert response.json()["course_id"] == course_id
    assert response.json()["document_count"] == 1

    monkeypatch.setattr(app.state, "course_manager", CourseManager(tmp_path))
    courses = client.get("/api/courses").json()["courses"]
    assert next(course for course in courses if course["course_id"] == course_id)["course_name"] == "Nhập môn tin học"
    result = client.post("/api/chat", json={"course_id": course_id, "question": "Hệ điều hành có những chức năng gì?"})
    assert result.json()["sources"][0]["document_id"] == "seed_tin_hoc_dai_cuong"
    assert client.patch(route, json={"course_name": "Kiểm thử phần mềm"}).status_code == 400
    assert client.patch(route, json={"course_name": "   "}).status_code == 400


def test_delete_course_hides_catalog_and_search_but_retains_data(tmp_path, monkeypatch):
    course_id = "tin_hoc_dai_cuong"
    route = f"/api/courses/{course_id}"
    pdf = app.state.course_manager.get_document_info("seed_tin_hoc_dai_cuong").path
    conversation = {"id": "retained", "course_id": course_id, "title": "Lịch sử", "updated_at": 1}
    assert client.post("/api/conversations", json=conversation).status_code == 200

    assert client.delete(route).status_code == 204
    assert client.delete(route).status_code == 404
    assert client.patch(route, json={"course_name": "Tên mới"}).status_code == 404
    assert client.post(f"{route}/documents", files=[pdf_file("new.pdf", "operating system")]).status_code == 404
    assert client.get("/api/documents/seed_tin_hoc_dai_cuong").status_code == 404
    assert pdf.is_file()

    monkeypatch.setattr(app.state, "course_manager", CourseManager(tmp_path))
    assert course_id not in {c["course_id"] for c in client.get("/api/courses").json()["courses"]}
    assert client.get(f"{route}/documents").status_code == 404
    assert client.post("/api/chat", json={"course_id": course_id, "question": "Hệ điều hành là gì?"}).status_code == 404
    assert app.state.course_manager.get_conversations(course_id)[0].id == "retained"


def test_removed_course_name_can_be_reused_without_restoring_old_documents():
    old = client.post("/api/courses", data={"course_name": "Mạng máy tính"}, files=[pdf_file("old.pdf", "Old network handbook")])
    assert old.status_code == 201
    old_id = old.json()["course_id"]
    assert client.delete(f"/api/courses/{old_id}").status_code == 204

    new = client.post("/api/courses", data={"course_name": "Mạng máy tính"}, files=[pdf_file("new.pdf", "New network handbook")])
    assert new.status_code == 201
    assert new.json()["course_id"] != old_id
    assert old_id not in {c["course_id"] for c in client.get("/api/courses").json()["courses"]}
    documents = client.get(f"/api/courses/{new.json()['course_id']}/documents").json()["documents"]
    assert [document["document_name"] for document in documents] == ["new.pdf"]


def test_get_course_documents():
    response = client.get("/api/courses/tin_hoc_dai_cuong/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert [doc["document_name"] for doc in data["documents"]] == ["operating_system.pdf"]
    for doc in data["documents"]:
        assert "document_id" in doc
        assert "document_name" in doc
        assert doc["page_count"] > 0


def test_get_course_documents_not_found():
    response = client.get("/api/courses/unknown_course/documents")
    assert response.status_code == 404


def test_chat_empty_question():
    response = client.post(
        "/api/chat",
        json={"course_id": "tin_hoc_dai_cuong", "question": "   ", "mode": "lookup"},
    )
    assert response.status_code == 422


def test_chat_nonexistent_course():
    response = client.post(
        "/api/chat",
        json={"course_id": "unknown_course", "question": "Hệ điều hành?", "mode": "lookup"},
    )
    assert response.status_code == 404


def test_chat_ambiguous_question():
    response = client.post(
        "/api/chat",
        json={
            "course_id": "tin_hoc_dai_cuong",
            "question": "giải thích cái này giúp mình với",
            "mode": "lookup",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert len(data["sources"]) == 0


@pytest.mark.parametrize("question", [
    "Cho ví dụ?", "Có mấy loại?", "Trang nào?", "Giải thích cái này",
    "Nó có mấy loại?", "Cho tôi thêm ví dụ?", "Có ví dụ nào không?",
])
def test_contextual_follow_up_requires_a_prior_topic(question):
    response = client.post(
        "/api/chat", json={"course_id": "tin_hoc_dai_cuong", "question": question}
    )
    assert response.json()["status"] == "needs_clarification"
    assert response.json()["sources"] == []
    assert response.json()["context_question"] is None


def test_follow_up_uses_the_latest_meaningful_question():
    appended = client.post(
        "/api/courses/tin_hoc_dai_cuong/documents",
        files=[pdf_file("network.pdf", "Network sockets and datagrams")],
    )
    assert appended.status_code == 201
    response = client.post(
        "/api/chat",
        json={
            "course_id": "tin_hoc_dai_cuong",
            "question": "Cho ví dụ?",
            "previous_questions": ["Network sockets and datagrams", "Hệ điều hành có những chức năng gì?", "Co may loai?"],
        },
    )
    assert response.json()["status"] == "success"
    assert response.json()["sources"][0]["document_name"] == "operating_system.pdf"


def test_explicit_example_question_ignores_history():
    payload = {"course_id": "tin_hoc_dai_cuong", "question": "Cho ví dụ về hệ điều hành?"}
    standalone = client.post("/api/chat", json=payload).json()
    with_history = client.post(
        "/api/chat", json={**payload, "previous_questions": ["Network sockets and datagrams"]}
    ).json()

    assert standalone["status"] == "success"
    assert with_history == standalone


def test_context_question_preserves_the_topic_across_repeated_follow_ups():
    topic = "Hệ điều hành có những chức năng gì?"
    previous_questions = []
    questions = [topic, "Cho ví dụ?", "Nó có mấy loại?", "Trang nào?", "Cho tôi thêm ví dụ?", "Có ví dụ nào không?"]
    for question in questions:
        response = client.post(
            "/api/chat",
            json={"course_id": "tin_hoc_dai_cuong", "question": question, "previous_questions": previous_questions[-3:]},
        ).json()
        assert response["status"] == "success"
        assert response.get("context_question") == topic
        assert response["sources"][0]["document_name"] == "operating_system.pdf"
        previous_questions.append(response["context_question"])


def test_follow_up_history_never_crosses_the_selected_course():
    response = client.post(
        "/api/chat",
        json={
            "course_id": "software_testing",
            "question": "Trang nào?",
            "previous_questions": ["Hệ điều hành có những chức năng gì?"],
        },
    )
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["sources"] == []


@pytest.mark.parametrize("previous_questions", [["topic"] * 4, ["a" * 2001]])
def test_chat_bounds_previous_questions(previous_questions):
    response = client.post(
        "/api/chat",
        json={"course_id": "tin_hoc_dai_cuong", "question": "Cho ví dụ?", "previous_questions": previous_questions},
    )
    assert response.status_code == 422


def test_chat_insufficient_evidence():
    response = client.post(
        "/api/chat",
        json={
            "course_id": "tin_hoc_dai_cuong",
            "question": "Nấu lẩu Tom Yum",
            "mode": "lookup",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "insufficient_evidence"
    assert len(data["sources"]) == 0


def test_chat_lookup_success():
    response = client.post(
        "/api/chat",
        json={
            "course_id": "tin_hoc_dai_cuong",
            "question": "Hệ điều hành có những chức năng gì?",
            "mode": "lookup",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["mode"] == "lookup"
    assert len(data["sources"]) > 0
    first_source = data["sources"][0]
    assert "document_name" in first_source
    assert "page" in first_source
    assert "excerpt" in first_source
    assert first_source["page"] > 0


def test_legacy_ai_mode_uses_the_same_course_lookup():
    payload = {"course_id": "tin_hoc_dai_cuong", "question": "Hệ điều hành có những chức năng gì?"}
    response = client.post(
        "/api/chat",
        json={**payload, "mode": "ai"},
    )
    assert response.status_code == 200
    assert response.json() == client.post("/api/chat", json=payload).json()
    assert response.json()["mode"] == "lookup"
    assert response.json()["status"] == "success"


def pdf_file(name, text):
    with pymupdf.open() as document:
        document.new_page().insert_text((40, 60), text)
        return ("files", (name, document.tobytes(), "application/pdf"))


def seed_document(directory, course_id, license_type, name, text):
    (directory / name).write_bytes(pdf_file(name, text)[1][1])
    (directory / "manifest.csv").write_text(
        "course_id,document_id,document_name,path,license\n"
        f"{course_id},seed_{course_id},{name},{name},{license_type}\n",
        encoding="utf-8",
    )


def test_create_and_append_course_keep_retrieval_isolated_after_reload(tmp_path, monkeypatch):
    first = pdf_file("network.pdf", "Network sockets and datagrams")
    second = pdf_file("routing.pdf", "Distance vector routing tables")
    other = pdf_file("algebra.pdf", "Linear algebra matrices")

    created = client.post("/api/courses", data={"course_name": "Mạng máy tính"}, files=[first])
    assert created.status_code == 201
    course = created.json()
    assert course["course_name"] == "Mạng máy tính"
    assert course["document_count"] == 1
    path = f"/api/courses/{course['course_id']}/documents"

    appended = client.post(path, files=[second])
    assert appended.status_code == 201
    assert [doc["document_name"] for doc in appended.json()["documents"]] == ["network.pdf", "routing.pdf"]
    other_course = client.post("/api/courses", data={"course_name": "Đại số"}, files=[other]).json()

    monkeypatch.setattr(app.state, "course_manager", CourseManager(tmp_path))
    assert client.get(path).json() == appended.json()
    payload = {"course_id": course["course_id"], "question": "Distance vector routing tables"}
    answer = client.post("/api/chat", json=payload).json()
    assert answer["status"] == "success"
    assert answer["sources"][0]["document_name"] == "routing.pdf"
    outside = client.post("/api/chat", json={**payload, "course_id": other_course["course_id"]}).json()
    assert outside["status"] == "insufficient_evidence"
    assert outside["sources"] == []


def test_append_to_seeded_course_and_reject_unknown_course():
    files = [pdf_file("testing.pdf", "Boundary analysis example")]
    assert client.post("/api/courses/unknown/documents", files=files).status_code == 404
    response = client.post("/api/courses/software_testing/documents", files=files)
    assert response.status_code == 201
    assert [doc["document_name"] for doc in response.json()["documents"]] == ["seed-testing.pdf", "testing.pdf"]
    assert client.get("/api/courses/algorithm_analysis/documents").json()["documents"] == []


def test_invalid_upload_batch_does_not_create_course(tmp_path):
    private = tmp_path / "data" / "local_course_pdfs"
    manifest = private / "manifest.csv"
    previous = manifest.read_bytes()
    response = client.post(
        "/api/courses",
        data={"course_name": "Mạng máy tính"},
        files=[pdf_file("valid.pdf", "Network sockets"), ("files", ("invalid.pdf", b"invalid", "application/pdf"))],
    )
    assert response.status_code == 400
    assert manifest.read_bytes() == previous
    assert [path.name for path in private.glob("*.pdf")] == ["operating_system.pdf"]


def test_uploaded_source_preview_rejects_replaced_pdf():
    result = client.post(
        "/api/courses", data={"course_name": "Mạng máy tính"},
        files=[pdf_file("old.pdf", "Network sockets and datagrams")],
    )
    course_id = result.json()["course_id"]
    answer = client.post(
        "/api/chat", json={"course_id": course_id, "question": "Network sockets and datagrams"}
    ).json()
    source = answer["sources"][0]
    url = f"/api/documents/{source['document_id']}/page/1"
    assert source.get("document_sha256")
    preview = client.get(url, params={"sha256": source["document_sha256"]})
    assert preview.status_code == 200
    assert preview.content.startswith(b"\x89PNG")

    original = app.state.course_manager.get_document_info(source["document_id"])
    original.path.write_bytes(pdf_file("new.pdf", "Replacement content")[1][1])
    appended = client.post(
        f"/api/courses/{course_id}/documents", files=[pdf_file("other.pdf", "Network administration")]
    )
    assert appended.status_code == 201
    assert client.get(url, params={"sha256": source["document_sha256"]}).status_code == 409
    assert client.get(url).status_code == 200


def test_course_with_missing_pdf_remains_available_for_append(tmp_path, monkeypatch):
    created = client.post(
        "/api/courses", data={"course_name": "Mạng máy tính"},
        files=[pdf_file("missing.pdf", "Network sockets")],
    )
    course_id = created.json()["course_id"]
    url = f"/api/courses/{course_id}/documents"
    original = client.get(url).json()["documents"][0]
    app.state.course_manager.get_document_info(original["document_id"]).path.unlink()

    monkeypatch.setattr(app.state, "course_manager", CourseManager(tmp_path))
    listed = next(item for item in client.get("/api/courses").json()["courses"] if item["course_id"] == course_id)
    assert listed["status"] == "empty"
    assert client.get(url).json() == {"documents": []}
    repaired = client.post(url, files=[pdf_file("recovery.pdf", "Network sockets")])
    assert repaired.status_code == 201
    assert repaired.json()["documents"][0]["document_name"] == "recovery.pdf"


def test_upload_enforces_multipart_byte_cap(monkeypatch):
    monkeypatch.setattr("backend.routers.courses._MAX_UPLOAD_BYTES", 128)
    response = client.post(
        "/api/courses", data={"course_name": "Mạng máy tính"},
        files=[pdf_file("notes.pdf", "Network sockets")],
    )
    assert response.status_code == 413


def test_small_course_refuses_query_with_only_incidental_ngram_overlap():
    created = client.post(
        "/api/courses", data={"course_name": "Đại số"},
        files=[pdf_file("algebra.pdf", "Cosine identities and matrices")],
    )
    course_id = created.json()["course_id"]
    unrelated = client.post(
        "/api/chat", json={"course_id": course_id, "question": "Sapphire structures and directed graphs"}
    ).json()
    related = client.post(
        "/api/chat", json={"course_id": course_id, "question": "Cosine identities"}
    ).json()

    assert unrelated["status"] == "insufficient_evidence"
    assert unrelated["sources"] == []
    assert related["status"] == "success"


def test_get_document_info_returns_page_count_and_name():
    doc_id = "operating_system.pdf"
    docs = client.get("/api/courses/tin_hoc_dai_cuong/documents").json()["documents"]
    target_id = docs[0]["document_id"]
    res = client.get(f"/api/documents/{target_id}/info")
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == target_id
    assert data["document_name"] == "operating_system.pdf"
    assert data["page_count"] >= 1


def test_conversation_crud_persistence():
    # 1. Initially empty
    list_res = client.get("/api/conversations")
    assert list_res.status_code == 200

    # 2. Save conversation
    payload = {
        "id": "conv-test-1",
        "course_id": "tin_hoc_dai_cuong",
        "title": "Hệ điều hành có những chức năng gì?",
        "updated_at": 1794226810000,
        "messages": [
            {
                "id": "msg-1",
                "sender": "user",
                "content": "Hệ điều hành có những chức năng gì?",
                "timestamp": "19:30",
            },
            {
                "id": "msg-2",
                "sender": "assistant",
                "content": "Quản lý tài nguyên phần cứng và phần mềm.",
                "timestamp": "19:30",
                "status": "success",
            },
        ],
    }
    save_res = client.post("/api/conversations", json=payload)
    assert save_res.status_code == 200
    assert save_res.json()["id"] == "conv-test-1"

    # 3. Retrieve
    filtered = client.get("/api/conversations?course_id=tin_hoc_dai_cuong")
    assert filtered.status_code == 200
    items = filtered.json()["conversations"]
    assert any(c["id"] == "conv-test-1" for c in items)

    # 4. Delete
    del_res = client.delete("/api/conversations/conv-test-1")
    assert del_res.status_code == 200
    after_del = client.get("/api/conversations?course_id=tin_hoc_dai_cuong").json()["conversations"]
    assert not any(c["id"] == "conv-test-1" for c in after_del)


def test_late_conversation_save_preserves_replies_and_latest_activity():
    question = {"id": "q1", "sender": "user", "content": "Một", "timestamp": "19:30", "created_at": 1}
    next_question = {**question, "id": "q2", "content": "Hai", "created_at": 2}
    reply = {**question, "id": "a1", "sender": "assistant", "reply_to": "q1", "created_at": 3}
    first = {"id": "thread", "course_id": "software_testing", "title": "Gần nhất", "updated_at": 3,
             "messages": [question, next_question, reply]}
    assert client.post("/api/conversations", json=first).status_code == 200
    late = {**first, "title": "Cũ", "updated_at": 1, "messages": [question]}
    response = client.post("/api/conversations", json=late)
    assert response.status_code == 200
    assert [message["id"] for message in response.json()["messages"]] == ["q1", "a1", "q2"]
    assert response.json()["updated_at"] == 3
    assert response.json()["title"] == "Gần nhất"
    assert client.post("/api/conversations", json={**late, "course_id": "algorithm_analysis"}).status_code == 409


def test_corrupt_conversation_store_is_preserved(tmp_path):
    path = tmp_path / "data" / "conversations.json"
    broken = b'[{"id":"incomplete"'
    path.write_bytes(broken)
    payload = {"id": "thread", "course_id": "software_testing", "title": "Test", "updated_at": 1}
    assert client.get("/api/conversations").status_code == 500
    assert client.post("/api/conversations", json=payload).status_code == 500
    assert client.delete("/api/conversations/thread").status_code == 500
    assert path.read_bytes() == broken


def test_failed_conversation_replace_keeps_the_previous_file(tmp_path, monkeypatch):
    path = tmp_path / "data" / "conversations.json"
    payload = {"id": "thread", "course_id": "software_testing", "title": "Cũ", "updated_at": 1}
    assert client.post("/api/conversations", json=payload).status_code == 200
    before = path.read_bytes()
    existing_files = set(path.parent.iterdir())
    replace = Path.replace

    def fail_history_replace(staged, target):
        if target == path:
            raise OSError("Cannot replace fixture")
        return replace(staged, target)

    monkeypatch.setattr(Path, "replace", fail_history_replace)
    response = client.post("/api/conversations", json={**payload, "title": "Mới", "updated_at": 2})
    assert response.status_code == 500
    assert path.read_bytes() == before
    assert set(path.parent.iterdir()) == existing_files


def test_rename_conversation():
    payload = {
        "id": "conv-rename-test",
        "course_id": "tin_hoc_dai_cuong",
        "title": "Tiêu đề cũ",
        "updated_at": 1794226810000,
        "messages": [
            {
                "id": "msg-1",
                "sender": "user",
                "content": "Câu hỏi test",
                "timestamp": "19:30",
            },
        ],
    }
    save_res = client.post("/api/conversations", json=payload)
    assert save_res.status_code == 200

    # Rename
    patch_res = client.patch("/api/conversations/conv-rename-test", json={"title": "Tiêu đề mới"})
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Tiêu đề mới"
    assert patch_res.json()["id"] == "conv-rename-test"

    # Verify via get
    get_res = client.get("/api/conversations?course_id=tin_hoc_dai_cuong")
    assert get_res.status_code == 200
    conv = next(c for c in get_res.json()["conversations"] if c["id"] == "conv-rename-test")
    assert conv["title"] == "Tiêu đề mới"

    # Rename 404
    not_found = client.patch("/api/conversations/non-existent-id", json={"title": "Tiêu đề mới"})
    assert not_found.status_code == 404

    # Validation 422
    invalid = client.patch("/api/conversations/conv-rename-test", json={"title": ""})
    assert invalid.status_code == 422


