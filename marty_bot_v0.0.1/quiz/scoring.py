from datetime import datetime, timezone

import discord

from bot_config import (
    CORRECT_ANSWER_POINTS,
    calculate_speed_bonus,
)

from data.database import add_points


def get_response_seconds(
    message: discord.Message,
    posted_at: str
) -> float:

    posted_time = datetime.strptime(
        posted_at,
        "%Y-%m-%d %H:%M:%S"
    ).replace(
        tzinfo=timezone.utc
    )

    seconds = (
        message.created_at - posted_time
    ).total_seconds()

    return max(0, seconds)


async def award_question_points(
    message: discord.Message,
    posted_at: str
):
    response_seconds = get_response_seconds(
        message,
        posted_at
    )

    speed_bonus = calculate_speed_bonus(
        response_seconds
    )

    await add_points(
        guild_id=message.guild.id,
        user_id=message.author.id,
        amount=CORRECT_ANSWER_POINTS,
        reason="correct_question"
    )

    if speed_bonus > 0:
        await add_points(
            guild_id=message.guild.id,
            user_id=message.author.id,
            amount=speed_bonus,
            reason="question_speed_bonus"
        )

    return {
        "base_points": CORRECT_ANSWER_POINTS,
        "speed_bonus": speed_bonus,
        "total_points": (
            CORRECT_ANSWER_POINTS
            + speed_bonus
        ),
        "response_seconds": response_seconds,
    }