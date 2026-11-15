"""Serve the built app with disposable study data and a local Chat Completions test double."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shutil import copy2
from tempfile import TemporaryDirectory
from threading import Thread

import uvicorn

from backend.main import app
from backend.services.course_manager import CourseManager
from backend.services.llm_service import AIConfig
from backend.services.study import LESSONS


class StudyModel(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        content = json.loads(payload["messages"][1]["content"])
        if not content.get("evidence"):
            self.send_error(400)
            return

        reply = {
            "status": "success",
            "answer": (
                "Phép hợp lấy mọi phần tử xuất hiện trong ít nhất một tập. "
                "Phép giao chỉ lấy các phần tử có mặt trong cả hai tập [S1]. "
                "Với A = {0, 3} và B = {3, 10}, vì sao số 0 thuộc phép hợp nhưng không thuộc phép giao?"
            ),
            "source_ids": ["S1"],
        }
        body = json.dumps({"choices": [{"message": {"content": json.dumps(reply)}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    source = Path(__file__).resolve().parents[2]
    if not (source / "frontend" / "dist" / "index.html").is_file():
        raise SystemExit("Build the frontend before running the browser test.")

    with TemporaryDirectory(prefix="unistudy-browser-") as directory:
        root = Path(directory)
        data = root / "data"
        (data / "demo_licensed").mkdir(parents=True)
        selected_ids = {lesson.document_id for lesson in LESSONS.values()}
        header, *records = (source / "data" / "manifest.csv").read_text(encoding="utf-8").splitlines()
        selected = [record for record in records if record.split(",")[1] in selected_ids]
        for record in selected:
            relative_path = Path(record.split(",")[3])
            copy2(source / "data" / relative_path, data / relative_path)
        (data / "manifest.csv").write_text("\n".join([header, *selected]) + "\n", encoding="utf-8")

        with ThreadingHTTPServer(("127.0.0.1", 0), StudyModel) as model:
            Thread(target=model.serve_forever, daemon=True).start()
            endpoint = f"http://127.0.0.1:{model.server_port}/v1/chat/completions"
            manager = CourseManager(root)
            manager._ai = AIConfig(endpoint=endpoint, model="study-test-double", api_key="")
            app.state.course_manager = manager
            try:
                uvicorn.run(app, host="127.0.0.1", port=18173)
            finally:
                model.shutdown()


if __name__ == "__main__":
    main()
