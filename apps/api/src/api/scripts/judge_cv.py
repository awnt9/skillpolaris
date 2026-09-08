"""Calibration-only CLI: run the CV skill extractor over local resume PDFs and
have an LLM judge score each extraction against the resume text.

Standalone by design, never wired into /cv/upload: the endpoint deliberately
has no tracing or persistence for uploaded resumes (privacy/consent question
deferred, see docs/langfuse-judges.md). This tool is meant for the developer's
own manual calibration round ("run N test CVs, read the verdicts, adjust
cv_extract.md, repeat") on locally-held resumes, not for production traffic.

Usage (from the repo root, with .env populated):
    uv run --package api python -m api.scripts.judge_cv path/to/cv1.pdf path/to/cv2.pdf
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from api.config import get_settings
from api.services.cv_extractor import CVSkillExtractor
from api.services.cv_judge import CVJudge
from api.services.pdf import extract_text
from api.services.skills import normalized_skills


def _judge_one(path: str, extractor: CVSkillExtractor, judge: CVJudge) -> None:
    pdf_bytes = Path(path).read_bytes()
    resume_text = extract_text(pdf_bytes)
    if not resume_text:
        print(f"=== {path} ===\ncould not extract any text, skipping\n")
        return

    profile = asyncio.run(extractor.extract(resume_text))
    normalized = normalized_skills(profile.hard_skills)
    verdict = judge.score(
        resume_text=resume_text,
        hard_skills=profile.hard_skills,
        normalized_skills=normalized,
        years_experience=profile.years_experience,
    )

    print(f"=== {path} ===")
    print(f"hard_skills:       {profile.hard_skills}")
    print(f"normalized_skills: {normalized}")
    print(f"years_experience:  {profile.years_experience}")
    print(f"score:             {verdict.score:.2f}")
    print(f"reasoning:         {verdict.reasoning}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdfs", nargs="+", help="Paths to local resume PDFs")
    args = parser.parse_args()

    settings = get_settings()
    extractor = CVSkillExtractor(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )
    judge = CVJudge(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )

    for path in args.pdfs:
        _judge_one(path, extractor, judge)


if __name__ == "__main__":
    main()
