# ==================================================
# QUESTION ATTEMPTS
# ==================================================

QUESTION_ATTEMPT_LIMIT = 1


# ==================================================
# QUESTION SCORING
# ==================================================

CORRECT_ANSWER_POINTS = 10


def calculate_speed_bonus(
    response_seconds: float
) -> int:

    if response_seconds <= 10:
        return 5

    if response_seconds <= 20:
        return 3

    if response_seconds <= 60:
        return 1

    return 0


# ==================================================
# QUESTION SCHEDULING
# ==================================================

# Temporary testing interval.
# Later this will become the real
# 6 AM / 2 PM / 10 PM Chicago schedule.

QUESTION_INTERVAL_SECONDS = 90


# ==================================================
# QUESTION CATEGORIES
# ==================================================

CATEGORY_NAMES = {
    "random_nremt": "Random NREMT Question",
    "cpr_airway": "CPR / Airway",
    "cardiac": "Cardiac",
    "neurological": "Neurological",
    "anaphylaxis": "Anaphylaxis",
    "acute_abdomen": "Acute Abdomen",
    "ob_labor": "OB / Labor",
    "trauma": "Trauma",
    "cet_fun_fact": "CET Fun Fact",
}