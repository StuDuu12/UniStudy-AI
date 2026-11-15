import logging
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import streamlit as st

from services.chatbot_service import ChatbotService
from services.course_upload import MAX_COURSE_NAME_LENGTH, MAX_PDF_FILES, MAX_PDF_MB, CourseUploadError, add_course
from services.pdf_preview import PdfChangedError, render_pdf_preview
from src.schemas import MAX_QUESTION_LENGTH, ChatRequest, ChatResponse, Course


DATA_DIR = Path(__file__).resolve().parent / "data"
MODE_LABELS = {"lookup": "Tra cứu học liệu", "ai": "Giải thích bằng AI"}
LIBRARY_LABELS = {"private": "Học liệu của bạn", "demo": "Học liệu demo"}
LOGGER = logging.getLogger(__name__)


@st.cache_resource(show_spinner=False, max_entries=2)
def get_service(data_dir: Path, private: bool, manifest_version: str = "") -> ChatbotService:
    # The version is part of the cache key so new courses appear immediately.
    return ChatbotService(data_dir, private=private)


def queue_question() -> None:
    state = st.session_state
    question = (state.get("question") or "").strip()
    if not question:
        state["input_notice"] = "Hãy nhập câu hỏi về học phần đang chọn."
        return
    if state.get("pending_request") is not None:
        return

    library = state.get("library", "demo")
    course_id = state.get(f"course_{library}")
    if library != state.get("active_library") or not course_id:
        state["input_notice"] = "Thư viện đã thay đổi. Hãy nhập lại câu hỏi cho học phần đang chọn."
        return
    state["pending_request"] = (library, ChatRequest(uuid4().hex, course_id, question, mode="auto"))


def render_question(question: str) -> None:
    with st.chat_message("Bạn", avatar=":material/person:"):
        st.text(question)


def render_response(
    request: ChatRequest, response: ChatResponse, course: Course, *, private: bool
) -> None:
    with st.chat_message("UniStudy AI", avatar=":material/auto_stories:"):
        if response.status == "success":
            st.badge(MODE_LABELS[response.mode], color="blue" if response.mode == "lookup" else "gray")
            st.text(response.answer)
            if response.message:
                st.caption(response.message)
        elif response.status == "error":
            st.error(response.message or "Có lỗi khi xử lý. Bạn có thể gửi lại câu hỏi.")
        else:
            st.warning(response.message or "Chưa thể trả lời câu hỏi này từ học liệu đã nạp.")

        if not response.sources:
            return

        st.caption("Nguồn để đối chiếu")
        preview_license = "local_only" if private else "project_demo"
        documents = {document.document_id: document for document in course.documents}
        for index, source in enumerate(response.sources, start=1):
            label = f"{source.document_name} · Trang PDF {source.page}"
            expander = st.expander(
                label,
                expanded=index == 1,
                key=f"pdf-{request.request_id}-{index}",
                on_change="rerun",
            )
            if not expander.open:
                continue
            with expander:
                st.text(source.excerpt)
                document = documents.get(source.document_id)
                if document is None or document.license != preview_license:
                    st.caption("Không thể hiển thị ảnh trang PDF này.")
                    continue
                source_digest = getattr(source, "document_sha256", "")
                if not source_digest or source_digest != document.sha256:
                    st.caption("Nguồn đã thay đổi. Gửi lại câu hỏi để cập nhật ảnh trang PDF.")
                    continue
                try:
                    preview = render_pdf_preview(document.path, source_digest, source.page)
                except PdfChangedError:
                    st.caption("Tệp PDF đã thay đổi. Khởi động lại ứng dụng để cập nhật nguồn.")
                    continue
                except (OSError, ValueError, RuntimeError):
                    st.caption("Không thể hiển thị ảnh trang PDF này.")
                    continue
                st.image(preview, caption=f"Ảnh trang PDF {source.page}", width="stretch", output_format="PNG")


