from datetime import date, timedelta

import aiosqlite

from data.user_db import (
    USER_DB_PATH,
)

from points.mechanics.question_of_the_day.qotd_config import (
    QOTD_STREAK_DAY_1_BONUS,
    QOTD_STREAK_DAYS_2_TO_3_BONUS,
    QOTD_STREAK_DAYS_4_TO_6_BONUS,
    QOTD_STREAK_DAY_7_PLUS_BONUS,
)


# ==================================================
# GET STREAK
# ==================================================


async def get_qotd_streak(
    guild_id: int,
    user_id: int,
) -> tuple[int, date | None]:
    """
    Return a user's current QoTD streak and
    the date of their most recent completion.

    A user with no existing streak returns:

        (0, None)
    """

    async with aiosqlite.connect(
        USER_DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            SELECT
                current_streak,
                last_completion_date
            FROM qotd_streaks
            WHERE guild_id = ?
              AND user_id = ?
            """,
            (
                guild_id,
                user_id,
            ),
        )

        row = await cursor.fetchone()

    if row is None:
        return (
            0,
            None,
        )

    current_streak = int(
        row[0]
    )

    last_completion_date = (
        date.fromisoformat(
            row[1]
        )
    )

    return (
        current_streak,
        last_completion_date,
    )


# ==================================================
# CALCULATE NEXT STREAK
# ==================================================


def calculate_next_qotd_streak(
    current_streak: int,
    last_completion_date: date | None,
    completion_date: date,
) -> int:
    """
    Calculate the streak that should result
    from completing a QoTD on completion_date.
    """

    if last_completion_date is None:
        return 1

    if (
        last_completion_date
        == completion_date
    ):
        return current_streak

    previous_day = (
        completion_date
        - timedelta(days=1)
    )

    if (
        last_completion_date
        == previous_day
    ):
        return current_streak + 1

    return 1


# ==================================================
# STREAK BONUS
# ==================================================


def get_qotd_streak_bonus(
    streak_days: int,
) -> int:

    if streak_days <= 0:
        return 0

    if streak_days == 1:
        return (
            QOTD_STREAK_DAY_1_BONUS
        )

    if streak_days <= 3:
        return (
            QOTD_STREAK_DAYS_2_TO_3_BONUS
        )

    if streak_days <= 6:
        return (
            QOTD_STREAK_DAYS_4_TO_6_BONUS
        )

    return (
        QOTD_STREAK_DAY_7_PLUS_BONUS
    )


# ==================================================
# UPDATE STREAK
# ==================================================


async def update_qotd_streak(
    guild_id: int,
    user_id: int,
    streak_days: int,
    completion_date: date,
):

    async with aiosqlite.connect(
        USER_DB_PATH
    ) as db:

        await db.execute(
            """
            INSERT INTO qotd_streaks (
                guild_id,
                user_id,
                current_streak,
                last_completion_date
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                current_streak =
                    excluded.current_streak,

                last_completion_date =
                    excluded.last_completion_date
            """,
            (
                guild_id,
                user_id,
                streak_days,
                completion_date.isoformat(),
            ),
        )

        await db.commit()
