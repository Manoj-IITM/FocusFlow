import os
import tempfile
import unittest
from datetime import datetime, timedelta

import app.db as database
from app import create_app


class StatsApiTests(unittest.TestCase):
    def setUp(self):
        self.original_db_path = database.DB_PATH
        database.DB_PATH = tempfile.mktemp(suffix=".db")
        self.app = create_app()
        self.client = self.app.test_client()
        self.user = self._signup("owner")
        self.headers = {"Authorization": f"Bearer {self.user['access_token']}"}
        self.other = self._signup("intruder")
        self.other_headers = {"Authorization": f"Bearer {self.other['access_token']}"}

    def tearDown(self):
        if os.path.exists(database.DB_PATH):
            os.remove(database.DB_PATH)
        database.DB_PATH = self.original_db_path

    def _signup(self, username):
        response = self.client.post(
            "/api/auth/signup",
            json={
                "username": username,
                "email": f"{username}@example.test",
                "password": "test-password",
            },
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["user"]

    def _delete_stats_row(self, user_id):
        connection = database.get_db()
        connection.execute("DELETE FROM user_stats WHERE user_id = ?", (user_id,))
        connection.commit()
        connection.close()

    def _stats_row(self, user_id):
        connection = database.get_db()
        row = connection.execute(
            "SELECT * FROM user_stats WHERE user_id = ?", (user_id,)
        ).fetchone()
        connection.close()
        return row

    def _record(self, seconds, headers=None, payload=None):
        body = payload if payload is not None else {"seconds": seconds}
        return self.client.post(
            "/api/stats/record", json=body, headers=headers or self.headers
        )

    def _get_stats(self, headers=None, query=""):
        return self.client.get(
            f"/api/stats{query}", headers=headers or self.headers
        )

    def test_record_focus_creates_missing_stats_row(self):
        """Recorded focus time must survive even when the account has no stats row."""
        self._delete_stats_row(self.user["id"])
        self.assertIsNone(self._stats_row(self.user["id"]))

        recorded = self._record(120)
        self.assertEqual(recorded.status_code, 200, recorded.get_json())

        row = self._stats_row(self.user["id"])
        self.assertIsNotNone(row, "record_focus should create the missing stats row")
        self.assertEqual(row["focus_seconds_today"], 120)
        self.assertEqual(row["focus_minutes_today"], 2)
        self.assertEqual(row["focus_seconds_week"], 120)
        self.assertEqual(row["focus_minutes_week"], 2)

        stats = self._get_stats().get_json()
        self.assertEqual(stats["focus_seconds_today"], 120)
        self.assertEqual(stats["focus_minutes_today"], 2)

    def test_record_focus_accumulates_across_requests(self):
        self._delete_stats_row(self.user["id"])
        self._record(60)
        self._record(30)
        row = self._stats_row(self.user["id"])
        self.assertEqual(row["focus_seconds_today"], 90)
        self.assertEqual(row["focus_minutes_today"], 2)

    def test_stats_reports_zero_instead_of_placeholder_values(self):
        self._delete_stats_row(self.user["id"])
        stats = self._get_stats().get_json()
        self.assertEqual(stats["focus_minutes_today"], 0)
        self.assertEqual(stats["focus_seconds_today"], 0)
        self.assertEqual(stats["focus_minutes_week"], 0)
        self.assertEqual(stats["focus_seconds_week"], 0)

    def test_stats_ignores_client_supplied_user_id(self):
        """Identity comes from the bearer token, never from a request parameter."""
        self._record(90)
        other_before = self._stats_row(self.other["id"])

        stats = self._get_stats(query=f"?user_id={self.other['id']}").get_json()
        self.assertEqual(stats["focus_seconds_today"], 90)

        recorded = self._record(
            30, payload={"seconds": 30, "user_id": self.other["id"]}
        )
        self.assertEqual(recorded.status_code, 200, recorded.get_json())

        self.assertEqual(self._stats_row(self.user["id"])["focus_seconds_today"], 120)
        self.assertEqual(
            self._stats_row(self.other["id"])["focus_seconds_today"],
            other_before["focus_seconds_today"],
        )

    def test_record_focus_requires_authentication(self):
        response = self.client.post("/api/stats/record", json={"seconds": 60})
        self.assertEqual(response.status_code, 401)

    def test_record_focus_rejects_negative_seconds(self):
        response = self._record(-10)
        self.assertEqual(response.status_code, 400)

    def test_record_focus_ignores_non_numeric_payload(self):
        response = self._record(None, payload={"seconds": "not-a-number"})
        self.assertEqual(response.status_code, 200, response.get_json())


if __name__ == "__main__":
    unittest.main()
