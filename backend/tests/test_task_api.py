import os
import tempfile
import unittest
from datetime import datetime, timedelta

import app.db as database
from app import create_app


class TaskApiTests(unittest.TestCase):
    def setUp(self):
        self.original_db_path = database.DB_PATH
        database.DB_PATH = tempfile.mktemp(suffix=".db")
        self.app = create_app()
        self.client = self.app.test_client()
        self.user = self._signup("owner")
        self.headers = {"Authorization": f"Bearer {self.user['access_token']}"}

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

    def _create_task(self, **kwargs):
        payload = {
            "title": "Practice algebra",
            "tag": "Study",
            "duration_minutes": 45,
            "scheduled_date": "2026-10-21",
            "start_date": "2026-10-21",
            "task_list_id": "list-math",
        }
        payload.update(kwargs)
        response = self.client.post("/api/tasks", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()

    def _day_tasks(self, day):
        response = self.client.get(
            f"/api/tasks?date={day}&view=day", headers=self.headers
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def test_logout_revokes_the_access_token(self):
        """Logging out must invalidate the token on the server."""
        self.assertEqual(self.client.get("/api/tasks", headers=self.headers).status_code, 200)

        logout = self.client.post("/api/auth/logout", headers=self.headers)
        self.assertEqual(logout.status_code, 200, logout.get_json())

        # The revoked token must no longer authenticate any request.
        after_logout = self.client.get("/api/tasks", headers=self.headers)
        self.assertEqual(after_logout.status_code, 401, after_logout.get_json())

    def test_logout_without_a_token_is_still_successful(self):
        response = self.client.post("/api/auth/logout")
        self.assertEqual(response.status_code, 200, response.get_json())

    def test_one_time_task_and_calendar_date(self):
        task = self._create_task(due_date="2026-10-23")
        self.assertEqual(task["scheduled_date"], "2026-10-21")
        self.assertEqual(task["due_date"], "2026-10-23")
        self.assertIn(task["id"], [row["id"] for row in self._day_tasks("2026-10-21")])
        self.assertNotIn(
            task["id"], [row["id"] for row in self._day_tasks("2026-10-22")]
        )

    def test_recurring_generation_is_idempotent_and_completion_is_per_occurrence(self):
        series_task = self._create_task(
            recurrence_rule={"frequency": "daily", "interval": 1}
        )
        first = series_task["id"]
        day_22 = self._day_tasks("2026-10-22")
        occurrence_22 = next(
            task for task in day_22 if task["series_id"] == series_task["series_id"]
        )
        self._day_tasks("2026-10-22")
        connection = database.get_db()
        count = connection.execute(
            "SELECT COUNT(*) FROM tasks WHERE series_id = ? AND scheduled_date = ?",
            (series_task["series_id"], "2026-10-22"),
        ).fetchone()[0]
        connection.close()
        self.assertEqual(count, 1)

        completed = self.client.post(
            f"/api/tasks/{first}/toggle", json={"completed": True}, headers=self.headers
        )
        self.assertEqual(completed.status_code, 200)
        self.assertTrue(completed.get_json()["completed"])
        self.assertFalse(occurrence_22["completed"])

    def test_series_future_edit_and_this_occurrence_edit(self):
        initial = self._create_task(
            recurrence_rule={"frequency": "daily", "interval": 1}
        )
        self.client.put(
            f"/api/tasks/{initial['id']}",
            json={"scope": "this", "title": "Only this date", "duration_minutes": 30},
            headers=self.headers,
        )
        self.assertEqual(
            next(
                task
                for task in self._day_tasks("2026-10-21")
                if task["id"] == initial["id"]
            )["title"],
            "Only this date",
        )
        next_day = self._day_tasks("2026-10-22")
        next_occurrence = next(
            task for task in next_day if task["series_id"] == initial["series_id"]
        )
        self.assertEqual(next_occurrence["title"], "Practice algebra")

        edited = self.client.put(
            f"/api/tasks/{next_occurrence['id']}",
            json={"scope": "future", "title": "Algebra review", "duration_minutes": 50},
            headers=self.headers,
        )
        self.assertEqual(edited.status_code, 200, edited.get_json())
        third_day = self._day_tasks("2026-10-23")
        third_occurrence = next(
            task for task in third_day if task["series_id"] == initial["series_id"]
        )
        self.assertEqual(third_occurrence["title"], "Algebra review")

    def test_skip_is_not_completion(self):
        task = self._create_task()
        response = self.client.post(
            f"/api/tasks/{task['id']}/skip", headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        skipped = next(
            row for row in self._day_tasks("2026-10-21") if row["id"] == task["id"]
        )
        self.assertTrue(skipped["skipped"])
        self.assertFalse(skipped["completed"])

    def test_user_cannot_read_or_mutate_another_users_task(self):
        owner_task = self._create_task()
        other = self._signup("other")
        other_headers = {"Authorization": f"Bearer {other['access_token']}"}
        denied = self.client.post(
            f"/api/tasks/{owner_task['id']}/toggle",
            json={"completed": True},
            headers=other_headers,
        )
        self.assertEqual(denied.status_code, 404)
        unauthorized = self.client.get("/api/tasks?user_id=1")
        self.assertEqual(unauthorized.status_code, 401)
        wrong_owner = self.client.get(
            f"/api/tasks?user_id={self.user['id']}&view=all", headers=other_headers
        )
        self.assertEqual(wrong_owner.status_code, 200)
        self.assertNotIn(
            owner_task["id"], [task["id"] for task in wrong_owner.get_json()]
        )

    def test_duplicate_focus_session_is_ignored(self):
        task = self._create_task()
        payload = {
            "client_session_id": "focus-session-1",
            "started_at": "2026-10-21T10:00:00+00:00",
            "ended_at": "2026-10-21T10:01:00+00:00",
            "duration_seconds": 60,
        }
        first = self.client.post(
            f"/api/tasks/{task['id']}/sessions", json=payload, headers=self.headers
        )
        second = self.client.post(
            f"/api/tasks/{task['id']}/sessions", json=payload, headers=self.headers
        )
        self.assertEqual(first.status_code, 201)
        self.assertFalse(first.get_json()["duplicate"])
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.get_json()["duplicate"])
        connection = database.get_db()
        seconds = connection.execute(
            "SELECT actual_duration_seconds FROM tasks WHERE id = ?", (task["id"],)
        ).fetchone()[0]
        connection.close()
        self.assertEqual(seconds, 60)

    def test_weekly_totals_roll_over_on_local_monday(self):
        initial = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(initial["focus_seconds_week"], 0)
        self.client.post(
            "/api/stats/record",
            json={"seconds": 37},
            headers=self.headers,
        )
        current = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(current["focus_seconds_week"], 37)

        connection = database.get_db()
        connection.execute(
            "UPDATE user_stats SET focus_seconds_week = 37, focus_minutes_week = 1, stats_week_start = ? WHERE user_id = ?",
            ("2000-01-03", self.user["id"]),
        )
        connection.commit()
        connection.close()
        reset = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(reset["focus_seconds_week"], 0)
        self.assertEqual(reset["focus_minutes_week"], 0)

    def test_analytics_uses_sessions_not_scheduled_duration(self):
        today = datetime.now().date().isoformat()
        started_at = datetime.now().astimezone().replace(second=0, microsecond=0)
        ended_at = started_at + timedelta(minutes=1)
        task = self._create_task(scheduled_date=today)
        session = self.client.post(
            f"/api/tasks/{task['id']}/sessions",
            json={
                "client_session_id": "analytics-session",
                "started_at": started_at.isoformat(),
                "ended_at": ended_at.isoformat(),
                "study_date": today,
                "duration_seconds": 60,
            },
            headers=self.headers,
        )
        self.assertEqual(session.status_code, 201, session.get_json())
        self.client.post(
            f"/api/tasks/{task['id']}/toggle",
            json={"completed": True, "actual_duration_seconds": 60},
            headers=self.headers,
        )
        analytics = self.client.get(
            f"/api/analytics?start={today}&end={today}",
            headers=self.headers,
        ).get_json()
        self.assertEqual(analytics["days"][0]["study_seconds"], 60)
        self.assertEqual(analytics["days"][0]["completed_occurrences"], 1)
        self.assertEqual(analytics["days"][0]["scheduled_occurrences"], 1)

    def test_overdue_and_reschedule_use_due_date(self):
        task = self._create_task(scheduled_date="2026-10-19", due_date="2026-10-20")
        overdue = self.client.get(
            "/api/tasks?view=overdue", headers=self.headers
        ).get_json()
        self.assertIn(task["id"], [item["id"] for item in overdue])
        response = self.client.post(
            f"/api/tasks/{task['id']}/reschedule",
            json={"scheduled_date": "2026-10-22", "due_date": "2026-10-22"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["scheduled_date"], "2026-10-22")
        self.assertEqual(response.get_json()["due_date"], "2026-10-22")
        overdue = self.client.get(
            "/api/tasks?view=overdue", headers=self.headers
        ).get_json()
        self.assertNotIn(task["id"], [item["id"] for item in overdue])

    def test_rescheduled_occurrence_is_not_regenerated_on_refresh(self):
        first = self._create_task(recurrence_rule={"frequency": "daily", "interval": 1})
        moved = self.client.post(
            f"/api/tasks/{first['id']}/reschedule",
            json={"scheduled_date": "2026-10-20"},
            headers=self.headers,
        )
        self.assertEqual(moved.status_code, 200, moved.get_json())
        self._day_tasks("2026-10-21")
        self._day_tasks("2026-10-21")

        connection = database.get_db()
        occurrence = connection.execute(
            "SELECT id, occurrence_date, scheduled_date FROM tasks "
            "WHERE series_id = ? AND occurrence_date = ?",
            (first["series_id"], "2026-10-21"),
        ).fetchone()
        connection.close()
        self.assertEqual(occurrence["id"], first["id"])
        self.assertEqual(occurrence["scheduled_date"], "2026-10-20")

    def test_stopping_future_occurrences_preserves_completed_history(self):
        first = self._create_task(recurrence_rule={"frequency": "daily", "interval": 1})
        self.client.post(
            f"/api/tasks/{first['id']}/toggle",
            json={"completed": True},
            headers=self.headers,
        )
        second = next(
            task
            for task in self._day_tasks("2026-10-22")
            if task["series_id"] == first["series_id"]
        )
        deleted = self.client.delete(
            f"/api/tasks/{second['id']}",
            json={"scope": "future"},
            headers=self.headers,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(
            next(
                task
                for task in self._day_tasks("2026-10-21")
                if task["id"] == first["id"]
            )["completed"]
        )
        later = self._day_tasks("2026-10-23")
        self.assertFalse(
            any(task.get("series_id") == first["series_id"] for task in later)
        )

    def test_weekly_series_starting_midweek_returns_first_selected_weekday(self):
        first = self._create_task(
            start_date="2026-10-21",
            scheduled_date="2026-10-21",
            recurrence_rule={"frequency": "weekly", "interval": 1, "weekdays": [0]},
        )
        self.assertEqual(first["scheduled_date"], "2026-10-26")
        monday = self._day_tasks("2026-10-26")
        self.assertIn(first["id"], [task["id"] for task in monday])

    def test_completed_history_is_not_overwritten_by_series_edit(self):
        first = self._create_task(recurrence_rule={"frequency": "daily", "interval": 1})
        completed_at = self.client.post(
            f"/api/tasks/{first['id']}/toggle",
            json={"completed": True},
            headers=self.headers,
        ).get_json()["completed_at"]
        second = next(
            task
            for task in self._day_tasks("2026-10-22")
            if task["series_id"] == first["series_id"]
        )
        self.client.put(
            f"/api/tasks/{second['id']}",
            json={"scope": "series", "title": "Updated title", "duration_minutes": 60},
            headers=self.headers,
        )
        historical = next(
            task for task in self._day_tasks("2026-10-21") if task["id"] == first["id"]
        )
        self.assertTrue(historical["completed"])
        self.assertEqual(historical["title"], "Practice algebra")
        self.assertEqual(historical["completed_at"], completed_at)


if __name__ == "__main__":
    unittest.main()
