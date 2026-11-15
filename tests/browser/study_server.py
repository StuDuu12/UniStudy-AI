"""Serve the built app with disposable study data and a local Chat Completions test double."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
from threading import Thread

import uvicorn

from backend.main import app
from backend.services.course_manager import CourseManager
from backend.services.llm_service import AIConfig


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
                "Hãy chia đầu vào theo cách hệ thống xử lý [S1]. "
                "Ví dụ, ô số chỗ nhận từ 22 đến 32. Nếu nhập 21, ô sẽ xử lý thế nào?"
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
        copytree(source / "data" / "demo_licensed", data / "demo_licensed")
        (data / "manifest.csv").write_bytes((source / "data" / "manifest.csv").read_bytes())

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
