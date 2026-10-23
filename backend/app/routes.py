import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .scheduling import (
    is_occurrence_date,
    normalize_recurrence,
    occurrence_dates,
    parse_date,
)
from .task_service import materialize_occurrences, task_select_sql, task_to_dict

api = Blueprint("api", __name__)


def _issue_api_token(cursor, user_id):
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    cursor.execute(
        "INSERT INTO api_tokens (token_hash, user_id) VALUES (?, ?)",
        (token_hash, user_id),
    )
    return token


def _authenticated_user_id():
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None

    token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    conn = get_db()
    row = conn.execute(
        "SELECT user_id FROM api_tokens WHERE token_hash = ? AND revoked = 0",
        (token_hash,),
    ).fetchone()
    conn.close()
    return int(row["user_id"]) if row else None


def _unauthorized():
    return jsonify({"error": "Sign in to access your tasks"}), 401


def _owned_task(cursor, user_id, task_id):
    cursor.execute(
        task_select_sql() + "WHERE tasks.user_id = ? AND tasks.id = ?",
        (user_id, task_id),
    )
    return cursor.fetchone()


@api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "FocusFlow API is running"})


# AUTHENTICATION


@api.route("/auth/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not username or not email or not password:
        return (
            jsonify({"error": "Username, email, and password are required"}),
            400,
        )

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (username, email),
    )
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Username or email already exists"}), 409

    pw_hash = generate_password_hash(password)
    cursor.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, pw_hash),
    )
    user_id = cursor.lastrowid

    # Seed default tasks & stats for new user
    initial_tasks = [
        (user_id, "Maths Revision - Chapter 5", "Study", 85, 0, None),
        (user_id, "Physics Numericals", "Study", 45, 1, "Today, 06:15 PM"),
        (user_id, "Chemistry Notes", "Study", 120, 0, None),
        (user_id, "Read Chapter 3 (English)", "Study", 60, 0, None),
        (user_id, "DSA Practice Questions", "Study", 90, 1, "Today, 04:20 PM"),
    ]
    cursor.executemany(
        "INSERT INTO tasks (user_id, title, tag, duration_minutes, completed, completed_time) VALUES (?, ?, ?, ?, ?, ?)",
        initial_tasks,
    )
    today = datetime.now().date()
    week_start = (today - timedelta(days=today.weekday())).isoformat()
    cursor.execute(
        "INSERT INTO user_stats (user_id, streak_days, focus_minutes_today, focus_minutes_week, "
        "focus_seconds_today, stats_date, focus_seconds_week, stats_week_start) "
        "VALUES (?, 1, 0, 0, 0, ?, 0, ?)",
        (user_id, today.isoformat(), week_start),
    )
    access_token = _issue_api_token(cursor, user_id)

    conn.commit()
    conn.close()

    return (
        jsonify(
            {
                "message": "User registered successfully",
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "access_token": access_token,
                },
            }
        ),
        201,
    )


@api.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    identifier = data.get("email", "").strip() or data.get("username", "").strip()
    password = data.get("password", "")

    if not identifier or not password:
        return jsonify({"error": "Email/username and password required"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE email = ? OR username = ?",
        (identifier, identifier),
    )
    user = cursor.fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        conn.close()
        return jsonify({"error": "Invalid email or password"}), 401

    access_token = _issue_api_token(cursor, user["id"])
    conn.commit()
    conn.close()

    return jsonify(
        {
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "access_token": access_token,
            },
        }
    )


@api.route("/auth/logout", methods=["POST"])
def logout():
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
        conn = get_db()
        conn.execute(
            "UPDATE api_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,)
        )
        conn.commit()
        conn.close()
    return jsonify({"success": True})


# TASKS ENDPOINTS


@api.route("/tasks", methods=["GET"])
def get_tasks():
    user_id = _authenticated_user_id()
    if not user_id:
        return _unauthorized()

    today = datetime.now().date()
    view = request.args.get("view", "day")
    try:
        selected_date = parse_date(request.args.get("date") or today.isoformat())
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    conn = get_db()
    cursor = conn.cursor()
    if view == "day":
        range_start = range_end = selected_date
    elif view == "upcoming":
        range_start, range_end = today, today + timedelta(days=90)
    elif view == "overdue":
        range_start, range_end = today - timedelta(days=366), today
    elif view == "all":
        # The all-tasks view must include recurring occurrences around the
        # selected date as well as previously materialized tasks.
        range_start = selected_date - timedelta(days=366)
        range_end = selected_date + timedelta(days=366)
    else:
        conn.close()
        return jsonify({"error": "Unsupported task view"}), 400

    materialize_occurrences(cursor, user_id, range_start, range_end)
    if view == "day":
        query = task_select_sql() + (
            "WHERE tasks.user_id = ? AND (tasks.scheduled_date = ? OR tasks.scheduled_date IS NULL) "
            "ORDER BY tasks.skipped, tasks.completed, tasks.due_date, tasks.id"
        )
        params = (user_id, selected_date.isoformat())
    elif view == "upcoming":
        query = task_select_sql() + (
            "WHERE tasks.user_id = ? AND tasks.scheduled_date BETWEEN ? AND ? "
            "AND tasks.completed = 0 AND tasks.skipped = 0 ORDER BY tasks.scheduled_date, tasks.id"
        )
        params = (user_id, today.isoformat(), (today + timedelta(days=90)).isoformat())
    elif view == "overdue":
        query = task_select_sql() + (
            "WHERE tasks.user_id = ? AND tasks.due_date < ? AND tasks.completed = 0 AND tasks.skipped = 0 "
            "ORDER BY tasks.due_date, tasks.id"
        )
        params = (user_id, today.isoformat())
    else:
        query = (
            task_select_sql()
            + "WHERE tasks.user_id = ? ORDER BY tasks.scheduled_date, tasks.id"
        )
        params = (user_id,)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.commit()
    conn.close()
    return jsonify([task_to_dict(row) for row in rows])


