"""Pydantic AI agent that extracts job-offer metadata."""

from __future__ import annotations

from pathlib import Path

from pipeline.schemas.enrich import JobOfferMetadata, StandardRoleOption, format_roles_block
from pydantic_ai import Agent, PromptedOutput
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

_PROMPT_PATH = Path(__file__).with_name("prompt.md")
_PROMPT_PLACEHOLDER = "{{ROLES}}"


def load_system_prompt(roles: list[StandardRoleOption]) -> str:
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace(_PROMPT_PLACEHOLDER, format_roles_block(roles))


def build_enrich_agent(
    *,
    base_url: str,
    api_key: str,
    model: str,
    roles: list[StandardRoleOption],
) -> Agent[None, JobOfferMetadata]:
    chat_model = OpenAIChatModel(
        model,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        settings=OpenAIChatModelSettings(temperature=0.0),
    )
    return Agent(
        chat_model,
        output_type=PromptedOutput(JobOfferMetadata),
        system_prompt=load_system_prompt(roles),
        retries=3,
    )


class MetadataExtractor:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        roles: list[StandardRoleOption],
    ):
        self.agent = build_enrich_agent(
            base_url=base_url,
            api_key=api_key,
            model=model,
            roles=roles,
        )

    def extract(self, *, title: str, description: str) -> JobOfferMetadata:
        user_content = f"TITLE: {title}\n\n### JOB OFFER TEXT:\n{description}\n###"
        result = self.agent.run_sync(user_content)
        return result.output
