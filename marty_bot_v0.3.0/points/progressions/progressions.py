from points.progressions.levels.levels import (
    get_level_from_points,
)

from points.progressions.ranks.ranks import (
    get_rank_for_level,
)


# ==================================================
# PROGRESSION CHANGE
# ==================================================


def get_progression_change(
    old_points: int,
    new_points: int,
) -> dict:
    """
    Compare a user's progression before
    and after a point change.
    """

    old_level = get_level_from_points(
        old_points
    )

    new_level = get_level_from_points(
        new_points
    )

    old_rank = get_rank_for_level(
        old_level
    )

    new_rank = get_rank_for_level(
        new_level
    )

    return {
        "leveled_up": (
            new_level > old_level
        ),
        "old_level": old_level,
        "new_level": new_level,

        "ranked_up": (
            new_rank["tier"]
            > old_rank["tier"]
        ),
        "old_rank": old_rank,
        "new_rank": new_rank,
    }


# ==================================================
# COMBINE PROGRESSION CHANGES
# ==================================================


def combine_progression_changes(
    *progressions: dict,
) -> dict:
    """
    Combine multiple consecutive point awards
    into one progression result.

    This prevents multiple related awards from
    creating duplicate level-up or rank-up
    notifications.

    Example:

    Activity:
        +1 normal Activity point
        +40 hidden weekly streak bonus

    These can be treated as one overall
    progression event.
    """

    if not progressions:
        raise ValueError(
            "At least one progression "
            "must be provided."
        )

    first_progression = (
        progressions[0]
    )

    final_progression = (
        progressions[-1]
    )

    old_level = first_progression[
        "old_level"
    ]

    new_level = final_progression[
        "new_level"
    ]

    old_rank = first_progression[
        "old_rank"
    ]

    new_rank = final_progression[
        "new_rank"
    ]

    return {
        "leveled_up": (
            new_level > old_level
        ),
        "old_level": old_level,
        "new_level": new_level,

        "ranked_up": (
            new_rank["tier"]
            > old_rank["tier"]
        ),
        "old_rank": old_rank,
        "new_rank": new_rank,
    }