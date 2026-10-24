import json

import pytest

from app import ai
from app.ai import AIError, ask_json, extract_json


@pytest.mark.parametrize(
    "reply",
    [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        '```\n{"a": 1}\n```',
        'Sure! Here is your plan:\n{"a": 1}\nEnjoy your meals.',
        'Here you go ```JSON {"a": 1} ``` hope it helps',
    ],
)
def test_extract_json_handles_fences_and_chatter(reply):
    assert extract_json(reply) == {"a": 1}


def test_extract_json_list():
    assert extract_json('result: [1, 2, 3] done') == [1, 2, 3]


def test_extract_json_garbage_raises():
    with pytest.raises(json.JSONDecodeError):
        extract_json("I can't help with that.")


def test_ask_json_retries_once_then_succeeds(gemma):
    gemma.queue("not json at all", '{"ok": true}')
    assert ask_json("give me json") == {"ok": True}
    assert len(gemma.prompts) == 2
    assert "previous reply could not be used" in gemma.prompts[1]


def test_ask_json_retries_when_validation_fails(gemma):
    def must_have_ok(data):
        if "ok" not in data:
            raise ValueError("missing ok")
        return data

    gemma.queue('{"nope": 1}', '{"ok": 1}')
    assert ask_json("q", validate=must_have_ok) == {"ok": 1}
    assert "missing ok" in gemma.prompts[1]


def test_ask_json_gives_up_after_two_bad_replies(gemma):
    gemma.queue("bad", "still bad")
    with pytest.raises(AIError):
        ask_json("q")
    assert len(gemma.prompts) == 2


def test_missing_api_key_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(ai, "_client", None)
    monkeypatch.setattr(ai.get_settings(), "gemini_api_key", "")
    with pytest.raises(AIError, match="GEMINI_API_KEY"):
        ai.ask_ai("hi")


# ---------- transient error retries ----------


def _api_error(code, message="boom"):
    from google.genai import errors

    cls = errors.ServerError if code >= 500 else errors.ClientError
    return cls(code, {"error": {"code": code, "message": message, "status": "X"}})


class _FakeClient:
    """Mimics client.models.generate_content_stream, raising the queued errors first."""

    def __init__(self, failures):
        self.failures = list(failures)
        self.configs = []
        self.models = self

    def generate_content_stream(self, model, contents, config):
        self.configs.append(config)
        if self.failures:
            raise self.failures.pop(0)
        return iter([type("C", (), {"text": "o"})(), type("C", (), {"text": None})(), type("C", (), {"text": "k"})()])

    @property
    def calls(self):
        return len(self.configs)


def _install(monkeypatch, failures):
    fake = _FakeClient(failures)
    monkeypatch.setattr(ai, "_get_client", lambda: fake)
    monkeypatch.setattr(ai.time, "sleep", lambda s: None)
    monkeypatch.setattr(ai, "_thinking_unsupported", False)
    return fake


def test_streams_and_joins_chunks_with_minimal_thinking(monkeypatch):
    fake = _install(monkeypatch, [])
    assert ai.ask_ai("hi") == "ok"
    assert fake.configs[0].thinking_config.thinking_level == "MINIMAL"


def test_retries_google_500_then_succeeds(monkeypatch):
    fake = _install(monkeypatch, [_api_error(500)])
    assert ai.ask_ai("hi") == "ok" and fake.calls == 2


def test_retries_rate_limit_and_network_errors(monkeypatch):
    import httpx

    fake = _install(monkeypatch, [_api_error(429), httpx.ReadTimeout("slow")])
    assert ai.ask_ai("hi") == "ok" and fake.calls == 3


def test_gives_up_after_three_attempts(monkeypatch):
    fake = _install(monkeypatch, [_api_error(500)] * 3)
    with pytest.raises(AIError):
        ai.ask_ai("hi")
    assert fake.calls == 3


def test_does_not_retry_bad_request(monkeypatch):
    fake = _install(monkeypatch, [_api_error(400)])
    with pytest.raises(AIError):
        ai.ask_ai("hi")
    assert fake.calls == 1


def test_drops_thinking_level_if_model_rejects_it(monkeypatch):
    fake = _install(monkeypatch, [_api_error(400, "Thinking level is not supported for this model.")])
    assert ai.ask_ai("hi") == "ok"
    assert fake.configs[0].thinking_config is not None and fake.configs[1].thinking_config is None
    ai.ask_ai("again")  # remembered for later calls
    assert fake.configs[2].thinking_config is None
