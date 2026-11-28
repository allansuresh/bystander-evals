"""
Provider-agnostic retry with exponential backoff for LLM API calls
(shared by Data_Collection and Eval_LLMs; no import-time side effects).
"""

import re
import time
from typing import Callable, Optional, TypeVar

T = TypeVar("T")

# Substrings (matched case-insensitively against the exception text) that mark an error as transient
RETRYABLE_MARKERS = (
    "503", "504", "429", "529",
    "unavailable", "deadline_exceeded", "resource_exhausted", "overloaded",
    "timeout", "timed out",
)

MAX_ATTEMPTS = 5
BASE_DELAY_SECONDS = 10
MAX_DELAY_SECONDS = 120


def is_retryable(error: Exception) -> bool:
    """True for rate-limit, overload, and timeout errors."""
    if isinstance(error, TimeoutError) or "timeout" in type(error).__name__.lower():
        return True
    text = str(error).lower()
    return any(marker in text for marker in RETRYABLE_MARKERS)


def retry_after_seconds(error: Exception) -> Optional[float]:
    """Server-suggested wait, from "Please retry in 37.3s" or "retryDelay': '37s'", if present."""
    text = str(error)
    for pattern in (r"retry in\s+(\d+(?:\.\d+)?)\s*s", r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s"):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def call_with_retry(
    fn: Callable[[], T],
    should_retry: Callable[[Exception], bool] = is_retryable,
    max_attempts: int = MAX_ATTEMPTS,
    base_delay: float = BASE_DELAY_SECONDS,
    max_delay: float = MAX_DELAY_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    label: str = "",
) -> T:
    """Call fn(), retrying errors for which should_retry(e) is true.

    Waits base_delay, 2*base_delay, ... (capped at max_delay) between attempts, or longer if
    the error says "Please retry in Ns". Non-retryable errors, and the last retryable one,
    are re-raised.
    """
    delay = base_delay
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            if attempt == max_attempts or not should_retry(e):
                raise
            wait = max(delay, retry_after_seconds(e) or 0)
            prefix = f"{label}: " if label else ""
            print(f"  ⏳ {prefix}transient error (attempt {attempt}/{max_attempts}): {str(e)[:200]}. "
                  f"Retrying in {wait:.0f}s...")
            sleep(wait)
            delay = min(delay * 2, max_delay)
    raise RuntimeError("unreachable")
