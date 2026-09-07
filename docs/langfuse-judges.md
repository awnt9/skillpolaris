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

Verified end-to-end against the actual running instance (Langfuse v4.27,
project `pipeline`) while writing this — every step below is the real UI,
not a guess.

### 1. LLM connection (Settings → LLM Connections)

`Project Settings → LLM Connections → Add LLM Connection`. Since we use
OpenRouter:
- **LLM adapter**: `openai` (OpenRouter is OpenAI-compatible).
- **Provider name**: e.g. `openrouter`.
- **API Key**: your OpenRouter key (same as `LLM_API_KEY` in `.env`, or a
  separate one if you want to budget the judge separately).
- Click **"Show advanced settings"**:
  - **API Base URL**: `https://openrouter.ai/api/v1` (same as
    `LLM_BASE_URL`).
  - **Enable default models**: turn this **off** — it lists OpenAI's own
    model names (`gpt-4o`, etc.), which don't exist on OpenRouter and will
    just be confusing in the model picker.
  - **Custom models → "Add custom model name"**: add the OpenRouter model
    slug(s) you want available, `provider/model` format — e.g.
    `deepseek/deepseek-chat-v3.1` (same as the pipeline uses), plus
    optionally a different one for the judge itself (e.g.
    `openai/gpt-4o-mini` or `anthropic/claude-3.5-haiku`) so the judge isn't
    grading the same model that generated the output.
- **Create connection**.

### 2. The evaluator (`Evaluators` in the sidebar → "New evaluator")

Pick **"New LLM-as-a-judge"** (not one of the templates — we have our own
rubric below). This opens a 3-step form:
1. **Define evaluation**: paste the judge prompt (below) into the message
   box — `{{input}}` and `{{output}}` are recognized automatically as
   template variables. Under **"with"**, pick the model from the LLM
   connection above. **Score output**: leave it as `number`, `between 0 and
   1`.
2. **Map variables to data**: `{{input}}` → `Input` and `{{output}}` →
   `Output` are set automatically — nothing to change, Langfuse already
   captures the full prompt/output on every trace.
3. **Name evaluator**: e.g. `filter-quality` / `enrich-quality`.

Click **"Create evaluator"**. It will show as **paused — "Default
evaluation model missing"** until you've picked a model in step 1 above
(this is expected if you create the evaluator before the LLM connection
exists — just go back and select the model, then Reactivate).

### 3. The rule (what traces it actually runs on)

An evaluator only runs once it's attached to a **Rule** — a separate object
that defines the trace filter and sampling rate. From the evaluator page,
click **Rules → Attach to rule → Create a new rule** (or `Evaluators →
Rules` tab → `New rule`):
- **Filter observations**: add `traceName:"filter run"` for the filter
  judge, or `traceName:"enrich run"` for the enrich judge. These exact
  names now exist because `build_filter_agent()` and `build_enrich_agent()`
  pass `name="filter"` / `name="enrich"` to pydantic-ai's `Agent(...)` —
  pydantic-ai's default instrumentation names an unnamed agent's trace
  generically `"agent run"`, which is indistinguishable between filter and
  enrich; the `name=` argument turns that into `"filter run"` / `"enrich
  run"` (verified live: after this change, `just filter` and `just enrich`
  produced 499 `filter run` and 25 `enrich run` traces respectively, versus
  a shared, ambiguous `agent run` before it).
- **Sampling rate**: a slider + `%` field, defaults to 100%. Set it to
  10-20% — this is thesis/demo scale, not production monitoring; judging
  every single trace just burns judge-model tokens without adding
  meaningful signal at this volume.
- **Attach evaluators**: pick the evaluator you created in step 2.
- **Name rule**, then **Save and activate**.

### Judge output

Both rubrics below ask for a numeric 0-1 score plus a short free-text
reasoning field — comparable across runs and, if this feeds into the thesis
writeup, something citable as a metric.

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
