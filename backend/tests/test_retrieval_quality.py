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


def test_operations_question_keeps_its_subject():
    chunks = [
        ChunkSource("logic", "logic.pdf", 1, "logic", "Các phép toán trên mệnh đề gồm phủ định và phép hội, phép tuyển."),
        ChunkSource("sets", "sets.pdf", 9, "sets", "Các phép toán trên tập hợp: phép hợp lấy phần tử thuộc A hoặc B, phép giao lấy phần tử thuộc cả hai."),
    ]
    result = CourseRetriever("math", [], chunks).search("Các phép toán tập hợp cơ bản gồm những phép nào?", 6)
    assert result
    assert all(source.document_id == "sets" for source in result)
