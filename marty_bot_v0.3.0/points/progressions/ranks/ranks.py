import math

from points.progressions.ranks.ranks_config import (
    RANK_NAMES,
    BASE_RANK_LEVELS,
    RANK_LEVEL_GROWTH_RATE,
)


# ==================================================
# GENERATE RANKS
# ==================================================


def generate_ranks() -> list:
    """
    Generate the level range for every rank.

    The final rank has no maximum level.
    """

    ranks = []

    current_start_level = 1

    for index, name in enumerate(RANK_NAMES):

        tier = index + 1

        is_final_rank = (
            index == len(RANK_NAMES) - 1
        )

        # ------------------------------------------
        # FINAL UNLIMITED RANK
        # ------------------------------------------

        if is_final_rank:

            ranks.append(
                {
                    "tier": tier,
                    "name": name,
                    "start_level": current_start_level,
                    "end_level": None,
                }
            )

            break

        # ------------------------------------------
        # LEVELS IN THIS RANK
        # ------------------------------------------

        levels_in_rank = math.ceil(
            BASE_RANK_LEVELS
            * (
                RANK_LEVEL_GROWTH_RATE
                ** index
            )
        )

        end_level = (
            current_start_level
            + levels_in_rank
            - 1
        )

        ranks.append(
            {
                "tier": tier,
                "name": name,
                "start_level": current_start_level,
                "end_level": end_level,
            }
        )

        # The next rank begins immediately
        # after this rank ends.
        current_start_level = (
            end_level + 1
        )

    return ranks


# Generate the rank structure when the
# progression system is loaded.
RANKS = generate_ranks()


# ==================================================
# LEVEL → RANK
# ==================================================


def get_rank_for_level(
    level: int,
) -> dict:
    """
    Return the rank associated with a level.
    """

    if level < 1:
        level = 1

    for rank in RANKS:

        start_level = rank[
            "start_level"
        ]

        end_level = rank[
            "end_level"
        ]

        # Final rank has no upper limit.
        if end_level is None:

            if level >= start_level:
                return rank

        elif (
            start_level
            <= level
            <= end_level
        ):
            return rank

    # Fallback in case the configuration
    # somehow produces an unexpected result.
    return RANKS[-1]


# ==================================================
# NEXT RANK
# ==================================================


def get_next_rank(
    level: int,
) -> dict | None:
    """
    Return the rank after the user's
    current rank.

    Returns None if the user is already
    in the highest rank.
    """

    current_rank = get_rank_for_level(
        level
    )

    current_tier = current_rank[
        "tier"
    ]

    for rank in RANKS:

        if (
            rank["tier"]
            == current_tier + 1
        ):
            return rank

    return None


# ==================================================
# RANK PROGRESS
# ==================================================


def get_rank_progress(
    level: int,
) -> dict:
    """
    Return information about the user's
    position within their current rank.

    This is primarily internal information.
    Rank thresholds do not need to be shown
    to users.
    """

    current_rank = get_rank_for_level(
        level
    )

    next_rank = get_next_rank(
        level
    )

    start_level = current_rank[
        "start_level"
    ]

    end_level = current_rank[
        "end_level"
    ]

    levels_into_rank = (
        level - start_level
    )

    # ------------------------------------------
    # FINAL UNLIMITED RANK
    # ------------------------------------------

    if end_level is None:

        return {
            "rank": current_rank,
            "next_rank": None,
            "levels_into_rank": levels_into_rank,
            "levels_remaining": None,
            "progress_percent": None,
        }

    # ------------------------------------------
    # NORMAL RANK
    # ------------------------------------------

    levels_in_rank = (
        end_level
        - start_level
        + 1
    )

    levels_remaining = (
        end_level
        - level
        + 1
    )

    progress_percent = (
        levels_into_rank
        / levels_in_rank
        * 100
    )

    return {
        "rank": current_rank,
        "next_rank": next_rank,
        "levels_into_rank": levels_into_rank,
        "levels_remaining": levels_remaining,
        "progress_percent": progress_percent,
    }