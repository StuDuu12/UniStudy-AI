from typing import Annotated, Literal
from pydantic import BaseModel, Field


ChatStatus = Literal[
    "success",
    "insufficient_evidence",
    "needs_clarification",
    "no_documents",
    "ai_unavailable",
    "error",
    "invalid_input",
]

ChatMode = Literal["lookup", "ai", "auto"]
Question = Annotated[str, Field(max_length=2000)]


class SourceItem(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page: int
    excerpt: str
    score: float | None = None
    document_sha256: str | None = None
    formatted_excerpt: str | None = None


class ChatRequest(BaseModel):
    course_id: str
    question: Question = Field(min_length=1)
    previous_questions: list[Question] = Field(default_factory=list, max_length=3)
    model_provider: Literal["local", "gemini", "chatgpt"] | None = None
    model_name: str | None = None
    api_key: str | None = None


class ChatResponse(BaseModel):
    status: ChatStatus
    answer: str
    mode: ChatMode
    sources: list[SourceItem] = Field(default_factory=list)
    message: str | None = None
    context_question: str | None = None
    model_name: str | None = None
    model_provider: str | None = None


class CourseItem(BaseModel):
    course_id: str
    course_name: str
    document_count: int
    status: str = "ready"
    suggested_questions: list[str] = Field(default_factory=list)


class RenameConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class CourseListResponse(BaseModel):
    courses: list[CourseItem]


class DocumentItem(BaseModel):
    document_id: str
    document_name: str
    page_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentItem]


class MessageModel(BaseModel):
    id: str
    sender: Literal["user", "assistant"]
    content: str
    timestamp: str
    created_at: int | None = None
    status: ChatStatus | None = None
    sources: list[SourceItem] | None = None
    message: str | None = None
    context_question: str | None = None
    retry_question: str | None = None
    reply_to: str | None = None


class ConversationModel(BaseModel):
    id: str
    course_id: str
    title: str
    updated_at: int
    messages: list[MessageModel] = Field(default_factory=list)


class ConversationListResponse(BaseModel):
    conversations: list[ConversationModel]
