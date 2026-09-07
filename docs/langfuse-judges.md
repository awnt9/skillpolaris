# LLM-as-a-Judge in Langfuse (filter + enrich)

This document is not code: it's the content for configuring two
**LLM-as-a-Judge evaluators** in the self-hosted Langfuse UI
(`LANGFUSE_PORT`, default `3001`). No pipeline changes are needed for this to
work — `filter` and `enrich` already call `pipeline.observability.configure_tracing`
(see `tasks/filter/runner.py` and `tasks/enrich/runner.py`), and
`Agent.instrument_all(True)` defaults to `include_content=True`, so every
trace already carries the full prompt/input and the structured output — the
judge has enough to evaluate without any extra instrumentation.

**CV upload is out of scope.** `/cv/upload` doesn't persist anything and
`apps/api` has no tracing configured; adding it would mean starting to
capture third-party CVs, which was deliberately left out (see this session's
plan) until the privacy/consent question is decided separately.

## Shared setup in the Langfuse UI

- **Judge model**: create an "LLM connection" in Langfuse (Settings →
  Models) pointing at the same provider the pipeline already uses
  (`LLM_BASE_URL` / `LLM_API_KEY` in `.env`), or a different model if you'd
  rather decouple the judge from the model being evaluated.
- **Target**: on each evaluator, filter by trace/observation name — `filter`
  and `enrich` respectively (these are the names Prefect/pydantic-ai already
  use for those agents; check the exact name in Langfuse's trace view before
  creating the evaluator).
- **Sampling**: start low — 10-20%. This is thesis/demo scale, not
  production monitoring; sampling everything just burns judge-model tokens
  without adding meaningful signal at this volume.
- **Variables**: map the judge prompt's `{{input}}` / `{{output}}` directly
  to the fields Langfuse already captures from the trace (the generation's
  input/output) — no manual JSONPath needed, they already come in full.
- **Judge output**: in both cases, a numeric 0-1 score plus a short
  free-text reasoning field — comparable across runs and, if this feeds into
  the thesis writeup, something citable as a metric.

---

## 1. Filter judge

Evaluates the trace/observation for `FilterLlmGate.decide` (`tasks/filter/llm.py`).
Captured input: `TITLE` + `DESCRIPTION_EXCERPT` (plus `source`/`keyword` when
present). Captured output: `{label, confidence}` (`FilterLlmDecision`).

**Judge prompt** (paste as-is — this is the text Langfuse sends the judge
model with `{{input}}`/`{{output}}` already substituted):

```
You are a quality reviewer for a classifier that decides whether a job
posting belongs in a software/data/IT engineering job-market index.

The policy the classifier was supposed to follow:
"You classify job offers for a software/data/IT engineering job market
index. Decide if the role is primarily about building, operating, or
analyzing software systems (developers, data engineers, DevOps/SRE, ML
engineers, QA automation, etc.). Reject sales, pure marketing, HR,
facilities, non-technical management, and roles with no meaningful
technical craft. Use uncertain only when the text is genuinely ambiguous."

Posting evaluated (classifier input):
{{input}}

Classifier decision (output):
{{output}}

Evaluate the decision on three criteria:
1. Correctness: does the label (accept/reject/uncertain) respect the policy
   above given the title and description excerpt?
2. Confidence calibration: is the confidence level consistent with how
   ambiguous or clear-cut the case actually is? Was "uncertain" used when it
   genuinely applied, rather than forcing accept/reject on a borderline case?
3. No hallucinated reasoning: the decision must not rely on facts that don't
   appear in the input.

Return:
- score: a number between 0 and 1 (1 = a perfect decision, 0 = clearly wrong
  or badly calibrated).
- reasoning: one sentence explaining the score, citing what in the input or
  output justifies it.
```

---

## 2. Enrich judge

Evaluates the trace/observation for `MetadataExtractor.extract` (`tasks/enrich/llm.py`).
Captured input: the posting's title and full description. Captured output:
the full `JobOfferMetadata` (`standard_role`, `standard_role_description`,
`standard_role_synonyms`, `hard_skills` — each with `requirement_level` and
`alt_group` since the requirement-level/OR-group work —, `is_remote`,
`language_required`).

**Judge prompt:**

```
You are a quality reviewer for a job-posting metadata extractor
(standardized role + technical skills) that feeds a CV-to-job matching
system.

Rules the extractor was supposed to follow (summarized from its real
prompt):
1. standard_role: reuse an existing role from the list if it's a good
   semantic fit (even if the employer's own title uses different words);
   only create a new one when nothing existing fits, and in that case it
   must come with standard_role_description and standard_role_synonyms.
2. hard_skills: only technical tools/languages/platforms/methodologies that
   appear literally in the text (or a conventional short form), max 3 words
   each, no duplicates, no soft skills. Each skill carries requirement_level
   (required/preferred/nice_to_have, based on the posting's own wording,
   required by default) and optionally alt_group (ONLY when the posting
   states a closed, explicit choice like "X or Y" — never for example lists
   introduced by "e.g./such as/like/for example/etc.", which illustrate a
   category rather than offer a closed alternative).
3. is_remote / language_required: null when not explicit in the text.
4. Zero hallucination: if a field isn't supported by the text, it must be
   null or empty.

Posting evaluated (extractor input):
{{input}}

Extracted metadata (output):
{{output}}

Evaluate on these criteria, heaviest first:
1. standard_role fit: did it reuse a reasonable existing role, or create a
   new one unnecessarily (duplicating a role that already existed in the
   list)? This is the most important criterion — an uncontrolled, growing
   role catalog degrades the whole matching system.
2. hard_skills precision/coverage: does every listed skill actually appear
   in the text? Is any obvious, explicitly-stated technical skill missing?
3. requirement_level: is the level assigned to each skill consistent with
   how the posting describes it (mandatory vs. desirable vs. optional)?
4. alt_group: was it used ONLY for explicit, closed alternatives ("X or
   Y"), and NEVER for example lists ("e.g.", "such as", "like")? This is the
   most common failure to watch for — the extractor tends to confuse "here
   are examples of category X" with "pick one of these".
5. is_remote / language_required: consistent with the text, without
   inventing anything not stated explicitly.

Return:
- score: a number between 0 and 1 (1 = a perfect extraction per the rules
  above).
- reasoning: one or two sentences explaining the score, pointing out the
  most relevant issue if there is one (or confirming none was found).
```

## Note on criterion 4 (alt_group)

This criterion was added after finding and fixing a real bug during
development: the extractor was grouping example lists ("cloud platforms
e.g. AWS, GCP, Azure") as if they were exclusive alternatives. The enrich
prompt has already been fixed to exclude that pattern explicitly, but it's
worth having the judge keep watching for it — it's the kind of regression
that can reappear if the prompt gets touched again later.
