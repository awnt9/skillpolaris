"""Postgres access via SQLModel sessions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pipeline.schemas.extract import SearchKeyword, SearchKeywordUpsert
from pipeline.schemas.jobs import (
    CanonicalJobOffer,
    PendingCanonicalJob,
    PendingRawJob,
    RawJobRecord,
)
from pipeline.storage.models import CanonicalJob, RawJob, SearchKeywordRow
from sqlalchemy import func, or_, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, create_engine, select


def build_database_url(configuration) -> str:
    return (
        f"postgresql+psycopg2://{configuration.postgres_user}:"
        f"{configuration.postgres_password}@{configuration.db_host}:"
        f"{configuration.db_port}/{configuration.postgres_db}"
    )


class PostgresManager:
    def __init__(self, configuration):
        self.configuration = configuration
        self.engine = create_engine(build_database_url(configuration), pool_pre_ping=True)
        self.session = Session(self.engine)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.session.rollback()
        self.close()
        return False

    def close(self):
        self.session.close()
        self.engine.dispose()

    def count_raw_jobs_by_keyword(self, keywords: list[str]) -> dict[str, int]:
        if not keywords:
            return {}

        try:
            statement = (
                select(RawJob.keyword, func.count())
                .where(col(RawJob.keyword).in_(keywords))
                .group_by(RawJob.keyword)
            )
            rows = self.session.exec(statement).all()
            self.session.commit()
            return {keyword: count for keyword, count in rows if keyword is not None}
        except SQLAlchemyError as e:
            print(f" ERROR on PostgresManager: Could not count keywords. Cause: {e}")
            self.session.rollback()
            return {}

    def filter_new_job_ids(self, source_name: str, raw_ids: list[str]) -> list[str]:
        if not raw_ids:
            return []

        try:
            statement = select(RawJob.job_id).where(
                RawJob.source == source_name,
                col(RawJob.job_id).in_(raw_ids),
            )
            existing_ids = set(self.session.exec(statement).all())
            self.session.commit()
            return [job_id for job_id in raw_ids if job_id not in existing_ids]
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not filter IDs for {source_name}. "
                f"Cause: {e}"
            )
            self.session.rollback()
            return []

    def save_raw_job(self, raw_job: RawJobRecord) -> None:
        try:
            statement = (
                insert(RawJob)
                .values(
                    source=raw_job.source,
                    job_id=raw_job.external_id,
                    extractor_kind=raw_job.extractor_kind,
                    keyword=raw_job.keyword,
                    title_raw=raw_job.title_raw,
                    description_raw=raw_job.description_raw,
                    url=raw_job.url,
                    company_raw=raw_job.company_raw,
                    location_raw=raw_job.location_raw,
                    posted_at_raw=raw_job.posted_at_raw,
                    raw_payload=raw_job.raw_payload,
                    filter_status="pending",
                )
                .on_conflict_do_nothing(index_elements=["source", "job_id"])
            )
            self.session.execute(statement)
            self.session.commit()
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not save raw job on "
                f"{raw_job.source}. Cause: {e}"
            )
            self.session.rollback()

    def upsert_search_keywords(self, keywords: list[SearchKeywordUpsert]) -> int:
        if not keywords:
            return 0

        try:
            affected = 0
            for item in keywords:
                statement = insert(SearchKeywordRow).values(
                    keyword=item.keyword,
                    dimension=item.dimension,
                    source_scope=item.source_scope or "",
                    priority=item.priority,
                    origin=item.origin,
                    active=item.active,
                )
                statement = statement.on_conflict_do_update(
                    index_elements=["keyword", "dimension", "source_scope"],
                    set_={
                        "priority": statement.excluded.priority,
                        "origin": statement.excluded.origin,
                        "active": statement.excluded.active,
                    },
                )
                result = self.session.execute(statement)
                affected += result.rowcount or 0
            self.session.commit()
            return affected
        except SQLAlchemyError as e:
            print(f" ERROR on PostgresManager: Could not upsert keywords. Cause: {e}")
            self.session.rollback()
            return 0

    def refresh_keyword_raw_jobs_counts(self) -> None:
        try:
            self.session.execute(
                text(
                    """
                    UPDATE search_keywords sk
                    SET raw_jobs_count = COALESCE(counts.cnt, 0)
                    FROM (
                        SELECT keyword, COUNT(*) AS cnt
                        FROM raw_jobs
                        WHERE keyword IS NOT NULL
                        GROUP BY keyword
                    ) counts
                    WHERE sk.keyword = counts.keyword
                    """
                )
            )
            self.session.commit()
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not refresh keyword counts. "
                f"Cause: {e}"
            )
            self.session.rollback()

    def get_keywords_for_extract(
        self,
        *,
        source_name: str,
        limit: int,
        cooldown_hours: int = 0,
    ) -> list[SearchKeyword]:
        try:
            statement = select(SearchKeywordRow).where(
                SearchKeywordRow.active.is_(True),
                or_(
                    SearchKeywordRow.source_scope.is_(None),
                    SearchKeywordRow.source_scope == "",
                    SearchKeywordRow.source_scope == source_name,
                ),
            )
            if cooldown_hours > 0:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)
                statement = statement.where(
                    or_(
                        SearchKeywordRow.last_searched_at.is_(None),
                        SearchKeywordRow.last_searched_at < cutoff,
                    )
                )
            statement = (
                statement.order_by(
                    col(SearchKeywordRow.priority).desc(),
                    col(SearchKeywordRow.raw_jobs_count).asc(),
                    col(SearchKeywordRow.last_searched_at).asc().nulls_first(),
                    col(SearchKeywordRow.id).asc(),
                ).limit(limit)
            )
            rows = self.session.exec(statement).all()
            self.session.commit()
            return [
                SearchKeyword(
                    id=row.id,
                    keyword=row.keyword,
                    dimension=row.dimension,  # type: ignore[arg-type]
                    source_scope=row.source_scope or None,
                    priority=row.priority,
                    origin=row.origin,  # type: ignore[arg-type]
                    active=row.active,
                    last_searched_at=(
                        row.last_searched_at.isoformat() if row.last_searched_at else None
                    ),
                    raw_jobs_count=row.raw_jobs_count,
                )
                for row in rows
                if row.id is not None
            ]
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not get keywords for extract. "
                f"Cause: {e}"
            )
            self.session.rollback()
            return []

    def mark_keyword_searched(self, keyword_id: int) -> None:
        try:
            row = self.session.get(SearchKeywordRow, keyword_id)
            if row is None:
                return
            row.last_searched_at = datetime.now(timezone.utc)
            self.session.add(row)
            self.session.commit()
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not mark keyword searched. "
                f"Cause: {e}"
            )
            self.session.rollback()

    def get_pending_filter_jobs(self, limit: int | None = None) -> list[PendingRawJob]:
        try:
            statement = (
                select(RawJob)
                .where(RawJob.filter_status == "pending")
                .order_by(col(RawJob.extracted_at).asc(), col(RawJob.id).asc())
            )
            if limit is not None:
                statement = statement.limit(limit)

            rows = self.session.exec(statement).all()
            self.session.commit()
            return [
                PendingRawJob(
                    id=row.id,
                    source=row.source,
                    job_id=row.job_id,
                    keyword=row.keyword,
                    title_raw=row.title_raw or "",
                    description_raw=row.description_raw or "",
                    url=row.url,
                    company_raw=row.company_raw,
                    location_raw=row.location_raw,
                    posted_at_raw=row.posted_at_raw,
                )
                for row in rows
                if row.id is not None
            ]
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not get pending filter jobs. "
                f"Cause: {e}"
            )
            self.session.rollback()
            return []

    def save_canonical_job(self, job: CanonicalJobOffer) -> None:
        try:
            statement = (
                insert(CanonicalJob)
                .values(
                    raw_job_id=job.raw_job_id,
                    source=job.source,
                    job_id=job.job_id,
                    title=job.title,
                    description=job.description,
                    url=job.url,
                    company=job.company,
                    location=job.location,
                    posted_at=job.posted_at,
                    keyword=job.keyword,
                    transform_status="pending",
                )
                .on_conflict_do_nothing(index_elements=["source", "job_id"])
            )
            self.session.execute(statement)
            self.session.commit()
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not save canonical job "
                f"{job.source}/{job.job_id}. Cause: {e}"
            )
            self.session.rollback()

    def update_raw_filter_status(
        self,
        raw_job_id: int,
        status: str,
        method: str | None = None,
    ) -> None:
        try:
            row = self.session.get(RawJob, raw_job_id)
            if row is None:
                return
            row.filter_status = status
            row.filter_method = method
            row.filtered_at = datetime.now(timezone.utc)
            self.session.add(row)
            self.session.commit()
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not update filter status for "
                f"{raw_job_id}. Cause: {e}"
            )
            self.session.rollback()

    def get_pending_canonical_jobs(
        self, limit: int | None = None
    ) -> list[PendingCanonicalJob]:
        try:
            statement = (
                select(CanonicalJob)
                .where(CanonicalJob.transform_status == "pending")
                .order_by(col(CanonicalJob.created_at).asc(), col(CanonicalJob.id).asc())
            )
            if limit is not None:
                statement = statement.limit(limit)

            rows = self.session.exec(statement).all()
            self.session.commit()
            return [
                PendingCanonicalJob(
                    id=row.id,
                    raw_job_id=row.raw_job_id or 0,
                    source=row.source,
                    job_id=row.job_id,
                    title=row.title,
                    description=row.description,
                    keyword=row.keyword,
                )
                for row in rows
                if row.id is not None
            ]
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not get pending canonical jobs. "
                f"Cause: {e}"
            )
            self.session.rollback()
            return []

    def mark_canonical_processed(self, canonical_id: int) -> None:
        self._update_canonical_transform_status(canonical_id, "processed")

    def mark_canonical_failed(self, canonical_id: int) -> None:
        self._update_canonical_transform_status(canonical_id, "failed")

    def _update_canonical_transform_status(self, canonical_id: int, status: str) -> None:
        try:
            row = self.session.get(CanonicalJob, canonical_id)
            if row is None:
                return
            row.transform_status = status
            row.transformed_at = datetime.now(timezone.utc)
            self.session.add(row)
            self.session.commit()
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not mark canonical {canonical_id} "
                f"as {status}. Cause: {e}"
            )
            self.session.rollback()