@api.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json() or {}
    user_id = _authenticated_user_id()
    if not user_id:
        return _unauthorized()

    title = str(data.get("title", "")).strip()
    tag = str(data.get("tag", "Study")).strip() or "Study"
    notes = str(data.get("notes", "")).strip()
    task_list_id = str(data.get("task_list_id", "")).strip() or None
    priority = str(data.get("priority", "medium")).lower()

    if not title:
        return jsonify({"error": "Title is required"}), 400
    if len(title) > 200 or len(notes) > 5000:
        return jsonify({"error": "Task title or notes are too long"}), 400
    if priority not in {"low", "medium", "high"}:
        return jsonify({"error": "Priority must be low, medium, or high"}), 400
    try:
        duration_minutes = int(data.get("duration_minutes", 45))
        if not 5 <= duration_minutes <= 300:
            raise ValueError
        scheduled_date = (
            parse_date(data["scheduled_date"]) if data.get("scheduled_date") else None
        )
        due_date = parse_date(data["due_date"]) if data.get("due_date") else None
        start_date = parse_date(
            data.get("start_date")
            or (
                scheduled_date.isoformat()
                if scheduled_date
                else datetime.now().date().isoformat()
            )
        )
        recurrence = normalize_recurrence(
            data.get("recurrence_rule") or {"frequency": "none"}, start_date
        )
    except (TypeError, ValueError) as error:
        return jsonify(
            {"error": str(error) or "Task duration must be between 5 and 300 minutes"}
        ), 400

    conn = get_db()
    cursor = conn.cursor()
    if recurrence["frequency"] == "none":
        cursor.execute(
            "INSERT INTO tasks (user_id, task_list_id, title, tag, duration_minutes, completed, "
            "scheduled_date, due_date, priority, notes) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)",
            (
                user_id,
                task_list_id,
                title,
                tag,
                duration_minutes,
                scheduled_date.isoformat() if scheduled_date else None,
                due_date.isoformat() if due_date else None,
                priority,
                notes,
            ),
        )
        task_id = cursor.lastrowid
    else:
        if due_date and due_date < start_date:
            conn.close()
            return jsonify(
                {"error": "Due date cannot be before the recurrence start date"}
            ), 400
        due_offset_days = (due_date - start_date).days if due_date else None
        cursor.execute(
            "INSERT INTO task_series (user_id, task_list_id, title, tag, duration_minutes, priority, notes, "
            "recurrence_rule, start_date, end_date, occurrence_limit, due_offset_days) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                task_list_id,
                title,
                tag,
                duration_minutes,
                priority,
                notes,
                json.dumps(recurrence),
                start_date.isoformat(),
                recurrence.get("end_date"),
                recurrence.get("occurrence_count"),
                due_offset_days,
            ),
        )
        series_id = cursor.lastrowid
        materialize_occurrences(
            cursor,
            user_id,
            start_date,
            start_date + timedelta(days=366),
        )
        cursor.execute(
            "SELECT id FROM tasks WHERE user_id = ? AND series_id = ? "
            "AND scheduled_date >= ? ORDER BY scheduled_date LIMIT 1",
            (user_id, series_id, start_date.isoformat()),
        )
        first_occurrence = cursor.fetchone()
        if not first_occurrence:
            conn.rollback()
            conn.close()
            return jsonify(
                {"error": "The recurrence settings produce no occurrences"}
            ), 400
        task_id = first_occurrence["id"]

    cursor.execute(
        task_select_sql() + "WHERE tasks.user_id = ? AND tasks.id = ?",
        (user_id, task_id),
    )
    task = task_to_dict(cursor.fetchone())
    conn.commit()
    conn.close()

    return jsonify(task), 201


@api.route("/tasks/<int:task_id>/toggle", methods=["POST"])
def toggle_task(task_id):
    user_id = _authenticated_user_id()
    if not user_id:
        return _unauthorized()

    data = request.get_json(silent=True) or {}
    conn = get_db()
    cursor = conn.cursor()
    row = _owned_task(cursor, user_id, task_id)
    if not row:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    new_status = int(data.get("completed", not bool(row["completed"])))
    if row["skipped"]:
        conn.close()
        return jsonify(
            {"error": "Skipped occurrences must be reopened before completion"}
        ), 409
    now = datetime.now().astimezone()
    completed_at = now.isoformat() if new_status else None
    completed_time = now.strftime("Today, %I:%M %p") if new_status else None

    cursor.execute(
        "UPDATE tasks SET completed = ?, completed_time = ?, completed_at = ?, "
        "skipped = 0 WHERE user_id = ? AND id = ?",
        (
            int(bool(new_status)),
            completed_time,
            completed_at,
            user_id,
            task_id,
        ),
    )
    conn.commit()
    conn.close()

    return jsonify(
        {
            "completed": bool(new_status),
            "completed_time": completed_time,
            "completed_at": completed_at,
            "actual_duration_seconds": row["actual_duration_seconds"],
        }
    )