def render_course_upload(data_dir: Path, *, busy: bool) -> None:
    state = st.session_state
    generation = state.get("course_upload_generation", 0)
    if state.pop("course_added", False):
        st.success("Đã thêm học phần. Bạn có thể đặt câu hỏi ngay.")

    with st.expander("Thêm học phần", icon=":material/add:"):
        with st.form(f"course_upload_{generation}", border=False):
            name = st.text_input(
                "Tên học phần", max_chars=MAX_COURSE_NAME_LENGTH, key=f"course_upload_name_{generation}", disabled=busy
            )
            files = st.file_uploader(
                "Chọn PDF học liệu",
                type="pdf",
                accept_multiple_files=True,
                max_upload_size=MAX_PDF_MB,
                help=f"Tối đa {MAX_PDF_FILES} PDF có văn bản, mỗi tệp tối đa {MAX_PDF_MB} MB.",
                disabled=busy,
            )
            submitted = st.form_submit_button("Tạo học phần", key="submit_course", type="primary", disabled=busy)

        if not submitted or busy:
            return
        try:
            with st.spinner("Đang lưu học liệu…"):
                course_id = add_course(data_dir, name, [(file.name, file.getvalue()) for file in files or []])
        except CourseUploadError as error:
            st.error(str(error))
            return

    state["library"] = "private"
    state["course_private"] = course_id
    state["course_upload_generation"] = generation + 1
    state["course_added"] = True
    st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="UniStudy AI · Tra cứu học liệu",
        page_icon="📘",
        layout="centered",
    )
    st.html("<style>.st-key-study-intro { background: rgba(37, 99, 235, 0.06); }</style>")

    state = st.session_state
    history = state.setdefault("messages_by_course", {})
    pending_library, pending = state.get("pending_request") or (None, None)
    busy = pending is not None
    private_data_dir = DATA_DIR / "local_course_pdfs"
    private_manifest = private_data_dir / "manifest.csv"
    local_server = st.get_option("server.address") in {"127.0.0.1", "::1", "localhost"}

    with st.sidebar:
        st.subheader("UniStudy AI", anchor=False)
        st.caption("Trợ lý học liệu theo học phần")
        st.divider()
        if local_server:
            render_course_upload(private_data_dir, busy=busy)
        library = "demo"
        if local_server and private_manifest.is_file():
            library = st.selectbox(
                "Thư viện",
                tuple(LIBRARY_LABELS),
                format_func=LIBRARY_LABELS.__getitem__,
                key="library",
                disabled=busy,
            )
        state["active_library"] = library
        private = library == "private"
        if private:
            try:
                manifest_version = sha256(private_manifest.read_bytes()).hexdigest()
            except OSError:
                manifest_version = ""
            service = get_service(private_data_dir, private=True, manifest_version=manifest_version)
        else:
            service = get_service(DATA_DIR, private=False)
        courses = {course.course_id: course for course in service.courses()}
        if not courses:
            st.info("Chưa có học phần để hiển thị.")
            st.stop()

        course_id = st.selectbox(
            "Học phần",
            tuple(courses),
            format_func=lambda value: courses[value].course_name,
            key=f"course_{library}",
            disabled=busy,
        )
        course = courses[course_id]
        with st.expander(f"Học liệu đã nạp ({len(course.documents)})", expanded=len(course.documents) <= 2):
            for document in course.documents:
                st.text(document.document_name)
            if not course.documents:
                st.caption("Chưa có tệp PDF khả dụng.")

        if service.issues:
            with st.expander("Lưu ý về học liệu", icon=":material/info:"):
                for issue in service.issues:
                    st.text(issue)

        if st.button(
            "Hội thoại mới",
            key="new_chat",
            icon=":material/add:",
            width="stretch",
            disabled=busy or not history.get(course_id),
        ):
            history.pop(course_id, None)

    st.title(course.course_name, anchor=False)
    st.caption("Đặt câu hỏi bằng tiếng Việt và đối chiếu câu trả lời với học liệu của môn.")
    turns = history.get(course_id, [])
    if not course.documents:
        st.info("Học phần này chưa có tài liệu sẵn sàng.")
    elif not turns and not busy:
        with st.container(border=True, key="study-intro", gap="small"):
            st.badge("Học liệu sẵn sàng", icon=":material/check_circle:", color="green")
            st.subheader("Bạn muốn tìm hiểu điều gì?", anchor=False)
            st.markdown("Bạn có thể hỏi về một khái niệm hoặc yêu cầu tìm một trang hay đoạn trích trong học liệu.")
            st.caption("Mỗi câu hỏi được xử lý độc lập.")

    with st.container():
        for request, response in turns:
            render_question(request.question)
            render_response(request, response, course, private=private)

        if pending and pending_library == library and pending.course_id == course_id:
            render_question(pending.question)

    notice = state.pop("input_notice", "")
    if notice:
        st.warning(notice)

    st.chat_input(
        "Nhập câu hỏi về học phần…",
        key="question",
        max_chars=MAX_QUESTION_LENGTH,
        disabled=busy or not course.documents,
        on_submit=queue_question,
    )

    if pending:
        if pending_library != library:
            state["pending_request"] = None
            state["input_notice"] = "Thư viện đã thay đổi. Hãy nhập lại câu hỏi cho học phần đang chọn."
            st.rerun()
        with st.spinner("Đang xử lý câu hỏi…"):
            try:
                response = service.answer_question(pending)
            except Exception as error:
                LOGGER.error("Chat request %s failed (%s)", pending.request_id, type(error).__name__)
                response = ChatResponse(pending.request_id, "error", "lookup")
            history.setdefault(pending.course_id, []).append((pending, response))
            state["pending_request"] = None
        st.rerun()


if __name__ == "__main__":
    main()
