import pytest

from backend.services.ingest import ChunkSource
from backend.services.retrieval import CourseRetriever


def test_definition_query_prefers_explanation_over_short_headings():
    chunks = [
        ChunkSource("sets", "sets.pdf", 1, "title", "Chương 2 LÝ THUYẾT TẬP HỢP"),
        ChunkSource("sets", "sets.pdf", 2, "definition",
                    "Khái niệm cơ bản Tập hợp hình thành từ việc nhóm một số đối tượng nào đó với nhau. "
                    "Các đối tượng được gọi là các phần tử của tập hợp."),
        ChunkSource("combinations", "combinations.pdf", 36, "other", "Tổ hợp lặp"),
    ]
    sources = CourseRetriever("math", [], chunks).search("Tập hợp là gì?", limit=1)
    assert sources[0].chunk_id == "definition"
    assert sources[0].page == 2


def test_definition_expansion_cannot_supply_a_missing_topic():
    chunks = [ChunkSource("sets", "sets.pdf", 2, "definition",
                          "Khái niệm cơ bản Tập hợp hình thành từ việc nhóm một số đối tượng nào đó với nhau.")]
    assert CourseRetriever("math", [], chunks).search("Tập hợp lượng tử là gì?") == []


@pytest.mark.parametrize(
    "question, expected",
    [
        ("Phân vùng tương đương (equivalence partitioning) là gì?", {"partitioning"}),
        ("Phân vùng tương đương là gì và phân tích giá trị biên là gì?", {"partitioning", "boundary"}),
    ],
)
def test_definition_variants_retain_relevant_sources(question, expected):
    chunks = [
        ChunkSource(
            "testing", "testing.pdf", 1, "partitioning",
            "Phân vùng tương đương phân chia miền dữ liệu vào thành các lớp. "
            "Các đầu vào cùng một lớp có hành vi giống nhau khi chạy chương trình.",
        ),
        ChunkSource(
            "testing", "testing.pdf", 2, "boundary",
            "Phân tích giá trị biên chọn dữ liệu ở các ranh giới của miền đầu vào, "
            "ngay dưới và ngay trên mỗi ranh giới.",
        ),
    ]
    sources = CourseRetriever("testing", [], chunks).search(question, minimum_score=0.20)
    assert {source.chunk_id for source in sources} == expected


def test_operations_question_keeps_its_subject():
    chunks = [
        ChunkSource("logic", "logic.pdf", 1, "logic", "Các phép toán trên mệnh đề gồm phủ định và phép hội, phép tuyển."),
        ChunkSource("sets", "sets.pdf", 9, "sets", "Các phép toán trên tập hợp: phép hợp lấy phần tử thuộc A hoặc B, phép giao lấy phần tử thuộc cả hai."),
    ]
    result = CourseRetriever("math", [], chunks).search("Các phép toán tập hợp cơ bản gồm những phép nào?", 6)
    assert result
    assert all(source.document_id == "sets" for source in result)


def test_weak_subquery_does_not_displace_evidence_from_another_topic():
    chunks = [
        ChunkSource(
            "astronomy", "astronomy.pdf", 1, "orbital-a",
            "Orbital mechanics guides satellite launches and space navigation by analyzing the motion of celestial bodies.",
        ),
        ChunkSource(
            "astronomy", "astronomy.pdf", 2, "orbital-b",
            "Orbital mechanics determines the trajectory of artificial satellites, including the shape, "
            "inclination and period of their orbits.",
        ),
        ChunkSource(
            "publishing", "publishing.pdf", 1, "weak",
            "The publishing protocol organizes manuscripts, editorial schedules, archives, correspondence, "
            "reference checks, issue planning, author credits, design templates, cover illustrations, "
            "proofreading, publication deadlines and library deposits.",
        ),
    ]
    retriever = CourseRetriever("synthetic", [], chunks)
    sources = retriever.search("Orbital mechanics? Datagram protocol", limit=2, minimum_score=0.20)
    assert {source.chunk_id for source in sources} == {"orbital-a", "orbital-b"}
