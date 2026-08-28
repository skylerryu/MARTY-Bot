from points.points_operations.add_points import (
    add_points,
)

from points.progressions.progressions import (
    combine_progression_changes,
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
    Award all points associated with completing
    a Question of the Day.

    This includes:
    - Base QoTD points
    - QoTD streak bonus

    The two point transactions are combined into
    one progression result so a student receives
    only one level/rank progression event.
    """

    # ==================================================
    # BASE QOTD POINTS
    # =================================================