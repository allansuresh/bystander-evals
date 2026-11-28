"""
Shared Gemini client helpers: client construction with an HTTP timeout, and
generate_content with retry + exponential backoff on transient errors.
"""

import os
import time
from typing import Any, Callable, Optional

DEFAULT_TIMEOUT_MS = 90_000

from llm_retry import (  # noqa: F401  (re-exported)
    BASE_DELAY_SECONDS, MAX_ATTEMPTS, MAX_DELAY_SECONDS, RETRYABLE_MARKERS, call_with_retry, is_retryable,
)


def make_client(api_key: Optional[str] = None, timeout_ms: int = DEFAULT_TIMEOUT_MS):
    """Create a google-genai Client with an HTTP timeout (milliseconds)."""
    from google import genai
    from google.genai import types

    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
    return genai.Client(http_options=types.HttpOptions(timeout=timeout_ms))


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

    See llm_retry.call_with_retry for the backoff rules.
    """
    kwargs = {"model": model, "contents": contents}
    if temperature is not None:
        from google.genai import types
        kwargs["config"] = types.GenerateContentConfig(temperature=temperature)

    def call() -> str:
        response = client.models.generate_content(**kwargs)
        return response.text if hasattr(response, "text") else str(response)

    return call_with_retry(call, max_attempts=max_attempts, base_delay=base_delay,
                           max_delay=max_delay, sleep=sleep)
