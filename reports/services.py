from datetime import datetime


def parse_date_param(value):
    """Parse a ``YYYY-MM-DD`` query-string value into a ``date``.

    Never trusts the browser: an empty/missing value is simply "no
    filter" (returns ``(None, None)``); a malformed value is dropped
    rather than raising, and a short message is returned so the view can
    surface it, instead of letting an invalid format break the page.
    """
    if not value:
        return None, None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date(), None
    except (ValueError, TypeError):
        return None, f"Fecha inválida: «{value}». Se ignoró ese filtro."


def format_average_resolution(duration):
    """Human-readable average resolution time, or ``None`` if there is
    no data (no ticket in the filtered set has actually been resolved).

    Unit: hours, or "days + hours" once the average reaches a full day,
    so the number stays easy to read regardless of scale.
    """
    if duration is None:
        return None
    total_hours = duration.total_seconds() / 3600
    days, hours = divmod(total_hours, 24)
    days = int(days)
    if days > 0:
        day_word = "día" if days == 1 else "días"
        return f"{days} {day_word} y {hours:.1f} horas"
    return f"{total_hours:.1f} horas"
