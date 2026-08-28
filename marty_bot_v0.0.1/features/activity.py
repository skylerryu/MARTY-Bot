import time

import discord

from bot_config import ACTIVITY_COOLDOWN
from data.database import add_points


# ==================================================
# ACTIVITY TRACKING
# ==================================================

# Stores the last time each student earned
# an activity point.
#
# Key:
# (guild_id, user_id)
#
# Value:
# time.monotonic() timestamp

last_activity_point = {}


async def handle_activity(
    message: discord.Message
):
    """
    Award +1 activity point if the student has not
    received an activity point within the cooldown.

    This function should only be called for normal
    Discord conversation, NOT question responses.
    """

    if message.guild is None:
        return

    user_key = (
        message.guild.id,
        message.author.id
    )

    current_time = time.monotonic()

    last_time = last_activity_point.get(
        user_key,
        0
    )

    # Student is still within the cooldown.
    if (
        current_time - last_time
        < ACTIVITY_COOLDOWN
    ):
        return

    # Award one activity point.
    await add_points(
        guild_id=message.guild.id,
        user_id=message.author.id,
        amount=1,
        reason="activity"
    )

    # Remember when this student earned the point.
    last_activity_point[user_key] = current_time