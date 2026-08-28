"""Pure computation of precomputed role/skill matching statistics.

score_weight is the per-skill decomposition of the mean per-offer coverage ratio
mean_j( |candidate ∩ skills(j)| / |skills(j)| ): summing score_weight over a
candidate's matched skills reproduces that mean exactly, without iterating jobs
at match time. market_pct is the plain "% of offers for this role that ask for
this skill", kept only for display.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from pipeline.schemas.stats import EnrichedJobSnapshot, RoleAggregate, RoleSkillWeight


def compute_role_stats(
    jobs: list[EnrichedJobSnapshot],
) -> tuple[list[RoleSkillWeight], list[RoleAggregate]]:
    by_role: dict[str, list[EnrichedJobSnapshot]] = defaultdict(list)
    for job in jobs:
        by_role[job.standard_role].append(job)

    skill_weights: list[RoleSkillWeight] = []
    role_aggregates: list[RoleAggregate] = []

    for role, role_jobs in by_role.items():
        n = len(role_jobs)

        skill_hits: Counter[int] = Counter()
        skill_weight_sum: dict[int, float] = defaultdict(float)
        for job in role_jobs:
            if not job.skill_ids:
                continue
            per_skill_weight = 1.0 / len(job.skill_ids)
            for skill_id in job.skill_ids:
                skill_hits[skill_id] += 1
                skill_weight_sum[skill_id] += per_skill_weight

        for skill_id, weight_sum in skill_weight_sum.items():
            skill_weights.append(
                RoleSkillWeight(
                    standard_role=role,
                    skill_id=skill_id,
                    score_weight=weight_sum / n,
                    market_pct=skill_hits[skill_id] / n,
                )
            )

        remote_known = [job.is_remote for job in role_jobs if job.is_remote is not None]
        is_remote_pct = (sum(remote_known) / len(remote_known)) if remote_known else None

        language_counts: Counter[str] = Counter(
            job.language_required for job in role_jobs if job.language_required
        )
        total_language_jobs = sum(language_counts.values())
        language_distribution = (
            {lang: count / total_language_jobs for lang, count in language_counts.items()}
            if total_language_jobs
            else {}
        )

        role_aggregates.append(
            RoleAggregate(
                standard_role=role,
                job_count=n,
                is_remote_pct=is_remote_pct,
                language_distribution=language_distribution,
            )
        )

    return skill_weights, role_aggregates
