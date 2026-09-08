"""LLM-as-a-judge for CV skill extraction.

Calibration-only, mirroring pipeline.tasks.judge.llm's FilterJudge/EnrichJudge
pattern: a separate Pydantic AI agent scores an already-produced extraction
against a rubric, instead of Langfuse's native Evaluators (verified broken on
this self-hosted instance, see docs/langfuse-judges.md). This one is not
wired into any request path: /cv/upload deliberately has no tracing or
persistence for uploaded resumes (privacy/consent question deferred, see the
same doc), so it is only ever invoked from api.scripts.judge_cv against the
developer's own local test resumes.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai import Agent, PromptedOutput
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "cv_judge.md"


class JudgeVerdict(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str


def build_cv_judge_agent(*, base_url: str, api_key: str, model: str) -> Agent[None, JudgeVerdict]:
    chat_model = OpenAIChatModel(
        model,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        settings=OpenAIChatModelSettings(temperature=0.0),
    )
    return Agent(
        chat_model,
        output_type=PromptedOutput(JudgeVerdict),
        system_prompt=_PROMPT_PATH.read_text(encoding="utf-8"),
        retries=3,
        name="judge-cv",
    )


class CVJudge:
    def __init__(self, *, base_url: str, api_key: str, model: str):
        self.agent = build_cv_judge_agent(base_url=base_url, api_key=api_key, model=model)

    def score(
        self,
        *,
        resume_text: str,
        hard_skills: list[str],
        normalized_skills: list[str],
        years_experience: int | None,
    ) -> JudgeVerdict:
        extraction = json.dumps(
            {
                "hard_skills": hard_skills,
                "normalized_skills": normalized_skills,
                "years_experience": years_experience,
            }
        )
        user_content = f"RESUME:\n{resume_text}\n\nEXTRACTED PROFILE (output):\n{extraction}"
        result = self.agent.run_sync(user_content)
        return result.output
