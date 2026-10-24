"""Single entry point to the LLM. Everything else calls ask_ai(), so swapping models is a one-line change."""

from google import genai

from app.config import get_settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set in backend/.env")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def ask_ai(prompt: str) -> str:
    response = _get_client().models.generate_content(
        model=get_settings().gemma_model,
        contents=prompt,
    )
    return response.text or ""
