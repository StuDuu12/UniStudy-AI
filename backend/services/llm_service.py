import json
import os
import re
from time import sleep
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

from backend.services.ingest import ChunkSource
from backend.services.pdf_text import readable_pdf_text

AI_TIMEOUT_SECONDS = 35
LOCAL_AI_TIMEOUT_SECONDS = 60
MAX_RESPONSE_BYTES = 256_000

SYSTEM_PROMPT = (
    "Bạn là gia sư học thuật UniStudy AI. Hãy viết lời giải thích tự nhiên, chính xác bằng tiếng Việt chuẩn sư phạm. "
    "Tuyệt đối không viết dồn thành một đoạn văn nguyên khối khó đọc. "
    "Quy chuẩn định dạng câu trả lời bằng Markdown:\n"
    "1. Nếu chỉ được hỏi định nghĩa, trả lời trực tiếp trong tối đa hai câu. Bỏ các thuật ngữ, ký hiệu và ví dụ phụ dù chúng xuất hiện cùng trang.\n"
    "2. **Cấu trúc & Phân loại:** Sử dụng danh sách gạch đầu dòng rõ ràng (- **Tên ý:** Giải thích cụ thể) để trình bày các đặc điểm, thành phần hoặc phân loại.\n"
    "3. Chỉ thêm mục đích, nguồn gốc hoặc ứng dụng khi câu hỏi yêu cầu và đoạn trích có thông tin.\n"
    "4. Luôn ngắt đoạn và xuống dòng đôi giữa các phần để bố cục thoáng mắt, sinh viên dễ học và ghi nhớ.\n"
    "5. Viết công thức toán bằng LaTeX trong dấu $...$, ví dụ $A \\cup B$, $2^{|S|}$.\n"
    "6. Không đoán ký hiệu bị lỗi; nếu gặp ký hiệu cần xem PDF gốc, nêu rõ giới hạn đó.\n"
    "7. Mỗi nhận định phải được đoạn trích hỗ trợ trực tiếp. Trùng từ khóa hoặc cùng trang chưa đủ để làm căn cứ.\n"
    "8. Nếu chỉ đủ căn cứ cho một phần, trả lời phần đó với status success và nêu rõ ý nào chưa xác nhận được.\n"
    "9. Chỉ trả insufficient_evidence khi không có căn cứ cho bất kỳ ý chính nào.\n"
    "10. Chỉ trả đối tượng JSON theo schema quy định: {\"status\":\"insufficient_evidence\",\"answer\":\"\",\"source_ids\":[]} hoặc {\"status\":\"success\",\"answer\":\"nội dung markdown\",\"source_ids\":[\"S1\"]} với đúng ID các đoạn trích thực tế đã dùng. Không tự tạo tên tài liệu, số trang hoặc liên kết."
)


