"""Cheap LLM gate for programmable-market classification."""

from __future__ import annotations

from pipeline.observability import start_root_span
from pipeline.schemas.filter import FilterLlmDecision
from pydantic_ai import Agent, PromptedOutput
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

SYSTEM_PROMPT = (
    "You classify job offers for a software/data/IT engineering job market index: only "
    "accept roles that involve hands-on building, operating, or analyzing software "
    "systems (developers, data engineers, DevOps/SRE, ML engineers, QA automation, and "
    "similar).\n"
    "Accept only when both hold:\n"
    "1. The text itself describes hands-on technical work personally done by the role "
    "(writing code, configuring or building systems, operating infrastructure), not "
    "merely a team, product, or company that is technical. A manager or lead over a "
    "technical team is still non-technical management unless the text shows the "
    "manager personally does this work; leading, hiring, or setting strategy for "
    "builders is not building. The same applies to designers: proximity to a software "
    "product or the phrase \"design system\" is not evidence the designer builds or "
    "configures anything.\n"
    "2. The text names at least one concrete technology (a specific tool, language, "
    "platform, or framework). A title, product or domain name (e.g. \"Solutions "
    "Architect\", \"SAP\"), or generic phrase (\"technical solutions\", \"delivery\", "
    "\"deployment methodologies\", \"implementation projects\") is not enough on its "
    "own; a posting with no concrete technology adds nothing to the skill aggregations "
    "even if the role is otherwise technical.\n"
    "Reject outright: sales, pure marketing, HR, facilities, and any role with no "
    "meaningful technical craft.\n"
    "Use uncertain only when the text is genuinely ambiguous about whether condition 1 "
    "or 2 above holds; a clean absence of hands-on work or of any named technology is "
    "a reject, not uncertain.\n"
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
        name="filter",
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

        with start_root_span("filter") as span:
            result = self.agent.run_sync(user_content)
            if span is not None:
                span.update(input=user_content, output=result.output.model_dump())
        return result.output

    async def decide_async(
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

        with start_root_span("filter") as span:
            result = await self.agent.run(user_content)
            if span is not None:
                span.update(input=user_content, output=result.output.model_dump())
        return result.output
