"""Cheap LLM gate for programmable-market classification."""

from __future__ import annotations

from pipeline.schemas.filter import FilterLlmDecision
from pydantic_ai import Agent, PromptedOutput
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

SYSTEM_PROMPT = (
    "You classify job offers for a software/data/IT engineering job market index.\n"
    "Decide if the role is primarily about building, operating, or analyzing software "
    "systems (developers, data engineers, DevOps/SRE, ML engineers, QA automation, etc.).\n"
    "Reject sales, pure marketing, HR, facilities, non-technical management, and roles "
    "with no meaningful technical craft.\n"
    "Use uncertain only when the text is genuinely ambiguous.\n"
    "Return flat JSON with keys label and confidence only."
)


def build_filter_agent(
    *,
    base_url: str,
    api_key: str,
    model: str,
) -> Agent[None, FilterLlmDecision]:
    chat_model = OpenAIChatModel(
        model,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        settings=OpenAIChatModelSettings(temperature=0.0),
    )
    return Agent(
        chat_model,
        output_type=PromptedOutput(FilterLlmDecision),
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )


class FilterLlmGate:
    """Single-shot JSON classification on title + short excerpt."""

    def __init__(self, *, base_url: str, api_key: str, model: str):
        self.agent = build_filter_agent(
            base_url=base_url,
            api_key=api_key,
            model=model,
        )

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

        result = self.agent.run_sync(user_content)
        return result.output
