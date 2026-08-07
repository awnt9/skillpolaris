"""Fixed pre-LLM filters: hygiene only (no skill vocabulary lists)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_URL_RE = re.compile(r"http[s]?://\S+")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b")
_ALNUM_RE = re.compile(r"[A-Za-z0-9]")


@dataclass(frozen=True)
class RuleOutcome:
    """Result of fixed filters before the LLM gate."""

    ok: bool
    cleaned_title: str = ""
    cleaned_description: str = ""
    reject_reason: str | None = None


def clean_description(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""

    cleaned = _URL_RE.sub("", text)
    cleaned = _EMAIL_RE.sub("", cleaned)
    cleaned = re.sub(r"#{2,}", "", cleaned)
    cleaned = re.sub(r"-{3,}", "", cleaned)
    cleaned = re.sub(r"\*{3,}", "", cleaned)
    cleaned = re.sub(r"\n\s*[\*\-]\s+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _symbol_ratio(text: str) -> float:
    if not text:
        return 1.0
    alnum = len(_ALNUM_RE.findall(text))
    return 1.0 - (alnum / len(text))


def apply_fixed_filters(
    *,
    title_raw: str | None,
    description_raw: str | None,
    min_description_chars: int,
    max_symbol_ratio: float = 0.45,
) -> RuleOutcome:
    """Reject empty / too-short / garbage text. Pass survivors to the LLM."""
    title = (title_raw or "").strip()
    if not title:
        return RuleOutcome(ok=False, reject_reason="empty_title")

    description = clean_description(description_raw or "")
    if not description:
        return RuleOutcome(ok=False, reject_reason="empty_description")

    if len(description) < min_description_chars:
        return RuleOutcome(ok=False, reject_reason="short_description")

    if _symbol_ratio(description) > max_symbol_ratio:
        return RuleOutcome(ok=False, reject_reason="garbage_text")

    return RuleOutcome(
        ok=True,
        cleaned_title=title,
        cleaned_description=description,
    )
