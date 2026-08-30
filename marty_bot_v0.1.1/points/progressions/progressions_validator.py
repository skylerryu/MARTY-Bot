from points.progressions.levels.levels_config import (
    MIN_LEVEL,
    WITHIN_RANK_COST_INCREASE,
    RANK_COST_GROWTH_RATE,
    TARGET_RANK_TIER,
    TARGET_RANK_START_POINTS,
)

from points.progressions.levels.levels import (
    get_points_required_for_next_level,
    get_total_points_required_for_level,
)

from points.progressions.ranks.ranks_config import (
    RANK_NAMES,
    BASE_RANK_LEVELS,
    RANK_LEVEL_GROWTH_RATE,
)

from points.progressions.ranks.ranks import (
    RANKS,
)


# ==================================================
# PROGRESSION CONFIG VALIDATION
# ==================================================


def validate_progression_config():
    """
    Validate the complete generated progression
    configuration.

    Raises ValueError if something is invalid.
    """

    _validate_ranks_config()
    _validate_levels_config()
    _validate_generated_ranks()
    _validate_target_rank()
    _validate_generated_level_costs()

    print(
        "Progression configuration validated."
    )


# ==================================================
# RANK CONFIG
# ==================================================


def _validate_ranks_config():
    """
    Validate the settings used to generate ranks.
    """

    if not RANK_NAMES:
        raise ValueError(
            "RANK_NAMES cannot be empty."
        )

    if len(RANK_NAMES) < 2:
        raise ValueError(
            "At least two ranks are required."
        )

    # ----------------------------------------------
    # RANK NAMES
    # ----------------------------------------------

    for name in RANK_NAMES:

        if not isinstance(name, str):
            raise ValueError(
                "Every rank name must be a string."
            )

        if not name.strip():
            raise ValueError(
                "Rank names cannot be empty."
            )

    if len(set(RANK_NAMES)) != len(RANK_NAMES):
        raise ValueError(
            "Rank names must be unique."
        )

    # ----------------------------------------------
    # BASE RANK LENGTH
    # ----------------------------------------------

    if not isinstance(
        BASE_RANK_LEVELS,
        int,
    ):
        raise ValueError(
            "BASE_RANK_LEVELS must be an integer."
        )

    if BASE_RANK_LEVELS < 1:
        raise ValueError(
            "BASE_RANK_LEVELS must be "
            "at least 1."
        )

    # ----------------------------------------------
    # RANK LEVEL GROWTH
    # ----------------------------------------------

    if not isinstance(
        RANK_LEVEL_GROWTH_RATE,
        (int, float),
    ):
        raise ValueError(
            "RANK_LEVEL_GROWTH_RATE must "
            "be a number."
        )

    if RANK_LEVEL_GROWTH_RATE < 1:
        raise ValueError(
            "RANK_LEVEL_GROWTH_RATE must "
            "be at least 1."
        )


# ==================================================
# LEVEL CONFIG
# ==================================================


def _validate_levels_config():
    """
    Validate the settings used to generate
    level point requirements.
    """

    if MIN_LEVEL != 1:
        raise ValueError(
            "MIN_LEVEL must be 1."
        )

    # ----------------------------------------------
    # WITHIN-RANK GROWTH
    # ----------------------------------------------

    if not isinstance(
        WITHIN_RANK_COST_INCREASE,
        (int, float),
    ):
        raise ValueError(
            "WITHIN_RANK_COST_INCREASE "
            "must be a number."
        )

    if WITHIN_RANK_COST_INCREASE < 0:
        raise ValueError(
            "WITHIN_RANK_COST_INCREASE "
            "cannot be negative."
        )

    # ----------------------------------------------
    # RANK COST GROWTH
    # ----------------------------------------------

    if not isinstance(
        RANK_COST_GROWTH_RATE,
        (int, float),
    ):
        raise ValueError(
            "RANK_COST_GROWTH_RATE must "
            "be a number."
        )

    if RANK_COST_GROWTH_RATE < 1:
        raise ValueError(
            "RANK_COST_GROWTH_RATE must "
            "be at least 1."
        )

    # ----------------------------------------------
    # TARGET RANK
    # ----------------------------------------------

    if not isinstance(
        TARGET_RANK_TIER,
        int,
    ):
        raise ValueError(
            "TARGET_RANK_TIER must "
            "be an integer."
        )

    if TARGET_RANK_TIER < 1:
        raise ValueError(
            "TARGET_RANK_TIER must "
            "be at least 1."
        )

    # ----------------------------------------------
    # TARGET POINTS
    # ----------------------------------------------

    if not isinstance(
        TARGET_RANK_START_POINTS,
        int,
    ):
        raise ValueError(
            "TARGET_RANK_START_POINTS "
            "must be an integer."
        )

    if TARGET_RANK_START_POINTS <= 0:
        raise ValueError(
            "TARGET_RANK_START_POINTS "
            "must be greater than 0."
        )


