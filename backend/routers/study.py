import sqlite3

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from backend.schemas.study import StudyCatalog, StudyState, StudyTurn, StudyTurnRequest
from backend.services.study import LESSONS, STUDY_COURSE, STUDY_DOCUMENT, InvalidStudyAction, study_turn
from backend.services.study_progress import StaleStudyProgress, StudyProgress


router = APIRouter(prefix="/study", tags=["study"])
_STALE = "Tiến độ đã thay đổi. Hãy mở lại trạng thái mới nhất."
_STORAGE_ERROR = "Không thể truy cập tiến độ học đã lưu. Hãy thử lại."


@router.get("/{course_id}", response_model=StudyCatalog)
def get_study_catalog(course_id: str, request: Request):
    manager = request.app.state.course_manager
    if manager.get_course_documents(course_id) is None:
        raise HTTPException(404, "Không tìm thấy học phần.")
    topics = [
        lesson.topic for lesson in LESSONS.values()
        if manager.get_demo_page_chunks(course_id, STUDY_DOCUMENT, lesson.topic.page)
    ] if course_id == STUDY_COURSE else []
    return StudyCatalog(topics=topics, ai_configured=manager.ai_config is not None)


@router.post("/{course_id}/{topic_id}", response_model=StudyTurn)
def post_study_turn(course_id: str, topic_id: str, payload: StudyTurnRequest, request: Request):
    manager = request.app.state.course_manager
    lesson = LESSONS.get(topic_id) if course_id == STUDY_COURSE else None
    if lesson is None:
        raise HTTPException(404, "Học phần chưa có bài học này.")
    chunks = manager.get_demo_page_chunks(course_id, STUDY_DOCUMENT, lesson.topic.page)
    if not chunks:
        raise HTTPException(404, "Không tìm thấy trang học liệu của bài học.")

    progress = StudyProgress(manager.data_dir)
    saved = None
    opening = payload.action == "open"
    if payload.session_id is not None:
        try:
            saved = progress.read(course_id, topic_id, str(payload.session_id), create=opening)
        except (OSError, sqlite3.Error, ValidationError):
            raise HTTPException(503, _STORAGE_ERROR) from None
        if saved is None:
            raise HTTPException(404, "Không tìm thấy phiên học đã lưu.")
        if payload.action not in {"view", "open"} and payload.revision != saved.revision:
            raise HTTPException(409, _STALE)
    elif payload.revision is not None or opening:
        raise HTTPException(422, "Cần mã phiên để tiếp tục tiến độ đã lưu.")

    previous = saved.state if saved else StudyState()
    try:
        result = study_turn(lesson, payload, previous, chunks, manager.ai_config)
    except InvalidStudyAction as error:
        raise HTTPException(409, str(error)) from None
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    if result.state != previous:
        try:
            saved = progress.save(course_id, topic_id, result.state, saved)
        except StaleStudyProgress:
            raise HTTPException(409, _STALE) from None
        except (OSError, sqlite3.Error):
            raise HTTPException(503, _STORAGE_ERROR) from None
    if saved:
        result.session_id = saved.session_id
        result.revision = saved.revision
    return result
