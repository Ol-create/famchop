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
