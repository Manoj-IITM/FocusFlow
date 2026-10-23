from calendar import monthrange
from datetime import date, timedelta

FREQUENCIES = {"none", "daily", "weekly", "monthly", "custom"}
UNITS = {"days", "weeks", "months"}
END_CONDITIONS = {"never", "date", "count"}


def parse_date(value):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as error:
        raise ValueError("Dates must use YYYY-MM-DD format") from error


def normalize_recurrence(rule, start_date):
    start = parse_date(start_date)
    if not isinstance(rule, dict):
        raise ValueError("Repeat settings must be an object")

    frequency = str(rule.get("frequency", "none")).lower()
    if frequency not in FREQUENCIES:
        raise ValueError("Unsupported repeat frequency")
    if frequency == "none":
        return {"frequency": "none", "end_condition": "never"}

    try:
        interval = int(rule.get("interval", 1))
    except (TypeError, ValueError) as error:
        raise ValueError("Repeat interval must be a whole number") from error
    if interval < 1 or interval > 366:
        raise ValueError("Repeat interval must be between 1 and 366")

    unit = rule.get("unit", "days" if frequency == "daily" else "weeks")
    if frequency == "custom":
        unit = str(unit).lower()
        if unit not in UNITS:
            raise ValueError("Custom repeat unit must be days, weeks, or months")
    elif frequency == "daily":
        unit = "days"
    elif frequency == "weekly":
        unit = "weeks"
    else:
        unit = "months"

    weekdays = rule.get("weekdays", [start.weekday()])
    if frequency == "weekly" or (frequency == "custom" and unit == "weeks"):
        if not isinstance(weekdays, list) or not weekdays:
            raise ValueError("Choose at least one weekday")
        try:
            weekdays = sorted({int(day) for day in weekdays})
        except (TypeError, ValueError) as error:
            raise ValueError("Weekdays must be numbers from 0 to 6") from error
        if any(day < 0 or day > 6 for day in weekdays):
            raise ValueError("Weekdays must be numbers from 0 to 6")
    else:
        weekdays = []

    try:
        month_day = int(rule.get("day_of_month", start.day))
    except (TypeError, ValueError) as error:
        raise ValueError("Monthly day must be between 1 and 31") from error
    if month_day < 1 or month_day > 31:
        raise ValueError("Monthly day must be between 1 and 31")

    end_condition = str(rule.get("end_condition", "never")).lower()
    if end_condition not in END_CONDITIONS:
        raise ValueError("Unsupported repeat end condition")
    end_date = None
    occurrence_limit = None
    if end_condition == "date":
        end_date = parse_date(rule.get("end_date"))
        if end_date < start:
            raise ValueError("Repeat end date cannot be before its start date")
    elif end_condition == "count":
        try:
            occurrence_limit = int(rule.get("occurrence_count"))
        except (TypeError, ValueError) as error:
            raise ValueError("Occurrence count must be a whole number") from error
        if occurrence_limit < 1 or occurrence_limit > 10000:
            raise ValueError("Occurrence count must be between 1 and 10000")

    return {
        "frequency": frequency,
        "unit": unit,
        "interval": interval,
        "weekdays": weekdays,
        "day_of_month": month_day,
        "end_condition": end_condition,
        "end_date": end_date.isoformat() if end_date else None,
        "occurrence_count": occurrence_limit,
    }


def _matches_base_rule(rule, start, candidate):
    if candidate < start:
        return False
    frequency = rule["frequency"]
    if frequency == "none":
        return candidate == start

    unit = rule["unit"]
    interval = rule["interval"]
    day_delta = (candidate - start).days
    if unit == "days":
        return day_delta % interval == 0
    if unit == "weeks":
        start_week = start - timedelta(days=start.weekday())
        candidate_week = candidate - timedelta(days=candidate.weekday())
        week_delta = (candidate_week - start_week).days // 7
        return week_delta % interval == 0 and candidate.weekday() in rule["weekdays"]

    month_delta = (candidate.year - start.year) * 12 + candidate.month - start.month
    target_day = min(
        rule["day_of_month"], monthrange(candidate.year, candidate.month)[1]
    )
    return month_delta % interval == 0 and candidate.day == target_day


def occurrence_dates(
    start_date,
    end_date,
    rule,
    end_condition=None,
    end_date_limit=None,
    occurrence_limit=None,
):
    start = parse_date(start_date)
    end = parse_date(end_date)
    normalized = normalize_recurrence(rule, start)
    if end < start:
        return

    condition = end_condition or normalized["end_condition"]
    date_limit = (
        parse_date(end_date_limit)
        if end_date_limit
        else (parse_date(normalized["end_date"]) if normalized["end_date"] else None)
    )
    count_limit = occurrence_limit or normalized["occurrence_count"]
    if condition == "date" and date_limit is None:
        raise ValueError("An end date is required")
    if condition == "count" and (count_limit is None or int(count_limit) < 1):
        raise ValueError("A positive occurrence count is required")

    final_day = min(end, date_limit) if condition == "date" and date_limit else end
    occurrence_number = 0
    current = start
    while current <= final_day:
        if _matches_base_rule(normalized, start, current):
            occurrence_number += 1
            if condition == "count" and occurrence_number > int(count_limit):
                break
            yield current
        current += timedelta(days=1)


def is_occurrence_date(start_date, candidate_date, rule):
    candidate = parse_date(candidate_date)
    return any(
        occurrence == candidate
        for occurrence in occurrence_dates(start_date, candidate, rule)
    )
