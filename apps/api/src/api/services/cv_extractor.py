"""Pydantic AI agent that extracts skills from a resume.

Same construction pattern as pipeline.tasks.enrich.llm.MetadataExtractor
(Agent + PromptedOutput, temperature 0), adapted for CV text instead of a job
offer and run async since it's called from a request handler.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent, PromptedOutput
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from api.schemas.cv import CVProfile

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "cv_extract.md"


def load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def build_cv_agent(*, base_url: str, api_key: str, model: str) -> Agent[None, CVProfile]:
    chat_model = OpenAIChatModel(
        model,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        settings=OpenAIChatModelSettings(temperature=0.0),
    )
    return Agent(
        chat_model,
        output_type=PromptedOutput(CVProfile),
        system_prompt=load_system_prompt(),
        retries=3,
    )


class CVSkillExtractor:
    def __init__(self, *, base_url: str, api_key: str, model: str):
        self.agent = build_cv_agent(base_url=base_url, api_key=api_key, model=model)

    async def extract(self, resume_text: str) -> CVProfile:
        result = await self.agent.run(resume_text)
        return result.output
