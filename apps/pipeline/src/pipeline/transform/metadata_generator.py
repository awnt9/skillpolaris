import instructor
from openai import OpenAI

from pipeline.transform.models import JobOfferMetadata

SYSTEM_PROMPT = (
    "You are an expert HR Data Analyst. Your task is to extract structured information from job "
    "offers.\n\n"
    "RULES:\n"
    "1. **standart_position**: Map the job title to a standard industry role "
    "(e.g., 'Ninja Python Guru' -> 'Backend Developer').\n"
    "2. **hard_skills**: Extract ONLY technical tools or specific methodologies. Must be EXACT "
    "words from the text. Max 3 words per skill. No soft skills.\n"
    "3. **Zero Hallucination**: If not mentioned, return an empty list or null.\n"
    "4. **NO NESTING**: Do NOT wrap the response in 'properties', 'JobOfferMetadata' or any "
    "other top-level key.\n"
    "5. **FLAT JSON**: The keys must be at the ROOT of the JSON object.\n\n"
    "CORRECT FORMAT:\n"
    '{"standart_position": "Data Scientist", "hard_skills": ["Python", "SQL"], '
    '"is_remote": true, "language_required": "English"}\n\n'
    "INCORRECT FORMAT:\n"
    '{"properties": {"standart_position": "...", ...}}'
)


class MetadataGenerator:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = instructor.patch(
            OpenAI(
                base_url=base_url,
                api_key=api_key,
            ),
            mode=instructor.Mode.JSON,
        )
        self.model = model

    def extract(self, clean_text: str) -> JobOfferMetadata:
        user_content = f"### JOB OFFER TEXT:\n{clean_text}\n###"

        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_model=JobOfferMetadata,
            max_retries=3,
            extra_body={"temperature": 0.0},
        )