@api.route("/tasks/<int:task_id>/skip", methods=["POST"])
def skip_task(task_id):
    user_id = _authenticated_user_id()
    if not user_id:
        return _unauthorized()
    conn = get_db()
    cursor = conn.cursor()
    row = _owned_task(cursor, user_id, task_id)
    if not row:
        conn.close()
        return jsonify({"error": "Task not found"}), 404
    data = request.get_json(silent=True) or {}
    skipped = bool(data.get("skipped", True))
    if row["completed"] and skipped:
        conn.close()
        return jsonify({"error": "Completed occurrences cannot be skipped"}), 409
    cursor.execute(
        "UPDATE tasks SET skipped = ?, completed = CASE WHEN ? = 1 THEN 0 ELSE completed END "
        "WHERE user_id = ? AND id = ?",
        (int(skipped), int(skipped), user_id, task_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "skipped": skipped})


@api.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    user_id = _authenticated_user_id()
    if not user_id:
        return _unauthorized()
    data = request.get_json() or {}
    title = str(data.get("title", "")).strip()
    tag = str(data.get("tag", "Study")).strip() or "Study"
    notes = str(data.get("notes", "")).strip()
    priority = str(data.get("priority", "medium")).lower()
    scope = str(data.get("scope", "this"))

    if not title:
        return jsonify({"error": "Title is required"}), 400
    if scope not in {"this", "future", "series"}:
        return jsonify({"error": "Edit scope must be this, future, or series"}), 400
    if priority not in {"low", "medium", "high"}:
        return jsonify({"error": "Priority must be low, medium, or high"}), 400

    conn = get_db()
    cursor = conn.cursor()
    row = _owned_task(cursor, user_id, task_id)
    if not row:
        conn.close()
        return jsonify({"error": "Task not found"}), 404
    try:
        duration_minutes = int(data.get("duration_minutes", row["duration_minutes"]))
        if not 5 <= duration_minutes <= 300:
            raise ValueError
        scheduled = (
            parse_date(data["scheduled_date"]) if data.get("scheduled_date") else None
        )
        due = parse_date(data["due_date"]) if data.get("due_date") else None
    except (TypeError, ValueError) as error:
        conn.close()
        return jsonify(
            {"error": str(error) or "Duration must be between 5 and 300 minutes"}
        ), 400

    scheduled_value = (
        (scheduled.isoformat() if scheduled else None)
        if "scheduled_date" in data
        else row["scheduled_date"]
    )
    due_value = (
        (due.isoformat() if due else None)
        if "due_date" in data
        else row["due_date"]
    )
    task_list_id = (
        str(data.get("task_list_id", row["task_list_id"] or "")).strip() or None
    )
    recurrence_input = data.get("recurrence_rule") or {"frequency": "none"}
    if not isinstance(recurrence_input, dict):
        conn.close()
        return jsonify({"error": "Repeat settings must be an object"}), 400

    if not row["series_id"] and recurrence_input.get("frequency", "none") != "none":
        try:
            series_start = parse_date(
                data.get("start_date") or scheduled_value or datetime.now().date().isoformat()
            )
            recurrence = normalize_recurrence(recurrence_input, series_start)
        except (TypeError, ValueError) as error:
            conn.close()
            return jsonify({"error": str(error)}), 400

        first_occurrence = next(
            occurrence_dates(
                series_start,
                series_start + timedelta(days=366),
                recurrence,
                end_date_limit=recurrence.get("end_date"),
                occurrence_limit=recurrence.get("occurrence_count"),
            ),
            None,
        )
        if not first_occurrence:
            conn.close()
            return jsonify({"error": "The repeat settings produce no occurrences"}), 400
        due_offset = (due - first_occurrence).days if due else None
        if due_offset is not None and due_offset < 0:
            conn.close()
            return jsonify({"error": "Due date cannot be before the first occurrence"}), 400

        cursor.execute(
            "INSERT INTO task_series (user_id, task_list_id, title, tag, duration_minutes, priority, notes, "
            "recurrence_rule, start_date, end_date, occurrence_limit, due_offset_days) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id, task_list_id, title, tag, duration_minutes, priority, notes,
                json.dumps(recurrence), first_occurrence.isoformat(), recurrence.get("end_date"),
                recurrence.get("occurrence_count"), due_offset,
            ),
        )
        series_id = cursor.lastrowid
        first_due = (
            (first_occurrence + timedelta(days=due_offset)).isoformat()
            if due_offset is not None else None
        )
        cursor.execute(
            "UPDATE tasks SET title = ?, tag = ?, duration_minutes = ?, task_list_id = ?, "
            "scheduled_date = ?, occurrence_date = ?, due_date = ?, priority = ?, notes = ?, series_id = ? "
            "WHERE user_id = ? AND id = ?",
            (
                title, tag, duration_minutes, task_list_id, first_occurrence.isoformat(),
                first_occurrence.isoformat(), first_due, priority, notes, series_id, user_id, task_id,
            ),
        )
        materialize_occurrences(
            cursor, user_id, first_occurrence, first_occurrence + timedelta(days=366)
        )
    elif not row["series_id"] or scope == "this":
        cursor.execute(
            "UPDATE tasks SET title = ?, tag = ?, duration_minutes = ?, task_list_id = ?, "
            "scheduled_date = ?, due_date = ?, priority = ?, notes = ? WHERE user_id = ? AND id = ?",
            (
                title,
                tag,
                duration_minutes,
                task_list_id,
                scheduled_value,
                due_value,
                priority,
                notes,
                user_id,
                task_id,
            ),
        )
    else:
        cursor.execute(
            "SELECT * FROM task_series WHERE id = ? AND user_id = ?",
            (row["series_id"], user_id),
        )
        series = cursor.fetchone()
        if not series:
            conn.close()
            return jsonify({"error": "Task series not found"}), 404
        if scope == "future":
            effective_start = (
                scheduled_value
                if scheduled_value != row["scheduled_date"]
                else row["occurrence_date"] or scheduled_value or series["start_date"]
            )
        else:
            effective_start = data.get("start_date", series["start_date"])
        try:
            effective_start = parse_date(effective_start).isoformat()
            recurrence = normalize_recurrence(
                data.get("recurrence_rule", json.loads(series["recurrence_rule"])),
                effective_start,
            )
        except ValueError as error:
            conn.close()
            return jsonify({"error": str(error)}), 400

        due_offset = (
            (due - parse_date(effective_start)).days
            if due
            else series["due_offset_days"]
        )
        end_date = recurrence.get("end_date")
        cursor.execute(
            "UPDATE task_series SET task_list_id = ?, title = ?, tag = ?, duration_minutes = ?, priority = ?, "
            "notes = ?, recurrence_rule = ?, start_date = ?, end_date = ?, occurrence_limit = ?, "
            "due_offset_days = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            (
                task_list_id,
                title,
                tag,
                duration_minutes,
                priority,
                notes,
                json.dumps(recurrence),
                effective_start,
                end_date,
                recurrence.get("occurrence_count"),
                due_offset,
                row["series_id"],
                user_id,
            ),
        )
        date_clause = "occurrence_date >= ?" if scope == "future" else "1 = 1"
        params = [row["series_id"]]
        if scope == "future":
            params.append(effective_start)
        cursor.execute(
            f"SELECT id, scheduled_date, occurrence_date FROM tasks WHERE series_id = ? AND completed = 0 AND skipped = 0 AND {date_clause}",
            tuple(params),
        )
        pending_rows = cursor.fetchall()
        for pending in pending_rows:
            occurrence_key = pending["occurrence_date"] or pending["scheduled_date"]
            if not occurrence_key or not is_occurrence_date(
                effective_start, occurrence_key, recurrence
            ):
                cursor.execute(
                    "DELETE FROM tasks WHERE user_id = ? AND id = ?",
                    (user_id, pending["id"]),
                )
                continue
            occurrence_due = None
            if due_offset is not None:
                occurrence_due = (
                    parse_date(occurrence_key) + timedelta(days=due_offset)
                ).isoformat()
            cursor.execute(
                "UPDATE tasks SET task_list_id = ?, title = ?, tag = ?, duration_minutes = ?, priority = ?, "
                "notes = ?, due_date = ? WHERE user_id = ? AND id = ?",
                (
                    task_list_id,
                    title,
                    tag,
                    duration_minutes,
                    priority,
                    notes,
                    occurrence_due,
                    user_id,
                    pending["id"],
                ),
            )
        generation_end = datetime.now().date() + timedelta(days=90)
        materialize_occurrences(cursor, user_id, effective_start, generation_end)

    cursor.execute(
        task_select_sql() + "WHERE tasks.user_id = ? AND tasks.id = ?",
        (user_id, task_id),
    )
    updated = task_to_dict(cursor.fetchone())
    conn.commit()
    conn.close()
    return jsonify(updated)


