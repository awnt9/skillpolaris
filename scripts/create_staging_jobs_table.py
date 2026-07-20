from pathlib import Path

import psycopg2
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DatabaseSettings(BaseSettings):
    """
    Minimal database settings needed by this script.
    """

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


def create_staging_table():
    query = """
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
    settings = DatabaseSettings()
    with psycopg2.connect(
        host=settings.db_host,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        port=settings.db_port,
    ) as connection:
        with connection.cursor() as cur:
            cur.execute(query)
            connection.commit()


if __name__ == "__main__":
    create_staging_table()
