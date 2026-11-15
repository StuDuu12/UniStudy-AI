from pathlib import Path
from shutil import copy2, copytree
from types import SimpleNamespace

import streamlit as st
from streamlit.testing.v1 import AppTest


PROJECT = Path(__file__).resolve().parents[1]


def test_upload_opens_new_course_on_a_clean_install(tmp_path, monkeypatch):
    app_path = tmp_path / "app.py"
    copy2(PROJECT / "app.py", app_path)
    data = tmp_path / "data"
    data.mkdir()
    copy2(PROJECT / "data/manifest.csv", data)
    copytree(PROJECT / "data/demo_licensed", data / "demo_licensed")
    pdf = (data / "demo_licensed/software_testing.pdf").read_bytes()
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: [
        SimpleNamespace(name="Kiem thu.pdf", getvalue=lambda: pdf),
    ])

    app = AppTest.from_file(str(app_path), default_timeout=20).run()
    assert not app.exception
    app.sidebar.text_input(key="course_upload_name_0").set_value("Kiểm thử tự học")
    app.sidebar.button(key="submit_course").click().run()
    assert not app.exception
    assert app.sidebar.selectbox(key="library").value == "private"
    assert app.title[0].value == "Kiểm thử tự học"
    assert app.sidebar.success[0].value == "Đã thêm học phần. Bạn có thể đặt câu hỏi ngay."

    app.chat_input[0].set_value("Phân vùng tương đương là gì?").run()
    assert not app.exception
    assert any(source.label == "Kiem thu.pdf · Trang PDF 2" for source in app.expander)
