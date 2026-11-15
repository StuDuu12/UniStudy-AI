import json
from types import SimpleNamespace
import pytest
from backend.services import llm_service
from backend.services.llm_service import AIConfig, AIUnavailable
from backend.services.ingest import ChunkSource


@pytest.mark.parametrize("statuses, expected_calls", [([503, 200], 2), ([429, 200], 2), ([200], 1)])
def test_transient_errors_are_retried(monkeypatch, statuses, expected_calls):
    calls = []
    raw = json.dumps({"choices": [{"message": {"content": '```json\n{"status":"success","answer":"OK","source_ids":["S1"]}\n```'}}]}).encode()
    class Connection:
        def __init__(self, *args, **kwargs): pass
        def request(self, *args): calls.append(1)
        def getresponse(self): return SimpleNamespace(status=statuses[len(calls)-1], read=lambda _:raw)
        def close(self): pass
    monkeypatch.setattr(llm_service, "HTTPSConnection", Connection)
    monkeypatch.setattr(llm_service, "sleep", lambda _: None)
    result = AIConfig("https://example.test/v1/chat/completions", "test", "secret").explain(
        "Question", [ChunkSource("doc", "doc.pdf", 1, "c1", "Evidence")]
    )
    assert result[0] == "OK"
    assert len(calls) == expected_calls


def test_invalid_credentials_are_not_retried_or_exposed(monkeypatch):
    calls = []
    class Connection:
        def __init__(self, *args, **kwargs): pass
        def request(self, *args): calls.append(1)
        def getresponse(self): return SimpleNamespace(status=401)
        def close(self): pass
    monkeypatch.setattr(llm_service, "HTTPSConnection", Connection)
    with pytest.raises(AIUnavailable) as error:
        AIConfig("https://example.test/v1/chat/completions", "test", "secret").explain("Q", [])
    assert len(calls) == 1
    assert "secret" not in str(error.value)


def test_local_uses_json_object_mode_for_ollama_compatibility(monkeypatch):
    payloads = []
    raw = json.dumps({"choices": [{"message": {"content": json.dumps({
        "status": "success", "answer": "OK", "source_ids": ["S1"]
    })}}]}).encode()

    class Connection:
        def __init__(self, *args, **kwargs): pass
        def request(self, _method, _path, body, _headers): payloads.append(json.loads(body))
        def getresponse(self): return SimpleNamespace(status=200, read=lambda _: raw)
        def close(self): pass

    monkeypatch.setattr(llm_service, "HTTPConnection", Connection)
    result = AIConfig("http://127.0.0.1:11434/v1/chat/completions", "qwen2.5:3b", "").explain(
        "Question", [ChunkSource("doc", "doc.pdf", 1, "c1", "Evidence")]
    )
    assert result[0] == "OK"
    assert payloads[0]["response_format"] == {"type": "json_object"}

