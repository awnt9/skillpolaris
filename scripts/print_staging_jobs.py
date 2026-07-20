import argparse
from pathlib import Path

import psycopg2
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIMIT = 50


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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Print staging_jobs records without the raw_content column."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum number of rows to print. Defaults to {DEFAULT_LIMIT}.",
    )
    return parser.parse_args()


def get_staging_jobs(connection, limit: int):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                id,
                source,
                job_id,
                keyword,
                status,
                extracted_at,
                processed_at
            FROM staging_jobs
            ORDER BY extracted_at DESC, id DESC
            LIMIT %s
            """,
            (limit,),
        )
        return cursor.fetchall()


def print_jobs(rows):
    console = Console()

    if not rows:
        console.print("[yellow]No records found in staging_jobs.[/]")
        return

    table = Table(title="staging_jobs")
    table.add_column("id", justify="right")
    table.add_column("source")
    table.add_column("job_id")
    table.add_column("keyword")
    table.add_column("status")
    table.add_column("extracted_at")
    table.add_column("processed_at")

    for row in rows:
        table.add_row(*(str(value) if value is not None else "" for value in row))

    console.print(table)


def main() -> int:
    args = parse_args()
    settings = DatabaseSettings()

    try:
        with psycopg2.connect(
            host=settings.db_host,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            port=settings.db_port,
        ) as connection:
            rows = get_staging_jobs(connection, args.limit)
            print_jobs(rows)
            return 0

    except psycopg2.Error as e:
        Console().print("[red]Could not read staging_jobs[/]")
        Console().print(e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
