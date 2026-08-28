import discord

from points.time_helpers import (
    get_current_chicago_date,
)

from points.mechanics.question_of_the_day.qotd import (
    submit_qotd_answer,
)

from points.mechanics.question_of_the_day.qotd_questions import (
    get_qotd,
)

from points.mechanics.question_of_the_day.qotd_completions import (
    has_completed_qotd,
)

from points.mechanics.question_of_the_day.qotd_config import (
    QOTD_ANSWER_MAX_LENGTH,
)

from points.mechanics.question_of_the_day.qotd_display import (
    build_qotd_correct_embed,
    build_qotd_incorrect_embed,
    build_qotd_uncertain_embed,
    build_qotd_completed_embed,
    build_qotd_expired_embed,
    build_qotd_unavailable_embed,
)

from points.progressions.levels.level_up_display import (
    build_level_up_embed,
)

from points.progressions.ranks.rank_up_display import (
    build_rank_up_embed,
)


# ==================================================
# ANSWER MODAL
# ==================================================


class QotdAnswerModal(
    discord.ui.Modal
):
    """
    Private modal used by a student to submit
    their answer to the Question of the Day.
    """

    def __init__(
        self,
        qotd_id: int,
    ):
        super().__init__(
            title="Question of the Day"
        )

        self.qotd_id = qotd_id

        self.answer_input = discord.ui.TextInput(
            label="Your Answer",
            placeholder="Enter your answer here...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=QOTD_ANSWER_MAX_LENGTH,
        )

        self.add_item(
            self.answer_input
        )


    # ==================================================
    # SUBMIT ANSWER
    # ==================================================


    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        """
        Send the submitted answer into the QoTD
        workflow and display the result privately.
        """

        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        if interaction.guild is None:

            await interaction.followup.send(
                (
                    "This question can only "
                    "be answered in the server."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # SUBMITTED ANSWER
        # ==================================================


        submitted_answer = str(
            self.answer_input.value
        )


        # ==================================================
        # PROCESS ANSWER
        # ==================================================


        try:

            result = await submit_qotd_answer(
                qotd_id=self.qotd_id,
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                username=interaction.user.display_name,
                submitted_answer=submitted_answer,
            )

        except Exception as error:

            print(
                "QoTD submission error: "
                f"{error!r}"
            )

            await interaction.followup.send(
                (
                    "⚠️ Something went wrong while "
                    "processing your answer. "
                    "Please try again."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # RESULT STATUS
        # ==================================================


        status = result["status"]


        # ==================================================
        # QUESTION NOT FOUND
        # ==================================================


        if status == "not_found":

            await interaction.followup.send(
                embed=build_qotd_unavailable_embed(),
                ephemeral=True,
            )

            return


        # ==================================================
        # QUESTION EXPIRED
        # ==================================================


        if status == "expired":

            await interaction.followup.send(
                embed=build_qotd_expired_embed(),
                ephemeral=True,
            )

            return


        # ==================================================
        # ALREADY COMPLETED
        # ==================================================


        if status == "already_completed":

            await interaction.followup.send(
                embed=build_qotd_completed_embed(),
                ephemeral=True,
            )

            return


        # ==================================================
        # LLM UNCERTAIN
        # ==================================================


        if status == "uncertain":

            await interaction.followup.send(
                embed=build_qotd_uncertain_embed(
                    submitted_answer=submitted_answer,
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # INCORRECT
        # ==================================================


        if status == "incorrect":

            await interaction.followup.send(
                embed=build_qotd_incorrect_embed(
                    submitted_answer=submitted_answer,
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # CORRECT
        # ==================================================


        if status != "correct":

            raise RuntimeError(
                "Unknown QoTD result status: "
                f"{status}"
            )

        await interaction.followup.send(
            embed=build_qotd_correct_embed(
                submitted_answer=submitted_answer,
                base_points=result["base_points"],
                streak_bonus=result["streak_bonus"],
                streak_days=result["streak_days"],
                explanation=result["explanation"],
            ),
            ephemeral=True,
        )


        # ==================================================
        # PROGRESSION
        # ==================================================


        progression = result[
            "progression"
        ]


        # ==================================================
        # PRIVATE LEVEL UP
        # ==================================================


        if progression["leveled_up"]:

            level_up_embed = build_level_up_embed(
                old_level=progression["old_level"],
                new_level=progression["new_level"],
            )

            await interaction.followup.send(
                embed=level_up_embed,
                ephemeral=True,
            )


        # ==================================================
        # PUBLIC RANK UP
        # ==================================================


        if progression["ranked_up"]:

            await _send_rank_up_message(
                interaction=interaction,
                channel_id=result["channel_id"],
                progression=progression,
            )


# ==================================================
# PERSISTENT ANSWER VIEW
# ==================================================


class QotdAnswerView(
    discord.ui.View
):
    """
    Persistent Discord view containing the
    Answer Question button.

    timeout=None allows the button to survive
    beyond the lifetime of the bot process when
    the view is restored during startup.
    """

    def __init__(
        self,
        qotd_id: int,
    ):
        super().__init__(
            timeout=None
        )

        self.qotd_id = qotd_id

        answer_button = discord.ui.Button(
            label="Answer Question",
            style=discord.ButtonStyle.primary,
            emoji="✏️",
            custom_id=(
                f"qotd:answer:{qotd_id}"
            ),
        )

        answer_button.callback = (
            self.answer_button
        )

        self.add_item(
            answer_button
        )


    # ==================================================
    # ANSWER BUTTON
    # ==================================================


    async def answer_button(
        self,
        interaction: discord.Interaction,
    ):
        """
        Check whether the user can answer this
        QoTD and open the private answer modal.
        """

        if interaction.guild is None:

            await interaction.response.send_message(
                (
                    "This question can only "
                    "be answered in the server."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # GET QUESTION
        # ==================================================


        qotd = await get_qotd(
            self.qotd_id
        )

        if qotd is None:

            await interaction.response.send_message(
                embed=build_qotd_unavailable_embed(),
                ephemeral=True,
            )

            return


        # ==================================================
        # VERIFY SERVER
        # ==================================================


        if (
            qotd["guild_id"]
            != interaction.guild.id
        ):

            await interaction.response.send_message(
                embed=build_qotd_unavailable_embed(),
                ephemeral=True,
            )

            return


        # ==================================================
        # VERIFY DATE
        # ==================================================


        current_date = (
            get_current_chicago_date()
        )

        if (
            qotd["question_date"]
            != current_date.isoformat()
        ):

            await interaction.response.send_message(
                embed=build_qotd_expired_embed(),
                ephemeral=True,
            )

            return


        # ==================================================
        # CHECK COMPLETION
        # ==================================================


        if await has_completed_qotd(
            qotd_id=self.qotd_id,
            user_id=interaction.user.id,
        ):

            await interaction.response.send_message(
                embed=build_qotd_completed_embed(),
                ephemeral=True,
            )

            return


        # ==================================================
        # OPEN MODAL
        # ==================================================


        await interaction.response.send_modal(
            QotdAnswerModal(
                qotd_id=self.qotd_id
            )
        )


# ==================================================
# PUBLIC RANK-UP MESSAGE
# ==================================================


async def _send_rank_up_message(
    interaction: discord.Interaction,
    channel_id: int,
    progression: dict,
):
    """
    Publish a rank-up announcement in the
    channel where the QoTD was posted.
    """

    rank_up_embed = build_rank_up_embed(
        username=interaction.user.display_name,
        new_rank=progression["new_rank"],
        new_level=progression["new_level"],
    )

    channel = interaction.client.get_channel(
        channel_id
    )

    if channel is None:

        try:

            channel = await interaction.client.fetch_channel(
                channel_id
            )

        except (
            discord.Forbidden,
            discord.NotFound,
            discord.HTTPException,
        ):

            return

    try:

        await channel.send(
            embed=rank_up_embed
        )

    except (
        discord.Forbidden,
        discord.HTTPException,
    ):

        pass