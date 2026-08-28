import os

from dotenv import load_dotenv


load_dotenv()


# ==================================================
# DISCORD
# ==================================================

TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID_RAW = os.getenv("DEV_GUILD_ID")


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN was not found in .env."
    )

if not DEV_GUILD_ID_RAW:
    raise RuntimeError(
        "DEV_GUILD_ID was not found in .env."
    )


DEV_GUILD_ID = int(DEV_GUILD_ID_RAW)