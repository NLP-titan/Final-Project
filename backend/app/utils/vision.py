"""Claude vision helper — extracts structured JSON from images and PDFs.

The endpoints that consume this are best-effort and fail gracefully: if no API key
is configured or the model cannot produce parseable JSON, the caller surfaces a
"could not analyse" message instead of crashing.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Optional

from app.config import settings
from app.utils.retry import retry_call


log = logging.getLogger(__name__)


SUPPORTED_IMAGE_MEDIA_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}
SUPPORTED_PDF_MEDIA_TYPE = "application/pdf"


class VisionUnavailable(RuntimeError):
    """Raised when no vision-capable LLM is configured."""


class VisionParseError(RuntimeError):
    """Raised when the model's response cannot be parsed as JSON."""


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model response.

    Handles ```json fences, plain ``` fences, and bare objects.
    """
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        # find the outermost {...}
        first = text.find("{")
        last = text.rfind("}")
        if first == -1 or last == -1 or last <= first:
            raise VisionParseError(f"no JSON object found in response: {text[:200]!r}")
        candidate = text[first : last + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise VisionParseError(f"invalid JSON: {exc}; raw={candidate[:200]!r}")


def analyze_with_claude(
    image_bytes: bytes,
    media_type: str,
    prompt: str,
    *,
    max_tokens: int = 1024,
) -> dict:
    """Send `image_bytes` + `prompt` to Claude and parse the JSON response.

    `media_type` should be one of the supported image MIME types or `application/pdf`.
    Raises `VisionUnavailable` if no Anthropic API key is configured.
    Raises `VisionParseError` if the model's response is not valid JSON.
    """
    if not settings.anthropic_api_key:
        raise VisionUnavailable("ANTHROPIC_API_KEY is not configured")

    if media_type not in SUPPORTED_IMAGE_MEDIA_TYPES and media_type != SUPPORTED_PDF_MEDIA_TYPE:
        raise ValueError(
            f"unsupported media type {media_type!r}; expected image/* or application/pdf"
        )

    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    encoded = base64.standard_b64encode(image_bytes).decode("utf-8")

    if media_type == SUPPORTED_PDF_MEDIA_TYPE:
        media_block = {
            "type": "document",
            "source": {"type": "base64", "media_type": media_type, "data": encoded},
        }
    else:
        media_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": encoded},
        }

    resp = retry_call(
        lambda: client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [media_block, {"type": "text", "text": prompt}],
                }
            ],
        ),
        attempts=2,
        description="anthropic.vision.messages.create",
    )

    text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    raw = "\n".join(text_parts).strip()
    log.debug("claude vision raw response: %s", raw[:500])
    return _extract_json(raw)


def guess_media_type(filename: str, content_type: Optional[str]) -> str:
    """Best-effort media type from filename + Content-Type header.

    Falls back to image/jpeg for unknown image extensions.
    """
    if content_type:
        ct = content_type.lower().split(";")[0].strip()
        if ct in SUPPORTED_IMAGE_MEDIA_TYPES or ct == SUPPORTED_PDF_MEDIA_TYPE:
            return ct
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return SUPPORTED_PDF_MEDIA_TYPE
    if name.endswith(".png"):
        return "image/png"
    if name.endswith(".webp"):
        return "image/webp"
    if name.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"
