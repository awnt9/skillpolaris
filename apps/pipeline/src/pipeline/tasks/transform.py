"""Transform task: metadata, embeddings, and Qdrant upsert."""

from __future__ import annotations

import instructor
from openai import OpenAI
from pipeline.config import Settings, get_configuration
from pipeline.schemas.jobs import PendingCanonicalJob
from pipeline.schemas.transform import EmbeddedJobOffer, JobOfferMetadata
from pipeline.storage.postgres import PostgresManager
from pipeline.storage.qdrant import QdrantManager
from prefect import get_run_logger, task

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
            OpenAI(base_url=base_url, api_key=api_key),
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


class EmbeddingGenerator:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def embed(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            input=[text],
            model=self.model,
        )
        return response.data[0].embedding


def build_embedded_job_offer(
    canonical_job: PendingCanonicalJob,
    embedding_service: EmbeddingGenerator,
    metadata_service: MetadataGenerator,
) -> EmbeddedJobOffer:
    vector = embedding_service.embed(canonical_job.description)
    metadata = metadata_service.extract(canonical_job.description)

    return EmbeddedJobOffer(
        id=canonical_job.id,
        source=canonical_job.source,
        job_id=canonical_job.job_id,
        title=canonical_job.title,
        description=canonical_job.description,
        keyword=canonical_job.keyword,
        vector=vector,
        metadata=metadata,
    )


def run_transform(configuration: Settings) -> dict[str, int]:
    embedding_service = EmbeddingGenerator(
        base_url=configuration.ollama_base_url,
        api_key=configuration.ollama_api_key,
        model=configuration.embedding_model,
    )
    metadata_service = MetadataGenerator(
        base_url=configuration.ollama_base_url,
        api_key=configuration.ollama_api_key,
        model=configuration.model,
    )

    processed = 0
    failed = 0

    with PostgresManager(configuration) as store, QdrantManager(configuration) as vector_store:
        pending = store.get_pending_canonical_jobs(limit=configuration.transform_batch_size)

        for canonical_job in pending:
            try:
                embedded_job = build_embedded_job_offer(
                    canonical_job=canonical_job,
                    embedding_service=embedding_service,
                    metadata_service=metadata_service,
                )
                vector_store.upsert_job(embedded_job)
                store.mark_canonical_processed(canonical_job.id)
                processed += 1
            except Exception:
                store.mark_canonical_failed(canonical_job.id)
                failed += 1

    return {"pending": len(pending), "processed": processed, "failed": failed}


@task(name="transform", retries=1)
def transform_task() -> dict[str, int]:
    logger = get_run_logger()
    configuration = get_configuration()
    result = run_transform(configuration)
    logger.info(
        "Transform finished. pending=%s processed=%s failed=%s",
        result["pending"],
        result["processed"],
        result["failed"],
    )
    return result
