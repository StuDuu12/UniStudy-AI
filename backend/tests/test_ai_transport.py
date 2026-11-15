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


@pytest.mark.parametrize("marker", ["S2", "S99"])
def test_inline_citations_only_point_to_sources_returned_to_reader(monkeypatch, marker):
    payloads = []
    reply = {"status": "success", "answer": f"Giải thích theo giáo trình [{marker}].", "source_ids": ["S2"]}
    raw = json.dumps({"choices": [{"message": {"content": json.dumps(reply)}}]}).encode()

    class Connection:
        def __init__(self, *args, **kwargs): pass
        def request(self, _method, _path, body, _headers): payloads.append(json.loads(body))
        def getresponse(self): return SimpleNamespace(status=200, read=lambda _: raw)
        def close(self): pass

    monkeypatch.setattr(llm_service, "HTTPConnection", Connection)
    config = AIConfig("http://127.0.0.1:11434/v1/chat/completions", "test", "")
    sources = [
        ChunkSource("doc", "doc.pdf", 1, "c1", "Intro"),
        ChunkSource("doc", "doc.pdf", 2, "c2", "Evidence", formatted_excerpt="**Evidence**"),
    ]
    if marker == "S99":
        with pytest.raises(ValueError, match="citation"):
            config.explain("Q", sources, answer_style="review", context_question="Previous topic")
    else:
        answer, cited = config.explain("Q", sources, answer_style="review", context_question="Previous topic")
        assert answer.endswith("[1].")
        assert cited == sources[1:]
    user_content = json.loads(payloads[0]["messages"][-1]["content"])
    assert user_content["previous_question"] == "Previous topic"
    assert user_content["evidence"][1] == {"id": "S2", "text": "**Evidence**"}
    assert "tự kiểm tra" in payloads[0]["messages"][0]["content"]


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



@pytest.mark.parametrize("model, expected_effort", [
    ("gemini-3.8-flash", "low"),
    ("gemini-3.1-flash-lite", None),
    ("gemini-2.5-flash", None),
])
def test_gemini_preserves_fast_defaults_or_requests_low_effort(monkeypatch, model, expected_effort):
    captured = {}
    reply = {"status": "success", "answer": "Answer [S1]", "source_ids": ["S1"]}
    raw = json.dumps({"choices": [{"message": {"content": json.dumps(reply)}}]}).encode()

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, _method, _path, body, _headers):
            captured.update(json.loads(body))

        def getresponse(self):
            return SimpleNamespace(status=200, read=lambda _: raw)

        def close(self):
            pass

    monkeypatch.setattr(llm_service, "HTTPSConnection", Connection)
    source = ChunkSource("doc", "doc.pdf", 9, "c1", "Evidence")
    config, _ = llm_service.get_provider_config("gemini", api_key="test-key", model_name=model)
    assert config.explain("Question", [source]) == ("Answer [1]", [source])
    assert captured.get("reasoning_effort") == expected_effort


def test_slow_gemini_gets_one_generation_attempt(monkeypatch):
    calls = []

    class Connection:
        def __init__(self, *args, timeout):
            calls.append(timeout)

        def request(self, *args):
            pass

        def getresponse(self):
            raise TimeoutError("read timed out")

        def close(self):
            pass

    monkeypatch.setattr(llm_service, "HTTPSConnection", Connection)
    monkeypatch.setattr(llm_service, "sleep", lambda _: None)
    config, _ = llm_service.get_provider_config("gemini", api_key="test-key")
    source = ChunkSource("doc", "doc.pdf", 9, "c1", "Evidence")
    with pytest.raises(AIUnavailable) as error:
        config.explain("Question", [source])
    assert error.value.reason == "timeout"
    assert calls == [60]


def test_visual_input_uses_the_same_citation_id_as_the_selected_source(monkeypatch):
    captured = {}
    reply = {"status": "success", "answer": "See the formula [S1].", "source_ids": ["S1"]}
    raw = json.dumps({"choices": [{"message": {"content": json.dumps(reply)}}]}).encode()

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, _method, _path, body, _headers):
            captured.update(json.loads(body))

        def getresponse(self):
            return SimpleNamespace(status=200, read=lambda _: raw)

        def close(self):
            pass

    monkeypatch.setattr(llm_service, "HTTPSConnection", Connection)
    config, _ = llm_service.get_provider_config("gemini", api_key="test-key")
    chunk = ChunkSource("doc", "doc.pdf", 8, "page-eight", "A formula is printed on the slide.")
    assert config.explain("What is the formula?", [chunk], page_images={"page-eight": b"PNG"}) == (
        "See the formula [1].", [chunk],
    )
    parts = captured["messages"][-1]["content"]
    assert json.loads(parts[0]["text"])["evidence"][0]["id"] == "S1"
    assert "[S1]" in parts[1]["text"]
    assert parts[2]["image_url"]["url"] == "data:image/png;base64,UE5H"
