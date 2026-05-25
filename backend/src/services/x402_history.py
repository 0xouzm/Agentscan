"""Persist and read x402 ecosystem trend snapshots."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.models import X402EcosystemSnapshot

logger = structlog.get_logger()

SNAPSHOT_MIN_INTERVAL_SECONDS = 30 * 60
HISTORY_LIMIT = 12


def record_x402_snapshot(db: Session, overview: dict[str, Any]) -> None:
    """Persist a new snapshot when enough time has passed since the last one."""
    fetched_at = datetime.utcfromtimestamp(float(overview.get("fetched_at") or time.time()))
    try:
        latest = (
            db.query(X402EcosystemSnapshot)
            .order_by(X402EcosystemSnapshot.snapshot_time.desc())
            .first()
        )
        if latest and (fetched_at - latest.snapshot_time).total_seconds() < SNAPSHOT_MIN_INTERVAL_SECONDS:
            return

        official = overview.get("official_stats") or {}
        discovery = overview.get("discovery") or {}
        agentscan = overview.get("agentscan") or {}
        snapshot = X402EcosystemSnapshot(
            snapshot_time=fetched_at,
            transactions_30d=_stat_value(official, "transactions"),
            volume_30d=_stat_value(official, "volume"),
            buyers_30d=_stat_value(official, "buyers"),
            sellers_30d=_stat_value(official, "sellers"),
            total_resources=discovery.get("total_resources"),
            sampled_resources=discovery.get("sampled_resources"),
            priced_resources=discovery.get("priced_resources"),
            base_resources=_count_named(discovery.get("networks") or [], "eip155:8453"),
            x402_capability_agents=agentscan.get("x402_capability_agents"),
            agentkit_capability_agents=agentscan.get("agentkit_capability_agents"),
            payable_capability_agents=agentscan.get("payable_capability_agents"),
            discovery_status=discovery.get("status"),
        )
        db.add(snapshot)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("x402_history_record_failed", error=str(exc))


def get_x402_history(db: Session, limit: int = HISTORY_LIMIT) -> list[dict[str, Any]]:
    """Return recent x402 snapshots ordered oldest to newest."""
    try:
        rows = (
            db.query(X402EcosystemSnapshot)
            .order_by(X402EcosystemSnapshot.snapshot_time.desc())
            .limit(limit)
            .all()
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("x402_history_read_failed", error=str(exc))
        return []

    return [_serialize(row) for row in reversed(rows)]


def _serialize(row: X402EcosystemSnapshot) -> dict[str, Any]:
    return {
        "snapshot_time": row.snapshot_time.isoformat() + "Z",
        "transactions_30d": row.transactions_30d,
        "volume_30d": row.volume_30d,
        "buyers_30d": row.buyers_30d,
        "sellers_30d": row.sellers_30d,
        "total_resources": row.total_resources,
        "sampled_resources": row.sampled_resources,
        "priced_resources": row.priced_resources,
        "base_resources": row.base_resources,
        "x402_capability_agents": row.x402_capability_agents,
        "agentkit_capability_agents": row.agentkit_capability_agents,
        "payable_capability_agents": row.payable_capability_agents,
        "discovery_status": row.discovery_status,
    }


def _stat_value(stats: dict[str, Any], key: str) -> float | None:
    value = stats.get(key)
    if not isinstance(value, dict):
        return None
    raw = value.get("value")
    return float(raw) if raw is not None else None


def _count_named(rows: list[dict[str, Any]], name: str) -> int | None:
    for row in rows:
        if row.get("name") == name:
            return int(row.get("count") or 0)
    return 0
