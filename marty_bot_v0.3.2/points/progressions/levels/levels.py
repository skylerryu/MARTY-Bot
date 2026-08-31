from points.progressions.levels.levels_config import (
    MIN_LEVEL,
)

from points.progressions.levels.levels_cache import (
    initialize_level_cache as _initialize_level_cache,
    get_level_start_points,
    get_cached_level_cost,
    find_level_from_points,
)


# ==================================================
# INITIALIZE LEVEL SYSTEM
# ==================================================


def initialize_level_cache():
    """
    Precalculate the initial level threshold cache.
    """

    _initialize_level_cache()


# ==================================================
# POINTS REQUIRED FOR NEXT LEVEL
# ==================================================


def get_points_required_for_next_level(
    level: int,
) -> int:
    """
    Return the number of points required
    to advance from this level to the next.
    """

    return get_cached_level_cost(
        level
    )


# ==================================================
# TOTAL POINTS REQUIRED FOR LEVEL
# ==================================================


def get_total_points_required_for_level(
    level: int,
) -> int:
    """
    Return the total points required
    to reach a particular level.

    Level 1 begins at 0 points.
    """

    if level <= MIN_LEVEL:
        return 0

    return get_level_start_points(
        level
    )


# ==================================================
# POINTS → LEVEL
# ==================================================


def get_level_from_points(
    points: int,
) -> int:
    """
    Determine a user's current level
    from their total progression points.
    """

    return find_level_from_points(
        points
    )


# ==================================================
# LEVEL PROGRESS
# ==================================================


def get_level_progress(
    points: int,
) -> dict:
    """
    Return information about the user's
    progress through their current level.
    """

    level = get_level_from_points(
        points
    )

    level_start_points = (
        get_level_start_points(
            level
        )
    )

    points_required = (
        get_cached_level_cost(
            level
        )
    )

    points_into_level = max(
        0,
        points - level_start_points,
    )

    points_remaining = max(
        0,
        points_required
        - points_into_level,
    )

    progress_percent = (
        points_into_level
        / points_required
        * 100
    )

    return {
        "level": level,
        "points_into_level": points_into_level,
        "points_required": points_required,
        "points_remaining": points_remaining,
        "progress_percent": progress_percent,
    }