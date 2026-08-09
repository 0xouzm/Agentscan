"""Add and backfill the constant-time reputation aggregate state."""

import os
import sqlite3
from pathlib import Path

import structlog
from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger(__name__)


def _get_db_path() -> Path:
    db_url = os.getenv("DATABASE_URL", "sqlite:///./8004scan.db")
    if not db_url.startswith("sqlite:///"):
        raise ValueError("This migration only works with SQLite databases")

    db_path = db_url.replace("sqlite:///", "")
    if not db_path.startswith("/"):
        db_path = Path(__file__).parent.parent.parent / db_path
    return Path(db_path)


def _decimal_divisor_sql() -> str:
    cases = " ".join(
        f"WHEN {decimals} THEN {10 ** decimals}.0"
        for decimals in range(19)
    )
    return f"CASE value_decimals {cases} ELSE 1.0 END"


def migrate():
    """Add aggregate state and reconcile it with locally cached feedback."""
    db_path = _get_db_path()
    if not db_path.exists():
        logger.info("reputation_aggregate_migration_skipped", reason="db_not_exists")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(agents)")
        columns = {column[1] for column in cursor.fetchall()}
        if not columns:
            logger.info("reputation_aggregate_migration_skipped", reason="table_not_exists")
            return

        if "reputation_value_sum" not in columns:
            logger.info("reputation_aggregate_migration_starting")
            cursor.execute(
                "ALTER TABLE agents ADD COLUMN reputation_value_sum REAL"
            )

        cursor.execute(
            "SELECT 1 FROM agents WHERE reputation_value_sum IS NULL LIMIT 1"
        )
        if cursor.fetchone() is None:
            logger.info("reputation_aggregate_migration_already_done")
            return

        # Preserve non-feedback/external ratings, then replace on-chain aggregates
        # with exact values computed from the locally cached active feedback.
        cursor.execute("""
            UPDATE agents
            SET reputation_value_sum =
                COALESCE(reputation_score, 0.0) * COALESCE(reputation_count, 0)
            WHERE reputation_value_sum IS NULL
        """)
        cursor.execute("DROP TABLE IF EXISTS temp.reputation_aggregate_backfill")
        cursor.execute("""
            CREATE TEMP TABLE reputation_aggregate_backfill (
                agent_id TEXT PRIMARY KEY,
                value_sum REAL NOT NULL,
                feedback_count INTEGER NOT NULL
            )
        """)
        divisor = _decimal_divisor_sql()
        cursor.execute(f"""
            INSERT INTO reputation_aggregate_backfill (
                agent_id, value_sum, feedback_count
            )
            SELECT
                agent_id,
                SUM(CAST(value AS REAL) / ({divisor})),
                COUNT(*)
            FROM feedbacks
            WHERE is_revoked = 0
            GROUP BY agent_id
        """)
        cursor.execute("""
            UPDATE agents
            SET
                reputation_value_sum = (
                    SELECT value_sum
                    FROM reputation_aggregate_backfill
                    WHERE agent_id = agents.id
                ),
                reputation_count = (
                    SELECT feedback_count
                    FROM reputation_aggregate_backfill
                    WHERE agent_id = agents.id
                ),
                reputation_score = (
                    SELECT value_sum / feedback_count
                    FROM reputation_aggregate_backfill
                    WHERE agent_id = agents.id
                )
            WHERE id IN (SELECT agent_id FROM reputation_aggregate_backfill)
        """)
        cursor.execute("SELECT COUNT(*) FROM reputation_aggregate_backfill")
        backfilled_agents = cursor.fetchone()[0]
        cursor.execute("DROP TABLE reputation_aggregate_backfill")
        conn.commit()
        logger.info(
            "reputation_aggregate_migration_completed",
            backfilled_agents=backfilled_agents,
        )
    except Exception as error:
        conn.rollback()
        logger.error("reputation_aggregate_migration_failed", error=str(error))
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
