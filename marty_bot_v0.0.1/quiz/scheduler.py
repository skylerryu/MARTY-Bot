import discord

from discord.ext import tasks

from bot_config import (
    QUESTION_CHANNEL_ID,
    QUESTION_INTERVAL_SECONDS,
    CATEGORY_NAMES,
)

from features.channel_locks import (
    restore_question_channel_locks,
)

from quiz.attempt_tracker import (
    clear_question_attempts_for_channel,
)

from data.question_bank import (
    get_random_question,
)

from data.database import (
    set_active_question,
)


_client = None


# ==================================================
# AUTOMATIC QUESTION LOOP
# ==================================================

@tasks.loop(
    seconds=QUESTION_INTERVAL_SECONDS
)
async def automatic_question_loop():

    if _client is None:
        return

    channel = _client.get_channel(
        QUESTION_CHANNEL_ID
    )

    if channel is None:

        print(
            "Could not find the question channel."
        )

        return

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    # ------------------------------------------
    # UNLOCK PREVIOUS STUDENTS
    # ------------------------------------------

    failed_restores = (
        await restore_question_channel_locks(
            guild=channel.guild,
            channel=channel
        )
    )

    if failed_restores:

        print(
            "Could not restore all student "
            "permissions. Skipping question."
        )

        return

    # ------------------------------------------
    # CLEAR PREVIOUS ATTEMPTS
    # ------------------------------------------

    clear_question_attempts_for_channel(
        guild_id=channel.guild.id,
        channel_id=channel.id
    )

    # ------------------------------------------
    # CHOOSE RANDOM QUESTION
    # ------------------------------------------

    question_data = get_random_question()

    if question_data is None:

        print(
            "There are no active questions."
        )

        return

    question_id = question_data["id"]
    category_code = question_data["category"]
    question_text = question_data["question"]

    category_name = CATEGORY_NAMES.get(
        category_code,
        category_code
    )

    # ------------------------------------------
    # SET ACTIVE QUESTION
    # ------------------------------------------

    await set_active_question(
        guild_id=channel.guild.id,
        channel_id=channel.id,
        question_id=question_id
    )

    # ------------------------------------------
    # POST QUESTION
    # ------------------------------------------

    await channel.send(
        f"## 🚑 M.A.R.T.Y. Question "
        f"#{question_id}\n"
        f"**Category:** {category_name}\n\n"
        f"{question_text}"
    )

    print(
        f"Automatically posted "
        f"Question #{question_id}."
    )


# ==================================================
# WAIT UNTIL BOT IS READY
# ==================================================

@automatic_question_loop.before_loop
async def before_automatic_question_loop():

    if _client is not None:

        await _client.wait_until_ready()


# ==================================================
# START SCHEDULER
# ==================================================

def start_question_scheduler(
    client: discord.Client
):
    global _client

    _client = client

    if not automatic_question_loop.is_running():
        automatic_question_loop.start()