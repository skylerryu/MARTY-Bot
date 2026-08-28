import discord

from points.displays.displays_helpers import (
    build_progress_bar,
)

from points.mechanics.question_of_the_day.qotd_config import (
    QOTD_STREAK_MAX_BONUS_DAY,
)


# ==================================================
# QUESTION DISPLAY
# ==================================================


def build_qotd_question_embed(
    question_text: str,
) -> discord.Embed:
    """
    Build the public Question of the Day embed.
    """

    embed = discord.Embed(
        title="🩺 Question of the Day",
        description=question_text,
    )

    embed.set_footer(
        text=(
            "Click Answer Question to submit "
            "your answer privately."
        )
    )

    return embed


# ==================================================
# CORRECT ANSWER
# ==================================================


def build_qotd_correct_embed(
    submitted_answer: str,
    base_points: int,
    streak_bonus: int,
    streak_days: int,
    explanation: str | None,
) -> discord.Embed:
    """
    Build the private response shown after
    a correct QoTD answer.
    """

    total_points = (
        base_points
        + streak_bonus
    )

    embed = discord.Embed(
        title="✅ Correct!",
        description=(
            f"You earned **+{total_points} points**."
        ),
    )

    embed.add_field(
        name="Your Answer",
        value=submitted_answer[:1024],
        inline=False,
    )

    embed.add_field(
        name="Points",
        value=(
            f"Question: **+{base_points}**\n"
            f"Streak Bonus: **+{streak_bonus}**"
        ),
        inline=False,
    )


    # ==================================================
    # STREAK PROGRESS
    # ==================================================


    displayed_streak_days = min(
        streak_days,
        QOTD_STREAK_MAX_BONUS_DAY,
    )

    progress_percent = (
        displayed_streak_days
        / QOTD_STREAK_MAX_BONUS_DAY
        * 100
    )

    progress_bar = build_progress_bar(
        progress_percent=progress_percent,
        length=QOTD_STREAK_MAX_BONUS_DAY,
    )

    if (
        streak_days
        >= QOTD_STREAK_MAX_BONUS_DAY
    ):

        streak_text = (
            f"`{progress_bar}`\n"
            f"🔥 **{streak_days} day streak**\n"
            "Maximum streak bonus active!"
        )

    else:

        streak_text = (
            f"`{progress_bar}`\n"
            f"🔥 **{streak_days} day streak**\n"
            f"{streak_days} / "
            f"{QOTD_STREAK_MAX_BONUS_DAY} days"
        )

    embed.add_field(
        name="QoTD Streak",
        value=streak_text,
        inline=False,
    )


    # ==================================================
    # EXPLANATION
    # ==================================================


    if explanation:

        embed.add_field(
            name="Explanation",
            value=explanation[:1024],
            inline=False,
        )

    return embed


# ==================================================
# INCORRECT ANSWER
# ==================================================


def build_qotd_incorrect_embed(
    submitted_answer: str,
) -> discord.Embed:
    """
    Build the private response shown after
    a confidently incorrect answer.
    """

    embed = discord.Embed(
        title="❌ Not Quite",
        description=(
            "That answer isn't correct.\n\n"
            "You can try again."
        ),
    )

    embed.add_field(
        name="Your Answer",
        value=submitted_answer[:1024],
        inline=False,
    )

    return embed


# ==================================================
# UNCERTAIN ANSWER
# ==================================================


def build_qotd_uncertain_embed(
    submitted_answer: str,
) -> discord.Embed:
    """
    Build the private response shown when the
    LLM cannot grade the answer confidently.
    """

    embed = discord.Embed(
        title="🤔 Try Rephrasing",
        description=(
            "I couldn't confidently evaluate "
            "that answer.\n\n"
            "Try answering again with a little "
            "more detail or different wording."
        ),
    )

    embed.add_field(
        name="Your Answer",
        value=submitted_answer[:1024],
        inline=False,
    )

    return embed


# ==================================================
# ALREADY COMPLETED
# ==================================================


def build_qotd_completed_embed() -> discord.Embed:
    """
    Build the private response shown when a user
    has already completed this QoTD.
    """

    return discord.Embed(
        title="✅ Already Completed",
        description=(
            "You've already completed today's "
            "Question of the Day."
        ),
    )


# ==================================================
# EXPIRED QUESTION
# ==================================================


def build_qotd_expired_embed() -> discord.Embed:
    """
    Build the private response shown when someone
    tries to answer an older QoTD.
    """

    return discord.Embed(
        title="⌛ Question Expired",
        description=(
            "This is no longer today's "
            "Question of the Day."
        ),
    )


# ==================================================
# UNAVAILABLE QUESTION
# ==================================================


def build_qotd_unavailable_embed() -> discord.Embed:
    """
    Build the private response shown when the
    requested QoTD cannot be found.
    """

    return discord.Embed(
        title="Question Unavailable",
        description=(
            "This Question of the Day "
            "is no longer available."
        ),
    )