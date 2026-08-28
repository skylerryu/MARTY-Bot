import discord

from discord import app_commands

from bot_config import CATEGORY_NAMES

from data.database import (
    ensure_user,
    get_points,
    get_weekly_points,
    get_leaderboard,
    get_weekly_leaderboard,
    get_golden_spatulas,
    award_previous_week_winner,
    set_active_question,
)

from data.question_bank import (
    get_random_question,
    get_question_by_id,
    add_question,
)

from quiz.attempt_tracker import (
    clear_question_attempts_for_channel,
)

from features.channel_locks import (
    restore_question_channel_locks,
)

from services.llm import (
    test_llm,
)


# ==================================================
# QUESTION CATEGORIES
# ==================================================

QUESTION_CATEGORIES = [
    app_commands.Choice(
        name=display_name,
        value=category_code
    )
    for category_code, display_name
    in CATEGORY_NAMES.items()
]


# ==================================================
# REGISTER COMMANDS
# ==================================================

def register_commands(
    client: discord.Client,
    guild: discord.Object
):

    # ==================================================
    # /PING
    # ==================================================

    @client.tree.command(
        name="ping",
        description="Check whether M.A.R.T.Y. is online.",
        guild=guild
    )
    async def ping(
        interaction: discord.Interaction
    ):

        await ensure_user(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            username=interaction.user.display_name
        )

        latency_ms = round(
            client.latency * 1000
        )

        await interaction.response.send_message(
            f"🚑 **M.A.R.T.Y. is online!**\n"
            f"Latency: `{latency_ms} ms`"
        )


    # ==================================================
    # /POINTS
    # ==================================================

    @client.tree.command(
        name="points",
        description="View your M.A.R.T.Y. points.",
        guild=guild
    )
    async def points(
        interaction: discord.Interaction
    ):

        await ensure_user(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            username=interaction.user.display_name
        )

        weekly_total = await get_weekly_points(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id
        )

        all_time_total = await get_points(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id
        )

        spatulas = await get_golden_spatulas(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id
        )

        await interaction.response.send_message(
            f"🚑 **{interaction.user.display_name}'s "
            f"M.A.R.T.Y. Stats**\n\n"
            f"**Weekly Points:** {weekly_total}\n"
            f"**All-Time Points:** {all_time_total}\n"
            f"**Golden Spatulas:** {spatulas} 🍳"
        )


    # ==================================================
    # /LEADERBOARD
    # ==================================================

    @client.tree.command(
        name="leaderboard",
        description="View the M.A.R.T.Y. leaderboards.",
        guild=guild
    )
    async def leaderboard(
        interaction: discord.Interaction
    ):

        weekly_rows = await get_weekly_leaderboard(
            guild_id=interaction.guild.id,
            limit=10
        )

        all_time_rows = await get_leaderboard(
            guild_id=interaction.guild.id,
            limit=10
        )

        medals = [
            "🥇",
            "🥈",
            "🥉"
        ]

        # ------------------------------------------
        # WEEKLY LEADERBOARD
        # ------------------------------------------

        weekly_lines = []

        for position, row in enumerate(
            weekly_rows,
            start=1
        ):
            user_id, username, points = row

            if position <= 3:
                prefix = medals[position - 1]
            else:
                prefix = f"{position}."

            weekly_lines.append(
                f"{prefix} "
                f"**{username}** — "
                f"{points} pts"
            )

        # ------------------------------------------
        # ALL-TIME LEADERBOARD
        # ------------------------------------------

        all_time_lines = []

        for position, row in enumerate(
            all_time_rows,
            start=1
        ):
            user_id, username, points = row

            if position <= 3:
                prefix = medals[position - 1]
            else:
                prefix = f"{position}."

            all_time_lines.append(
                f"{prefix} "
                f"**{username}** — "
                f"{points} pts"
            )

        weekly_text = (
            "\n".join(weekly_lines)
            if weekly_lines
            else "No points yet."
        )

        all_time_text = (
            "\n".join(all_time_lines)
            if all_time_lines
            else "No points yet."
        )

        await interaction.response.send_message(
            "## 🍳 Weekly Leaderboard\n"
            f"{weekly_text}\n\n"
            "## 🏆 All-Time Leaderboard\n"
            f"{all_time_text}"
        )


    # ==================================================
    # /AWARDLASTWEEK
    # ==================================================

    @client.tree.command(
        name="awardlastweek",
        description="Award last week's Golden Spatula.",
        guild=guild
    )
    async def awardlastweek(
        interaction: discord.Interaction
    ):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "You do not have permission "
                "to use this command.",
                ephemeral=True
            )

            return

        result = await award_previous_week_winner(
            guild_id=interaction.guild.id
        )

        if result is None:

            await interaction.response.send_message(
                "There were no point transactions "
                "from last week.",
                ephemeral=True
            )

            return

        if not result["awarded"]:

            await interaction.response.send_message(
                "Last week's Golden Spatula "
                "has already been awarded.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🍳 **Golden Spatula Awarded!**\n\n"
            f"**{result['username']}** "
            f"is Chef of the Week!\n"
            f"Weekly Points: **{result['points']}**"
        )


    # ==================================================
    # /ADDQUESTION
    # ==================================================

    @client.tree.command(
        name="addquestion",
        description="Add a question to the M.A.R.T.Y. question bank.",
        guild=guild
    )
    @app_commands.choices(
        category=QUESTION_CATEGORIES
    )
    async def addquestion(
        interaction: discord.Interaction,
        category: app_commands.Choice[str],
        question: str,
        answer: str,
        explanation: str
    ):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "You do not have permission "
                "to add questions.",
                ephemeral=True
            )

            return

        new_question = add_question(
            category=category.value,
            question_text=question,
            correct_answer=answer,
            explanation=explanation
        )

        await interaction.response.send_message(
            f"✅ Question #{new_question['id']} "
            f"added to **{category.name}**.",
            ephemeral=True
        )


    # ==================================================
    # /QUESTION
    #
    # Manual question posting for admins/testing.
    # ==================================================

    @client.tree.command(
        name="question",
        description="Manually post a M.A.R.T.Y. question.",
        guild=guild
    )
    @app_commands.choices(
        category=QUESTION_CATEGORIES
    )
    async def question(
        interaction: discord.Interaction,
        category: app_commands.Choice[str] | None = None,
        question_id: int | None = None
    ):

        # ------------------------------------------
        # ADMIN ONLY
        # ------------------------------------------

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "You do not have permission "
                "to manually post questions.",
                ephemeral=True
            )

            return

        # ------------------------------------------
        # REQUIRE TEXT CHANNEL
        # ------------------------------------------

        if not isinstance(
            interaction.channel,
            discord.TextChannel
        ):

            await interaction.response.send_message(
                "M.A.R.T.Y. questions must be "
                "posted in a standard text channel.",
                ephemeral=True
            )

            return

        # ------------------------------------------
        # DON'T ALLOW BOTH PARAMETERS
        # ------------------------------------------

        if (
            category is not None
            and question_id is not None
        ):

            await interaction.response.send_message(
                "Choose either a category "
                "or a question ID, not both.",
                ephemeral=True
            )

            return

        # ------------------------------------------
        # SPECIFIC QUESTION
        # ------------------------------------------

        if question_id is not None:

            question_data = get_question_by_id(
                question_id
            )

            if question_data is None:

                await interaction.response.send_message(
                    f"Question #{question_id} "
                    f"was not found.",
                    ephemeral=True
                )

                return

        # ------------------------------------------
        # RANDOM QUESTION
        # ------------------------------------------

        else:

            category_value = (
                category.value
                if category is not None
                else None
            )

            question_data = get_random_question(
                category=category_value
            )

            if question_data is None:

                await interaction.response.send_message(
                    "There are no active questions "
                    "matching that selection.",
                    ephemeral=True
                )

                return

        # ------------------------------------------
        # QUESTION INFORMATION
        # ------------------------------------------

        selected_question_id = (
            question_data["id"]
        )

        category_code = (
            question_data["category"]
        )

        question_text = (
            question_data["question"]
        )

        category_name = CATEGORY_NAMES.get(
            category_code,
            category_code
        )

        # Permission changes can take a moment.
        await interaction.response.defer()

        # ------------------------------------------
        # UNLOCK STUDENTS FROM PREVIOUS QUESTION
        # ------------------------------------------

        failed_restores = (
            await restore_question_channel_locks(
                guild=interaction.guild,
                channel=interaction.channel
            )
        )

        if failed_restores:

            await interaction.followup.send(
                "⚠️ M.A.R.T.Y. could not restore "
                "all student channel permissions.\n\n"
                "The new question was not posted.",
                ephemeral=True
            )

            return

        # ------------------------------------------
        # RESET ATTEMPTS
        # ------------------------------------------

        clear_question_attempts_for_channel(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id
        )

        # ------------------------------------------
        # ACTIVATE QUESTION
        # ------------------------------------------

        await set_active_question(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            question_id=selected_question_id
        )

        # ------------------------------------------
        # POST QUESTION
        # ------------------------------------------

        await interaction.followup.send(
            f"## 🚑 M.A.R.T.Y. Question "
            f"#{selected_question_id}\n"
            f"**Category:** "
            f"{category_name}\n\n"
            f"{question_text}"
        )


    # ==================================================
    # /LLMTEST
    # ==================================================

    @client.tree.command(
        name="llmtest",
        description="Test M.A.R.T.Y.'s LLM connection.",
        guild=guild
    )
    async def llmtest(
        interaction: discord.Interaction
    ):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "You do not have permission "
                "to use this command.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            result = await test_llm()

            await interaction.followup.send(
                result,
                ephemeral=True
            )

        except Exception as error:

            print(
                f"LLM test failed: {error}"
            )

            await interaction.followup.send(
                "⚠️ M.A.R.T.Y. could not "
                "connect to the LLM.",
                ephemeral=True
            )