type MatchedSkill = {
  name: string;
  market_pct: number;
};

type RoleMatch = {
  standard_role: string;
  score: number;
  job_count: number;
  is_remote_pct: number | null;
  language_distribution: Record<string, number>;
  matched_skills: MatchedSkill[];
};

export type CVMatchResponse = {
  matched_skills: string[];
  unmatched_skills: string[];
  roles: RoleMatch[];
};

const pct = (value: number) => `${Math.round(value * 100)}%`;

export default function CvMatchResults({ result }: { result: CVMatchResponse }) {
  if (result.roles.length === 0) {
    return (
      <div className="clay mx-auto mt-8 w-full max-w-2xl rounded-3xl px-8 py-6 text-center">
        <p className="font-medium text-primary">
          {result.matched_skills.length === 0
            ? "We couldn't detect any technical skills in this resume."
            : "None of the detected skills matched a role in our database yet."}
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto mt-8 flex w-full max-w-2xl flex-col gap-4">
      {result.roles.map((role, index) => (
        <div key={role.standard_role} className="clay rounded-3xl px-6 py-5">
          <div className="flex items-baseline justify-between gap-4">
            <h3 className="text-lg font-semibold text-primary">
              {index + 1}. {role.standard_role}
            </h3>
            <span className="text-xl font-bold text-accent">{pct(role.score)}</span>
          </div>
          <ul className="mt-3 flex flex-col gap-1.5">
            {role.matched_skills.map((skill) => (
              <li
                key={skill.name}
                className="flex items-center justify-between text-sm text-secondary"
              >
                <span className="capitalize">{skill.name}</span>
                <span className="font-medium text-primary">{pct(skill.market_pct)}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}

      {result.unmatched_skills.length > 0 && (
        <p className="text-center text-xs text-secondary">
          Not matched against our database: {result.unmatched_skills.join(", ")}
        </p>
      )}
    </div>
  );
}
