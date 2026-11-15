from dataclasses import dataclass
from pathlib import Path


MAX_QUESTION_LENGTH = 1000


@dataclass(frozen=True)
class Document:
    document_id: str
    document_name: str
    path: Path
    license: str
    sha256: str = ""


@dataclass(frozen=True)
class Course:
    course_id: str
    course_name: str
    documents: tuple[Document, ...]


@dataclass(frozen=True)
class Source:
    document_id: str
    document_name: str
    page: int
    chunk_id: str
    excerpt: str
    score: float
    document_sha256: str = ""


@dataclass(frozen=True)
class ChatRequest:
    request_id: str
    course_id: str
    question: str
    mode: str = "lookup"


@dataclass(frozen=True)
class ChatResponse:
    request_id: str
    status: str
    mode: str
    answer: str = ""
    message: str = ""
    sources: tuple[Source, ...] = ()