@api.route("/tasks/<int:task_id>/reschedule", methods=["POST"])
def reschedule_task(task_id):
    user_id = _authenticated_user_id()
    if not user_id:
        return _unauthorized()
    data = request.get_json() or {}
    try:
        scheduled = parse_date(data.get("scheduled_date"))
        due = parse_date(data["due_date"]) if data.get("due_date") else None
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    conn = get_db()
    cursor = conn.cursor()
    row = _owned_task(cursor, user_id, task_id)
    if not row:
        conn.close()
        return jsonify({"error": "Task not found"}), 404
    if row["completed"] or row["skipped"]:
        conn.close()
        return jsonify(
            {"error": "Completed or skipped occurrences cannot be rescheduled"}
        ), 409
    try:
        cursor.execute(
            "UPDATE tasks SET scheduled_date = ?, due_date = ? WHERE user_id = ? AND id = ?",
            (
                scheduled.isoformat(),
                due.isoformat() if due else row["due_date"],
                user_id,
                task_id,
            ),
        )
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        return jsonify(
            {"error": "Another occurrence is already scheduled for that date"}
        ), 409
    if cursor.rowcount != 1:
        conn.close()
        return jsonify({"error": "Unable to reschedule occurrence"}), 409
    conn.commit()
    cursor.execute(
        task_select_sql() + "WHERE tasks.user_id = ? AND tasks.id = ?",
        (user_id, task_id),
    )
    updated = task_to_dict(cursor.fetchone())
    conn.close()
    return jsonify(updated)


