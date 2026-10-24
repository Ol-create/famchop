from contextlib import contextmanager

from fastapi import HTTPException, status

from app.ai import AIError


@contextmanager
def ai_http_errors():
    """Turn AI failures into a clear HTTP error instead of a 500."""
    try:
        yield
    except AIError as exc:
        if "GEMINI_API_KEY" in str(exc):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI planner had a problem, please try again",
        ) from exc
