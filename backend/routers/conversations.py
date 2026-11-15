from fastapi import APIRouter, HTTPException, Query, Request

from backend.schemas.chat import ConversationListResponse, ConversationModel, RenameConversationRequest
from backend.services.course_manager import ConversationConflict, ConversationStorageError

router = APIRouter()
_STORAGE_ERROR = "Không thể truy cập tệp lịch sử hội thoại."


@router.get("/conversations", response_model=ConversationListResponse)
def get_conversations(request: Request, course_id: str | None = Query(default=None)):
    course_manager = request.app.state.course_manager
    try:
        convs = course_manager.get_conversations(course_id)
    except ConversationStorageError:
        raise HTTPException(status_code=500, detail=_STORAGE_ERROR) from None
    return ConversationListResponse(conversations=convs)


@router.post("/conversations", response_model=ConversationModel)
def save_conversation(conversation: ConversationModel, request: Request):
    course_manager = request.app.state.course_manager
    try:
        return course_manager.save_conversation(conversation)
    except ConversationConflict:
        raise HTTPException(status_code=409, detail="Mã hội thoại đã thuộc học phần khác.") from None
    except ConversationStorageError:
        raise HTTPException(status_code=500, detail=_STORAGE_ERROR) from None


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, request: Request):
    course_manager = request.app.state.course_manager
    try:
        deleted = course_manager.delete_conversation(conversation_id)
    except ConversationStorageError:
        raise HTTPException(status_code=500, detail=_STORAGE_ERROR) from None
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "id": conversation_id}


@router.patch("/conversations/{conversation_id}", response_model=ConversationModel)
def rename_conversation(conversation_id: str, payload: RenameConversationRequest, request: Request):
    course_manager = request.app.state.course_manager
    try:
        updated = course_manager.rename_conversation(conversation_id, payload.title)
    except ConversationStorageError:
        raise HTTPException(status_code=500, detail=_STORAGE_ERROR) from None
    if updated is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return updated
