"""Alembic environment: SQLModel metadata + pipeline DB settings."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from pipeline.config import get_configuration
from pipeline.storage.models import (
    CanonicalJob,
    CanonicalJobSkill,
    RawJob,
    SearchKeywordRow,
    Skill,
)
from pipeline.storage.postgres import build_database_url
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Register models on metadata for autogenerate.
_ = (RawJob, CanonicalJob, SearchKeywordRow, Skill, CanonicalJobSkill)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_url() -> str:
    return build_database_url(get_configuration())


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
