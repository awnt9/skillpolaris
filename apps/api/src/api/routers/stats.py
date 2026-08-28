from fastapi import APIRouter
from sqlalchemy import text

from api.db import get_engine

router = APIRouter()


@router.get("/stats")
def get_stats() -> dict[str, int]:
    with get_engine().connect() as conn:
        sources = conn.execute(text("SELECT COUNT(DISTINCT source) FROM raw_jobs")).scalar_one()
        records = conn.execute(text("SELECT COUNT(*) FROM canonical_jobs")).scalar_one()
        positions = conn.execute(
            text(
                "SELECT COUNT(DISTINCT standard_role) FROM canonical_jobs "
                "WHERE standard_role IS NOT NULL"
            )
        ).scalar_one()

    return {"sources": sources, "records": records, "positions": positions}
