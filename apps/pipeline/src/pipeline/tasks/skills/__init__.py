"""Skill descriptions: fill in missing skills.description via LLM."""

from pipeline.tasks.skills.runner import describe_skills_task, run_describe_skills

__all__ = [
    "describe_skills_task",
    "run_describe_skills",
]
