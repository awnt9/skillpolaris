"""Cheap LLM gate for programmable-market classification."""

from __future__ import annotations

import instructor
from openai import OpenAI
from pipeline.schemas.filter import FilterLlmDecision

SYSTEM_PROMPT = (
    "You classify job offers for a software/data/IT engineering job market index.\n"
    "Decide if the role is primarily about building, operating, or analyzing software "
    "systems (developers, data engineers, DevOps/SRE, ML engineers, QA automation, etc.).\n"
    "Reject sales, pure marketing, HR, facilities, non-technical management, and roles "
    "with no meaningful technical craft.\n"
    "Use uncertain only when the text is genuinely ambiguous.\n"
    "Return flat JSON with keys label and confidence only."
)


class FilterLlmGate:
    """Single-shot JSON classification on title + short excerpt."""

    def __init__(self, *, base_url: str, api_key: str, model: str):
        self.client = instructor.patch(
            OpenAI(base_url=base_url, api_key=api_key),
            mode=instructor.Mode.JSON,
        )
        self.model = model

    def decide(
        self,
        *,
        title: str,
        description_excerpt: str,
        source: str | None = None,
        keyword: str | None = None,
    ) -> FilterLlmDecision:
        meta_bits = []
        if source:
            meta_bits.append(f"source={source}")
        if keyword:
            meta_bits.append(f"keyword={keyword}")
        meta = f"({' '.join(meta_bits)})\n" if meta_bits else ""

        user_content = (
            f"{meta}"
            f"TITLE: {title}\n"
            f"DESCRIPTION_EXCERPT:\n{description_excerpt}\n"
        )

        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_model=FilterLlmDecision,
            max_retries=2,
            extra_body={"temperature": 0.0},
        )
