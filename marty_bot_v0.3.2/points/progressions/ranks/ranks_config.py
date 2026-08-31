# ==================================================
# RANK CONFIGURATION
# ==================================================


# Rank names in progression order.
#
# The final rank has no maximum level.

RANK_NAMES = [
    "Dishwasher",
    "Potato Peeler",
    "Garnish Goblin",
    "Sauce Boss",
    "Grill Sergeant",
    "Pan Commander",
    "Kitchen Warlord",
    "The Big Cheese",
    "Supreme Kitchen Commander",
]


# ==================================================
# RANK LENGTH
# ==================================================


# Number of levels in the first rank.
BASE_RANK_LEVELS = 5


# Each successive rank contains approximately
# 24% more levels than the previous rank.
#
# The number of levels is rounded upward.
#
# This currently generates:
#
# Dishwasher                 1-5
# Potato Peeler              6-12
# Garnish Goblin            13-20
# Sauce Boss                21-30
# Grill Sergeant            31-42
# Pan Commander             43-57
# Kitchen Warlord           58-76
# The Big Cheese            77-99
# Supreme Kitchen Commander 100+

RANK_LEVEL_GROWTH_RATE = 1.24