import asyncio

import discord

from features.activity import handle_activity

from features.channel_locks import (
    lock_member_from_question_channel,
    delete_extra_question_message,
)

from data.database import (
    get_active_question,
    mark_question_answered,
)

from services.llm import (
    grade_answer_with_llm,
)

from data.question_bank import (
    get_question_by_id,
)

from quiz.attempt_tracker import (
    record_question_attempt,
)

from quiz.reactions import (
    add_reaction,
    remove_bot_reaction,
)

from quiz.scoring import (
    award_question_points,
)


# ==================================================
# GRADING LOCKS
# ==================================================

grading_locks = {}


def get_grading_lock(
    guild_id: int,
    channel_id: int
):
    key = (
        guild_id,
        channel_id
    )

    if key not in grading_locks:
        grading_locks[key] = asyncio.Lock()

    return grading_locks[key]


# ==================================================
# QUESTION MESSAGE HANDLER
# ==================================================

async def handle_question_message(
    client: discord.Client,
    message: discord.Message
):
    content = message.content.strip()

    if not content:
        return

    if message.guild is None:
        return

    # ------------------------------------------
    # CHECK FOR ACTIVE QUESTION
    # ------------------------------------------

    active_question = await get_active_question(
        guild_id=message.guild.id,
        channel_id=message.channel.id
    )

    # No active question = normal activity
    if active_question is None:

        await handle_activity(
            message
        )

        return

    (
        question_id,
        posted_at,
        answered_by
    ) = active_question

    # Question is already finished
    if answered_by is not None:
        return

    if not isinstance(
        message.channel,
        discord.TextChannel
    ):
        return

    # ------------------------------------------
    # RECORD ATTEMPT
    # ------------------------------------------

    allowed, attempts_used = record_question_attempt(
        guild_id=message.guild.id,
        channel_id=message.channel.id,
        question_id=question_id,
        posted_at=posted_at,
        user_id=message.author.id
    )

    # Extra messages are deleted
    if not allowed:

        await delete_extra_question_message(
            message
        )

        return

    # ------------------------------------------
    # LOCK STUDENT
    # ------------------------------------------

    if isinstance(
        message.author,
        discord.Member
    ):

        await lock_member_from_question_channel(
            channel=message.channel,
            member=message.author
        )

    # ------------------------------------------
    # GRADING QUEUE
    # ------------------------------------------

    lock = get_grading_lock(
        guild_id=message.guild.id,
        channel_id=message.channel.id
    )

    async with lock:

        # Re-check question after waiting
        active_question = await get_active_question(
            guild_id=message.guild.id,
            channel_id=message.channel.id
        )

        if active_question is None:
            return

        (
            current_question_id,
            current_posted_at,
            answered_by
        ) = active_question

        # New question replaced this one
        if (
            current_question_id != question_id
            or current_posted_at != posted_at
        ):
            return

        # Someone else already won
        if answered_by is not None:
            return

        # ------------------------------------------
        # LOAD QUESTION
        # ------------------------------------------

        question_data = get_question_by_id(
            question_id
        )

        if question_data is None:
            return

        question_text = (
            question_data["question"]
        )

        correct_answer = (
            question_data["answer"]
        )

        explanation = (
            question_data["explanation"]
        )

        # ------------------------------------------
        # GRADE ANSWER
        # ------------------------------------------

        await add_reaction(
            message,
            "⏳"
        )

        try:

            grade = await grade_answer_with_llm(
                question=question_text,
                correct_answer=correct_answer,
                student_answer=content
            )

        except Exception as error:

            print(
                f"Error grading answer: {error}"
            )

            await add_reaction(
                message,
                "⚠️"
            )

            await remove_bot_reaction(
                client,
                message,
                "⏳"
            )

            return

        # ------------------------------------------
        # INCORRECT
        # ------------------------------------------

        if not grade.correct:

            await add_reaction(
                message,
                "❌"
            )

            await remove_bot_reaction(
                client,
                message,
                "⏳"
            )

            return

        # ------------------------------------------
        # CLAIM WINNER
        # ------------------------------------------

        won = await mark_question_answered(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            user_id=message.author.id
        )

        if not won:

            await remove_bot_reaction(
                client,
                message,
                "⏳"
            )

            return

        # ------------------------------------------
        # SCORE
        # ------------------------------------------

        score = await award_question_points(
            message=message,
            posted_at=posted_at
        )

        # ------------------------------------------
        # SUCCESS
        # ------------------------------------------

        await add_reaction(
            message,
            "✅"
        )

        await remove_bot_reaction(
            client,
            message,
            "⏳"
        )

        speed_text = ""

        if score["speed_bonus"] > 0:

            speed_text = (
                f"\n⚡ **Speed Bonus:** "
                f"+{score['speed_bonus']}"
            )

        await message.reply(
            f"✅ **Correct, "
            f"{message.author.mention}!**\n\n"

            f"**Answer:** "
            f"{correct_answer}\n"

            f"**Explanation:** "
            f"{explanation}\n\n"

            f"🏆 **Correct Answer:** "
            f"+{score['base_points']}"

            f"{speed_text}\n"

            f"**Total Earned:** "
            f"+{score['total_points']} points"
        )