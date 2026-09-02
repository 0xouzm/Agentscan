"""Regression tests for endpoint-health RPC safety boundaries."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.api.endpoint_health import (
    _cached_report,
    get_full_endpoint_health_report,
    get_working_agents,
)
from src.services.endpoint_health_service import EndpointHealthService


def _agent() -> SimpleNamespace:
    return SimpleNamespace(
        id="agent-1",
        name="Cached Agent",
        token_id=7,
        network_id="base",
        metadata_uri="https://example.com/agent.json",
        endpoint_status={
            "has_working_endpoints": True,
            "total_endpoints": 1,
            "healthy_endpoints": 1,
            "endpoints": [
                {
                    "url": "https://example.com/mcp",
                    "is_healthy": True,
                    "status_code": 200,
                    "response_time_ms": 12.0,
                    "checked_at": "2026-09-02T00:00:00",
                }
            ],
        },
        reputation_score=90.0,
        reputation_count=3,
        endpoint_checked_at=None,
    )


def _db_for_agents(agents: list[SimpleNamespace], count: int = 1) -> MagicMock:
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = agents
    query.scalar.return_value = count
    db.query.return_value = query
    return db


class EndpointHealthSafetyTests(unittest.TestCase):
    def test_cached_report_has_no_live_feedback_payload(self):
        report = _cached_report(_agent())

        self.assertTrue(report["has_working_endpoints"])
        self.assertEqual(report["recent_feedbacks"], [])
        self.assertEqual(report["network_key"], "base")

    def test_working_agents_never_calls_live_health_service(self):
        db = _db_for_agents([_agent()], count=1)

        with patch(
            "src.api.endpoint_health.get_endpoint_health_service",
            side_effect=AssertionError("live service must not be called"),
        ):
            result = asyncio.run(
                get_working_agents(
                    network="base", min_reputation=0, limit=20, db=db
                )
            )

        self.assertEqual(result["total_working"], 1)
        self.assertEqual(len(result["agents"]), 1)

    def test_full_report_is_bounded_and_database_only(self):
        db = _db_for_agents([_agent()])

        with patch(
            "src.api.endpoint_health.get_endpoint_health_service",
            side_effect=AssertionError("live service must not be called"),
        ):
            result = asyncio.run(
                get_full_endpoint_health_report(network="base", limit=100, db=db)
            )

        self.assertEqual(result.summary.total_agents, 1)
        self.assertEqual(len(result.all_reports), 1)

    def test_recent_feedbacks_use_local_database_cache(self):
        feedback = MagicMock()
        feedback.to_dict.return_value = {"id": "feedback-1"}
        db = _db_for_agents([feedback])

        with patch(
            "src.services.endpoint_health_service.SessionLocal",
            return_value=db,
        ):
            result = asyncio.run(
                EndpointHealthService()._get_recent_feedbacks(7, "base", limit=5)
            )

        self.assertEqual(result, [{"id": "feedback-1"}])
        db.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
