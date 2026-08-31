# ==================================================
# LEVEL CONFIGURATION
# ==================================================


# Everyone begins at Level 1.
MIN_LEVEL = 1


# ==================================================
# WITHIN-RANK LEVEL GROWTH
# ==================================================


# Each successive level within the same rank
# costs approximately 1% more than the previous
# level in that rank.
WITHIN_RANK_COST_INCREASE = 0.01


# ==================================================
# RANK-TO-RANK COST GROWTH
# ==================================================


# Each new rank has a base level cost
# approximately 20% higher than the previous rank.
RANK_COST_GROWTH_RATE = 1.20


# ==================================================
# PROGRESSION CALIBRATION
# ==================================================


# Tier 4 is Sauce Boss.
TARGET_RANK_TIER = 4


# Sauce Boss should begin at approximately
# 1,200 total points.
TARGET_RANK_START_POINTS = 1200


# ==================================================
# LEVEL CACHE
# ==================================================


# Precalculate this many levels when M.A.R.T.Y.
# starts.
#
# Levels remain unlimited. If somebody exceeds
# this value, the cache automatically expands.
INITIAL_CACHED_LEVELS = 150