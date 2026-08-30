from datetime import date, timedelta

import aiosqlite

from data.database import DB_PATH

from points.time_helpers import (
    get_current_week_start_chicago,
)

from points.mechanics.activity.activity_config import (
    ACTIVITY_STREAK_BONUS_PER_WEEK,
    ACTIVITY_STREAK_MAX_BONUS,
)


# ==================================================
# PROCESS ACTIVITY STREAK
# ==================================================


async def process_activity_streak(
    guild_id: int,
    user_id: int,
) -> int:
    """
    Process a user's hidden weekly Activity streak.

    Returns the number of bonus points that should
    be awarded.

    Returns 0 if the user's weekly streak has
    already been processed this week.
    """

    current_week = (
        get_current_week_start_chicago()
    )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            SELECT
                current_streak,
                last_active_week
            FROM activity_streaks
            WHERE guild_id = ?
              AND user_id = ?
            """,
            (
                guild_id,
                user_id,
            ),
        )

        row = await cursor.fetchone()

        # --------------------------------------------------
        # EXISTING STREAK
        # --------------------------------------------------

        if row is not None:

            current_streak = int(
                row[0]
            )

            last_active_week = (
                date.fromisoformat(
                    row[1]
                )
            )

            # The streak has already been processed
            # during the current week.
            if last_active_week == current_week:
                return 0

            previous_week = (
                current_week
                - timedelta(days=7)
            )

            # User was active last week.
            if (
                last_active_week
                == previous_week
            ):
                current_streak += 1

            # User missed at least one full week.
            else:
                current_streak = 1

        # --------------------------------------------------
        # NEW STREAK
        # --------------------------------------------------

        else:
            current_streak = 1

        # --------------------------------------------------
        # CALCULATE BONUS
        # --------------------------------------------------

        streak_bonus = min(
            (
                current_streak
                * ACTIVITY_STREAK_BONUS_PER_WEEK
            ),
            ACTIVITY_STREAK_MAX_BONUS,
        )

        # --------------------------------------------------
        # SAVE STREAK
        # --------------------------------------------------

        await db.execute(
            """
            INSERT INTO activity_streaks (
                guild_id,
                user_id,
                current_streak,
                last_active_week
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                current_streak = excluded.current_streak,
                last_active_week = excluded.last_active_week
            """,
            (
                guild_id,
                user_id,
                current_streak,
                current_week.isoformat(),
            ),
        )

        await db.commit()

    return streak_bonus