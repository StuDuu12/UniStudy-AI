from hashlib import sha256
from pathlib import Path
from shutil import copy2, copytree

import pymupdf
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from services.chatbot_service import ChatbotService
from services.llm_service import AIConfig, AIUnavailable


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
TESTING_QUESTION = "Phân vùng tương đương là gì?"
SOURCE_QUESTION = "Tìm trang về phân vùng tương đương"
ALGORITHM_QUESTION = "Độ phức tạp thời gian của thuật toán là gì?"


@pytest.fixture(autouse=True)
def disable_real_ai(monkeypatch):
    monkeypatch.setenv("UNISTUDY_AI_ENDPOINT", "")


def open_app(path=APP_PATH, *, library="demo"):
    assert path.is_file(), "The Streamlit entry point must exist"
    app = AppTest.from_file(str(path), default_timeout=20).run()
    assert not app.exception
    if any(widget.key == "library" for widget in app.sidebar.selectbox) and library:
        app.sidebar.selectbox(key="library").set_value(library).run()
        assert not app.exception
    return app


def test_lookup_shows_a_real_pdf_source_and_does_not_repeat_on_rerun():
    app = open_app()
    assert not app.sidebar.radio

    app.chat_input[0].set_value(SOURCE_QUESTION).run()
    assert not app.exception
    assert len(app.chat_message) == 2
    assert any(source.label == "software_testing.pdf · Trang PDF 2" for source in app.expander)
    assert not app.get("download_button")
    assert [image.proto.imgs[0].caption for image in app.get("imgs")] == ["Ảnh trang PDF 2"]

    app.run()
    assert not app.exception
    assert len(app.chat_message) == 2


def test_course_history_is_isolated_and_can_be_cleared_per_course():
    app = open_app()
    app.chat_input[0].set_value(TESTING_QUESTION).run()

    app.sidebar.selectbox(key="course_demo").set_value("algorithm_analysis").run()
    assert not app.exception
    assert not app.chat_message

    app.chat_input[0].set_value(ALGORITHM_QUESTION).run()
    assert len(app.chat_message) == 2
    assert all(TESTING_QUESTION not in element.value for element in app.text)
    assert any(source.label == "algorithm_analysis.pdf · Trang PDF 1" for source in app.expander)
    assert all("software_testing.pdf" not in source.label for source in app.expander)

    app.sidebar.button(key="new_chat").click().run()
    assert not app.chat_message

    app.sidebar.selectbox(key="course_demo").set_value("software_testing").run()
    assert not app.exception
    assert len(app.chat_message) == 2
    assert any(TESTING_QUESTION == element.value for element in app.text)


def test_whitespace_does_not_create_a_turn():
    app = open_app()
    app.chat_input[0].set_value(" \t ").run()

    assert not app.exception
    assert not app.chat_message
    assert app.warning


def test_ai_connection_failure_automatically_shows_sources(monkeypatch):
    attempted_questions = []

    def provider_unavailable(config, question, sources):
        attempted_questions.append(question)
        raise AIUnavailable

    monkeypatch.setenv("UNISTUDY_AI_ENDPOINT", "http://127.0.0.1:1/v1/chat/completions")
    monkeypatch.setenv("UNISTUDY_AI_MODEL", "test-provider")
    monkeypatch.setenv("UNISTUDY_AI_API_KEY", "")
    monkeypatch.setattr(AIConfig, "explain", provider_unavailable)
    st.cache_resource.clear()
    try:
        app = open_app()
        app.chat_input[0].set_value(TESTING_QUESTION).run()
        assert not app.exception
        assert "Tra cứu học liệu" in app.chat_message[1].markdown[0].value
        assert any("AI tạm thời" in caption.value for caption in app.chat_message[1].caption)
        assert any("Trang PDF" in source.label for source in app.expander)
        assert app.get("imgs")

        app.chat_input[0].set_value(SOURCE_QUESTION).run()
        assert not app.exception
        assert len(app.chat_message) == 4
        assert attempted_questions == [TESTING_QUESTION]
        assert "Tra cứu học liệu" in app.chat_message[3].markdown[0].value
    finally:
        st.cache_resource.clear()


def test_unexpected_service_error_is_safe_and_input_recovers(monkeypatch):
    original_answer = ChatbotService.answer_question
    requests = []

    def fail_once(service, request):
        requests.append(request.request_id)
        if len(requests) == 1:
            raise RuntimeError("private diagnostic detail")
        return original_answer(service, request)

    monkeypatch.setattr(ChatbotService, "answer_question", fail_once)
    app = open_app()
    app.chat_input[0].set_value(TESTING_QUESTION).run()
    assert not app.exception
    assert app.error
    assert "private diagnostic detail" not in app.error[0].value

    app.chat_input[0].set_value(TESTING_QUESTION).run()
    assert not app.exception
    assert len(app.chat_message) == 4
    assert len(set(requests)) == len(requests) == 2
    assert app.get("imgs")


