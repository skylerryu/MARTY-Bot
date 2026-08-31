import discord

from questions.q_manager import (
    get_question_by_id,
)

from questions.q_attempts import (
    get_recent_question_attempts,
)

from questions.q_edit_queue import (
    is_question_marked_for_edit,
)

from questions.q_flag import (
    QuestionAlreadyFlaggedError,
    create_question_flag,
    user_has_open_question_flag,
)


FLAG_REASON_MAX_LENGTH = 1000


# ==================================================
# FLAG MODAL
# ==================================================


class QuestionFlagModal(
    discord.ui.Modal
):

    def __init__(
        self,
        question_bank_id: int,
        context_key: str,
    ):

        super().__init__(
            title=(
                f"Flag Question "
                f"#{question_bank_id}"
            )
        )

        self.question_bank_id = (
            question_bank_id
        )

        self.context_key = (
            context_key
        )

        self.reason_input = (
            discord.ui.TextInput(
                label=(
                    "What is the problem?"
                ),
                placeholder=(
                    "Explain what seems incorrect, "
                    "unclear, or misleading..."
                ),
                style=(
                    discord.TextStyle.paragraph
                ),
                required=True,
                max_length=(
                    FLAG_REASON_MAX_LENGTH
                ),
            )
        )

        self.add_item(
            self.reason_input
        )


    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                (
                    "Questions can only be flagged "
                    "inside the server."
                ),
                ephemeral=True,
            )

            return

        question = (
            get_question_by_id(
                self.question_bank_id
            )
        )

        if question is None:

            await interaction.response.send_message(
                (
                    "⚠️ This question no longer "
                    "exists in the question bank."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # RACE-SAFE DUPLICATE CHECK
        # ==================================================


        if is_question_marked_for_edit(
            self.question_bank_id
        ):

            await interaction.response.send_message(
                (
                    "✅ This question has already "
                    "been sent to the editing queue."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # ATTEMPTS
        # ==================================================


        try:

            attempts = (
                await get_recent_question_attempts(
                    guild_id=(
                        interaction.guild.id
                    ),
                    user_id=(
                        interaction.user.id
                    ),
                    question_bank_id=(
                        self.question_bank_id
                    ),
                    context_key=(
                        self.context_key
                    ),
                    limit=3,
                )
            )

        except Exception as error:

            print(
                "Question attempt lookup error: "
                f"{error!r}"
            )

            attempts = []

        answers = [
            attempt["answer_text"]
            for attempt in attempts
        ]


        # ==================================================
        # SAVE
        # ==================================================


        try:

            await create_question_flag(
                guild_id=(
                    interaction.guild.id
                ),
                question_bank_id=(
                    self.question_bank_id
                ),
                user_id=(
                    interaction.user.id
                ),
                context_key=(
                    self.context_key
                ),
                reason=(
                    str(
                        self.reason_input.value
                    )
                ),
                attempted_answers=answers,
            )

        except QuestionAlreadyFlaggedError:

            await interaction.response.send_message(
                (
                    "🚩 You already have an open "
                    "flag for this question."
                ),
                ephemeral=True,
            )

            return

        except Exception as error:

            print(
                "Flag submission error: "
                f"{error!r}"
            )

            await interaction.response.send_message(
                (
                    "⚠️ M.A.R.T.Y. could not "
                    "submit your flag."
                ),
                ephemeral=True,
            )

            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="🚩 Question Flagged",
                description=(
                    "Your report has been "
                    "submitted for review."
                ),
                color=(
                    discord.Color.orange()
                ),
            ),
            ephemeral=True,
        )


# ==================================================
# GENERIC FLAG ENTRY
# ==================================================


async def open_question_flag_modal(
    interaction: discord.Interaction,
    question_bank_id: int,
    context_key: str,
):

    if interaction.guild is None:

        await interaction.response.send_message(
            (
                "Questions can only be flagged "
                "inside the server."
            ),
            ephemeral=True,
        )

        return

    if is_question_marked_for_edit(
        question_bank_id
    ):

        await interaction.response.send_message(
            (
                "✅ This question has already "
                "been marked for editing and "
                "removed from question selection."
            ),
            ephemeral=True,
        )

        return

    already_flagged = (
        await user_has_open_question_flag(
            guild_id=(
                interaction.guild.id
            ),
            user_id=(
                interaction.user.id
            ),
            question_bank_id=(
                question_bank_id
            ),
        )
    )

    if already_flagged:

        await interaction.response.send_message(
            (
                "🚩 You already have an open "
                "flag for this question."
            ),
            ephemeral=True,
        )

        return

    await interaction.response.send_modal(
        QuestionFlagModal(
            question_bank_id=(
                question_bank_id
            ),
            context_key=(
                context_key
            ),
        )
    )


# ==================================================
# GENERIC FLAG VIEW
# ==================================================


class QuestionFlagView(
    discord.ui.View
):

    def __init__(
        self,
        question_bank_id: int,
        context_key: str,
    ):

        super().__init__(
            timeout=None
        )

        self.question_bank_id = (
            question_bank_id
        )

        self.context_key = (
            context_key
        )

        button = discord.ui.Button(
            label="Flag Question",
            emoji="🚩",
            style=(
                discord.ButtonStyle.secondary
            ),
        )

        button.callback = (
            self.flag_button
        )

        self.add_item(
            button
        )


    async def flag_button(
        self,
        interaction: discord.Interaction,
    ):

        await open_question_flag_modal(
            interaction=interaction,
            question_bank_id=(
                self.question_bank_id
            ),
            context_key=(
                self.context_key
            ),
        )