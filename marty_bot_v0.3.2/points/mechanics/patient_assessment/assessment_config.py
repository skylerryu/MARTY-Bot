# ==================================================
# PATIENT ASSESSMENT SIMULATOR CONFIGURATION
# ==================================================


ASSESSMENT_ENABLED = True


# ==================================================
# DAILY POSTING
# ==================================================


ASSESSMENT_TIMEZONE = "America/Chicago"

ASSESSMENT_POST_HOUR = 6

ASSESSMENT_POST_MINUTE = 0


# Number of public assessment cards MARTY keeps
# visible in the assessment channel.
ASSESSMENT_VISIBLE_MESSAGE_COUNT = 1


# Number of assessment views MARTY restores after
# a restart.
ASSESSMENT_PERSISTENT_VIEW_LIMIT = 30


# If a transient LLM/Discord error prevents the daily post,
# MARTY retries the ensure step periodically after post time.
ASSESSMENT_RECOVERY_CHECK_SECONDS = 10 * 60


# ==================================================
# STUDENT SESSION
# ==================================================


# The practical rubric treats failure to call for
# transport within 12 minutes as a critical fail.
# The simulator does NOT automatically end at this
# time; it simply tracks whether transport was called
# in time.
ASSESSMENT_TRANSPORT_LIMIT_SECONDS = 12 * 60


# Maximum text a student can enter in one modal.
ASSESSMENT_INPUT_MAX_LENGTH = 1800


# Number of recent student/MARTY turns sent back to
# the LLM for conversational continuity.
ASSESSMENT_HISTORY_TURNS = 8


# ==================================================
# LLM
# ==================================================


# Use a stronger model once per day to create the frozen
# scenario and a lower-cost model for the high-volume
# student turns. They are config variables so you can
# change them without touching simulator logic.
ASSESSMENT_SCENARIO_MODEL = "gpt-5.6-terra"

ASSESSMENT_TURN_MODEL = "gpt-5.6-luna"


# Maximum number of assessment LLM requests allowed to
# run at the same time across the entire bot.
ASSESSMENT_LLM_MAX_CONCURRENT_REQUESTS = 5

ASSESSMENT_LLM_RETRY_ATTEMPTS = 3

ASSESSMENT_LLM_RETRY_BASE_SECONDS = 1.5


# ==================================================
# DAILY SCENARIO MIX
# ==================================================


ASSESSMENT_ENABLED_SCENARIO_TYPES = (
    "respiratory",
    "cardiac",
    "neurological",
    "anaphylaxis",
    "acute_abdomen",
    "ob_labor",
    "trauma",
    "airway",
)


# MARTY tries not to repeat any of the most recent
# scenario types if alternatives are available.
ASSESSMENT_RECENT_TYPE_AVOID_COUNT = 2
