import os

from dotenv import load_dotenv


load_dotenv()


# ==================================================
# DISCORD
# ==================================================


TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

DEV_GUILD_ID_RAW = os.getenv(
    "DEV_GUILD_ID"
)

QOTD_CHANNEL_ID_RAW = os.getenv(
    "QOTD_CHANNEL_ID"
)


# ==================================================
# VALIDATION
# ==================================================


if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN was not found in .env."
    )


if not DEV_GUILD_ID_RAW:

    raise RuntimeError(
        "DEV_GUILD_ID was not found in .env."
    )


if not QOTD_CHANNEL_ID_RAW:

    raise RuntimeError(
        "QOTD_CHANNEL_ID was not found in .env."
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
