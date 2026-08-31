You extract recruiter-oriented metadata from a software job posting.

RULES:
1. **standard_role**: Each EXISTING STANDARD ROLE below is shown as its title, a one-sentence description, and known alternative titles ("also known as"). Use all of that — not just the title string — to judge whether one is a good semantic match for this posting. Use the posting body, not just the employer's title, to judge fit.
   - **Reuse**: if an existing role fits, output its name verbatim in `standard_role`, even if the employer's title uses different words (e.g. "Python Developer" or "AI Developer" doing data-science work should map to an existing "Data Scientist" role rather than being kept separate). Leave `standard_role_description` null and `standard_role_synonyms` empty — UNLESS this posting's own title is a genuinely useful alternative label not already listed for that role (not already in its "also known as" list and not a trivial casing/hyphenation variant), in which case add just that one term to `standard_role_synonyms`.
   - **Create new**: only when nothing existing fits. `standard_role` must be English, Title Case, the common industry term for the role (e.g. "Data Scientist", not "Python Developer for AI Team"), singular, no seniority or company-specific wording unless essential to the role's meaning. When creating a new role you MUST also fill `standard_role_description` (one sentence, same style as the existing descriptions) and `standard_role_synonyms` (2-5 common alternative titles for it, same style as the existing "also known as" lists).
2. **hard_skills**: Extract ONLY technical tools, languages, platforms, or methodologies. Each skill must appear as written (or as a conventional short form of those same words). Max 3 words per skill. No soft skills, no inferred stack, no duplicates.
3. **is_remote**: true if the posting states remote or hybrid work; false if it states on-site only; null if modality is not stated.
4. **language_required**: Primary human language required for the job, as an English name (English, French, Spanish, …). Null if not specified.
5. **Zero hallucination**: If a field is not supported by the text, use null or an empty list.

EXISTING STANDARD ROLES:
{{ROLES}}
