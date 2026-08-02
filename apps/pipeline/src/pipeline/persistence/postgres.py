import psycopg2
from psycopg2.extras import Json, RealDictCursor

from pipeline.domain.models import CanonicalJobOffer, RawJobRecord


class PostgresManager:
    def __init__(self, configuration):
        self.configuration = configuration
        self.connection = psycopg2.connect(
            host=configuration.db_host,
            database=configuration.postgres_db,
            user=configuration.postgres_user,
            password=configuration.postgres_password,
            port=configuration.db_port,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type and self.connection:
            self.connection.rollback()
        self.close()
        return False

    def close(self):
        if self.connection and not self.connection.closed:
            self.connection.close()

    def count_raw_jobs_by_keyword(self, keywords: list[str]) -> dict[str, int]:
        if not keywords:
            return {}

        cursor = None
        try:
            cursor = self.connection.cursor()
            query = """
                SELECT keyword, COUNT(*)
                FROM raw_jobs
                WHERE keyword = ANY(%s)
                GROUP BY keyword
            """
            cursor.execute(query, (keywords,))
            results = dict(cursor.fetchall())
            self.connection.commit()
            return results

        except psycopg2.Error as e:
            print(f" ERROR on PostgresManager: Could not count keywords. Cause: {e}")
            if self.connection:
                self.connection.rollback()
            return {}

        finally:
            if cursor:
                cursor.close()

    def filter_new_job_ids(self, source_name: str, raw_ids: list[str]) -> list[str]:
        if not raw_ids:
            return []

        cursor = None
        try:
            cursor = self.connection.cursor()
            query = """
                SELECT job_id
                FROM raw_jobs
                WHERE source = %s AND job_id = ANY(%s)
            """
            cursor.execute(query, (source_name, raw_ids))
            existing_ids = {row[0] for row in cursor.fetchall()}
            self.connection.commit()
            return [job_id for job_id in raw_ids if job_id not in existing_ids]

        except psycopg2.Error as e:
            print(
                f" ERROR on PostgresManager: Could not filter IDs for {source_name}. "
                f"Cause: {e}"
            )
            if self.connection:
                self.connection.rollback()
            return []

        finally:
            if cursor:
                cursor.close()

    def save_raw_job(self, raw_job: RawJobRecord) -> None:
        cursor = None
        try:
            cursor = self.connection.cursor()
            query = """
                INSERT INTO raw_jobs (
                    source,
                    job_id,
                    extractor_kind,
                    keyword,
                    title_raw,
                    description_raw,
                    url,
                    company_raw,
                    location_raw,
                    posted_at_raw,
                    raw_payload,
                    filter_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                ON CONFLICT (source, job_id) DO NOTHING
            """
            cursor.execute(
                query,
                (
                    raw_job.source,
                    raw_job.external_id,
                    raw_job.extractor_kind,
                    raw_job.keyword,
                    raw_job.title_raw,
                    raw_job.description_raw,
                    raw_job.url,
                    raw_job.company_raw,
                    raw_job.location_raw,
                    raw_job.posted_at_raw,
                    Json(raw_job.raw_payload),
                ),
            )
            self.connection.commit()

        except psycopg2.Error as e:
            print(
                f" ERROR on PostgresManager: Could not save raw job on "
                f"{raw_job.source}. Cause: {e}"
            )
            if self.connection:
                self.connection.rollback()

        finally:
            if cursor:
                cursor.close()

    def get_pending_filter_jobs(self, limit: int | None = None):
        cursor = None
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            query = """
                SELECT
                    id, source, job_id, extractor_kind, keyword,
                    title_raw, description_raw, url, company_raw,
                    location_raw, posted_at_raw, raw_payload, filter_status
                FROM raw_jobs
                WHERE filter_status = 'pending'
                ORDER BY extracted_at ASC, id ASC
            """
            params: tuple = ()
            if limit is not None:
                query += " LIMIT %s"
                params = (limit,)

            cursor.execute(query, params)
            results = cursor.fetchall()
            self.connection.commit()
            return results

        except psycopg2.Error as e:
            print(
                f" ERROR on PostgresManager: Could not get pending filter jobs. "
                f"Cause: {e}"
            )
            if self.connection:
                self.connection.rollback()
            return []

        finally:
            if cursor:
                cursor.close()

    def save_canonical_job(self, job: CanonicalJobOffer) -> None:
        cursor = None
        try:
            cursor = self.connection.cursor()
            query = """
                INSERT INTO canonical_jobs (
                    raw_job_id, source, job_id, title, description,
                    url, company, location, posted_at, keyword
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, job_id) DO NOTHING
            """
            cursor.execute(
                query,
                (
                    job.raw_job_id,
                    job.source,
                    job.job_id,
                    job.title,
                    job.description,
                    job.url,
                    job.company,
                    job.location,
                    job.posted_at,
                    job.keyword,
                ),
            )
            self.connection.commit()

        except psycopg2.Error as e:
            print(
                f" ERROR on PostgresManager: Could not save canonical job "
                f"{job.source}/{job.job_id}. Cause: {e}"
            )
            if self.connection:
                self.connection.rollback()

        finally:
            if cursor:
                cursor.close()

    def update_raw_filter_status(
        self,
        raw_job_id: int,
        status: str,
        method: str | None = None,
    ) -> None:
        cursor = None
        try:
            cursor = self.connection.cursor()
            query = """
                UPDATE raw_jobs
                SET filter_status = %s,
                    filter_method = %s,
                    filtered_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            cursor.execute(query, (status, method, raw_job_id))
            self.connection.commit()

        except psycopg2.Error as e:
            print(
                f" ERROR on PostgresManager: Could not update filter status for "
                f"{raw_job_id}. Cause: {e}"
            )
            if self.connection:
                self.connection.rollback()

        finally:
            if cursor:
                cursor.close()

    # --- Legacy staging_* API (transform still uses staging_jobs) ---

    def count_jobs_by_keyword(self, keywords: list[str]) -> dict[str, int]:
        return self.count_raw_jobs_by_keyword(keywords)

    def save_to_staging(self, staged_job: RawJobRecord):
        """Backward-compatible alias; prefer save_raw_job."""
        self.save_raw_job(staged_job)

    def get_from_staging(self):
        cursor = None
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            query = """
                SELECT id, source, job_id, raw_content, keyword
                FROM staging_jobs
                WHERE status = 'pending'
            """
            cursor.execute(query)
            results = cursor.fetchall()
            self.connection.commit()
            return results

        except psycopg2.Error as e:
            print(f" ERROR on PostgresManager. Cause: {e}")
            if self.connection:
                self.connection.rollback()
            return []

        finally:
            if cursor:
                cursor.close()

    def get_pending_staging_jobs(self, limit: int | None = None):
        cursor = None
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            query = """
                SELECT id, source, job_id, raw_content, keyword
                FROM staging_jobs
                WHERE status = 'pending'
                ORDER BY extracted_at ASC, id ASC
            """
            params: tuple = ()
            if limit is not None:
                query += " LIMIT %s"
                params = (limit,)

            cursor.execute(query, params)
            results = cursor.fetchall()
            self.connection.commit()
            return results

        except psycopg2.Error as e:
            print(
                f" ERROR on PostgresManager: Could not get pending jobs. Cause: {e}"
            )
            if self.connection:
                self.connection.rollback()
            return []

        finally:
            if cursor:
                cursor.close()

    def mark_as_processed(self, staging_id: int):
        self._update_staging_status(staging_id=staging_id, status="processed")

    def mark_as_failed(self, staging_id: int):
        self._update_staging_status(staging_id=staging_id, status="failed")

    def _update_staging_status(self, staging_id: int, status: str):
        cursor = None
        try:
            cursor = self.connection.cursor()
            query = """
                UPDATE staging_jobs
                SET status = %s,
                    processed_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            cursor.execute(query, (status, staging_id))
            self.connection.commit()

        except psycopg2.Error as e:
            print(
                f" ERROR on PostgresManager: Could not mark {staging_id} as "
                f"{status}. Cause: {e}"
            )
            if self.connection:
                self.connection.rollback()

        finally:
            if cursor:
                cursor.close()
