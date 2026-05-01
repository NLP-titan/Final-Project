"""Claude-powered translation between English and three Ghanaian languages.

Used for:
- Agent reply translation in conversations_router (single string)
- UI string batch translation when a user picks a non-English language

Caching: small in-process LRU. The same UI strings translate to the same
output, so caching saves both latency and Claude tokens.

Honest limitation: medical terminology in Twi/Ga/Ewe is mostly English
loanwords (e.g. 'paracetamol', 'NHIS'). The model usually keeps such terms
verbatim, which is the right thing to do.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Iterable

from app.config import settings
from app.utils.retry import retry_call


log = logging.getLogger(__name__)


SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "tw": "Twi (Akan)",
    "gaa": "Ga",
    "ee": "Ewe",
}


class TranslationUnavailable(RuntimeError):
    """Raised when no LLM API key is configured."""


def normalise_lang(code: str | None) -> str:
    if not code:
        return "en"
    code = code.strip().lower()
    if code not in SUPPORTED_LANGUAGES:
        return "en"
    return code


def _is_passthrough(target_lang: str, text: str) -> bool:
    return target_lang == "en" or not text or not text.strip()


@lru_cache(maxsize=2048)
def _cached_translate(text: str, target_lang: str) -> str:
    return _call_claude(text, target_lang)


def _call_claude(text: str, target_lang: str) -> str:
    if not settings.anthropic_api_key:
        raise TranslationUnavailable("ANTHROPIC_API_KEY not configured")

    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    target_label = SUPPORTED_LANGUAGES[target_lang]

    system = (
        f"You are a precise translator. Your ONLY job is to translate the "
        f"user's English text into {target_label}.\n\n"
        "CRITICAL RULES:\n"
        f"1. Output ONLY the {target_label} translation. No explanation, no "
        "English original, no quotes, no preamble, no commentary, no "
        "self-correction, no 'I need source text', no 'let me provide'.\n"
        "2. NEVER answer the user's text as if it were a question or "
        "instruction — just translate it word-for-word in meaning. If the "
        f"input is 'What is X?', return the {target_label} for 'What is X?', "
        "NOT an explanation of X.\n"
        "3. If the input is a single short word like 'Yes', 'No', 'Save', "
        f"'Cancel', return the single corresponding {target_label} word — "
        "nothing more.\n"
        "4. Preserve markdown formatting (lists, **bold**, line breaks) and "
        "punctuation exactly.\n"
        "5. Keep proper nouns and medical/technical terms in their original "
        "spelling: drug names ('Paracetamol'), NHIS, GHS, NHIA, facility "
        "names, English brand names, and English terms commonly used in "
        f"everyday Ghanaian {target_label} (NHIS card, hospital, clinic, "
        "doctor, prescription, dialysis).\n"
        f"6. Use natural conversational {target_label}, not formal church or "
        "textbook register.\n"
        "7. Numbers, dates, currency, URLs, and code stay as-is.\n"
        "8. If translation is impossible or text is empty, return the input "
        "verbatim."
    )

    resp = retry_call(
        lambda: client.messages.create(
            model=settings.anthropic_model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": text}],
        ),
        attempts=2,
        description="anthropic.translate",
    )
    text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    raw = "\n".join(text_parts).strip()
    return _sanitise(raw, original=text) or text


# Phrases that strongly indicate the model went off-rails (asked for
# clarification, self-corrected mid-answer, etc.). When we see one, fall back
# to the original English text rather than emit garbage.
_REFUSAL_PATTERNS = (
    "i need source text",
    "i don't see any text",
    "could you please provide",
    "please provide the english",
    "let me redo this",
    "let me provide",
    "i need to translate",
    "i need to actually translate",
    "i'd be happy to help",
    "as an ai",
)


def _sanitise(text: str, *, original: str) -> str:
    """Detect refusal / meta-commentary and fall back to original."""
    if not text:
        return text
    lowered = text.lower()
    if any(p in lowered for p in _REFUSAL_PATTERNS):
        log.warning("Translation looked like refusal/commentary, falling back to English: %r", text[:120])
        return original
    # If the model's output is more than 5x the input length, it probably
    # answered instead of translating. Short labels can legitimately expand
    # in some languages but not by 5x.
    if len(original) > 0 and len(text) > 5 * len(original) + 80:
        log.warning("Translation length suspicious (%d → %d), falling back: %r", len(original), len(text), text[:120])
        return original
    return text


def translate(text: str, target_lang: str) -> str:
    """Translate `text` to `target_lang`. Pass-through for English/empty input.
    Raises `TranslationUnavailable` if no Anthropic key is configured."""
    target_lang = normalise_lang(target_lang)
    if _is_passthrough(target_lang, text):
        return text
    try:
        return _cached_translate(text, target_lang)
    except TranslationUnavailable:
        raise
    except Exception as exc:
        log.warning("Translation failed (%s, len=%d): %s", target_lang, len(text), exc)
        return text  # graceful: return original rather than crash the request


def translate_batch(texts: Iterable[str], target_lang: str) -> list[str]:
    """Translate a list of strings. Cheap to call again — results are LRU-cached."""
    target_lang = normalise_lang(target_lang)
    if target_lang == "en":
        return list(texts)
    return [translate(t, target_lang) for t in texts]