@api.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    user_id = _authenticated_user_id()
    if not user_id:
        return _unauthorized()
    data = request.get_json(silent=True) or {}
    scope = str(data.get("scope", "this"))
    if scope not in {"this", "future", "series"}:
        return jsonify({"error": "Delete scope must be this, future, or series"}), 400
    conn = get_db()
    cursor = conn.cursor()
    row = _owned_task(cursor, user_id, task_id)
    if not row:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    if row["series_id"] and scope == "this":
        cursor.execute(
            "UPDATE tasks SET skipped = 1, completed = 0 WHERE user_id = ? AND id = ?",
            (user_id, task_id),
        )
        # If no rows updated (task was already completed), that's fine - still mark as preserved
    elif row["series_id"]:
        if scope == "future":
            occurrence_date = (
                row["occurrence_date"]
                or row["scheduled_date"]
                or datetime.now().date().isoformat()
            )
            stop_date = (parse_date(occurrence_date) - timedelta(days=1)).isoformat()
            cursor.execute(
                "SELECT recurrence_rule, start_date FROM task_series WHERE id = ? AND user_id = ?",
                (row["series_id"], user_id),
            )
            series = cursor.fetchone()
            if not series:
                conn.close()
                return jsonify({"error": "Task series not found"}), 404
            if stop_date < series["start_date"]:
                cursor.execute(
                    "UPDATE task_series SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
                    (row["series_id"], user_id),
                )
            else:
                rule = json.loads(series["recurrence_rule"])
                rule["end_condition"] = "date"
                rule["end_date"] = stop_date
                cursor.execute(
                    "UPDATE task_series SET end_date = ?, recurrence_rule = ?, updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = ? AND user_id = ?",
                    (stop_date, json.dumps(rule), row["series_id"], user_id),
                )
            cursor.execute(
                "DELETE FROM tasks WHERE user_id = ? AND series_id = ? AND completed = 0 "
                "AND COALESCE(occurrence_date, scheduled_date) >= ?",
                (user_id, row["series_id"], occurrence_date),
            )
        else:
            cursor.execute(
                "UPDATE task_series SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
                (row["series_id"], user_id),
            )
            cursor.execute(
                "DELETE FROM tasks WHERE user_id = ? AND series_id = ? AND completed = 0",
                (user_id, row["series_id"]),
            )
    else:
        cursor.execute(
            "DELETE FROM tasks WHERE user_id = ? AND id = ? AND completed = 0",
            (user_id, task_id),
        )
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Completed tasks are preserved"}), 409
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@api.route("/tasks/<int:task_id>/sessions", methods=["GET", "POST"])
def task_sessions(task_id):
    user_id = _authenticated_user_id()
    if not user_id:
        return _unauthorized()
    conn = get_db()
    cursor = conn.cursor()
    task = _owned_task(cursor, user_id, task_id)
    if not task:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    if request.method == "GET":
        cursor.execute(
            "SELECT id, client_session_id, started_at, ended_at, duration_seconds "
            "FROM focus_sessions WHERE user_id = ? AND task_id = ? ORDER BY started_at",
            (user_id, task_id),
        )
        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(sessions)

    data = request.get_json() or {}
    try:
        session_key = str(data.get("client_session_id", "")).strip()
        if not session_key or len(session_key) > 100:
            raise ValueError("A valid client session ID is required")
        started_at = datetime.fromisoformat(
            str(data.get("started_at", "")).replace("Z", "+00:00")
        )
        ended_at = datetime.fromisoformat(
            str(data.get("ended_at", "")).replace("Z", "+00:00")
        )
        study_date = parse_date(
            data.get("study_date") or started_at.date().isoformat()
        ).isoformat()
        duration = int(data.get("duration_seconds", 0))
        elapsed = int((ended_at - started_at).total_seconds())
        if started_at.tzinfo is None:
            started_at = started_at.astimezone()
        if ended_at.tzinfo is None:
            ended_at = ended_at.astimezone()
        if duration < 1 or duration > 86400 or elapsed < 0 or duration > elapsed + 1:
            raise ValueError("Focus session duration is invalid")
    except (TypeError, ValueError) as error:
        conn.close()
        return jsonify({"error": str(error) or "Invalid focus session"}), 400

    cursor.execute(
        "INSERT OR IGNORE INTO focus_sessions "
        "(user_id, task_id, client_session_id, started_at, ended_at, study_date, duration_seconds) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
            task_id,
            session_key,
            started_at.isoformat(),
            ended_at.isoformat(),
            study_date,
            duration,
        ),
    )
    inserted = cursor.rowcount == 1
    if inserted:
        cursor.execute(
            "UPDATE tasks SET actual_duration_seconds = actual_duration_seconds + ? WHERE user_id = ? AND id = ?",
            (duration, user_id, task_id),
        )
    conn.commit()
    cursor.execute(
        "SELECT id, client_session_id, started_at, ended_at, duration_seconds "
        "FROM focus_sessions WHERE user_id = ? AND client_session_id = ?",
        (user_id, session_key),
    )
    session = dict(cursor.fetchone())
    conn.close()
    return jsonify(
        {"session": session, "duplicate": not inserted}
    ), 201 if inserted else 200


@api.route("/calendar", methods=["GET"])
def get_calendar():
    user_id = _authenticated_user_id()
    if not user_id:
        return _unauthorized()
    try:
        start = parse_date(request.args.get("start"))
        end = parse_date(request.args.get("end"))
        if end < start or (end - start).days > 366:
            raise ValueError("Calendar range must be between 1 and 367 days")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    conn = get_db()
    cursor = conn.cursor()
    materialize_occurrences(cursor, user_id, start, end)
    cursor.execute(
        "SELECT scheduled_date, COUNT(*) AS total, SUM(completed) AS completed, SUM(skipped) AS skipped "
        "FROM tasks WHERE user_id = ? AND scheduled_date BETWEEN ? AND ? GROUP BY scheduled_date ORDER BY scheduled_date",
        (user_id, start.isoformat(), end.isoformat()),
    )
    events = [dict(row) for row in cursor.fetchall()]
    conn.commit()
    conn.close()
    return jsonify(events)


