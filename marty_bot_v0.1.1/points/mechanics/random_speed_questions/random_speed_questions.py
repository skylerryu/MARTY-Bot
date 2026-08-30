import asyncio

from datetime import datetime, timezone

import aiosqlite
import discord

from data.database import DB_PATH

from data.questions.q_manager import (
    get_question_by_id,
)

from points.points_operations.add_points import (
    add_points,
)

from services.llm import (
    grade_answer_with_llm,
)


# ==================================================
# SPEED QUESTION POINTS
# ==================================================


SPEED_QUESTION_BASE_POINTS = 25

SPEED_QUESTION_30_SECOND_BONUS = 25
SPEED_QUESTION_1_MINUTE_BONUS = 10
SPEED_QUESTION_3_MINUTE_BONUS = 5


# ==================================================
# GRADING LOCKS
# ==================================================


_grading_locks = {}


def _get_grading_lock(
    guild_id: int,
    channel_id: int,
) -> asyncio.Lock:
    """
    Return the grading lock for a particular
    Discord channel.
    """

    key = (
        guild_id,
        channel_id,
    )

    if key not in _grading_locks:

        _grading_locks[key] = (
            asyncio.Lock()
        )

    return _grading_locks[key]


# ==================================================
# SET ACTIVE QUESTION
# ==================================================


async def set_active_speed_question(
    guild_id: int,
    channel_id: int,
    question_id: int,
):
    """
    Set the currently active speed question
    for a Discord channel.
    """

    posted_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await db.execute(
            """
            INSERT INTO active_speed_questions (
                guild_id,
                channel_id,
                question_id,
                posted_at,
                answered_by,
                answered_at
            )

            VALUES (
                ?,
                ?,
                ?,
                ?,
                NULL,
                NULL
            )

            ON CONFLICT (
                guild_id,
                channel_id
            )

            DO UPDATE SET
                question_id = excluded.question_id,
                posted_at = excluded.posted_at,
                answered_by = NULL,
                answered_at = NULL
            """,
            (
                guild_id,
                channel_id,
                question_id,
                posted_at,
            ),
        )

        await db.commit()


# ==================================================
# GET ACTIVE QUESTION
# ==================================================


async def get_active_speed_question(
    guild_id: int,
    channel_id: int,
) -> dict | None:
    """
    Return the active speed question for a
    Discord channel.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            SELECT
                question_id,
                posted_at,
                answered_by,
                answered_at

            FROM active_speed_questions

            WHERE guild_id = ?
              AND channel_id = ?
            """,
            (
                guild_id,
                channel_id,
            ),
        )

        row = await cursor.fetchone()

    if row is None:
        return None

    return {
        "question_id": row[0],
        "posted_at": row[1],
        "answered_by": row[2],
        "answered_at": row[3],
    }


# ==================================================
# MARK QUESTION ANSWERED
# ==================================================


