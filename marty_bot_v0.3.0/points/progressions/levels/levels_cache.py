from bisect import bisect_right

from points.progressions.levels.levels_config import (
    MIN_LEVEL,
    INITIAL_CACHED_LEVELS,
)

from points.progressions.levels.levels_calculations import (
    calculate_level_cost,
)


# ==================================================
# LEVEL THRESHOLD CACHE
# ==================================================


# Each value is the total number of points
# required to START a level.
#
# The list index determines the level.
#
# Example:
#
# LEVEL_THRESHOLDS = [
#     0,      # Level 1
#     47,     # Level 2
#     94,     # Level 3
#     142,    # Level 4
# ]

LEVEL_THRESHOLDS = [
    0,
]


# ==================================================
# CACHE CREATION
# ==================================================


def _cache_next_threshold():
    """
    Generate the starting point threshold
    for the next uncached level.
    """

    # The final threshold currently stored
    # belongs to this level.
    current_level = (
        MIN_LEVEL
        + len(LEVEL_THRESHOLDS)
        - 1
    )

    current_start_points = (
        LEVEL_THRESHOLDS[-1]
    )

    points_required = calculate_level_cost(
        current_level
    )

    next_start_points = (
        current_start_points
        + points_required
    )

    LEVEL_THRESHOLDS.append(
        next_start_points
    )


# ==================================================
# ENSURE LEVEL IS CACHED
# ==================================================


def ensure_level_cached(
    level: int,
):
    """
    Make sure the complete point range for
    a level exists in the cache.

    To know the cost of a level, both its
    starting threshold and the next level's
    threshold must be cached.
    """

    if level < MIN_LEVEL:
        level = MIN_LEVEL

    required_thresholds = (
        level
        - MIN_LEVEL
        + 2
    )

    while (
        len(LEVEL_THRESHOLDS)
        < required_thresholds
    ):
        _cache_next_threshold()


# ==================================================
# INITIALIZE CACHE
# ==================================================


def initialize_level_cache(
    through_level: int = INITIAL_CACHED_LEVELS,
):
    """
    Precalculate level thresholds through
    the configured initial level.

    Levels remain unlimited. The cache
    automatically expands when necessary.
    """

    if through_level < MIN_LEVEL:
        raise ValueError(
            "through_level must be at least 1."
        )

    ensure_level_cached(
        through_level
    )

    print(
        f"Level cache initialized through "
        f"Level {through_level}."
    )


# ==================================================
# LEVEL START POINTS
# ==================================================


def get_level_start_points(
    level: int,
) -> int:
    """
    Return the total points required
    to begin a particular level.
    """

    if level < MIN_LEVEL:
        level = MIN_LEVEL

    ensure_level_cached(
        level
    )

    index = (
        level - MIN_LEVEL
    )

    return LEVEL_THRESHOLDS[
        index
    ]


# ==================================================
# LEVEL COST
# ==================================================


def get_cached_level_cost(
    level: int,
) -> int:
    """
    Return the points required to advance
    from a level to the next level.

    The cost is calculated from the difference
    between two adjacent thresholds.
    """

    if level < MIN_LEVEL:
        level = MIN_LEVEL

    ensure_level_cached(
        level
    )

    index = (
        level - MIN_LEVEL
    )

    current_threshold = (
        LEVEL_THRESHOLDS[
            index
        ]
    )

    next_threshold = (
        LEVEL_THRESHOLDS[
            index + 1
        ]
    )

    return (
        next_threshold
        - current_threshold
    )


# ==================================================
# FIND LEVEL FROM POINTS
# ==================================================


def find_level_from_points(
    points: int,
) -> int:
    """
    Determine a user's level from their
    total progression points.

    The cache automatically expands if the
    point total exceeds the cached range.

    Once enough thresholds exist, binary search
    is used to find the user's level.
    """

    if points <= 0:
        return MIN_LEVEL

    # ------------------------------------------
    # EXTEND CACHE IF NECESSARY
    # ------------------------------------------

    # The last threshold represents the start
    # of the next known level.
    #
    # If the user has reached or exceeded it,
    # generate another threshold until their
    # complete level range is known.

    while (
        points
        >= LEVEL_THRESHOLDS[-1]
    ):
        _cache_next_threshold()

    # ------------------------------------------
    # BINARY SEARCH
    # ------------------------------------------

    index = (
        bisect_right(
            LEVEL_THRESHOLDS,
            points,
        )
        - 1
    )

    return (
        MIN_LEVEL
        + index
    )