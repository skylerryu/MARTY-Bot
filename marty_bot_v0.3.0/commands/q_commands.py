import discord

from discord import (
    app_commands,
)

from commands.command_helpers import (
    make_command,
)

from questions.q_manager import (
    CATEGORY_NAMES,
    add_question,
    get_question_by_id,
    get_random_question,
)

from questions.q_edit_queue import (
    is_question_marked_for_edit,
)

from questions.q_flag_ui import (
    QuestionFlagView,
)

from points.mechanics.random_speed_questions.random_speed_questions import (
    set_active_speed_question,
)


QUESTION_CATEGORIES = [
    app_commands.Choice(
        name=category_name,
        value=category_code,
    )
    for (
        category_code,
        category_name,
    )
    in CATEGORY_NAMES.items()
]


def _parse_accepted_answers(
    accepted_answers: str,
) -> list[str]:

    return [
        answer.strip()
        for answer
        in accepted_answers.split("|")
        if answer.strip()
    ]


def register_question_commands(
    tree: app_commands.CommandTree,
    guild: discord.Object,
):

    command = make_command(
        tree=tree,
        guild=guild,
    )


    # ==================================================
    # ADD QUESTION
    # ==================================================


    @command(
        name="addquestion",
        description=(
            "Add a question to the "
            "M.A.R.T.Y. question bank."
        ),
    )
    @app_commands.choices(
        category=QUESTION_CATEGORIES
    )
    async def addquestion(
        interaction: discord.Interaction,
        category: app_commands.Choice[str],
        question: str,
        accepted_answers: str,
        explanation: str,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "This command must be used in a server.",
                ephemeral=True,
            )

            return

        if (
            not interaction.user
            .guild_permissions
            .administrator
        ):

            await interaction.response.send_message(
                "You do not have permission to add questions.",
                ephemeral=True,
            )

            return

        parsed_answers = (
            _parse_accepted_answers(
                accepted_answers
            )
        )

        if not parsed_answers:

            await interaction.response.send_message(
                "At least one accepted answer is required.",
                ephemeral=True,
            )

            return

        try:

            new_question = add_question(
                category=category.value,
                question_text=question,
                accepted_answers=parsed_answers,
                explanation=explanation,
            )

        except (
            ValueError,
            OSError,
        ) as error:

            await interaction.response.send_message(
                f"⚠️ {error}",
                ephemeral=True,
            )

            return

        question_id = (
            new_question["id"]
        )

        await interaction.response.send_message(
            (
                f"✅ **Question #{question_id} added.**"
            ),
            ephemeral=True,
        )


    # ==================================================
    # POST SPEED QUESTION
    # ==================================================


    @command(
        name="question",
        description=(
            "Post a M.A.R.T.Y. speed question."
        ),
    )
    @app_commands.choices(
        category=QUESTION_CATEGORIES
    )
    async def question(
        interaction: discord.Interaction,
        category: (
            app_commands.Choice[str]
            | None
        ) = None,
        question_id: int | None = None,
    ):

        if (
            interaction.guild is None
            or interaction.channel_id is None
        ):

            await interaction.response.send_message(
                "This command must be used in a server channel.",
                ephemeral=True,
            )

            return

        if (
            category is not None
            and question_id is not None
        ):

            await interaction.response.send_message(
                (
                    "Choose either a category "
                    "or a question ID, not both."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # SPECIFIC ID
        # ==================================================


        if question_id is not None:

            question_data = (
                get_question_by_id(
                    question_id
                )
            )

            if question_data is None:

                await interaction.response.send_message(
                    (
                        f"Question #{question_id} "
                        "was not found."
                    ),
                    ephemeral=True,
                )

                return

            if not question_data.get(
                "active",
                True,
            ):

                await interaction.response.send_message(
                    (
                        f"Question #{question_id} "
                        "is inactive."
                    ),
                    ephemeral=True,
                )

                return

            if is_question_marked_for_edit(
                question_id
            ):

                await interaction.response.send_message(
                    (
                        f"⚠️ **Question #{question_id} "
                        "is currently marked for editing.**\n\n"
                        "It cannot be posted until an "
                        "administrator resolves it in "
                        "`/flaggededit`."
                    ),
                    ephemeral=True,
                )

                return


        # ==================================================
        # RANDOM
        # ==================================================


        else:

            category_value = (
                category.value
                if category is not None
                else None
            )

            question_data = (
                get_random_question(
                    category=category_value
                )
            )

            if question_data is None:

                await interaction.response.send_message(
                    (
                        "There are no eligible "
                        "questions matching that selection."
                    ),
                    ephemeral=True,
                )

                return


        # ==================================================
        # POST
        # ==================================================


        selected_id = (
            question_data["id"]
        )

        category_code = (
            question_data["category"]
        )

        category_name = (
            CATEGORY_NAMES.get(
                category_code,
                category_code,
            )
        )

        context_key = (
            await set_active_speed_question(
                guild_id=(
                    interaction.guild.id
                ),
                channel_id=(
                    interaction.channel_id
                ),
                question_id=(
                    selected_id
                ),
            )
        )

        view = QuestionFlagView(
            question_bank_id=(
                selected_id
            ),
            context_key=(
                context_key
            ),
        )

        await interaction.response.send_message(
            (
                "## 🚑 M.A.R.T.Y. Question "
                f"#{selected_id}\n"
                f"**Category:** {category_name}\n\n"
                f"{question_data['question']}"
            ),
            view=view,
        )