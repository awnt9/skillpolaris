"""Pydantic AI judge agents: score a sampled filter/enrich output against a rubric.

Custom code harness instead of Langfuse's native Evaluators/Rules — those
don't reliably trigger on this self-hosted instance (verified: the
create-eval-queue step is never invoked, across two Langfuse versions).
"""

from __future__ import annotations

from pathlib import Path

from pipeline.schemas.judge import JudgeVerdict
from pydantic_ai import Agent, PromptedOutput
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

_PROMPT_DIR = Path(__file__).parent


def _build_judge_agent(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt_file: str,
    name: str,
) -> Agent[None, JudgeVerdict]:
    chat_model = OpenAIChatModel(
        model,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        settings=OpenAIChatModelSettings(temperature=0.0),
    )
    return Agent(
        chat_model,
        output_type=PromptedOutput(JudgeVerdict),
        system_prompt=(_PROMPT_DIR / prompt_file).read_text(encoding="utf-8"),
        retries=3,
        name=name,
    )


class FilterJudge:
    def __init__(self, *, base_url: str, api_key: str, model: str):
        self.agent = _build_judge_agent(
            base_url=base_url,
            api_key=api_key,
            model=model,
            prompt_file="prompt_filter.md",
            name="judge-filter",
        )

    def score(
        self,
        *,
        title: str,
        description_excerpt: str,
        label: str,
        confidence: float,
    ) -> JudgeVerdict:
        user_content = (
            f"POSTING (classifier input):\nTITLE: {title}\n"
            f"DESCRIPTION_EXCERPT:\n{description_excerpt}\n\n"
            f"CLASSIFIER DECISION (output):\nlabel={label}, confidence={confidence}"
        )
        result = self.agent.run_sync(user_content)
        return result.output


class EnrichJudge:
    def __init__(self, *, base_url: str, api_key: str, model: str):
        self.agent = _build_judge_agent(
            base_url=base_url,
            api_key=api_key,
            model=model,
            prompt_file="prompt_enrich.md",
            name="judge-enrich",
        )

    def score(self, *, title: str, description: str, metadata_json: str) -> JudgeVerdict:
        user_content = (
            f"POSTING (extractor input):\nTITLE: {title}\n\n{description}\n\n"
            f"EXTRACTED METADATA (output):\n{metadata_json}"
        )
        result = self.agent.run_sync(user_content)
        return result.output