def test_submission_uses_course_selected_in_the_same_rerun():
    app = open_app()
    app.sidebar.selectbox(key="course_demo").set_value("algorithm_analysis")
    app.chat_input[0].set_value(ALGORITHM_QUESTION).run()

    assert not app.exception
    assert app.title[0].value == "Phân tích thuật toán"
    assert any(source.label == "algorithm_analysis.pdf · Trang PDF 1" for source in app.expander)


def test_switch_libraries_keeps_sources_and_history_in_their_library(tmp_path):
    app_path = tmp_path / "app.py"
    copy2(APP_PATH, app_path)
    data = tmp_path / "data"
    private = data / "local_course_pdfs"
    private.mkdir(parents=True)
    demo = APP_PATH.parent / "data"
    copy2(demo / "manifest.csv", data)
    copytree(demo / "demo_licensed", data / "demo_licensed")
    copy2(demo / "demo_licensed" / "software_testing.pdf", private / "private_ui_fixture.pdf")
    (private / "manifest.csv").write_text(
        "course_id,document_id,document_name,path,license\n"
        "tin_hoc_dai_cuong,fixture,private_ui_fixture.pdf,private_ui_fixture.pdf,local_only\n",
        encoding="utf-8",
    )

    app = open_app(app_path, library=None)
    assert app.sidebar.selectbox(key="library").value == "private"
    assert app.title[0].value == "Tin học đại cương"
    assert app.sidebar.selectbox(key="course_private").options == [
        "Tin học đại cương", "Toán rời rạc", "Thu thập và phân tích yêu cầu"
    ]
    app.chat_input[0].set_value(TESTING_QUESTION).run()
    assert any(source.label == "private_ui_fixture.pdf · Trang PDF 2" for source in app.expander)
    assert app.get("imgs")

    app.sidebar.selectbox(key="library").set_value("demo")
    app.chat_input[0].set_value(TESTING_QUESTION).run()
    assert not app.exception
    assert app.title[0].value == "Kiểm thử phần mềm"
    assert not app.chat_message
    app.chat_input[0].set_value(TESTING_QUESTION).run()
    assert any(source.label == "software_testing.pdf · Trang PDF 2" for source in app.expander)

    app.sidebar.selectbox(key="library").set_value("private").run()
    assert not app.exception
    assert len(app.chat_message) == 2
    assert all("software_testing.pdf" not in source.label for source in app.expander)


def test_changed_pdf_cannot_be_previewed_as_a_cached_source(monkeypatch):
    app = open_app()
    app.chat_input[0].set_value(TESTING_QUESTION).run()
    assert app.get("imgs")

    read_bytes = Path.read_bytes
    with pymupdf.open(APP_PATH.parent / "data" / "demo_licensed" / "software_testing.pdf") as pdf:
        pdf.set_metadata({"title": "Updated PDF"})
        replacement = pdf.tobytes()

    def changed_bytes(path):
        if path.name == "software_testing.pdf":
            return replacement
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", changed_bytes)
    app.run()
    assert not app.exception
    assert any("Trang PDF" in source.label for source in app.expander)
    assert not app.get("imgs")
    assert any("Tệp PDF đã thay đổi" in message.value for message in app.caption)

    st.cache_resource.clear()
    app.run()
    assert not app.exception
    assert len(app.chat_message) == 2
    assert not app.get("imgs")
    assert any("Nguồn đã thay đổi" in message.value for message in app.caption)
    st.cache_resource.clear()


def test_preview_renders_the_requested_physical_page_with_bounded_dimensions(tmp_path):
    from services.pdf_preview import render_pdf_preview

    path = tmp_path / "two-pages.pdf"
    with pymupdf.open() as pdf:
        for color in [(1, 0, 0), (0, 0, 1)]:
            page = pdf.new_page(width=4000, height=2000)
            page.draw_rect(page.rect, color=None, fill=color)
        pdf.save(path)

    png = render_pdf_preview(path, sha256(path.read_bytes()).hexdigest(), 2)
    image = pymupdf.Pixmap(png)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert image.pixel(image.width // 2, image.height // 2) == (0, 0, 255)
    assert image.width <= 1440
    assert image.width == 2 * image.height
