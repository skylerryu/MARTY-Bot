from points.progressions.levels.levels_config import (
    MIN_LEVEL,
    WITHIN_RANK_COST_INCREASE,
    RANK_COST_GROWTH_RATE,
    TARGET_RANK_TIER,
    TARGET_RANK_START_POINTS,
)

from points.progressions.ranks.ranks import (
    RANKS,
    get_rank_for_level,
)


# ==================================================
# RANK BASE MULTIPLIERS
# ==================================================


def _generate_rank_base_multipliers() -> dict:
    """
    Generate the starting cost multiplier
    for each rank.

    Each new rank begins at a fixed percentage
    above the FINAL level cost of the previous rank.

    This guarantees that level costs never decrease
    when a user ranks up.
    """

    rank_base_multipliers = {}

    current_base_multiplier = 1.0

    for rank in RANKS:

        tier = rank["tier"]

        rank_base_multipliers[
            tier
        ] = current_base_multiplier

        end_level = rank["end_level"]

        # The final rank is unlimited, so there
        # is no following rank to calculate.
        if end_level is None:
            break

        levels_into_rank_at_end = (
            end_level
            - rank["start_level"]
        )

        # Cost multiplier of the final level
        # inside the current rank.
        final_level_multiplier = (
            current_base_multiplier
            * (
                1
                + (
                    WITHIN_RANK_COST_INCREASE
                    * levels_into_rank_at_end
                )
            )
        )

        # The next rank begins above the final
        # level cost of this rank.
        current_base_multiplier = (
            final_level_multiplier
            * RANK_COST_GROWTH_RATE
        )

    return rank_base_multipliers


RANK_BASE_MULTIPLIERS = (
    _generate_rank_base_multipliers()
)


# ==================================================
# LEVEL COST MULTIPLIER
# ==================================================


def _get_level_cost_multiplier(
    level: int,
) -> float:
    """
    Return the relative cost multiplier
    for a particular level.
    """

    if level < MIN_LEVEL:
        level = MIN_LEVEL

    rank = get_rank_for_level(
        level
    )

    tier = rank["tier"]

    levels_into_rank = (
        level
        - rank["start_level"]
    )

    rank_base_multiplier = (
        RANK_BASE_MULTIPLIERS[
            tier
        ]
    )

    within_rank_multiplier = (
        1
        + (
            WITHIN_RANK_COST_INCREASE
            * levels_into_rank
        )
    )

    return (
        rank_base_multiplier
        * within_rank_multiplier
    )


# ==================================================
# BASE LEVEL COST
# ==================================================


def _calculate_base_level_cost() -> float:
    """
    Calculate the base level cost required
    for the configured target rank to begin
    near the configured target point total.
    """

    target_rank = None

    for rank in RANKS:

        if (
            rank["tier"]
            == TARGET_RANK_TIER
        ):
            target_rank = rank
            break

    if target_rank is None:
        raise ValueError(
            f"TARGET_RANK_TIER "
            f"{TARGET_RANK_TIER} does not exist."
        )

    target_start_level = (
        target_rank[
            "start_level"
        ]
    )

    if target_start_level <= MIN_LEVEL:
        raise ValueError(
            "TARGET_RANK_TIER must begin "
            "after Level 1."
        )

    relative_total_cost = 0.0

    # Determine how expensive reaching the
    # target rank would be if the base cost
    # were exactly 1 point.
    for level in range(
        MIN_LEVEL,
        target_start_level,
    ):

        relative_total_cost += (
            _get_level_cost_multiplier(
                level
            )
        )

    if relative_total_cost <= 0:
        raise ValueError(
            "Unable to calculate the "
            "base level cost."
        )

    # Scale the entire curve so the target
    # rank begins near the configured
    # point target.
    return (
        TARGET_RANK_START_POINTS
        / relative_total_cost
    )


BASE_LEVEL_COST = (
    _calculate_base_level_cost()
)


# ==================================================
# LEVEL COST
# ==================================================


def calculate_level_cost(
    level: int,
) -> int:
    """
    Calculate the number of points required
    to advance from a level to the next level.

    Once generated, this value is stored
    in the level cache.
    """

    if level < MIN_LEVEL:
        level = MIN_LEVEL

    level_cost = (
        BASE_LEVEL_COST
        * _get_level_cost_multiplier(
            level
        )
    )

    return max(
        1,
        round(level_cost),
    )