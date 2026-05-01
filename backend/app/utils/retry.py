"""Tiny retry helper with exponential backoff and jitter, used for LLM calls."""
from __future__ import annotations

import logging
import random
import time
from typing import Callable, Iterable, Optional, TypeVar

from app.config import settings


T = TypeVar("T")
log = logging.getLogger(__name__)


def retry_call(
    fn: Callable[[], T],
    attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    retry_on: Iterable[type[BaseException]] = (Exception,),
    description: str = "operation",
) -> T:
    if attempts is None:
        attempts = settings.llm_retry_attempts
    if base_delay is None:
        base_delay = settings.llm_retry_base_delay
    if max_delay is None:
        max_delay = settings.llm_retry_max_delay
    last_exc: BaseException | None = None
    retry_types = tuple(retry_on)
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except retry_types as exc:
            last_exc = exc
            if attempt == attempts:
                break
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0, base_delay)
            log.warning(
                "%s failed (attempt %d/%d): %s — retrying in %.2fs",
                description,
                attempt,
                attempts,
                exc,
                delay,
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc
