from backend.services.query import query_parts
import pytest


@pytest.mark.parametrize("question", [
    "Mình đang học môn Toán rời rạc nhưng chưa hiểu bài. Bạn giải thích giúp mình tập hợp là gì nhé.",
    "Bạn có thể giải thích cho mình tập hợp là gì không?",
    "Giải thích giúp em tập hợp là gì với ạ",
    "Tôi muốn biết tập hợp là gì",
    "Cho mình hỏi tập hợp là gì nhé",
    "Tập hợp là gì vậy bạn?",
])
def test_conversational_wrappers_preserve_definition_subject(question):
    assert query_parts(question) == ["tap hop la gi"]


def test_long_introduction_does_not_become_definition_subject():
    assert query_parts("Mình đang học và chưa hiểu bài. Vậy tập hợp là gì?") == ["tap hop la gi"]


def test_multiple_questions_keep_separate_topics():
    assert query_parts("Tập con là gì? Tập rỗng là gì?") == ["tap con la gi", "tap rong la gi"]


def test_query_expansion_is_bounded():
    assert len(query_parts(";".join(f"chu de {i}" for i in range(50)))) == 6