async def mark_speed_question_answered(
    guild_id: int,
    channel_id: int,
    question_id: int,
    user_id: int,
) -> bool:
    """
    Attempt to claim the active question for
    the first student who answers correctly.
    """

    answered_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            UPDATE active_speed_questions

            SET
                answered_by = ?,
                answered_at = ?

            WHERE guild_id = ?
              AND channel_id = ?
              AND question_id = ?
              AND answered_by IS NULL
            """,
            (
                user_id,
                answered_at,
                guild_id,
                channel_id,
                question_id,
            ),
        )

        await db.commit()

        return cursor.rowcount > 0


# ==================================================
# BUILD LLM ANSWER KEY
# ==================================================


def _build_answer_key(
    accepted_answers: list[str],
) -> str:

    if len(accepted_answers) == 1:

        return accepted_answers[0]

    answers = "\n".join(
        f"- {answer}"
        for answer
        in accepted_answers
    )

    return (
        "Any ONE of the following answers "
        "should be considered acceptable:\n"
        f"{answers}"
    )


# ==================================================
# BUILD ANSWER DISPLAY
# ==================================================


def _build_answer_display(
    accepted_answers: list[str],
) -> str:

    if len(accepted_answers) == 1:

        return accepted_answers[0]

    return "\n".join(
        f"- {answer}"
        for answer
        in accepted_answers
    )


# ==================================================
# RESPONSE TIME
# ==================================================


def _get_response_seconds(
    posted_at: str,
    message_created_at: datetime,
) -> float:

    posted_datetime = (
        datetime.fromisoformat(
            posted_at
        )
    )

    if posted_datetime.tzinfo is None:

        posted_datetime = (
            posted_datetime.replace(
                tzinfo=timezone.utc
            )
        )

    response_seconds = (
        message_created_at
        - posted_datetime
    ).total_seconds()

    return max(
        0.0,
        response_seconds,
    )


# ==================================================
# SPEED BONUS
# ==================================================


def get_speed_question_bonus(
    response_seconds: float,
) -> int:

    if response_seconds <= 30:

        return (
            SPEED_QUESTION_30_SECOND_BONUS
        )

    if response_seconds <= 60:

        return (
            SPEED_QUESTION_1_MINUTE_BONUS
        )

    if response_seconds <= 180:

        return (
            SPEED_QUESTION_3_MINUTE_BONUS
        )

    return 0


# ==================================================
# REMOVE REACTION
# ==================================================


async def _remove_reaction(
    message: discord.Message,
    emoji: str,
    bot_user,
):

    if bot_user is None:
        return

    try:

        await message.remove_reaction(
            emoji,
            bot_user,
        )

    except discord.HTTPException:

        pass


# ==================================================
# PROCESS SPEED QUESTION MESSAGE
# ==================================================


async def process_speed_question_message(
    message: discord.Message,
    bot_user,
):


    # ==================================================
    # IGNORE BOT MESSAGES
    # ==================================================

    if message.author.bot:
        return


    # ==================================================
    # IGNORE DIRECT MESSAGES
    # ==================================================

    if message.guild is None:
        return


    # ==================================================
    # MESSAGE CONTENT
    # ==================================================

    content = (
        message.content.strip()
    )

    if not content:
        return

    if not any(
        character.isalnum()
        for character in content
    ):

        return


    # ==================================================
    # CHECK ACTIVE QUESTION
    # ==================================================

    active_question = (
        await get_active_speed_question(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
        )
    )

    if active_question is None:
        return

    if (
        active_question["answered_by"]
        is not None
    ):

        return


    # ==================================================
    # GRADING QUEUE
    # ==================================================

    lock = _get_grading_lock(
        guild_id=message.guild.id,
        channel_id=message.channel.id,
    )


    async with lock:


        # ==================================================
        # RE-CHECK ACTIVE QUESTION
        # ==================================================

        active_question = (
            await get_active_speed_question(
                guild_id=message.guild.id,
                channel_id=message.channel.id,
            )
        )

        if active_question is None:
            return

        if (
            active_question["answered_by"]
            is not None
        ):

            return


        question_id = (
            active_question[
                "question_id"
            ]
        )


        # ==================================================
        # GET QUESTION
        # ==================================================

        question_data = (
            get_question_by_id(
                question_id
            )
        )

        if question_data is None:
            return


        question_text = (
            question_data[
                "question"
            ]
        )

        accepted_answers = (
            question_data[
                "accepted_answers"
            ]
        )

        explanation = (
            question_data.get(
                "explanation",
                "",
            )
        )


        correct_answer = (
            _build_answer_key(
                accepted_answers
            )
        )


        # ==================================================
        # RESPONSE TIME
        # ==================================================

        response_seconds = (
            _get_response_seconds(
                posted_at=(
                    active_question[
                        "posted_at"
                    ]
                ),
                message_created_at=(
                    message.created_at
                ),
            )
        )


        # ==================================================
        # GRADING REACTION
        # ==================================================

        try:

            await message.add_reaction(
                "⏳"
            )

        except discord.HTTPException:

            pass


        # ==================================================
        # LLM
        # ==================================================

        try:

            grade = (
                await grade_answer_with_llm(
                    question=question_text,
                    correct_answer=correct_answer,
                    student_answer=content,
                )
            )

        except Exception as error:

            print(
                "Speed question grading error: "
                f"{error!r}"
            )

            try:

                await message.add_reaction(
                    "⚠️"
                )

            except discord.HTTPException:

                pass

            await _remove_reaction(
                message=message,
                emoji="⏳",
                bot_user=bot_user,
            )

            return


        # ==================================================
        # DEVELOPMENT LOGGING
        # ==================================================

        print(
            "\n"
            "Speed Question Answer\n"
            f"Question #{question_id}\n"
            f"Student: "
            f"{message.author.display_name}\n"
            f"Answer: {content}\n"
            f"Response Time: "
            f"{response_seconds:.2f} seconds\n"
            f"Correct: {grade.correct}\n"
            f"Confidence: {grade.confidence}\n"
            f"Reason: {grade.reason}\n"
        )


        # ==================================================
        # INCORRECT
        # ==================================================

        if not grade.correct:

            try:

                await message.add_reaction(
                    "❌"
                )

            except discord.HTTPException:

                pass

            await _remove_reaction(
                message=message,
                emoji="⏳",
                bot_user=bot_user,
            )

            return


        # ==================================================
        # CLAIM QUESTION
        # ==================================================

        won = (
            await mark_speed_question_answered(
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                question_id=question_id,
                user_id=message.author.id,
            )
        )

        if not won:

            await _remove_reaction(
                message=message,
                emoji="⏳",
                bot_user=bot_user,
            )

            return


        # ==================================================
        # POINTS
        # ==================================================

        speed_bonus = (
            get_speed_question_bonus(
                response_seconds
            )
        )

        total_points = (
            SPEED_QUESTION_BASE_POINTS
            + speed_bonus
        )


        # ==================================================
        # UNIQUE SOURCE KEY
        # ==================================================

        source_key = (
            "speed_question:"
            f"{message.channel.id}:"
            f"{question_id}:"
            f"{active_question['posted_at']}"
        )


        # ==================================================
        # AWARD POINTS
        # ==================================================

        try:

            await add_points(
                guild_id=message.guild.id,
                user_id=message.author.id,
                amount=total_points,
                reason=(
                    "Random speed question"
                ),
                username=(
                    message.author.display_name
                ),
                source_key=source_key,
            )

        except Exception as error:

            print(
                "Speed question point award error: "
                f"{error!r}"
            )


        # ==================================================
        # WINNER REACTION
        # ==================================================

        try:

            await message.add_reaction(
                "✅"
            )

        except discord.HTTPException:

            pass


        await _remove_reaction(
            message=message,
            emoji="⏳",
            bot_user=bot_user,
        )


        # ==================================================
        # ANSWER DISPLAY
        # ==================================================

        answer_display = (
            _build_answer_display(
                accepted_answers
            )
        )


        # ==================================================
        # WINNER EMBED
        # ==================================================

        winner_embed = discord.Embed(
            title=(
                f"✅ Correct!  "
                f"+{total_points} Points"
            ),
            description=(
                f"{message.author.mention} "
                f"answered in "
                f"**{response_seconds:.1f} seconds**."
            ),
            color=discord.Color.green(),
        )


        winner_embed.add_field(
            name="💡 Answer",
            value=answer_display,
            inline=False,
        )


        winner_embed.add_field(
            name="🏆 Base",
            value=(
                f"**+"
                f"{SPEED_QUESTION_BASE_POINTS}"
                f"**"
            ),
            inline=True,
        )

        winner_embed.add_field(
            name="⚡ Speed Bonus",
            value=(
                f"**+{speed_bonus}**"
            ),
            inline=True,
        )

        winner_embed.add_field(
            name="🎯 Total",
            value=(
                f"**+{total_points} pts**"
            ),
            inline=True,
        )


        winner_embed.add_field(
            name="📚 Explanation",
            value=explanation,
            inline=False,
        )


        # ==================================================
        # SEND WINNER MESSAGE
        # ==================================================

        await message.reply(
            embed=winner_embed
        )