"""Pure computation of precomputed role/skill matching statistics.

Each job's skills are grouped by `alt_group` (an ungrouped skill is its own
singleton group of size 1 — today every group is a singleton; alternative
groups of size >1, e.g. "AWS or GCP", are a later addition). Within a job, a
group's weight is the requirement_level weight of its strongest member
(required=1.0, preferred=0.6, nice_to_have=0.3 — see
pipeline.schemas.enrich.REQUIREMENT_LEVEL_WEIGHT), split evenly across the
group's members. This keeps the result bounded the same way the old uniform
1/n split was: matching every member of an alternative group never earns more
credit than a single fully-specified required skill would. It models
"coverage of a fully-specified requirement slot", not strict OR semantics —
knowing one alternative in a group scores less than knowing all of them,
rather than any single one giving full credit.

score_weight is the per-skill decomposition of the resulting mean per-offer
weighted coverage: summing score_weight over a candidate's matched skills
reproduces that mean exactly, without iterating jobs at match time.
market_pct is the plain "% of offers for this role that ask for this skill"
(unweighted presence rate), kept only for display.

Per-role, stats are computed once per distinct min_years_experience value
that actually occurs, PLUS the UNSPECIFIED_EXPERIENCE_YEARS bucket — and each
numbered bucket's job set is {jobs stating exactly that many years} UNION
{jobs that didn't state a number at all}. Postings with no stated experience
don't rule any candidate in or out, so folding them into every numbered
bucket both fixes bucket sparsity (most roles have far more unspecified
postings than any single explicit year) and lets the API's ranking fall back
to a plain UNSPECIFIED_EXPERIENCE_YEARS lookup rather than needing
nearest-bucket search logic.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from pipeline.schemas.enrich import REQUIREMENT_LEVEL_WEIGHT, SkillRequirementLevel
from pipeline.schemas.stats import (
    UNSPECIFIED_EXPERIENCE_YEARS,
    EnrichedJobSnapshot,
    RoleAggregate,
    RoleSkillWeight,
    SkillMention,
)


def _skill_stats_for_bucket(
    bucket_jobs: list[EnrichedJobSnapshot],
) -> tuple[Counter[int], dict[int, float]]:
    """skill_hits, skill_weight_sum for one bucket's job list."""
    skill_hits: Counter[int] = Counter()
    skill_weight_sum: dict[int, float] = defaultdict(float)
    for job in bucket_jobs:
        if not job.skills:
            continue

        groups: dict[str, list[SkillMention]] = defaultdict(list)
        for i, mention in enumerate(job.skills):
            groups[mention.alt_group or f"__singleton_{i}"].append(mention)

        group_weight: dict[str, float] = {}
        job_total_weight = 0.0
        for key, members in groups.items():
            level = max(
                REQUIREMENT_LEVEL_WEIGHT[SkillRequirementLevel(member.requirement_level)]
                for member in members
            )
            group_weight[key] = level
            job_total_weight += level

        for key, members in groups.items():
            per_member_weight = group_weight[key] / (len(members) * job_total_weight)
            for mention in members:
                skill_hits[mention.skill_id] += 1
                skill_weight_sum[mention.skill_id] += per_member_weight

    return skill_hits, skill_weight_sum


def compute_role_stats(
    jobs: list[EnrichedJobSnapshot],
) -> tuple[list[RoleSkillWeight], list[RoleAggregate]]:
    by_role: dict[str, list[EnrichedJobSnapshot]] = defaultdict(list)
    for job in jobs:
        by_role[job.standard_role].append(job)

    skill_weights: list[RoleSkillWeight] = []
    role_aggregates: list[RoleAggregate] = []

    for role, role_jobs in by_role.items():
        unspecified = [job for job in role_jobs if job.min_years_experience is None]
        explicit_values = sorted(
            {job.min_years_experience for job in role_jobs if job.min_years_experience is not None}
        )

        buckets: list[tuple[int, list[EnrichedJobSnapshot]]] = [
            (value, [job for job in role_jobs if job.min_years_experience == value] + unspecified)
            for value in explicit_values
        ]
        buckets.append((UNSPECIFIED_EXPERIENCE_YEARS, unspecified))

        for years, bucket_jobs in buckets:
            if not bucket_jobs:
                continue
            n = len(bucket_jobs)
            skill_hits, skill_weight_sum = _skill_stats_for_bucket(bucket_jobs)

            for skill_id, weight_sum in skill_weight_sum.items():
                skill_weights.append(
                    RoleSkillWeight(
                        standard_role=role,
                        experience_years=years,
                        skill_id=skill_id,
                        score_weight=weight_sum / n,
                        market_pct=skill_hits[skill_id] / n,
                    )
                )

            remote_known = [job.is_remote for job in bucket_jobs if job.is_remote is not None]
            is_remote_pct = (sum(remote_known) / len(remote_known)) if remote_known else None

            language_counts: Counter[str] = Counter(
                job.language_required for job in bucket_jobs if job.language_required
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
                    experience_years=years,
                    job_count=n,
                    is_remote_pct=is_remote_pct,
                    language_distribution=language_distribution,
                )
            )

    return skill_weights, role_aggregates
