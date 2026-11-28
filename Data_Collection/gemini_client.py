"""
Shared Gemini client helpers: client construction with an HTTP timeout, and
generate_content with retry + exponential backoff on transient errors.
"""

import os
import time
from typing import Any, Callable, Optional

DEFAULT_TIMEOUT_MS = 90_000

# Substrings (matched case-insensitively against the exception text) that mark an error as transient
RETRYABLE_MARKERS = (
    "503", "504", "429",
    "unavailable", "deadline_exceeded", "resource_exhausted",
    "timeout", "timed out",
)

MAX_ATTEMPTS = 5
BASE_DELAY_SECONDS = 10
MAX_DELAY_SECONDS = 120


def make_client(api_key: Optional[str] = None, timeout_ms: int = DEFAULT_TIMEOUT_MS):
    """Create a google-genai Client with an HTTP timeout (milliseconds)."""
    from google import genai
    from google.genai import types

    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
    return genai.Client(http_options=types.HttpOptions(timeout=timeout_ms))


def is_retryable(error: Exception) -> bool:
    """True for rate-limit, overload, and timeout errors."""
    if isinstance(error, TimeoutError) or "timeout" in type(error).__name__.lower():
        return True
    text = str(error).lower()
    return any(marker in text for marker in RETRYABLE_MARKERS)


def generate_with_retry(
    client: Any,
    model: str,
    contents: str,
    temperature: Optional[float] = None,
    max_attempts: int = MAX_ATTEMPTS,
    base_delay: float = BASE_DELAY_SECONDS,
    max_delay: float = MAX_DELAY_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Call client.models.generate_content, retrying transient errors with doubling backoff.

    Waits base_delay, 2*base_delay, ... (capped at max_delay) between attempts.
    Non-retryable errors, and the last retryable one, are re-raised.
    """
    kwargs = {"model": model, "contents": contents}
    if temperature is not None:
        from google.genai import types
        kwargs["config"] = types.GenerateContentConfig(temperature=temperature)

    delay = base_delay
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(**kwargs)
            return response.text if hasattr(response, "text") else str(response)
        except Exception as e:
            if attempt == max_attempts or not is_retryable(e):
                raise
            print(f"  ⏳ Transient error (attempt {attempt}/{max_attempts}): {e}. Retrying in {delay:.0f}s...")
            sleep(delay)
            delay = min(delay * 2, max_delay)
    raise RuntimeError("unreachable")
