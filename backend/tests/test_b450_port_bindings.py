"""Fail closed if private core DB/cache ports become network-wide bindings."""
from pathlib import Path
import unittest


class CoreLoopbackPortTests(unittest.TestCase):
    def test_postgres_redis_only_loopback(self) -> None:
        compose = (
            Path(__file__).resolve().parents[2] / "docker-compose.spark.yml"
        ).read_text()
        self.assertIn('"127.0.0.1:${POSTGRES_PORT:-5433}:5432"', compose)
        self.assertIn('"127.0.0.1:${REDIS_PORT:-6380}:6379"', compose)
        self.assertNotIn('"${POSTGRES_PORT:-5433}:5432"', compose)
        self.assertNotIn('"${REDIS_PORT:-6380}:6379"', compose)


if __name__ == "__main__":
    unittest.main()
