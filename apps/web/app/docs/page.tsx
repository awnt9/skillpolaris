const stages = [
  {
    title: "1. Extract",
    body: "The pipeline pulls raw job postings from every configured source — job boards and ATS platforms such as Greenhouse, plus dedicated feeds — on a recurring schedule. Each posting is stored as-is, keyed by (source, job ID), so re-runs never create duplicates.",
  },
  {
    title: "2. Filter",
    body: "Every raw posting passes through a filter gate that combines simple heuristics (description length, keyword relevance) with an LLM confidence check. Postings that pass become canonical job offers — deduplicated, cleaned records ready for enrichment.",
  },
  {
    title: "3. Enrich",
    body: "An LLM reads every canonical posting and extracts structured metadata: a standardized role from a closed vocabulary, the hard skills mentioned, whether the role is remote, and the language required. This is what turns free-text job ads into comparable data.",
  },
];

const statsExplained = [
  {
    label: "Sources tracked",
    body: "The number of distinct origins postings have been pulled from — every job board or ATS the pipeline has ingested at least one listing from.",
  },
  {
    label: "Job records",
    body: "The total number of canonical job offers stored — postings that passed the filter stage and are treated as real, de-duplicated listings.",
  },
  {
    label: "Job positions",
    body: "The number of distinct standardized roles assigned during enrichment — how many different kinds of positions are represented in the data.",
  },
];

export default function DocsPage() {
  return (
    <div className="flex flex-col gap-14 py-8">
      <section className="text-center">
        <h1 className="text-3xl font-bold tracking-tight text-primary">
          How SkillPolaris works
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-secondary">
          A short walkthrough of the pipeline that turns scattered job postings into the
          numbers shown on the home page.
        </p>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-xl font-semibold text-primary">The pipeline</h2>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {stages.map((stage) => (
            <div key={stage.title} className="clay rounded-3xl px-6 py-6">
              <h3 className="font-semibold text-primary">{stage.title}</h3>
              <p className="mt-2 text-sm text-secondary">{stage.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-xl font-semibold text-primary">
          Where the home page stats come from
        </h2>
        <div className="flex flex-col gap-4">
          {statsExplained.map((stat) => (
            <div key={stat.label} className="clay rounded-2xl px-6 py-5">
              <h3 className="font-semibold text-primary">{stat.label}</h3>
              <p className="mt-1 text-sm text-secondary">{stat.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
