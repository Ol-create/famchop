"""Single entry point to the LLM. Everything else calls ask_ai()/ask_json(), so swapping models is a one-line change."""

import json
import logging
import re
from typing import Any

from google import genai

from app.config import get_settings

log = logging.getLogger(__name__)

_client: genai.Client | None = None


class AIError(Exception):
    """The model couldn't be reached or didn't return usable output."""


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.gemini_api_key or settings.gemini_api_key.startswith("your_key"):
            raise AIError("GEMINI_API_KEY is not set in backend/.env")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def ask_ai(prompt: str) -> str:
    try:
        response = _get_client().models.generate_content(
            model=get_settings().gemma_model,
            contents=prompt,
        )
    except AIError:
        raise
    except Exception as exc:
        log.exception("Gemma request failed")
        raise AIError(f"AI request failed: {exc.__class__.__name__}") from exc
    return response.text or ""


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> Any:
    """Parse JSON from a model reply that may be wrapped in ``` fences or surrounded by chatter."""
    fenced = _FENCE.search(text)
    candidate = fenced.group(1) if fenced else text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    # Fall back to the outermost {...} or [...] block
    starts = [i for i in (candidate.find("{"), candidate.find("[")) if i != -1]
    if starts:
        start = min(starts)
        end = max(candidate.rfind("}"), candidate.rfind("]"))
        if end > start:
            return json.loads(candidate[start : end + 1])
    raise json.JSONDecodeError("No JSON found in model reply", candidate, 0)


JSON_RULES = (
    "\n\nRespond with ONLY valid JSON matching the shape above. "
    "No markdown, no code fences, no comments, no text before or after the JSON."
)


def ask_json(prompt: str, validate=None) -> Any:
    """Ask for JSON, retrying once if the reply can't be parsed or fails `validate`.

    `validate` takes the parsed JSON and returns the cleaned value, raising ValueError if it's unusable.
    """
    full_prompt = prompt + JSON_RULES
    last_error: Exception | None = None
    for attempt in range(2):
        reply = ask_ai(full_prompt)
        try:
            data = extract_json(reply)
            return validate(data) if validate else data
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            log.warning("Gemma returned unusable JSON (attempt %d): %s", attempt + 1, exc)
            full_prompt = (
                prompt
                + JSON_RULES
                + f"\n\nYour previous reply could not be used ({exc}). Return corrected JSON only."
            )
    raise AIError(f"AI returned invalid JSON twice: {last_error}")
