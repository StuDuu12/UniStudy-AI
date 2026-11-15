import json
import os
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

from src.schemas import Source


AI_TIMEOUT_SECONDS = 20
LOCAL_AI_TIMEOUT_SECONDS = 60
MAX_RESPONSE_BYTES = 256_000
SYSTEM_PROMPT = (
    'Bạn là trợ lý học tập UniStudy AI. Hãy trả lời câu hỏi của người học bằng tiếng Việt một cách rõ ràng, chuẩn xác và có cấu trúc sư phạm tốt. '
    'Dựa vào các đoạn trích giáo trình được cung cấp để giải thích trực tiếp vấn đề. '
    'Trình bày có cấu trúc đẹp mắt bằng Markdown: nêu rõ định nghĩa hoặc khái niệm cốt lõi, dùng gạch đầu dòng liệt kê các đặc điểm hoặc thành phần chính, '
    'và nêu ví dụ cụ thể nếu tài liệu có đề cập.\n'
    'ĐẶC BIỆT KHI VIẾT CÔNG THỨC, KÝ HIỆU TOÁN HỌC, TẬP HỢP, LOGIC, ĐỒ THỊ HOẶC ĐỘ PHỨC TẠP: '
    'Luôn sử dụng cú pháp LaTeX kẹp giữa dấu $ để hiển thị công thức chuẩn: ví dụ $A \\cap B$, $A \\cup B$, $A \\subseteq B$, $x \\in S$, tập rỗng $\\emptyset$, '
    'bản số $|S|$, tập lũy thừa $\\mathcal{P}(S)$ hoặc $P(S)$, lũy thừa $2^{|S|}$, $O(n \\log n)$, $T(n)$, đỉnh $V$, cạnh $E$, v.v. '
    'Thay thế các ký tự lỗi hiển thị như ô vuông [] bằng ký hiệu toán học chuẩn $\\emptyset$ hoặc $\\{\\}$.\n'
    'Chỉ giải thích các ý được đoạn trích hỗ trợ, không tự bịa đặt thông tin ngoài giáo trình. '
    'Nếu thiếu căn cứ cho ý chính, trả JSON {"status":"insufficient_evidence","answer":"","source_ids":[]}. '
    'Khi đủ căn cứ, trả JSON {"status":"success","answer":"lời giải thích chi tiết có định dạng markdown và LaTeX","source_ids":["S1"]} '
    'và chọn đúng các ID đoạn thực sự được dùng. Không tự tạo tên tài liệu hay số trang. Chỉ trả đối tượng JSON.'
)


class AIUnavailable(Exception):
    pass


@dataclass(frozen=True)
class AIConfig:
    endpoint: str
    model: str
    api_key: str

    @property
    def is_local(self) -> bool:
        return urlsplit(self.endpoint).hostname in {"localhost", "127.0.0.1", "::1"}

    @classmethod
    def load(cls, env_file: Path) -> "AIConfig | None":
        try:
            values = dotenv_values(env_file, interpolate=False)
        except (OSError, UnicodeError):
            values = {}

        def value(name: str) -> str:
            key = f"UNISTUDY_AI_{name}"
            return (os.environ.get(key, values.get(key)) or "").strip()

        endpoint, model, api_key = value("ENDPOINT"), value("MODEL"), value("API_KEY")
        try:
            url = urlsplit(endpoint)
            port = url.port
        except ValueError:
            return None

        if not model or not url.hostname or not url.path.endswith("/chat/completions"):
            return None
        if url.username is not None or url.query or url.fragment or port == 0:
            return None
        if url.scheme == "https" and api_key:
            return cls(endpoint, model, api_key)
        if url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}:
            return cls(endpoint, model, api_key)
        return None

    def explain(self, question: str, sources: tuple[Source, ...]) -> tuple[str, tuple[Source, ...]]:
        evidence = {f"S{index}": source for index, source in enumerate(sources, start=1)}
        content = {
            "question": question,
            "evidence": [{"id": key, "text": source.excerpt} for key, source in evidence.items()],
        }
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
            ],
        }
        url = urlsplit(self.endpoint)
        if url.scheme == "http":
            payload.update(reasoning_effort="none", max_tokens=400, temperature=0)
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "unistudy_answer",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "status": {"enum": ["success", "insufficient_evidence"]},
                            "answer": {"type": "string"},
                            "source_ids": {"type": "array", "items": {"enum": list(evidence)}},
                        },
                        "required": ["status", "answer", "source_ids"],
                        "additionalProperties": False,
                    },
                },
            }
            connection = HTTPConnection(url.hostname, url.port, timeout=LOCAL_AI_TIMEOUT_SECONDS)
        else:
            connection = HTTPSConnection(url.hostname, url.port, timeout=AI_TIMEOUT_SECONDS)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            connection.request("POST", url.path, json.dumps(payload).encode("utf-8"), headers)
            response = connection.getresponse()
            if response.status != 200:
                raise AIUnavailable
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        except (OSError, HTTPException):
            raise AIUnavailable from None
        finally:
            connection.close()

        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Oversized provider response")
        try:
            message = json.loads(raw)["choices"][0]["message"]["content"]
            reply = json.loads(message)
            status = reply["status"]
            if status == "insufficient_evidence":
                return "", ()
            answer, source_ids = reply["answer"], reply["source_ids"]
            if status != "success" or not isinstance(answer, str) or not answer.strip():
                raise ValueError("Invalid answer")
            if not isinstance(source_ids, list) or not source_ids:
                raise ValueError("Missing source IDs")
            return answer.strip(), tuple(evidence[key] for key in dict.fromkeys(source_ids))
        except (TypeError, KeyError, IndexError, RecursionError):
            raise ValueError("Invalid provider response") from None
