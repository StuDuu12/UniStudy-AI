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


@pytest.mark.parametrize(
    "endpoint, expected_format",
    [
        ("https://example.test/v1/chat/completions", "json_object"),
        ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "json_schema"),
        ("http://127.0.0.1:8080/v1/chat/completions", "json_schema"),
    ],
)
def test_provider_receives_compatible_response_format(monkeypatch, endpoint, expected_format):
    raw = json.dumps({
        "choices": [{"message": {"content": '{"status":"success","answer":"OK","source_ids":["S1"]}'}}],
    }).encode()

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, method, path, body, headers):
            response_format = json.loads(body)["response_format"]
            assert response_format["type"] == expected_format
            if expected_format == "json_schema":
                source_ids = response_format["json_schema"]["schema"]["properties"]["source_ids"]
                assert source_ids["items"]["enum"] == ["S1"]

        def getresponse(self):
            return SimpleNamespace(status=200, read=lambda _: raw)

        def close(self):
            pass

    monkeypatch.setattr(llm_service, "HTTPSConnection", Connection)
    monkeypatch.setattr(llm_service, "HTTPConnection", Connection)
    config = AIConfig(endpoint, "test-model", "test-key")
    source = ChunkSource("doc", "doc.pdf", 1, "c1", "Evidence")
    assert config.explain("Question", [source]) == ("OK", [source])
