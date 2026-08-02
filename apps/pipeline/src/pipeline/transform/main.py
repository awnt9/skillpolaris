from typing import Protocol

from rich import print

from pipeline.config import get_configuration
from pipeline.persistence import PostgresManager
from pipeline.serving import QdrantManager
from pipeline.transform.embedding_generator import EmbeddingGenerator
from pipeline.transform.metadata_generator import MetadataGenerator
from pipeline.transform.models import CleanJobOffer, EmbeddedJobOffer, JobOfferMetadata, RawJobOffer
from pipeline.transform.preprocessors import preprocess_job_offer


class StagingJobStore(Protocol):
    def get_pending_staging_jobs(self, limit: int | None = None):
        ...

    def mark_as_processed(self, staging_id: int):
        ...

    def mark_as_failed(self, staging_id: int):
        ...


class VectorStore(Protocol):
    def upsert_job(self, job: EmbeddedJobOffer):
        ...


class EmbeddingService(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class MetadataService(Protocol):
    def extract(self, clean_text: str) -> JobOfferMetadata:
        ...


def get_pending_jobs(staging_store: StagingJobStore, limit: int | None) -> list[RawJobOffer]:
    rows = staging_store.get_pending_staging_jobs(limit=limit)
    return [RawJobOffer.model_validate(dict(row)) for row in rows]


def build_embedded_job_offer(
    clean_job: CleanJobOffer,
    embedding_service: EmbeddingService,
    metadata_service: MetadataService,
) -> EmbeddedJobOffer:
    vector = embedding_service.embed(clean_job.description)
    metadata = metadata_service.extract(clean_job.description)

    return EmbeddedJobOffer(
        id=clean_job.id,
        source=clean_job.source,
        job_id=clean_job.job_id,
        title=clean_job.title,
        description=clean_job.description,
        keyword=clean_job.keyword,
        vector=vector,
        metadata=metadata,
    )


def transform_and_store_job(
    raw_job: RawJobOffer,
    vector_store: VectorStore,
    embedding_service: EmbeddingService,
    metadata_service: MetadataService,
) -> None:
    clean_job = preprocess_job_offer(raw_job)
    embedded_job = build_embedded_job_offer(
        clean_job=clean_job,
        embedding_service=embedding_service,
        metadata_service=metadata_service,
    )
    vector_store.upsert_job(embedded_job)


def run_transform_pipeline(
    staging_store: StagingJobStore,
    vector_store: VectorStore,
    embedding_service: EmbeddingService,
    metadata_service: MetadataService,
    batch_size: int,
) -> None:
    raw_jobs = get_pending_jobs(staging_store=staging_store, limit=batch_size)

    if not raw_jobs:
        print("[yellow]No pending jobs found.[/]")
        return

    print(f"Transforming {len(raw_jobs)} pending jobs...")

    processed_count = 0
    failed_count = 0

    for raw_job in raw_jobs:
        try:
            transform_and_store_job(
                raw_job=raw_job,
                vector_store=vector_store,
                embedding_service=embedding_service,
                metadata_service=metadata_service,
            )
            staging_store.mark_as_processed(raw_job.id)
            processed_count += 1
            print(f"[green]Processed[/] staging_id={raw_job.id} title_source={raw_job.source}")

        except Exception as e:
            staging_store.mark_as_failed(raw_job.id)
            failed_count += 1
            print(f"[red]Failed[/] staging_id={raw_job.id} source={raw_job.source}: {e}")

    print(f"Transform finished. processed={processed_count}, failed={failed_count}")


if __name__ == "__main__":
    config = get_configuration()

    embedding_service = EmbeddingGenerator(
        base_url=config.ollama_base_url,
        api_key=config.ollama_api_key,
        model=config.embedding_model,
    )
    metadata_service = MetadataGenerator(
        base_url=config.ollama_base_url,
        api_key=config.ollama_api_key,
        model=config.model,
    )

    with PostgresManager(config) as staging_store, QdrantManager(config) as vector_store:
        run_transform_pipeline(
            staging_store=staging_store,
            vector_store=vector_store,
            embedding_service=embedding_service,
            metadata_service=metadata_service,
            batch_size=config.transform_batch_size,
        )