@api.route("/analytics", methods=["GET"])
def get_analytics():
    user_id = _authenticated_user_id()
    if not user_id:
        return _unauthorized()
    today = datetime.now().date()
    try:
        end = parse_date(request.args.get("end") or today.isoformat())
        start = parse_date(
            request.args.get("start") or (end - timedelta(days=6)).isoformat()
        )
        if end < start or (end - start).days > 366:
            raise ValueError("Analytics range must be between 1 and 367 days")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    conn = get_db()
    cursor = conn.cursor()
    materialize_occurrences(cursor, user_id, start, end)
    cursor.execute(
        "SELECT study_date, SUM(duration_seconds) AS study_seconds "
        "FROM focus_sessions WHERE user_id = ? AND study_date BETWEEN ? AND ? GROUP BY study_date",
        (user_id, start.isoformat(), end.isoformat()),
    )
    sessions_by_day = {
        row["study_date"]: row["study_seconds"] or 0 for row in cursor.fetchall()
    }
    cursor.execute(
        "SELECT substr(completed_at, 1, 10) AS completion_date, COUNT(*) AS completed "
        "FROM tasks WHERE user_id = ? AND completed = 1 AND completed_at IS NOT NULL "
        "AND substr(completed_at, 1, 10) BETWEEN ? AND ? GROUP BY substr(completed_at, 1, 10)",
        (user_id, start.isoformat(), end.isoformat()),
    )
    completed_by_day = {
        row["completion_date"]: row["completed"] for row in cursor.fetchall()
    }
    cursor.execute(
        "SELECT scheduled_date, COUNT(*) AS total, SUM(completed) AS completed, SUM(skipped) AS skipped FROM tasks "
        "WHERE user_id = ? AND scheduled_date BETWEEN ? AND ? GROUP BY scheduled_date",
        (user_id, start.isoformat(), end.isoformat()),
    )
    scheduled_by_day = {row["scheduled_date"]: dict(row) for row in cursor.fetchall()}

    cursor.execute(
        "SELECT tasks.task_list_id, SUM(focus_sessions.duration_seconds) AS study_seconds, "
        "COUNT(*) AS session_count, MIN(tasks.tag) AS tag "
        "FROM focus_sessions JOIN tasks ON tasks.id = focus_sessions.task_id "
        "WHERE focus_sessions.user_id = ? AND focus_sessions.study_date BETWEEN ? AND ? "
        "GROUP BY tasks.task_list_id ORDER BY study_seconds DESC",
        (user_id, start.isoformat(), end.isoformat()),
    )
    distribution_by_list = [dict(row) for row in cursor.fetchall()]
    cursor.execute(
        "SELECT focus_sessions.id, focus_sessions.task_id, focus_sessions.started_at, "
        "focus_sessions.duration_seconds, tasks.title, tasks.tag, tasks.task_list_id, "
        "tasks.completed, tasks.skipped, tasks.duration_minutes "
        "FROM focus_sessions JOIN tasks ON tasks.id = focus_sessions.task_id "
        "WHERE focus_sessions.user_id = ? AND focus_sessions.study_date BETWEEN ? AND ? "
        "ORDER BY focus_sessions.started_at DESC, focus_sessions.id DESC LIMIT 12",
        (user_id, start.isoformat(), end.isoformat()),
    )
    recent_sessions = [dict(row) for row in cursor.fetchall()]
    conn.commit()
    conn.close()

    days = []
    current = start
    while current <= end:
        key = current.isoformat()
        scheduled = scheduled_by_day.get(key, {})
        days.append(
            {
                "date": key,
                "study_seconds": sessions_by_day.get(key, 0),
                "completed_occurrences": completed_by_day.get(key, 0),
                "scheduled_completed_occurrences": scheduled.get("completed", 0) or 0,
                "scheduled_occurrences": scheduled.get("total", 0),
                "skipped_occurrences": scheduled.get("skipped", 0) or 0,
            }
        )
        current += timedelta(days=1)
    return jsonify(
        {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": days,
            "distribution_by_list": distribution_by_list,
            "recent_sessions": recent_sessions,
        }
    )


# USER STATS


@api.route("/stats", methods=["GET"])
def get_stats():
    user_id = _authenticated_user_id()
    if not user_id:
        return _unauthorized()
    today_date = datetime.now().date()
    today = today_date.isoformat()
    week_start = (today_date - timedelta(days=today_date.weekday())).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
    stats = cursor.fetchone()
    if not stats:
        # Keep the stats row in sync with the account so reads and writes agree
        # on the same source of truth instead of returning placeholder numbers.
        cursor.execute(
            "INSERT INTO user_stats (user_id, streak_days, focus_minutes_today, "
            "focus_minutes_week, focus_seconds_today, stats_date, focus_seconds_week, "
            "stats_week_start) VALUES (?, 1, 0, 0, 0, ?, 0, ?) "
            "ON CONFLICT(user_id) DO NOTHING",
            (user_id, today, week_start),
        )
        conn.commit()
        cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
        stats = cursor.fetchone()
    if stats and (
        stats["stats_date"] != today or stats["stats_week_start"] != week_start
    ):
        cursor.execute(
            "UPDATE user_stats SET "
            "focus_minutes_today = CASE WHEN stats_date = ? THEN focus_minutes_today ELSE 0 END, "
            "focus_seconds_today = CASE WHEN stats_date = ? THEN focus_seconds_today ELSE 0 END, "
            "focus_minutes_week = CASE WHEN stats_week_start = ? THEN focus_minutes_week ELSE 0 END, "
            "focus_seconds_week = CASE WHEN stats_week_start = ? THEN focus_seconds_week ELSE 0 END, "
            "stats_date = ?, stats_week_start = ? WHERE user_id = ?",
            (today, today, week_start, week_start, today, week_start, user_id),
        )
        conn.commit()
        cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
        stats = cursor.fetchone()

    cursor.execute(
        "SELECT COUNT(*) as total, SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as done FROM tasks WHERE user_id = ?",
        (user_id,),
    )
    counts = cursor.fetchone()
    conn.close()

    total_tasks = counts["total"] if counts else 0
    completed_tasks = counts["done"] if (counts and counts["done"]) else 0

    return jsonify(
        {
            "streak_days": stats["streak_days"] if stats else 0,
            "focus_minutes_today": stats["focus_minutes_today"] if stats else 0,
            "focus_seconds_today": stats["focus_seconds_today"] if stats else 0,
            "stats_date": stats["stats_date"] if stats else today,
            "focus_minutes_week": stats["focus_minutes_week"] if stats else 0,
            "focus_seconds_week": stats["focus_seconds_week"] if stats else 0,
            "stats_week_start": stats["stats_week_start"] if stats else week_start,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
        }
    )


