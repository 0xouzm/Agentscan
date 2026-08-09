import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.db.migrate_reputation_aggregate import migrate
from src.services.reputation_aggregation import add_feedback_to_aggregate


class ReputationAggregationTests(unittest.TestCase):
    def test_adds_mixed_fixed_point_values_incrementally(self):
        value_sum, count, average = add_feedback_to_aggregate(0.0, 0, 9977, 2)
        value_sum, count, average = add_feedback_to_aggregate(
            value_sum, count, -32, 1
        )

        self.assertEqual(count, 2)
        self.assertAlmostEqual(value_sum, 96.57)
        self.assertAlmostEqual(average, 48.285)

    def test_handles_large_existing_aggregate_without_history(self):
        value_sum, count, average = add_feedback_to_aggregate(
            29_778_000.0, 297_780, 100, 0
        )

        self.assertEqual(count, 297_781)
        self.assertAlmostEqual(value_sum, 29_778_100.0)
        self.assertAlmostEqual(average, value_sum / count)

    def test_migration_backfills_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            connection = sqlite3.connect(db_path)
            connection.executescript("""
                CREATE TABLE agents (
                    id TEXT PRIMARY KEY,
                    reputation_score REAL NOT NULL DEFAULT 0,
                    reputation_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE feedbacks (
                    agent_id TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    value_decimals INTEGER NOT NULL DEFAULT 0,
                    is_revoked INTEGER NOT NULL DEFAULT 0
                );
                INSERT INTO agents VALUES ('onchain', 0, 0);
                INSERT INTO agents VALUES ('external', 4.5, 2);
                INSERT INTO feedbacks VALUES ('onchain', 9977, 2, 0);
                INSERT INTO feedbacks VALUES ('onchain', -32, 1, 0);
                INSERT INTO feedbacks VALUES ('onchain', 100, 0, 1);
            """)
            connection.commit()
            connection.close()

            with patch.dict(
                os.environ, {"DATABASE_URL": f"sqlite:///{db_path}"}
            ):
                migrate()
                migrate()

            connection = sqlite3.connect(db_path)
            onchain = connection.execute(
                "SELECT reputation_value_sum, reputation_count, reputation_score "
                "FROM agents WHERE id = 'onchain'"
            ).fetchone()
            external = connection.execute(
                "SELECT reputation_value_sum, reputation_count, reputation_score "
                "FROM agents WHERE id = 'external'"
            ).fetchone()
            connection.close()

            self.assertAlmostEqual(onchain[0], 96.57)
            self.assertEqual(onchain[1], 2)
            self.assertAlmostEqual(onchain[2], 48.285)
            self.assertAlmostEqual(external[0], 9.0)
            self.assertEqual(external[1], 2)
            self.assertAlmostEqual(external[2], 4.5)


if __name__ == "__main__":
    unittest.main()
