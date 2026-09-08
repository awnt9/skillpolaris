"use client";

import { useState } from "react";

type Skill = {
  name: string;
  market_pct: number;
  is_matched: boolean;
};

type RoleMatch = {
  standard_role: string;
  experience_years: number | null;
  score: number;
  job_count: number;
  is_remote_pct: number | null;
  language_distribution: Record<string, number>;
  skills: Skill[];
};

export type CVMatchResponse = {
  matched_skills: string[];
  unmatched_skills: string[];
  candidate_years_experience: number | null;
  roles: RoleMatch[];
};

type ExperienceBucket = {
  experience_years: number | null;
  job_count: number;
  skills: { name: string; market_pct: number }[];
};

type RoleExperienceBreakdown = {
  standard_role: string;
  buckets: ExperienceBucket[];
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const pct = (value: number) => `${Math.round(value * 100)}%`;

const bucketLabel = (years: number | null) => (years === null ? "Not specified" : `${years} yrs`);

function RoleCard({
  role,
  rank,
  matchedSkills,
}: {
  role: RoleMatch;
  rank: number;
  matchedSkills: Set<string>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [breakdown, setBreakdown] = useState<RoleExperienceBreakdown | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedYears, setSelectedYears] = useState<number | null | undefined>(undefined);

  const toggleExpanded = async () => {
    if (expanded) {
      setExpanded(false);
      return;
    }
    setExpanded(true);
    if (breakdown || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_URL}/roles/${encodeURIComponent(role.standard_role)}/experience-breakdown`
      );
      if (!res.ok) throw new Error("Could not load requirements by experience level.");
      setBreakdown((await res.json()) as RoleExperienceBreakdown);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load requirements.");
    } finally {
      setLoading(false);
    }
  };

  const selectedBucket = breakdown?.buckets.find(
    (bucket) => bucket.experience_years === selectedYears
  );

  return (
    <div className="clay rounded-3xl px-6 py-5">
      <button
        onClick={toggleExpanded}
        className="flex w-full items-center justify-between gap-4 text-left"
      >
        <h3 className="text-lg font-semibold text-primary">
          {rank}. {role.standard_role}
        </h3>
        <span className="flex items-center gap-2">
          <span className="text-xl font-bold text-accent">{pct(role.score)}</span>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className={`h-4 w-4 text-secondary transition-transform duration-200 ${
              expanded ? "rotate-90" : ""
            }`}
          >
            <path
              fillRule="evenodd"
              d="M7.21 14.77a.75.75 0 0 1 .02-1.06L11.168 10 7.23 6.29a.75.75 0 1 1 1.04-1.08l4.5 4.25a.75.75 0 0 1 0 1.08l-4.5 4.25a.75.75 0 0 1-1.06-.02Z"
              clipRule="evenodd"
            />
          </svg>
        </span>
      </button>

      {expanded && (
        <div className="mt-3">
          {loading && <p className="text-xs text-secondary">Loading experience levels…</p>}
          {error && <p className="text-xs text-red-400">{error}</p>}
          {breakdown && (
            <div className="flex flex-wrap gap-2">
              {breakdown.buckets.map((bucket) => {
                const isSelected = bucket.experience_years === selectedYears;
                const isCandidateBucket = bucket.experience_years === role.experience_years;
                return (
                  <button
                    key={bucket.experience_years ?? "null"}
                    onClick={() =>
                      setSelectedYears((current) =>
                        current === bucket.experience_years ? undefined : bucket.experience_years
                      )
                    }
                    className={`rounded-full border px-3 py-1 text-xs font-medium ${
                      isSelected
                        ? "border-accent text-accent"
                        : "border-white/10 text-secondary hover:text-primary"
                    }`}
                  >
                    {bucketLabel(bucket.experience_years)} ({bucket.job_count})
                    {isCandidateBucket && " · your level"}
                  </button>
                );
              })}
            </div>
          )}

          {selectedBucket && (
            <ul className="mt-3 flex flex-col gap-1.5">
              {selectedBucket.skills.map((skill) => {
                const isMatched = matchedSkills.has(skill.name);
                return (
                  <li
                    key={skill.name}
                    className={`flex items-center justify-between text-sm ${
                      isMatched ? "font-medium text-accent" : "text-secondary"
                    }`}
                  >
                    <span className="capitalize">{skill.name}</span>
                    <span className={isMatched ? "font-semibold text-accent" : "font-medium text-primary"}>
                      {pct(skill.market_pct)}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default function CvMatchResults({ result }: { result: CVMatchResponse }) {
  if (result.roles.length === 0) {
    return (
      <div className="clay mx-auto mt-8 w-full max-w-xl rounded-3xl px-8 py-6 text-center">
        <p className="font-medium text-primary">
          {result.matched_skills.length === 0
            ? "We couldn't detect any technical skills in this resume."
            : "None of the detected skills matched a role in our database yet."}
        </p>
      </div>
    );
  }

  const matchedSkills = new Set(result.matched_skills);

  return (
    <div className="mx-auto mt-8 flex w-full max-w-xl flex-col gap-4">
      {result.roles.map((role, index) => (
        <RoleCard
          key={role.standard_role}
          role={role}
          rank={index + 1}
          matchedSkills={matchedSkills}
        />
      ))}

      {result.unmatched_skills.length > 0 && (
        <p className="text-center text-xs text-secondary">
          Not matched against our database: {result.unmatched_skills.join(", ")}
        </p>
      )}
    </div>
  );
}