@api.route("/stats/record", methods=["POST"])
def record_focus():
    user_id = _authenticated_user_id()
    if not user_id:
        return _unauthorized()
    data = request.get_json() or {}
    try:
        minutes = int(data.get("minutes", 0))
    except (TypeError, ValueError):
        minutes = 0
    try:
        seconds = int(data.get("seconds", minutes * 60))
    except (TypeError, ValueError):
        seconds = minutes * 60
    if seconds < 0:
        return jsonify({"error": "Study seconds cannot be negative"}), 400
    minutes = round(seconds / 60)
    if seconds > 0:
        today_date = datetime.now().date()
        today = today_date.isoformat()
        week_start = (today_date - timedelta(days=today_date.weekday())).isoformat()
        conn = get_db()
        cursor = conn.cursor()
        # Users may not have a stats row yet (older accounts, seeded demo data,
        # or a row removed by a reset). Upsert first so the update below always
        # has a row to write to and recorded focus time is never dropped.
        cursor.execute(
            "INSERT INTO user_stats (user_id, streak_days, focus_minutes_today, "
            "focus_minutes_week, focus_seconds_today, stats_date, focus_seconds_week, "
            "stats_week_start) VALUES (?, 3, 0, 0, 0, ?, 0, ?) "
            "ON CONFLICT(user_id) DO NOTHING",
            (user_id, today, week_start),
        )
        cursor.execute(
            "UPDATE user_stats SET "
            "focus_seconds_today = CASE WHEN stats_date = ? THEN COALESCE(focus_seconds_today, 0) + ? ELSE ? END, "
            "focus_minutes_today = CAST((CASE WHEN stats_date = ? THEN COALESCE(focus_seconds_today, 0) + ? ELSE ? END + 30) / 60 AS INTEGER), "
            "focus_seconds_week = CASE WHEN stats_week_start = ? THEN COALESCE(focus_seconds_week, 0) + ? ELSE ? END, "
            "focus_minutes_week = CAST((CASE WHEN stats_week_start = ? THEN COALESCE(focus_seconds_week, 0) + ? ELSE ? END + 30) / 60 AS INTEGER), "
            "stats_date = ?, stats_week_start = ? WHERE user_id = ?",
            (
                today,
                seconds,
                seconds,
                today,
                seconds,
                seconds,
                week_start,
                seconds,
                seconds,
                week_start,
                seconds,
                seconds,
                today,
                week_start,
                user_id,
            ),
        )
        conn.commit()
        conn.close()
    return jsonify({"success": True})


