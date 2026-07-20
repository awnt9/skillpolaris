import psycopg2
from psycopg2.extras import Json, RealDictCursor


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

    def count_jobs_by_keyword(self, keywords: list[str]) -> dict[str, int]:
        """
        Counts already staged jobs for each keyword.
        """
        if not keywords:
            return {}

        cursor = None
        try:
            cursor = self.connection.cursor()
            query = """
                SELECT keyword, COUNT(*)
                FROM staging_jobs
                WHERE keyword = ANY(%s)
                GROUP BY keyword
            """
            cursor.execute(query, (keywords,))
            results = dict(cursor.fetchall())
            self.connection.commit()
            return results

        except psycopg2.Error as e:
            print(f" ERROR on StagingManager: Could not count keywords. Cause: {e}")
            if self.connection:
                self.connection.rollback()
            return {}

        finally:
            if cursor:
                cursor.close()

    def filter_new_job_ids(self, source_name: str, raw_ids: list[str]) -> list[str]:
        """
        Filters out IDs already present in staging for a source.
        """
        if not raw_ids:
            return []

        cursor = None
        try:
            cursor = self.connection.cursor()
            query = """
                SELECT job_id
                FROM staging_jobs
                WHERE source = %s AND job_id = ANY(%s)
            """
            cursor.execute(query, (source_name, raw_ids))
            existing_ids = {row[0] for row in cursor.fetchall()}
            self.connection.commit()
            return [job_id for job_id in raw_ids if job_id not in existing_ids]

        except psycopg2.Error as e:
            print(f" ERROR on StagingManager: Could not filter IDs for {source_name}. Cause: {e}")
            if self.connection:
                self.connection.rollback()
            return []

        finally:
            if cursor:
                cursor.close()

    def save_to_staging(self, source: str, job_id: str, raw_content: object, keyword: str = None):
        """
        Saves raw content from an offer into the table staging.
        """
        cursor = None
        try:
            cursor = self.connection.cursor()

            query = """
                INSERT INTO staging_jobs (source, job_id, raw_content, keyword)
                VALUES (%s, %s, %s, %s)
            """

            cursor.execute(query, (source, job_id, Json(raw_content), keyword))
            self.connection.commit()

        except psycopg2.Error as e:
            print(f" ERROR on StagingManager: Could not save on {source}. Cause: {e}")
            if self.connection:
                self.connection.rollback()

        finally:
            if cursor:
                cursor.close()

    def get_from_staging(self):
        cursor = None
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)

            query = """SELECT id,source,job_id,raw_content,keyword
                       FROM staging_jobs
                       WHERE status = 'pending'"""

            cursor.execute(query)
            results = cursor.fetchall()
            self.connection.commit()

            return results

        except psycopg2.Error as e:
            print(f" ERROR on StagingManager. Cause: {e}")
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
            params = ()

            if limit is not None:
                query += " LIMIT %s"
                params = (limit,)

            cursor.execute(query, params)
            results = cursor.fetchall()
            self.connection.commit()
            return results

        except psycopg2.Error as e:
            print(f" ERROR on StagingManager: Could not get pending jobs. Cause: {e}")
            if self.connection:
                self.connection.rollback()
            return []

        finally:
            if cursor:
                cursor.close()

    def mark_as_processed(self, staging_id: int):
        self._update_status(staging_id=staging_id, status="processed")

    def mark_as_failed(self, staging_id: int):
        self._update_status(staging_id=staging_id, status="failed")

    def _update_status(self, staging_id: int, status: str):
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
            print(f" ERROR on StagingManager: Could not mark {staging_id} as {status}. Cause: {e}")
            if self.connection:
                self.connection.rollback()

        finally:
            if cursor:
                cursor.close()
