from points.points_operations.add_points import (
    add_points,
)

from points.mechanics.question_of_the_day.qotd_config import (
    QOTD_CORRECT_POINTS,
)


# ==================================================
# AWARD QOTD POINTS
# ==================================================


async def award_qotd_points(
    qotd_id: int,
    guild_id: int,
    user_id: int,
    username: str,
    streak_bonus: int,
) -> dict:
    """
    Award all points associated with correctly
    completing a Question of the Day.

    The base QoTD points and streak bonus are
    awarded as one point transaction.

    This gives M.A.R.T.Y. one progression result
    and prevents duplicate level/rank notifications.

    source_key makes the reward idempotent, so
    the same QoTD cannot award points twice to
    the same user.
    """

    if streak_bonus < 0:

        raise ValueError(
            "QoTD streak bonus cannot "
            "be negative."
        )


    # ==================================================
    # TOTAL POINTS
    # ==================================================


    total_points = (
        QOTD_CORRECT_POINTS
        + streak_bonus
    )


    # ==================================================
    # UNIQUE SOURCE KEY
    # ==================================================


    source_key = (
        f"qotd:{qotd_id}:correct"
    )


    # ==================================================
    # AWARD POINTS
    # ==================================================


    progression = await add_points(
        guild_id=guild_id,
        user_id=user_id,
        amount=total_points,
        reason="Question of the Day",
        username=username,
        source_key=source_key,
    )


    # ==================================================
    # RETURN RESULT
    # ==================================================


    return {
        "base_points": (
            QOTD_CORRECT_POINTS
        ),
        "streak_bonus": (
            streak_bonus
        ),
        "total_points": (
            progression[
                "points_awarded"
            ]
        ),
        "progression": (
            progression
        ),
    }
