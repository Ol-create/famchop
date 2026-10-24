"""Single entry point to the LLM. Everything else calls ask_ai()/ask_json(), so swapping models is a one-line change."""

import json
import logging
import re
import time
from typing import Any

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

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


REQUEST_TIMEOUT_MS = 120_000
RETRY_DELAYS_S = (2, 6)  # after the 1st and 2nd failure; 3 attempts total

# Set once we learn the configured model rejects thinking_level, so we stop sending it
_thinking_unsupported = False


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, genai_errors.ServerError):  # 5xx: Google-side blip
        return True
    if isinstance(exc, genai_errors.ClientError):
        return exc.code == 429  # rate limited
    # Network trouble / timeouts from the HTTP layer
    return isinstance(exc, httpx.TransportError)


def _config() -> types.GenerateContentConfig:
    level = get_settings().gemma_thinking_level
    return types.GenerateContentConfig(
        # Gemma 4 thinks at length by default (~6k hidden tokens, 2.5 min for a meal plan).
        # MINIMAL brings that to ~25s with the same quality JSON.
        thinking_config=types.ThinkingConfig(thinking_level=level) if level and not _thinking_unsupported else None,
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
    )


def _generate(client: genai.Client, prompt: str) -> str:
    # Streaming keeps the connection active, so long replies don't hit read timeouts
    chunks = client.models.generate_content_stream(model=get_settings().gemma_model, contents=prompt, config=_config())
    return "".join(c.text for c in chunks if c.text)


def ask_ai(prompt: str) -> str:
    global _thinking_unsupported
    client = _get_client()
    for attempt, delay in enumerate((*RETRY_DELAYS_S, None), start=1):
        try:
            return _generate(client, prompt)
        except Exception as exc:
            if (
                isinstance(exc, genai_errors.ClientError)
                and exc.code == 400
                and "thinking" in str(exc).lower()
                and not _thinking_unsupported
            ):
                log.warning("Model doesn't support thinking_level; retrying without it")
                _thinking_unsupported = True
                try:
                    return _generate(client, prompt)
                except Exception as retry_exc:
                    exc = retry_exc
            if delay is None or not _is_transient(exc):
                log.exception("Gemma request failed (attempt %d)", attempt)
                raise AIError(f"AI request failed: {exc.__class__.__name__}") from exc
            log.warning("Gemma request failed (attempt %d), retrying in %ss: %s", attempt, delay, exc)
            time.sleep(delay)
    raise AssertionError("unreachable")


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
