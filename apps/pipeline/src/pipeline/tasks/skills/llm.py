"""Pydantic AI agent that writes a one-sentence description for a technical skill."""

from __future__ import annotations

from pathlib import Path

from pipeline.schemas.skills import SkillDescriptionOut
from pydantic_ai import Agent, PromptedOutput
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

_PROMPT_PATH = Path(__file__).with_name("prompt.md")


def load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def build_skill_description_agent(
    *,
    base_url: str,
    api_key: str,
    model: str,
) -> Agent[None, SkillDescriptionOut]:
    chat_model = OpenAIChatModel(
        model,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        settings=OpenAIChatModelSettings(temperature=0.0),
    )
    return Agent(
        chat_model,
        output_type=PromptedOutput(SkillDescriptionOut),
        system_prompt=load_system_prompt(),
        retries=3,
        name="describe-skills",
    )


class SkillDescriber:
    def __init__(self, *, base_url: str, api_key: str, model: str):
        self.agent = build_skill_description_agent(base_url=base_url, api_key=api_key, model=model)

    def describe(self, skill_name: str) -> str:
        result = self.agent.run_sync(f"SKILL: {skill_name}")
        return result.output.description
