"""Date parsing for the formats we see: ISO, 'YYYY-MM', and RFC-2822 (Tavily news, e.g. 'Mon, 03 Nov 2025 10:00:00 GMT')."""
from datetime import date, datetime
from email.utils import parsedate_to_datetime


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    v = value.strip()
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    try:
        return datetime.strptime(v, "%Y-%m").date()
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(v).date()
    except (TypeError, ValueError, IndexError):
        return None


def age_days(value: str | None, today: date | None = None) -> int | None:
    d = parse_date(value)
    return None if d is None else ((today or date.today()) - d).days
