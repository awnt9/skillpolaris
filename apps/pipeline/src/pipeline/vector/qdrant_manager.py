from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from pipeline.transform.models import EmbeddedJobOffer


class QdrantManager:
    def __init__(self, configuration):
        self.collection_name = configuration.qdrant_collection_name
        self.vector_size = configuration.qdrant_vector_size
        self.client = QdrantClient(
            host=configuration.qdrant_host,
            port=configuration.qdrant_port,
        )

    def __enter__(self):
        self.ensure_collection()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def close(self):
        if hasattr(self.client, "close"):
            self.client.close()

    def ensure_collection(self):
        if self.client.collection_exists(collection_name=self.collection_name):
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )

    def upsert_job(self, job: EmbeddedJobOffer):
        self.upsert_jobs([job])

    def upsert_jobs(self, jobs: list[EmbeddedJobOffer]):
        if not jobs:
            return

        points = [
            PointStruct(
                id=job.id,
                vector=job.vector,
                payload=job.to_payload(),
            )
            for job in jobs
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
