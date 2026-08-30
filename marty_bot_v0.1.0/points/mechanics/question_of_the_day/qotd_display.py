import math
from datetime import (
    date,
    datetime,
    timedelta,
)

import discord

from points.time_helpers import (
    get_chicago_datetime,
    get_current_chicago_datetime,
)

from points.mechanics.question_of_the_day.qotd_config import (
    QOTD_POST_HOUR,
    QOTD_POST_MINUTE,
)


# ==================================================
# QOTD DATE HELPERS
# ==================================================


def _parse_question_date(
    question_date: date | str,
) -> date:

    if isinstance(
        question_date,
        date,
    ):
        return question_date

    return date.fromisoformat(
        question_date
    )


def _format_qotd_date(
    question_date: date | str,
) -> str:

    parsed_date = (
        _parse_question_date(
            question_date
        )
    )

    return parsed_date.strftime(
        "%m/%d/%Y"
    )


def _get_qotd_expiration_datetime(
    question_date: date | str,
) -> datetime:

    parsed_date = (
        _parse_question_date(
            question_date
        )
    )

    return get_chicago_datetime(
        calendar_date=(
            parsed_date
            + timedelta(days=1)
        ),
        hour=QOTD_POST_HOUR,
        minute=QOTD_POST_MINUTE,
    )


# ==================================================
# TIME REMAINING
# ==================================================


def get_qotd_time_remaining_text(
    question_date: date | str,
    now: datetime | None = None,
) -> str:

    if now is None:

        now = (
            get_current_chicago_datetime()
        )

    expiration = (
        _get_qotd_expiration_datetime(
            question_date
        )
    )

    remaining_seconds = max(
        0,
        int(
            (
                expiration
                - now
            ).total_seconds()
        ),
    )


    # ==================================================
    # CLOSED
    # ==================================================


    if remaining_seconds <= 0:

        return "Closed"


    # ==================================================
    # 1 HOUR OR MORE
    # WHOLE-HOUR WARNINGS
    # ==================================================


    if remaining_seconds >= 3600:

        hours = math.ceil(
            remaining_seconds
            / 3600
        )

        return (
            f"< {hours} "
            "hrs"
        )


    # ==================================================
    # LESS THAN 1 HOUR
    # 15-MINUTE WARNINGS
    # ==================================================


    if remaining_seconds >= 900:

        minutes = (
            math.ceil(
                remaining_seconds
                / 900
            )
            * 15
        )

        return (
            f"< {minutes} mins"
        )


    # ==================================================
    # LESS THAN 15 MINUTES
    # 5-MINUTE WARNINGS
    # ==================================================


    if remaining_seconds >= 60:

        minutes = (
            math.ceil(
                remaining_seconds
                / 300
            )
            * 5
        )

        if minutes < 5:

            minutes = 5

        return (
            f"< {minutes} mins"
        )


    # ==================================================
    # LESS THAN 1 MINUTE
    # 15-SECOND WARNINGS
    # ==================================================


    if remaining_seconds >= 30:

        seconds = (
            math.ceil(
                remaining_seconds
                / 15
            )
            * 15
        )

        return (
            f"< {seconds} secs"
        )


    # ==================================================
    # LESS THAN 30 SECONDS
    # 5-SECOND WARNINGS
    # ==================================================


    seconds = (
        math.ceil(
            remaining_seconds
            / 5
        )
        * 5
    )

    return (
        f"< {seconds} secs"
    )


# ==================================================
# QUESTION DISPLAY
# ==================================================


def build_qotd_question_embed(
    question_text: str,
    question_date: date | str,
) -> discord.Embed:

    date_text = (
        _format_qotd_date(
            question_date
        )
    )

    time_remaining = (
        get_qotd_time_remaining_text(
            question_date
        )
    )

    embed = discord.Embed(
        title=(
            f"Question of the Day "
            f"[{date_text}]"
        ),
        description=(
            f"{question_text}\n\n"
            f"⏳ **Time Remaining:** **{time_remaining}** ⏳"
        ),
        color=discord.Color.blurple(),
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
    accepted_answers: list[str],
    submitted_answer: str,
    base_points: int,
    streak_bonus: int,
    streak_days: int,
    explanation: str | None,
) -> discord.Embed:

    total_points = (
        base_points
        + streak_bonus
    )

    day_label = (
        "Day"
        if streak_days == 1
        else "Days"
    )

    explanation_text = (
        explanation[:1500]
        if explanation
        else "No explanation provided."
    )


    # ==================================================
    # ACCEPTED ANSWER DISPLAY
    # ==================================================


    cleaned_answers = [
        answer.strip()
        for answer in accepted_answers
        if answer.strip()
    ]

    if not cleaned_answers:

        answer_text = (
            "No accepted answer provided."
        )

    elif len(cleaned_answers) == 1:

        answer_text = (
            cleaned_answers[0]
        )

    else:

        answer_text = "\n".join(
            f"• {answer}"
            for answer in cleaned_answers
        )


    # ==================================================
    # EMBED
    # ==================================================


    return discord.Embed(
        title="✅ Correct!",
        description=(
            "**Answer**\n"
            f"{answer_text[:1500]}\n\n"
            "**Your Answer**\n"
            f"{submitted_answer[:1000]}\n\n"
            "**Explanation**\n"
            f"{explanation_text}\n\n"
            "**QoTD Streak**\n"
            f"🔥 **{streak_days} {day_label}** 🔥\n\n"
            "**Points**\n"
            f"Correct Answer  **+{base_points}**\n"
            f"Streak Bonus  **+{streak_bonus}**\n\n"
            f"**You earned +{total_points} total points!**"
        ),
        color=discord.Color.green(),
    )


# ==================================================
# INCORRECT ANSWER
# ==================================================


def build_qotd_incorrect_embed(
    submitted_answer: str,
) -> discord.Embed:

    return discord.Embed(
        title="❌ Not Quite. Try again!",
        description=(
            "**Your Answer**\n"
            f"{submitted_answer[:1000]}"
        ),
        color=discord.Color.red(),
    )


# ==================================================
# UNCERTAIN ANSWER
# ==================================================


def build_qotd_uncertain_embed(
    submitted_answer: str,
) -> discord.Embed:

    return discord.Embed(
        title="🤔 Try Rephrasing",
        description=(
            "**Your Answer**\n"
            f"{submitted_answer[:1000]}\n\n"
            "I couldn't confidently evaluate that answer.\n\n"
            "Try answering again with a little more detail "
            "or different wording."
        ),
        color=discord.Color.orange(),
    )


# ==================================================
# ALREADY COMPLETED
# ==================================================


def build_qotd_completed_embed() -> discord.Embed:

    return discord.Embed(
        title="✅ Already Completed",
        description=(
            "You've already completed this "
            "Question of the Day."
        ),
        color=discord.Color.green(),
    )


# ==================================================
# EXPIRED QUESTION
# ==================================================


def build_qotd_expired_embed() -> discord.Embed:

    return discord.Embed(
        title="⌛ Question Expired",
        description=(
            "This Question of the Day has closed.\n\n"
            "The next daily question is now available."
        ),
        color=discord.Color.dark_grey(),
    )


# ==================================================
# UNAVAILABLE QUESTION
# ==================================================


def build_qotd_unavailable_embed() -> discord.Embed:

    return discord.Embed(
        title="Question Unavailable",
        description=(
            "This Question of the Day "
            "is no longer available."
        ),
        color=discord.Color.dark_grey(),
    )
