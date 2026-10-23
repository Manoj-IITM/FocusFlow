import json
from datetime import timedelta

from .scheduling import occurrence_dates, parse_date


def materialize_occurrences(cursor, user_id, start_date, end_date):
    start = parse_date(start_date)
    end = parse_date(end_date)
    if end < start:
        return

    cursor.execute(
        "SELECT * FROM task_series WHERE user_id = ? AND active = 1 AND start_date <= ?",
        (user_id, end.isoformat()),
    )
    for series in cursor.fetchall():
        rule = json.loads(series["recurrence_rule"])
        for occurrence_date in occurrence_dates(
            series["start_date"],
            end,
            rule,
            end_date_limit=series["end_date"],
            occurrence_limit=series["occurrence_limit"],
        ):
            if occurrence_date < start:
                continue
            due_date = None
            if series["due_offset_days"] is not None:
                due_date = (
                    occurrence_date + timedelta(days=series["due_offset_days"])
                ).isoformat()
            cursor.execute(
                "INSERT OR IGNORE INTO tasks "
                "(user_id, series_id, occurrence_date, task_list_id, title, tag, duration_minutes, priority, notes, scheduled_date, due_date) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    series["id"],
                    occurrence_date.isoformat(),
                    series["task_list_id"],
                    series["title"],
                    series["tag"],
                    series["duration_minutes"],
                    series["priority"],
                    series["notes"],
                    occurrence_date.isoformat(),
                    due_date,
                ),
            )


def task_to_dict(row):
    task = dict(row)
    task["completed"] = bool(task.get("completed"))
    task["skipped"] = bool(task.get("skipped"))
    if task.get("recurrence_rule"):
        task["recurrence_rule"] = json.loads(task["recurrence_rule"])
    return task


def task_select_sql():
    return (
        "SELECT tasks.*, task_series.recurrence_rule, task_series.start_date AS series_start_date, "
        "task_series.end_date AS series_end_date, task_series.occurrence_limit, task_series.active AS series_active "
        "FROM tasks LEFT JOIN task_series ON task_series.id = tasks.series_id "
    )
