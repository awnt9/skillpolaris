"""Postgres access via SQLModel sessions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pipeline.schemas.enrich import (
    JobOfferMetadata,
    StandardRoleOption,
    merge_synonyms,
    normalize_role_name,
    normalized_skills,
)
from pipeline.schemas.extract import SearchKeyword, SearchKeywordUpsert
from pipeline.schemas.jobs import (
    CanonicalJobOffer,
    PendingCanonicalJob,
    PendingRawJob,
    RawJobRecord,
)
from pipeline.storage.models import (
    CanonicalJob,
    CanonicalJobSkill,
    FeedCursor,
    RawJob,
    SearchKeywordRow,
    Skill,
    StandardRole,
)
from sqlalchemy import delete, func, or_, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, create_engine, select


def build_database_url(configuration) -> str:
    # Always 5432: this is the container-to-container Postgres port on the
    # Docker network, not the host-published port (DB_PORT), which only
    # matters for connecting from outside Docker (e.g. pgweb, host tools).
    return (
        f"postgresql+psycopg2://{configuration.postgres_user}:"
        f"{configuration.postgres_password}@{configuration.db_host}:"
        f"5432/{configuration.postgres_db}"
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
            print(f" ERROR on PostgresManager: Could not filter IDs for {source_name}. Cause: {e}")
            self.session.rollback()
            return []

    def save_raw_job(self, raw_job: RawJobRecord) -> bool:
        """Insert a raw job. Returns True if a new row was written."""
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
                    posted_at_raw=raw_job.posted_at_raw,
                    raw_payload=raw_job.raw_payload,
                    filter_status="pending",
                )
                .on_conflict_do_nothing(index_elements=["source", "job_id"])
            )
            result = self.session.execute(statement)
            self.session.commit()
            return (result.rowcount or 0) > 0
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not save raw job on {raw_job.source}. Cause: {e}"
            )
            self.session.rollback()
            return False

    def upsert_search_keywords(self, keywords: list[SearchKeywordUpsert]) -> int:
        if not keywords:
            return 0

        try:
            affected = 0
            for item in keywords:
                statement = insert(SearchKeywordRow).values(
                    keyword=item.keyword,
                    source_scope=item.source_scope or "",
                    origin=item.origin,
                    active=item.active,
                )
                statement = statement.on_conflict_do_update(
                    index_elements=["keyword", "source_scope"],
                    set_={
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
            print(f" ERROR on PostgresManager: Could not refresh keyword counts. Cause: {e}")
            self.session.rollback()

    def get_feed_cursor(self, source_name: str) -> str | None:
        """Resume point for an unscoped feed sweep, or None to start over."""
        try:
            row = self.session.get(FeedCursor, source_name)
            return row.cursor if row else None
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not read feed cursor for {source_name}. "
                f"Cause: {e}"
            )
            self.session.rollback()
            return None

    def save_feed_cursor(self, source_name: str, cursor: str | None) -> None:
        try:
            statement = (
                insert(FeedCursor)
                .values(source_name=source_name, cursor=cursor)
                .on_conflict_do_update(
                    index_elements=["source_name"],
                    set_={"cursor": cursor, "updated_at": func.now()},
                )
            )
            self.session.execute(statement)
            self.session.commit()
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not save feed cursor for {source_name}. "
                f"Cause: {e}"
            )
            self.session.rollback()

    def get_keywords_for_extract(
        self,
        *,
        source_name: str,
        limit: int,
        cooldown_hours: int = 0,
        scoped_only: bool = False,
    ) -> list[SearchKeyword]:
        try:
            statement = select(SearchKeywordRow).where(
                SearchKeywordRow.active.is_(True),
            )
            if scoped_only:
                statement = statement.where(
                    SearchKeywordRow.source_scope == source_name,
                )
            else:
                statement = statement.where(
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
            statement = statement.order_by(
                col(SearchKeywordRow.raw_jobs_count).asc(),
                col(SearchKeywordRow.last_searched_at).asc().nulls_first(),
                col(SearchKeywordRow.id).asc(),
            ).limit(limit)
            rows = self.session.exec(statement).all()
            self.session.commit()
            return [
                SearchKeyword(
                    id=row.id,
                    keyword=row.keyword,
                    source_scope=row.source_scope or None,
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
            print(f" ERROR on PostgresManager: Could not get keywords for extract. Cause: {e}")
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
            print(f" ERROR on PostgresManager: Could not mark keyword searched. Cause: {e}")
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
                    posted_at_raw=row.posted_at_raw,
                )
                for row in rows
                if row.id is not None
            ]
        except SQLAlchemyError as e:
            print(f" ERROR on PostgresManager: Could not get pending filter jobs. Cause: {e}")
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
                    posted_at=job.posted_at,
                    keyword=job.keyword,
                    enrich_status="pending",
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

    def get_pending_canonical_jobs(self, limit: int | None = None) -> list[PendingCanonicalJob]:
        try:
            statement = (
                select(CanonicalJob)
                .where(CanonicalJob.enrich_status == "pending")
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
            print(f" ERROR on PostgresManager: Could not get pending canonical jobs. Cause: {e}")
            self.session.rollback()
            return []

    def get_active_standard_roles(self) -> list[StandardRoleOption]:
        statement = (
            select(StandardRole)
            .where(col(StandardRole.merged_into_id).is_(None))
            .order_by(col(StandardRole.name).asc())
        )
        return [
            StandardRoleOption(
                name=role.name,
                description=role.description,
                synonyms=list(role.synonyms or []),
            )
            for role in self.session.exec(statement).all()
        ]

    def save_job_enrichment(self, canonical_id: int, metadata: JobOfferMetadata) -> None:
        try:
            row = self.session.get(CanonicalJob, canonical_id)
            if row is None:
                raise RuntimeError(f"canonical_job {canonical_id} not found")
            role_name = normalize_role_name(metadata.standard_role)
            role_id = self._upsert_standard_role(
                role_name,
                description=metadata.standard_role_description,
                new_synonyms=metadata.standard_role_synonyms,
            )
            role = self.session.get(StandardRole, role_id)
            row.standard_role_id = role_id
            row.standard_role = role.name if role is not None else role_name
            row.is_remote = metadata.is_remote
            row.language_required = metadata.language_required
            row.enrich_status = "processed"
            row.enriched_at = datetime.now(timezone.utc)
            self.session.add(row)

            self.session.execute(
                delete(CanonicalJobSkill).where(
                    CanonicalJobSkill.canonical_job_id == canonical_id,
                )
            )
            for skill_name in normalized_skills(metadata.hard_skills):
                skill_id = self._upsert_skill(skill_name)
                self.session.add(
                    CanonicalJobSkill(
                        canonical_job_id=canonical_id,
                        skill_id=skill_id,
                    )
                )
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            if isinstance(e, SQLAlchemyError):
                print(
                    f" ERROR on PostgresManager: Could not save enrichment for "
                    f"{canonical_id}. Cause: {e}"
                )
            raise

    def _upsert_standard_role(
        self,
        name: str,
        *,
        description: str | None,
        new_synonyms: list[str],
    ) -> int:
        clean_synonyms = merge_synonyms([], new_synonyms, name)
        statement = (
            insert(StandardRole)
            .values(name=name, description=description, synonyms=clean_synonyms)
            .on_conflict_do_nothing()
        )
        self.session.execute(statement)
        role = self.session.exec(
            select(StandardRole).where(func.lower(StandardRole.name) == name.lower())
        ).one()
        if role.id is None:
            raise RuntimeError(f"Standard role {name!r} has no id after upsert")

        # Role already existed: never clobber a curated description; only merge in
        # any new synonym the agent attached to this reuse decision.
        dirty = False
        if role.description is None and description:
            role.description = description
            dirty = True
        merged = merge_synonyms(list(role.synonyms or []), new_synonyms, role.name)
        if merged != (role.synonyms or []):
            role.synonyms = merged
            dirty = True
        if dirty:
            self.session.add(role)

        return role.id

    def _upsert_skill(self, name: str) -> int:
        statement = (
            insert(Skill)
            .values(name=name)
            .on_conflict_do_nothing(
                constraint="uq_skills_name",
            )
        )
        self.session.execute(statement)
        skill = self.session.exec(select(Skill).where(Skill.name == name)).one()
        if skill.id is None:
            raise RuntimeError(f"Skill {name!r} has no id after upsert")
        return skill.id

    def mark_canonical_processed(self, canonical_id: int) -> None:
        self._update_canonical_enrich_status(canonical_id, "processed")

    def mark_canonical_failed(self, canonical_id: int) -> None:
        self._update_canonical_enrich_status(canonical_id, "failed")

    def _update_canonical_enrich_status(self, canonical_id: int, status: str) -> None:
        try:
            row = self.session.get(CanonicalJob, canonical_id)
            if row is None:
                return
            row.enrich_status = status
            row.enriched_at = datetime.now(timezone.utc)
            self.session.add(row)
            self.session.commit()
        except SQLAlchemyError as e:
            print(
                f" ERROR on PostgresManager: Could not mark canonical {canonical_id} "
                f"as {status}. Cause: {e}"
            )
            self.session.rollback()
