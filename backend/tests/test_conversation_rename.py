from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers import conversations
from backend.services.course_manager import CourseManager


def test_rename_survives_a_later_message_save(tmp_path):
    app = FastAPI()
    app.state.course_manager = CourseManager(tmp_path)
    app.include_router(conversations.router, prefix="/api")
    client = TestClient(app)
    path = "/api/conversations/thread"
    question = {"id": "q1", "sender": "user", "content": "Câu hỏi", "timestamp": "10:00"}
    thread = {
        "id": "thread", "course_id": "math", "title": "Tên cũ",
        "updated_at": 1, "messages": [question],
    }

    assert client.post("/api/conversations", json=thread).status_code == 200
    renamed = client.patch(path, json={"title": "  Tên mới  "})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Tên mới"
    first_version = renamed.json()["title_version"]
    assert first_version > 0
    assert renamed.json()["updated_at"] == thread["updated_at"]
    repeated = client.patch(path, json={"title": "Tên mới"}).json()
    assert repeated["title"] == "Tên mới"
    assert repeated["title_version"] > first_version

    reply = {"id": "a1", "sender": "assistant", "content": "Trả lời", "timestamp": "10:01", "reply_to": "q1"}
    stale_title = {**thread, "updated_at": 2, "messages": [question, reply]}
    saved = client.post("/api/conversations", json=stale_title).json()
    assert saved["title"] == "Tên mới"
    assert saved["title_version"] == repeated["title_version"]
    assert saved["updated_at"] == 2
    assert [message["id"] for message in saved["messages"]] == ["q1", "a1"]

    for invalid in ("   ", "a" * 201):
        assert client.patch(path, json={"title": invalid}).status_code == 422
    assert client.patch("/api/conversations/missing", json={"title": "Tên mới"}).status_code == 404
    assert CourseManager(tmp_path).get_conversations()[0].title == "Tên mới"
