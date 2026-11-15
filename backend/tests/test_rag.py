import json
from pathlib import Path
from types import SimpleNamespace

import pymupdf
import pytest

from backend.services.course_manager import CourseManager
from backend.services.ingest import DocumentInfo, extract_pdf_chunks
from backend.services.llm_service import AIConfig, AIUnavailable
from backend.services.retrieval import CourseRetriever


def pdf_bytes(pages):
    with pymupdf.open() as pdf:
        for text in pages:
            page = pdf.new_page()
            page.insert_textbox(page.rect + (30, 30, -30, -30), text, fontsize=9)
        return pdf.tobytes()


def test_chunks_overlap_without_crossing_pdf_pages():
    words = [f"word{i:03}" for i in range(180)]
    data = pdf_bytes([" ".join(words), "SECOND_PAGE_ONLY"])
    document = DocumentInfo("doc", "lecture.pdf", Path("lecture.pdf"), "project_demo")
    chunks = list(extract_pdf_chunks(document, data))
    first_page = [chunk for chunk in chunks if chunk.page == 1]
    assert len(first_page) == 2
    assert first_page[0].excerpt.split()[-25:] == first_page[1].excerpt.split()[:25]
    assert all("SECOND_PAGE_ONLY" not in chunk.excerpt for chunk in first_page)
    assert chunks[-1].page == 2
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)


def test_retrieval_returns_the_actual_pdf_page_and_respects_top_k():
    data = pdf_bytes(["Network sockets and datagrams", "Equivalence partitioning divides inputs into classes"])
    document = DocumentInfo("doc", "lecture.pdf", Path("lecture.pdf"), "project_demo")
    chunks = list(extract_pdf_chunks(document, data))
    retriever = CourseRetriever("testing", [document], chunks)
    result = retriever.search("Equivalence partitioning", limit=1)
    assert len(result) == 1
    assert result[0].page == 2
    assert result[0].document_id == "doc"
    assert result[0].excerpt in pymupdf.open(stream=data)[1].get_text().replace("\n", " ")
    assert retriever.search("zzzzzzzzzzzzzzzzzzzzzz") == []


@pytest.fixture
def manager(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "lecture.pdf").write_bytes(pdf_bytes(["Operating system manages resources and executes programs"]))
    (data / "manifest.csv").write_text(
        "course_id,document_id,document_name,path,license\n"
        "software_testing,lecture,lecture.pdf,lecture.pdf,project_demo\n", encoding="utf-8"
    )
    result = CourseManager(tmp_path)
    result._ai = None
    return result


def test_ai_refusal_is_not_changed_to_success(manager):
    manager._ai = SimpleNamespace(explain=lambda *_: ("", []))
    response = manager.answer_question("software_testing", "Operating system")
    assert response.status == "insufficient_evidence"
    assert response.answer == ""
    assert response.sources[0].document_id == "lecture"


@pytest.mark.parametrize("is_local", [False, True])
def test_adjacent_private_excerpts_are_sent_only_to_local_providers(manager, is_local):
    manager.append_documents("software_testing", [("private.pdf", pdf_bytes([
        "Operating system controls access to computer resources and manages memory.",
        "Appendix with unrelated extra details about pythons and frogs in a shaded rainforest.",
    ]))])
    sent = []

    def explain(question, sources):
        sent.extend(sources)
        return "", []

    manager._ai = SimpleNamespace(explain=explain, is_local=is_local)
    response = manager.answer_question("software_testing", "Operating system gồm những gì?")

    private_sources = {source.page: source.score for source in response.sources if source.document_name == "private.pdf"}
    assert private_sources[1] >= 0.20
    assert private_sources[2] is None
    sent_pages = {source.page for source in sent if source.document_name == "private.pdf"}
    assert sent_pages == ({1, 2} if is_local else {1})


@pytest.mark.parametrize("question", ["!!!", "123456", "   ", "🙂🙂"])
def test_non_question_input_is_rejected(manager, question):
    assert manager.answer_question("software_testing", question).status == "invalid_input"


def test_intro_does_not_change_retrieved_sources(manager):
    short = manager.answer_question("software_testing", "Operating system")
    long = manager.answer_question("software_testing", "Mình đang học bài và chưa hiểu. Vậy Operating system")
    assert short.sources == long.sources


def test_contextual_definition_resolves_to_the_prior_topic(manager):
    response = manager.answer_question("software_testing", "Nó là gì?", ["Operating system?"])
    assert response.status == "success"
    assert response.context_question == "Operating system?"
    assert response.sources[0].document_id == "lecture"


def test_answer_without_valid_citations_is_rejected(manager):
    manager._ai = SimpleNamespace(explain=lambda *_: ("Unsupported answer", []))
    response = manager.answer_question("software_testing", "Operating system")
    assert response.status == "ai_unavailable"
    assert response.answer == ""


def test_provider_outage_is_reported(manager):
    def unavailable(*_):
        raise AIUnavailable
    manager._ai = SimpleNamespace(explain=unavailable)
    response = manager.answer_question("software_testing", "Operating system")
    assert response.status == "ai_unavailable"
    assert response.sources[0].document_id == "lecture"
    assert response.message


def test_valid_ai_answer_keeps_retrieved_metadata(manager):
    manager._ai = SimpleNamespace(explain=lambda question, sources: ("Manages resources", sources[:1]))
    response = manager.answer_question("software_testing", "Operating system")
    assert response.status == "success"
    assert response.mode == "ai"
    assert response.sources[0].document_id == "lecture"
    assert response.sources[0].page == 1
    assert response.sources[0].document_sha256


@pytest.mark.parametrize("source_ids", [["S999"], ["S1", "S999"], [], [123]])
def test_provider_cannot_invent_citations(monkeypatch, source_ids):
    from backend.services import llm_service
    from backend.services.ingest import ChunkSource

    reply = {"status": "success", "answer": "Answer", "source_ids": source_ids}
    raw = json.dumps({"choices": [{"message": {"content": json.dumps(reply)}}]}).encode()
    class Connection:
        def __init__(self, *args, **kwargs): pass
        def request(self, *args): pass
        def getresponse(self): return SimpleNamespace(status=200, read=lambda _: raw)
        def close(self): pass
    monkeypatch.setattr(llm_service, "HTTPSConnection", Connection)
    config = AIConfig("https://example.test/v1/chat/completions", "test-model", "test-key")
    source = ChunkSource("doc", "lecture.pdf", 2, "chunk", "Evidence")
    with pytest.raises(ValueError):
        config.explain("Question", [source])
