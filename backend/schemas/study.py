from typing import Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field

from backend.schemas.chat import SourceItem


StudyAction = Literal["open", "view", "submit", "explain", "practice", "hint", "solution", "retry", "ai"]
StudyStep = Literal["diagnose", "explain", "practice", "review"]
StudyMistake = Literal["confuses_intersection", "confuses_nonfunctional", "incomplete", "wrong_values", "extra_values"]
StudyResult = Literal["independent", "needs_practice"]
StudyAIStatus = Literal["used", "not_configured", "unavailable", "insufficient_evidence"]


class StudyState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: StudyStep = "diagnose"
    variant: Literal[0, 1, 2] = 0
    diagnosis: Literal["correct"] | StudyMistake | None = None
    practice_mistake: StudyMistake | None = None
    hint_level: int = Field(default=0, ge=0, le=2, strict=True)
    last_result: StudyResult | None = None
    last_mistake: StudyMistake | None = None
    mistake_count: int = Field(default=0, ge=0, le=999, strict=True)


class StudyTopic(BaseModel):
    id: str
    title: str
    goal: str
    page: int


class StudyCatalog(BaseModel):
    topics: list[StudyTopic]
    ai_configured: bool


class StudyTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: StudyAction
    session_id: UUID4 | None = None
    revision: int | None = Field(default=None, ge=1, strict=True)
    answer: str = Field(default="", max_length=120)


class StudyTurn(BaseModel):
    state: StudyState
    session_id: str | None = None
    revision: int | None = None
    prompt: str | None = None
    feedback: str | None = None
    lesson: str | None = None
    hint: str | None = None
    sources: list[SourceItem] = Field(default_factory=list)
    ai_status: StudyAIStatus | None = None
    ai_message: str | None = None
    ai_answer: str | None = None
    ai_sources: list[SourceItem] = Field(default_factory=list)
