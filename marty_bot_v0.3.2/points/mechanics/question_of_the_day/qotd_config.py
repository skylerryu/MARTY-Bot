# ==================================================
# QUESTION OF THE DAY CONFIGURATION
# ==================================================


# Points awarded for correctly completing
# the Question of the Day.
QOTD_CORRECT_POINTS = 10


# ==================================================
# DAILY POSTING
# ==================================================


# Question of the Day posting time.
#
# Uses a 24-hour clock in America/Chicago time.
#
# 6:00 AM:
# QOTD_POST_HOUR = 6
# QOTD_POST_MINUTE = 0

QOTD_TIMEZONE = "America/Chicago"

QOTD_POST_HOUR = 6

QOTD_POST_MINUTE = 0


# ==================================================
# VISIBLE QOTD MESSAGES
# ==================================================
#
# Number of QoTD Discord messages MARTY should
# keep visible in the QoTD channel.
#
# 1:
#     Only the current QoTD remains visible.
#
# 3:
#     Current QoTD + previous 2 QoTDs remain.
#
# Old database records are NEVER deleted by this
# setting. Only their Discord messages are removed.
#
# ==================================================


QOTD_VISIBLE_MESSAGE_COUNT = 1


# ==================================================
# LLM GRADING
# ==================================================


# M.A.R.T.Y. must be at least this confident
# before automatically accepting or rejecting
# a student's answer.
QOTD_GRADING_CONFIDENCE_THRESHOLD = 0.85


# Maximum length of a student's submitted answer.
QOTD_ANSWER_MAX_LENGTH = 500


# ==================================================
# STREAK BONUSES
# ==================================================


QOTD_STREAK_DAY_1_BONUS = 1

QOTD_STREAK_DAYS_2_TO_3_BONUS = 2

QOTD_STREAK_DAYS_4_TO_6_BONUS = 5

QOTD_STREAK_DAY_7_PLUS_BONUS = 10


# Maximum streak bonus begins on Day 7.
QOTD_STREAK_MAX_BONUS_DAY = 7


# ==================================================
# PERSISTENT VIEWS
# ==================================================
#
# This is only the maximum number of QoTD button
# views MARTY will restore after a bot restart.
#
# Because deleted QoTD messages have their
# message_id cleared, only retained messages will
# normally need to be restored.
#
# ==================================================


QOTD_PERSISTENT_VIEW_LIMIT = 30