from pathlib import Path

import psycopg2
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

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


RAW_JOBS_DDL = """
CREATE TABLE IF NOT EXISTS raw_jobs (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    job_id TEXT NOT NULL,
    extractor_kind TEXT NOT NULL,
    keyword TEXT,
    title_raw TEXT,
    description_raw TEXT,
    url TEXT,
    company_raw TEXT,
    location_raw TEXT,
    posted_at_raw TEXT,
    raw_payload JSONB NOT NULL,
    filter_status TEXT NOT NULL DEFAULT 'pending',
    filter_method TEXT,
    filtered_at TIMESTAMP,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source, job_id)
);
"""

CANONICAL_JOBS_DDL = """
CREATE TABLE IF NOT EXISTS canonical_jobs (
    id SERIAL PRIMARY KEY,
    raw_job_id INT REFERENCES raw_jobs(id),
    source TEXT NOT NULL,
    job_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    url TEXT,
    company TEXT,
    location TEXT,
    posted_at TEXT,
    keyword TEXT,
    transform_status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transformed_at TIMESTAMP,
    UNIQUE (source, job_id)
);
"""

# Legacy table kept for older datasets; new pipeline uses raw_jobs + canonical_jobs.
STAGING_JOBS_DDL = """
CREATE TABLE IF NOT EXISTS staging_jobs (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    job_id TEXT NOT NULL,
    raw_content JSONB NOT NULL,
    keyword TEXT,
    status TEXT DEFAULT 'pending',
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    UNIQUE (source, job_id)
);
"""


def create_pipeline_tables():
    settings = DatabaseSettings()
    migrations = [
        "ALTER TABLE canonical_jobs ADD COLUMN IF NOT EXISTS transform_status TEXT NOT NULL DEFAULT 'pending'",
        "ALTER TABLE canonical_jobs ADD COLUMN IF NOT EXISTS transformed_at TIMESTAMP",
    ]
    with psycopg2.connect(
        host=settings.db_host,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        port=settings.db_port,
    ) as connection:
        with connection.cursor() as cur:
            cur.execute(RAW_JOBS_DDL)
            cur.execute(CANONICAL_JOBS_DDL)
            cur.execute(STAGING_JOBS_DDL)
            for migration in migrations:
                cur.execute(migration)
            connection.commit()
    print("Created/verified tables: raw_jobs, canonical_jobs, staging_jobs")


if __name__ == "__main__":
    create_pipeline_tables()
