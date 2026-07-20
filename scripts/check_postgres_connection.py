from pathlib import Path

import psycopg2
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich import print

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_NAME = "staging_jobs"


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


def table_exists(connection, table_name: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                AND table_name = %s
            )
            """,
            (table_name,),
        )
        return cursor.fetchone()[0]


def print_connection_info(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                current_database(),
                current_user,
                current_schema(),
                version()
            """
        )
        database, user, schema, version = cursor.fetchone()

    print("[green]Connection OK[/]")
    print(f"Database: {database}")
    print(f"User: {user}")
    print(f"Schema: {schema}")
    print(f"Version: {version}")


def main() -> int:
    settings = DatabaseSettings()

    try:
        with psycopg2.connect(
            host=settings.db_host,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            port=settings.db_port,
        ) as connection:
            print_connection_info(connection)

            if table_exists(connection, TABLE_NAME):
                print(f"[green]Table exists:[/] {TABLE_NAME}")
                return 0

            print(f"[red]Table does not exist:[/] {TABLE_NAME}")
            return 1

    except psycopg2.Error as e:
        print("[red]Connection failed[/]")
        print(e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
