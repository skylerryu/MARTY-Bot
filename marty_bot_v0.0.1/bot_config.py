import os

from dotenv import load_dotenv


# ==================================================
# ENVIRONMENT
# ==================================================

load_dotenv()


# ==================================================
# DISCORD
# ==================================================

TOKEN = os.getenv("DISCORD_TOKEN")

DEV_GUILD_ID_RAW = os.getenv(
    "DEV_GUILD_ID"
)

QUESTION_CHANNEL_ID_RAW = os.getenv(
    "QUESTION_CHANNEL_ID"
)


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN was not found in .env."
    )

if not DEV_GUILD_ID_RAW:
    raise RuntimeError(
        "DEV_GUILD_ID was not found in .env."
    )

if not QUESTION_CHANNEL_ID_RAW:
    raise RuntimeError(
        "QUESTION_CHANNEL_ID was not found in .env."
    )


DEV_GUILD_ID = int(
    DEV_GUILD_ID_RAW
)

QUESTION_CHANNEL_ID = int(
    QUESTION_CHANNEL_ID_RAW
)


# ==================================================
# BOT STATUS
# ==================================================

ON_DUTY_NAME = (
    "M.A.R.T.Y. Bot [ON-DUTY]"
)

OFF_DUTY_NAME = (
    "M.A.R.T.Y. Bot [OFF-DUTY]"
)


# ==================================================
# ACTIVITY
# ==================================================

ACTIVITY_COOLDOWN = 90