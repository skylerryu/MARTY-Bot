import os

from dotenv import (
    load_dotenv,
)


load_dotenv()


# ==================================================
# DISCORD TOKEN
# ==================================================


TOKEN = os.getenv(
    "DISCORD_TOKEN"
)


# ==================================================
# DEVELOPMENT GUILD
# ==================================================


DEV_GUILD_ID_RAW = os.getenv(
    "DEV_GUILD_ID"
)


# ==================================================
# QOTD CHANNEL
# ==================================================


QOTD_CHANNEL_ID_RAW = os.getenv(
    "QOTD_CHANNEL_ID"
)


# ==================================================
# RANDOM SPEED QUESTION CHANNEL
# ==================================================


RANDOM_QUESTION_CHANNEL_ID_RAW = (
    os.getenv(
        "RANDOM_QUESTION_CHANNEL_ID"
    )
)


# ==================================================
# VALIDATION
# ==================================================


if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN was not found "
        "in .env."
    )


if not DEV_GUILD_ID_RAW:

    raise RuntimeError(
        "DEV_GUILD_ID was not found "
        "in .env."
    )


if not QOTD_CHANNEL_ID_RAW:

    raise RuntimeError(
        "QOTD_CHANNEL_ID was not found "
        "in .env."
    )


if not RANDOM_QUESTION_CHANNEL_ID_RAW:

    raise RuntimeError(
        "RANDOM_QUESTION_CHANNEL_ID "
        "was not found in .env."
    )


# ==================================================
# CONVERT IDS
# ==================================================


DEV_GUILD_ID = int(
    DEV_GUILD_ID_RAW
)


QOTD_CHANNEL_ID = int(
    QOTD_CHANNEL_ID_RAW
)


RANDOM_QUESTION_CHANNEL_ID = int(
    RANDOM_QUESTION_CHANNEL_ID_RAW
)