# ==================================================
# GENERATED RANKS
# ==================================================


def _validate_generated_ranks():
    """
    Make sure the automatically generated rank
    structure is continuous and valid.
    """

    if len(RANKS) != len(RANK_NAMES):
        raise ValueError(
            "Generated rank count does not match "
            "the number of configured rank names."
        )

    expected_start_level = MIN_LEVEL

    for index, rank in enumerate(RANKS):

        expected_tier = index + 1

        tier = rank["tier"]
        name = rank["name"]
        start_level = rank["start_level"]
        end_level = rank["end_level"]

        # ------------------------------------------
        # TIER
        # ------------------------------------------

        if tier != expected_tier:
            raise ValueError(
                f"Rank '{name}' has Tier {tier}, "
                f"but Tier {expected_tier} "
                f"was expected."
            )

        # ------------------------------------------
        # NAME
        # ------------------------------------------

        if name != RANK_NAMES[index]:
            raise ValueError(
                f"Generated rank name '{name}' "
                f"does not match configured rank "
                f"name '{RANK_NAMES[index]}'."
            )

        # ------------------------------------------
        # START LEVEL
        # ------------------------------------------

        if start_level != expected_start_level:
            raise ValueError(
                f"Rank '{name}' starts at "
                f"Level {start_level}, but "
                f"Level {expected_start_level} "
                f"was expected."
            )

        is_final_rank = (
            index == len(RANKS) - 1
        )

        # ------------------------------------------
        # FINAL RANK
        # ------------------------------------------

        if is_final_rank:

            if end_level is not None:
                raise ValueError(
                    f"Final rank '{name}' must "
                    "have no maximum level."
                )

        # ------------------------------------------
        # NORMAL RANK
        # ------------------------------------------

        else:

            if not isinstance(
                end_level,
                int,
            ):
                raise ValueError(
                    f"Rank '{name}' must have "
                    "an integer end level."
                )

            if end_level < start_level:
                raise ValueError(
                    f"Rank '{name}' ends before "
                    "it begins."
                )

            expected_start_level = (
                end_level + 1
            )


# ==================================================
# TARGET RANK
# ==================================================


def _validate_target_rank():
    """
    Make sure the progression calibration target
    refers to a valid generated rank.
    """

    if TARGET_RANK_TIER > len(RANKS):
        raise ValueError(
            f"TARGET_RANK_TIER "
            f"{TARGET_RANK_TIER} does not exist."
        )

    target_rank = RANKS[
        TARGET_RANK_TIER - 1
    ]

    if (
        target_rank["start_level"]
        <= MIN_LEVEL
    ):
        raise ValueError(
            "The target rank must begin "
            "after Level 1 so the progression "
            "curve can be calibrated."
        )


# ==================================================
# GENERATED LEVEL COSTS
# ==================================================


def _validate_generated_level_costs():
    """
    Test generated level costs to make sure they
    remain positive and increase sensibly.
    """

    # Test through the start of the final rank
    # plus additional unlimited levels.
    final_rank_start = RANKS[-1][
        "start_level"
    ]

    test_through_level = (
        final_rank_start + 100
    )

    previous_cost = None

    for level in range(
        MIN_LEVEL,
        test_through_level + 1,
    ):

        cost = (
            get_points_required_for_next_level(
                level
            )
        )

        if not isinstance(cost, int):
            raise ValueError(
                f"Generated cost for Level "
                f"{level} is not an integer."
            )

        if cost <= 0:
            raise ValueError(
                f"Generated cost for Level "
                f"{level} must be greater than 0."
            )

        # Because our progression is intended
        # to become harder rather than easier,
        # level costs should never decrease.
        if (
            previous_cost is not None
            and cost < previous_cost
        ):
            raise ValueError(
                f"Level cost decreases from "
                f"Level {level - 1} "
                f"({previous_cost} points) to "
                f"Level {level} "
                f"({cost} points)."
            )

        previous_cost = cost

    # ----------------------------------------------
    # VERIFY CALIBRATION
    # ----------------------------------------------

    target_rank = RANKS[
        TARGET_RANK_TIER - 1
    ]

    target_level = target_rank[
        "start_level"
    ]

    actual_target_points = (
        get_total_points_required_for_level(
            target_level
        )
    )

    # Individual level costs are rounded to whole
    # points, so the final total may differ slightly
    # from the requested calibration target.
    allowed_difference = max(
        5,
        int(
            TARGET_RANK_START_POINTS
            * 0.01
        ),
    )

    difference = abs(
        actual_target_points
        - TARGET_RANK_START_POINTS
    )

    if difference > allowed_difference:
        raise ValueError(
            f"Target Rank Tier "
            f"{TARGET_RANK_TIER} begins at "
            f"{actual_target_points} points, "
            f"which is too far from the configured "
            f"target of "
            f"{TARGET_RANK_START_POINTS} points."
        )