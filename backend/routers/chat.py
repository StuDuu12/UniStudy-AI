from fastapi import APIRouter, HTTPException, Request

from backend.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def post_chat(payload: ChatRequest, request: Request):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty")

    course_manager = request.app.state.course_manager
    if course_manager.get_course_documents(payload.course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")

    return course_manager.answer_question(
        payload.course_id,
        question,
        payload.previous_questions,
        model_provider=payload.model_provider,
        model_name=payload.model_name,
        api_key=payload.api_key,
    )
