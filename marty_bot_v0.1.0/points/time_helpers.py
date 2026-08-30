from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone,
)
from zoneinfo import ZoneInfo


# ==================================================
# TIME ZONE
# ==================================================


CHICAGO_TIMEZONE = ZoneInfo(
    "America/Chicago"
)


# ==================================================
# CURRENT CHICAGO DATETIME
# ==================================================


def get_current_chicago_datetime() -> datetime:
    """
    Return the current date and time in
    America/Chicago.
    """

    return datetime.now(
        CHICAGO_TIMEZONE
    )


# ==================================================
# CURRENT CHICAGO DATE
# ==================================================


def get_current_chicago_date() -> date:
    """
    Return today's calendar date in
    America/Chicago time.
    """

    return (
        get_current_chicago_datetime()
        .date()
    )


# ==================================================
# CHICAGO DATETIME FOR DATE
# ==================================================


def get_chicago_datetime(
    calendar_date: date,
    hour: int = 0,
    minute: int = 0,
) -> datetime:
    """
    Build an America/Chicago datetime for a
    particular calendar date and clock time.
    """

    return datetime.combine(
        calendar_date,
        time(
            hour=hour,
            minute=minute,
        ),
        tzinfo=CHICAGO_TIMEZONE,
    )


# ==================================================
# CURRENT CHICAGO WEEK
# ==================================================


def get_current_week_start_chicago() -> date:
    """
    Return the Monday that begins the current
    Chicago calendar week.
    """

    now_chicago = (
        get_current_chicago_datetime()
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
    """

    now_chicago = (
        get_current_chicago_datetime()
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