# YOUTUBE PLAYLIST & TRACK PARSER
@api.route("/youtube/playlist", methods=["GET"])
def get_youtube_playlist():
    import json
    import re
    import urllib.request
    import xml.etree.ElementTree as ET

    playlist_id = request.args.get("playlist_id", "").strip()
    raw_url = request.args.get("url", "").strip()

    if not playlist_id and raw_url:
        m = re.search(r"[?&]list=([^&#]+)", raw_url)
        if m:
            playlist_id = m.group(1)

    if not playlist_id:
        return jsonify({"error": "No playlist ID provided"}), 400

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    youtube_user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    playlist_title = "YouTube Playlist"
    tracks = []
    feed_error = None

    try:
        feed_url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
        req = urllib.request.Request(
            feed_url, headers={"User-Agent": "Mozilla/5.0 FocusFlow/1.0"}
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        feed_title = root.find("atom:title", ns)
        if feed_title is not None and feed_title.text:
            playlist_title = feed_title.text

        for entry in root.findall("atom:entry", ns):
            v_id_el = entry.find("yt:videoId", ns)
            title_el = entry.find("atom:title", ns)
            author_el = entry.find("atom:author/atom:name", ns)
            media_thumb = entry.find("media:group/media:thumbnail", ns)

            if (
                v_id_el is None
                or not v_id_el.text
                or title_el is None
                or not title_el.text
            ):
                continue

            video_id = v_id_el.text
            tracks.append(
                {
                    "id": f"yt-{video_id}-{len(tracks)}",
                    "videoId": video_id,
                    "title": title_el.text,
                    "artist": author_el.text
                    if author_el is not None and author_el.text
                    else "YouTube",
                    "source": "YouTube",
                    "url": f"https://www.youtube.com/watch?v={video_id}&list={playlist_id}",
                    "cover": (
                        media_thumb.attrib.get("url")
                        if media_thumb is not None
                        else f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                    ),
                    "duration": "YouTube",
                    "tag": "YouTube",
                    "isFavorite": False,
                }
            )
    except Exception as e:
        feed_error = str(e)

    try:
        page_url = f"https://www.youtube.com/playlist?list={playlist_id}"
        req = urllib.request.Request(
            page_url,
            headers={"User-Agent": youtube_user_agent},
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            page_html = response.read().decode("utf-8", errors="replace")

        markers = ('"ytInitialData":', "var ytInitialData =")
        marker_pos = -1
        marker = ""
        for candidate in markers:
            candidate_pos = page_html.find(candidate)
            if candidate_pos >= 0 and (marker_pos < 0 or candidate_pos < marker_pos):
                marker_pos = candidate_pos
                marker = candidate
        if marker_pos < 0:
            raise ValueError("YouTube did not provide playlist data")

        decoder = json.JSONDecoder()
        data_start = marker_pos + len(marker)
        initial_data, _ = decoder.raw_decode(page_html[data_start:].lstrip())

        video_ids = {track["videoId"] for track in tracks}

        def get_text(value):
            if isinstance(value, dict):
                if isinstance(value.get("content"), str):
                    return value["content"]
                if isinstance(value.get("simpleText"), str):
                    return value["simpleText"]
                runs = value.get("runs")
                if isinstance(runs, list):
                    return "".join(
                        run.get("text", "") for run in runs if isinstance(run, dict)
                    )
            if isinstance(value, str):
                return value
            return ""

        def add_track(video_id, title, artist="YouTube", thumbnails=None):
            if not video_id or not title or video_id in video_ids:
                return

            video_ids.add(video_id)
            thumbnails = thumbnails or []
            thumb = (
                thumbnails[-1].get("url")
                if thumbnails and isinstance(thumbnails[-1], dict)
                else f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            )
            tracks.append(
                {
                    "id": f"yt-{video_id}-{len(tracks)}",
                    "videoId": video_id,
                    "title": title,
                    "artist": artist or "YouTube",
                    "source": "YouTube",
                    "url": f"https://www.youtube.com/watch?v={video_id}&list={playlist_id}",
                    "cover": thumb,
                    "duration": "YouTube",
                    "tag": "YouTube",
                    "isFavorite": False,
                }
            )

        def collect_video_entries(value):
            if isinstance(value, dict):
                renderer = value.get("playlistVideoRenderer")
                if isinstance(renderer, dict):
                    video_id = renderer.get("videoId")
                    title = get_text(renderer.get("title"))
                    artist = get_text(renderer.get("shortBylineText"))
                    thumbnails = renderer.get("thumbnail", {}).get("thumbnails", [])
                    add_track(video_id, title, artist, thumbnails)

                lockup = value.get("lockupViewModel")
                if (
                    isinstance(lockup, dict)
                    and lockup.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO"
                ):
                    metadata = lockup.get("metadata", {}).get(
                        "lockupMetadataViewModel", {}
                    )
                    content_metadata = metadata.get("metadata", {}).get(
                        "contentMetadataViewModel", {}
                    )
                    metadata_rows = content_metadata.get("metadataRows", [])
                    artist = ""
                    if metadata_rows:
                        first_row = metadata_rows[0].get("metadataParts", [])
                        if first_row:
                            artist = get_text(first_row[0].get("text"))

                    image = (
                        lockup.get("contentImage", {})
                        .get("thumbnailViewModel", {})
                        .get("image", {})
                    )
                    thumbnails = image.get("sources", [])
                    add_track(
                        lockup.get("contentId"),
                        get_text(metadata.get("title")),
                        artist,
                        thumbnails,
                    )

                for child in value.values():
                    collect_video_entries(child)
            elif isinstance(value, list):
                for child in value:
                    collect_video_entries(child)

        header = initial_data.get("header", {}).get("pageHeaderRenderer", {})
        playlist_title = header.get("pageTitle") or playlist_title

        contents = initial_data.get("contents", {}).get(
            "twoColumnBrowseResultsRenderer", {}
        )
        for tab in contents.get("tabs", []):
            tab_content = tab.get("tabRenderer", {}).get("content", {})
            collect_video_entries(tab_content)
    except Exception as e:
        error = str(e)
        if feed_error:
            error = f"Playlist feed failed ({feed_error}); page import failed ({error})"
        return jsonify(
            {
                "error": error,
                "partial_count": len(tracks),
            }
        ), 502

    if not tracks:
        return jsonify({"error": "The playlist is private, empty, or unavailable"}), 502

    return jsonify(
        {
            "playlist_id": playlist_id,
            "title": playlist_title,
            "tracks": tracks,
            "count": len(tracks),
        }
    )


@api.route("/youtube/track", methods=["GET"])
def get_youtube_track():
    import json
    import re
    import urllib.request

    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return jsonify({"error": "No url provided"}), 400

    try:
        oembed_url = f"https://www.youtube.com/oembed?url={raw_url}&format=json"
        req = urllib.request.Request(
            oembed_url, headers={"User-Agent": "Mozilla/5.0 FocusFlow/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))

        video_id = ""
        m = re.search(r"(?:v=|youtu\.be/|/live/|/embed/)([^&#?]+)", raw_url)
        if m:
            video_id = m.group(1)

        cover = (
            f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            if video_id
            else data.get("thumbnail_url", "")
        )

        return jsonify(
            {
                "title": data.get("title", "YouTube Track"),
                "artist": data.get("author_name", "YouTube"),
                "videoId": video_id,
                "cover": cover,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
