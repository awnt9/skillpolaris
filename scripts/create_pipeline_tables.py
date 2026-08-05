from pathlib import Path

from pipeline.storage.models import CanonicalJob, RawJob, SearchKeywordRow, StagingJob
from pipeline.storage.postgres import build_database_url
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text
from sqlmodel import SQLModel, create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DatabaseSettings(BaseSettings):
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Ensure models are registered on SQLModel.metadata.
_ = (RawJob, CanonicalJob, SearchKeywordRow, StagingJob)

SEARCH_KEYWORDS_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_search_keywords_active
    ON search_keywords (
        active,
        priority DESC,
        raw_jobs_count ASC,
        last_searched_at ASC NULLS FIRST
    )
    WHERE active = TRUE
"""


def create_pipeline_tables():
    settings = DatabaseSettings()
    engine = create_engine(build_database_url(settings), pool_pre_ping=True)
    SQLModel.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text(SEARCH_KEYWORDS_INDEX_DDL))
    engine.dispose()
    print(
        "Created/verified tables: raw_jobs, canonical_jobs, "
        "search_keywords, staging_jobs"
    )


if __name__ == "__main__":
    create_pipeline_tables()
