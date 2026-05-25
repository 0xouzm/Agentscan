"""Migration: add x402 ecosystem history snapshots."""

import sqlite3

import structlog

from src.core.config import settings

logger = structlog.get_logger()


def migrate():
    """Create x402 history table if it does not already exist."""
    conn = sqlite3.connect(settings.database_url.replace("sqlite:///", ""))
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS x402_ecosystem_snapshots (
                id TEXT PRIMARY KEY,
                snapshot_time DATETIME NOT NULL,
                transactions_30d REAL,
                volume_30d REAL,
                buyers_30d REAL,
                sellers_30d REAL,
                total_resources INTEGER,
                sampled_resources INTEGER,
                priced_resources INTEGER,
                base_resources INTEGER,
                x402_capability_agents INTEGER,
                agentkit_capability_agents INTEGER,
                payable_capability_agents INTEGER,
                discovery_status TEXT,
                created_at DATETIME NOT NULL
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_x402_snapshots_time "
            "ON x402_ecosystem_snapshots(snapshot_time)"
        )
        conn.commit()
        logger.info("migration_add_x402_history_complete")
    except Exception as exc:
        logger.error("migration_add_x402_history_failed", error=str(exc))
        raise
    finally:
        conn.close()
