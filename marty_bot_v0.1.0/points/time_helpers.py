from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


# ==================================================
# TIME ZONE
# ==================================================


CHICAGO_TIMEZONE = ZoneInfo(
    "America/Chicago"
)


# ==================================================
# CURRENT CHICAGO DATE
# ==================================================


def get_current_chicago_date() -> date:
    """
    Return today's calendar date in
    America/Chicago time.
    """

    return datetime.now(
        CHICAGO_TIMEZONE
    ).date()


# ==================================================
# CURRENT CHICAGO WEEK
# ==================================================


def get_current_week_start_chicago() -> date:
    """
    Return the Monday that begins the current
    Chicago calendar week.
    """

    now_chicago = datetime.now(
        CHICAGO_TIMEZONE
    )

    monday_chicago = (
        now_chicago
        - timedelta(
            days=now_chicago.weekday()
        )
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    return monday_chicago.date()


# ==================================================
# CURRENT CHICAGO WEEK AS UTC
# ==================================================


def get_current_week_start_utc() -> str:
    """
    Return the beginning of the current Chicago
    calendar week converted to UTC.

    This is useful when comparing Chicago-based
    weekly activity against SQLite timestamps,
    which are stored in UTC.
    """

    now_chicago = datetime.now(
        CHICAGO_TIMEZONE
    )

    monday_chicago = (
        now_chicago
        - timedelta(
            days=now_chicago.weekday()
        )
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    monday_utc = monday_chicago.astimezone(
        timezone.utc
    )

    return monday_utc.strftime(
        "%Y-%m-%d %H:%M:%S"
    )