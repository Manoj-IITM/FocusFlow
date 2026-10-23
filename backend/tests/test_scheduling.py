import unittest
from datetime import date

from app.scheduling import is_occurrence_date, normalize_recurrence, occurrence_dates


class RecurrenceTests(unittest.TestCase):
    def test_daily_interval(self):
        dates = list(
            occurrence_dates(
                "2026-10-21",
                "2026-10-27",
                {
                    "frequency": "daily",
                    "interval": 2,
                },
            )
        )
        self.assertEqual(
            dates,
            [
                date(2026, 10, 21),
                date(2026, 10, 23),
                date(2026, 10, 25),
                date(2026, 10, 27),
            ],
        )

    def test_weekday_selection(self):
        dates = list(
            occurrence_dates(
                "2026-10-19",
                "2026-10-25",
                {
                    "frequency": "weekly",
                    "interval": 1,
                    "weekdays": [0, 2, 4],
                },
            )
        )
        self.assertEqual(
            dates, [date(2026, 10, 19), date(2026, 10, 21), date(2026, 10, 23)]
        )

    def test_every_two_weeks_on_selected_weekdays(self):
        self.assertTrue(
            is_occurrence_date(
                "2026-10-20",
                "2026-11-03",
                {
                    "frequency": "weekly",
                    "interval": 2,
                    "weekdays": [1, 3],
                },
            )
        )
        self.assertFalse(
            is_occurrence_date(
                "2026-10-20",
                "2026-10-27",
                {
                    "frequency": "weekly",
                    "interval": 2,
                    "weekdays": [1, 3],
                },
            )
        )

    def test_monthly_day_clamps_to_last_day(self):
        self.assertTrue(
            is_occurrence_date(
                "2026-01-31",
                "2026-02-28",
                {
                    "frequency": "monthly",
                    "interval": 1,
                    "day_of_month": 31,
                },
            )
        )
        self.assertTrue(
            is_occurrence_date(
                "2026-01-31",
                "2026-04-30",
                {
                    "frequency": "monthly",
                    "interval": 1,
                    "day_of_month": 31,
                },
            )
        )
        self.assertFalse(
            is_occurrence_date(
                "2026-01-31",
                "2026-03-30",
                {
                    "frequency": "monthly",
                    "interval": 1,
                    "day_of_month": 31,
                },
            )
        )

    def test_custom_month_interval_and_end_date(self):
        dates = list(
            occurrence_dates(
                "2026-01-15",
                "2026-06-30",
                {
                    "frequency": "custom",
                    "unit": "months",
                    "interval": 2,
                    "day_of_month": 15,
                    "end_condition": "date",
                    "end_date": "2026-05-15",
                },
            )
        )
        self.assertEqual(
            dates, [date(2026, 1, 15), date(2026, 3, 15), date(2026, 5, 15)]
        )

    def test_occurrence_limit_includes_start_date(self):
        dates = list(
            occurrence_dates(
                "2026-10-21",
                "2026-10-30",
                {
                    "frequency": "daily",
                    "interval": 1,
                    "end_condition": "count",
                    "occurrence_count": 3,
                },
            )
        )
        self.assertEqual(
            dates, [date(2026, 10, 21), date(2026, 10, 22), date(2026, 10, 23)]
        )

    def test_invalid_rules_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_recurrence({"frequency": "daily", "interval": 0}, "2026-10-21")
        with self.assertRaises(ValueError):
            normalize_recurrence({"frequency": "weekly", "weekdays": []}, "2026-10-21")


if __name__ == "__main__":
    unittest.main()