class AIUnavailable(Exception):
    def __init__(self, reason: str = "temporary"):
        self.reason = reason
        super().__init__(reason)


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


    def explain(self, question: str, sources: list[ChunkSource]) -> tuple[str, list[ChunkSource]]:
        evidence = {f"S{index}": source for index, source in enumerate(sources, start=1)}
        content = {
            "question": question,
            "evidence": [{"id": key, "text": readable_pdf_text(source.excerpt)} for key, source in evidence.items()],
        }
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
            ],
        }
        # Reasoning models (OpenAI o1, o3-mini, gpt-6.1-sol) require developer role and reject temperature
        if self.model.startswith(("o1", "o3")) or "sol" in self.model:
            payload.pop("temperature", None)
            payload["messages"] = [
                {"role": "developer", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
            ]
            payload["max_completion_tokens"] = 3000
        url = urlsplit(self.endpoint)
        # Ollama's OpenAI-compatible endpoint supports JSON-object mode reliably,
        # while json_schema support varies by version/model. Keep the stricter
        # schema for hosted providers; validation below remains mandatory for both.
        if not self.is_local:
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
        if url.scheme == "http":
            payload.update(max_tokens=1200)
            connection_type, timeout = HTTPConnection, LOCAL_AI_TIMEOUT_SECONDS
        else:
            connection_type, timeout = HTTPSConnection, AI_TIMEOUT_SECONDS
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        for attempt in range(2):
            connection = connection_type(url.hostname, url.port, timeout=timeout)
            try:
                connection.request("POST", url.path, json.dumps(payload).encode("utf-8"), headers)
                response = connection.getresponse()
                if response.status in {401, 403}:
                    raise AIUnavailable("credentials")
                if response.status == 404:
                    raise AIUnavailable("model")
                if response.status != 200:
                    reason = "quota" if response.status == 429 else "temporary"
                    if attempt == 0 and (response.status == 429 or response.status >= 500):
                        sleep(1)
                        continue
                    raise AIUnavailable(reason)
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                break
            except (OSError, HTTPException):
                if attempt:
                    raise AIUnavailable("network") from None
                sleep(1)
            finally:
                connection.close()

        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Oversized provider response")
        try:
            message = json.loads(raw)["choices"][0]["message"]["content"]
            if isinstance(message, str):
                message = re.sub(r"^```(?:json)?\s*|\s*```$", "", message.strip())
            reply = json.loads(message)
            status = reply["status"]
            if status == "insufficient_evidence":
                return "", []
            answer, source_ids = reply["answer"], reply["source_ids"]
            if status != "success" or not isinstance(answer, str) or not answer.strip():
                raise ValueError("Invalid answer")
            if not isinstance(source_ids, list) or not source_ids:
                raise ValueError("Missing source IDs")
            if any(not isinstance(key, str) or key not in evidence for key in source_ids):
                raise ValueError("Unknown source ID")
            return answer.strip(), [evidence[key] for key in dict.fromkeys(source_ids)]
        except (TypeError, KeyError, IndexError, RecursionError):
            raise ValueError("Invalid provider response") from None


def get_provider_config(
    provider: str | None,
    api_key: str | None = None,
    fallback_ai: AIConfig | None = None,
    model_name: str | None = None,
) -> tuple[AIConfig | None, str | None]:
    """Resolve an AIConfig for a requested provider ('local', 'gemini', 'chatgpt') or fallback.

    Returns (config, error_reason). error_reason can be 'missing_key' or None.
    """
    if not provider:
        if model_name == "lookup":
            return None, None
        return fallback_ai, None

    provider = provider.lower().strip()
    key = (api_key or "").strip()
    chosen_model = (model_name or "").strip()

    if provider == "gemini":
        effective_key = key or (
            fallback_ai.api_key if fallback_ai and "generativelanguage" in fallback_ai.endpoint else ""
        )
        if not effective_key:
            return None, "missing_key"
        # Official Google Gemini OpenAI-compatible endpoint
        return AIConfig(
            endpoint="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            model=chosen_model or "gemini-3.8-flash",
            api_key=effective_key,
        ), None

    if provider == "chatgpt":
        effective_key = key or (
            fallback_ai.api_key if fallback_ai and "openai.com" in fallback_ai.endpoint else ""
        )
        if not effective_key:
            return None, "missing_key"
        return AIConfig(
            endpoint="https://api.openai.com/v1/chat/completions",
            model=chosen_model or "gpt-6-astra",
            api_key=effective_key,
        ), None

    if provider == "local":
        if chosen_model == "lookup":
            # Explicit pure offline retrieval (no local LLM)
            return None, None
        if fallback_ai and fallback_ai.is_local and not chosen_model:
            return fallback_ai, None
        # Default local Ollama endpoint; fallback to lookup if not running
        return AIConfig(
            endpoint="http://127.0.0.1:11434/v1/chat/completions",
            model=chosen_model or "qwen3.5:4b",
            api_key="",
        ), None

    return fallback_ai, None

