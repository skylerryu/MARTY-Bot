# ==================================================
# RANDOM SPEED QUESTION CONFIGURATION
# ==================================================
#
# Change normal RSQ behavior here rather than
# editing the scheduler itself.
#
# IMPORTANT:
#
# Config changes take effect after MARTY restarts.
#
# A schedule that has already been generated for
# the current day stays intact. New settings will
# be used when the next day's schedule is created.
# ==================================================


# ==================================================
# MASTER SWITCH
# ==================================================


RSQ_ENABLED = True


# ==================================================
# TIMEZONE
# ==================================================


RSQ_TIMEZONE = "America/Chicago"


# ==================================================
# DAILY POSTING WINDOW
# ==================================================
#
# Automatic RSQs will only be scheduled inside
# this local-time window.
#
# Default:
#
#     8:00 AM through 11:59 PM
#
# ==================================================


RSQ_WINDOW_START_HOUR = 0
RSQ_WINDOW_START_MINUTE = 0

RSQ_WINDOW_END_HOUR = 23
RSQ_WINDOW_END_MINUTE = 59


# ==================================================
# DAILY QUESTION FREQUENCY
# ==================================================
#
# MARTY chooses a new target every day using a
# normal distribution.
#
# Mean 16 / standard deviation 2.5 means most
# days should land around 12–20 questions, but
# counts outside that range remain possible.
#
# ==================================================


RSQ_DAILY_QUESTION_MEAN = 16.0

RSQ_DAILY_QUESTION_STD_DEV = 2.5


# ==================================================
# ABSOLUTE SAFETY LIMITS
# ==================================================
#
# These are NOT the normal target range.
#
# They only prevent a very unusual random draw
# from creating a ridiculous schedule.
#
# ==================================================


RSQ_ABSOLUTE_MIN_DAILY = 4
RSQ_ABSOLUTE_MAX_DAILY = 30


# ==================================================
# MINIMUM INTERVAL
# ==================================================
#
# No RSQ may be posted within this many minutes
# of the previous RSQ.
#
# This applies to:
#
#     automatic RSQs
#     manual /question RSQs
#
# Keep this at 15 or higher.
#
# ==================================================


RSQ_MIN_INTERVAL_MINUTES = 15


# ==================================================
# TIMING RANDOMNESS
# ==================================================
#
# 0.0 = essentially evenly distributed
# 1.0 = highly randomized placement
#
# 0.85 gives substantial unpredictability without
# letting the schedule become excessively clumped.
#
# ==================================================


RSQ_TIMING_RANDOMNESS = 0.85


# ==================================================
# DISTRIBUTION SMOOTHING
# ==================================================
#
# This controls how strongly MARTY resists
# question clustering.
#
# 0.0 = allow more extreme clustering
# 1.0 = keep posts closer to even distribution
#
# This is separate from timing randomness.
#
# ==================================================


RSQ_DISTRIBUTION_SMOOTHING = 0.35


# ==================================================
# RECENT QUESTION AVOIDANCE
# ==================================================
#
# MARTY will try not to reuse any of the last
# N questions that were posted as RSQs.
#
# With:
#
#     50 questions
#     ~16 RSQs/day
#
# a question will normally remain out of RSQ
# rotation for roughly 3 days.
#
# This is a preference rather than an absolute
# prohibition. If the bank becomes too small,
# MARTY progressively relaxes the avoidance
# window rather than failing to post.
#
# ==================================================


RSQ_RECENT_QUESTION_AVOID_COUNT = 50


# ==================================================
# AUTOMATICALLY EXCLUDED CATEGORIES
# ==================================================
#
# These categories are excluded from RANDOM
# automatic RSQ selection.
#
# An administrator can still explicitly select
# one through /question if desired.
#
# ==================================================


RSQ_EXCLUDED_CATEGORIES = {
    "cet_fun_fact",
}


# ==================================================
# MISSED SLOT GRACE PERIOD
# ==================================================
#
# If MARTY was supposed to post an RSQ but was
# offline or otherwise delayed, it will only post
# that question if the scheduled time is no more
# than this many minutes old.
#
# Older slots become "missed".
#
# This prevents MARTY from dumping several old
# RSQs into the channel after a restart.
#
# ==================================================


RSQ_MISSED_SLOT_GRACE_MINUTES = 10


# ==================================================
# SCHEDULER POLL FREQUENCY
# ==================================================
#
# MARTY checks this often to see whether a
# scheduled posting time has arrived.
#
# This is NOT the RSQ posting frequency.
#
# ==================================================


RSQ_SCHEDULER_POLL_SECONDS = 20


# ==================================================
# VALIDATION
# ==================================================


if not (
    0.0
    <= RSQ_TIMING_RANDOMNESS
    <= 1.0
):

    raise ValueError(
        "RSQ_TIMING_RANDOMNESS must be "
        "between 0.0 and 1.0."
    )


if not (
    0.0
    <= RSQ_DISTRIBUTION_SMOOTHING
    <= 1.0
):

    raise ValueError(
        "RSQ_DISTRIBUTION_SMOOTHING must "
        "be between 0.0 and 1.0."
    )


if (
    RSQ_DAILY_QUESTION_MEAN
    <= 0
):

    raise ValueError(
        "RSQ_DAILY_QUESTION_MEAN must "
        "be greater than zero."
    )


if (
    RSQ_DAILY_QUESTION_STD_DEV
    < 0
):

    raise ValueError(
        "RSQ_DAILY_QUESTION_STD_DEV "
        "cannot be negative."
    )


if (
    RSQ_ABSOLUTE_MIN_DAILY
    < 1
):

    raise ValueError(
        "RSQ_ABSOLUTE_MIN_DAILY must "
        "be at least 1."
    )


if (
    RSQ_ABSOLUTE_MAX_DAILY
    < RSQ_ABSOLUTE_MIN_DAILY
):

    raise ValueError(
        "RSQ_ABSOLUTE_MAX_DAILY must be "
        "greater than or equal to "
        "RSQ_ABSOLUTE_MIN_DAILY."
    )


if (
    RSQ_MIN_INTERVAL_MINUTES
    < 15
):

    raise ValueError(
        "RSQ_MIN_INTERVAL_MINUTES must "
        "be at least 15."
    )


if (
    RSQ_RECENT_QUESTION_AVOID_COUNT
    < 0
):

    raise ValueError(
        "RSQ_RECENT_QUESTION_AVOID_COUNT "
        "cannot be negative."
    )


if (
    RSQ_MISSED_SLOT_GRACE_MINUTES
    < 0
):

    raise ValueError(
        "RSQ_MISSED_SLOT_GRACE_MINUTES "
        "cannot be negative."
    )


if (
    RSQ_SCHEDULER_POLL_SECONDS
    <= 0
):

    raise ValueError(
        "RSQ_SCHEDULER_POLL_SECONDS must "
        "be greater than zero."
    )