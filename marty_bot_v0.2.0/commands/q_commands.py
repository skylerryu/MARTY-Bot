import discord
from discord import app_commands

from commands.command_helpers import (
    make_command,
)

from data.questions.q_manager import (
    CATEGORY_NAMES,
    add_question,
    get_question_by_id,
    get_random_question,
)

from points.mechanics.random_speed_questions.random_speed_questions import (
    set_active_speed_question,
)


# ==================================================
# QUESTION CATEGORY CHOICES
# ==================================================


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


# ==================================================
# PARSE ACCEPTED ANSWERS
# ==================================================


def _parse_accepted_answers(
    accepted_answers: str,
) -> list[str]:
    """
    Convert pipe-separated accepted answers
    into a list.

    Example:

        respiratory depression|pinpoint pupils
    """

    return [
        answer.strip()
        for answer
        in accepted_answers.split("|")
        if answer.strip()
    ]


# ==================================================
# REGISTER QUESTION COMMANDS
# ==================================================


def register_question_commands(
    tree: app_commands.CommandTree,
    guild: discord.Object,
):
    """
    Register commands for M.A.R.T.Y.'s
    master question bank.
    """

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
    @app_commands.describe(
        category="Question category.",
        question="Question shown to students.",
        accepted_answers=(
            "Correct answers separated by |"
        ),
        explanation=(
            "Explanation shown after "
            "the question is answered."
        ),
    )
    async def addquestion(
        interaction: discord.Interaction,
        category: app_commands.Choice[str],
        question: str,
        accepted_answers: str,
        explanation: str,
    ):


        # ==================================================
        # SERVER CHECK
        # ==================================================


        if interaction.guild is None:

            await interaction.response.send_message(
                (
                    "This command must be used "
                    "inside a server."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # ADMIN CHECK
        # ==================================================


        if (
            not interaction.user
            .guild_permissions
            .administrator
        ):

            await interaction.response.send_message(
                (
                    "You do not have permission "
                    "to add questions."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # PARSE ANSWERS
        # ==================================================


        parsed_answers = (
            _parse_accepted_answers(
                accepted_answers
            )
        )

        if not parsed_answers:

            await interaction.response.send_message(
                (
                    "You must provide at least "
                    "one accepted answer."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # SAVE QUESTION
        # ==================================================


        try:

            new_question = add_question(
                category=category.value,
                question_text=question,
                accepted_answers=parsed_answers,
                explanation=explanation,
            )

        except ValueError as error:

            await interaction.response.send_message(
                str(error),
                ephemeral=True,
            )

            return

        except OSError as error:

            print(
                "Question bank write error: "
                f"{error!r}"
            )

            await interaction.response.send_message(
                (
                    "⚠️ M.A.R.T.Y. could not "
                    "save the question."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # SUCCESS
        # ==================================================


        await interaction.response.send_message(
            (
                f"✅ **Question #{new_question['id']} "
                "added.**\n\n"
                f"Category: **{category.name}**\n"
                f"Accepted answers: "
                f"**{len(new_question['accepted_answers'])}**"
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
    @app_commands.describe(
        category=(
            "Optionally choose a question category."
        ),
        question_id=(
            "Optionally post a specific question ID."
        ),
    )
    async def question(
        interaction: discord.Interaction,
        category: (
            app_commands.Choice[str] | None
        ) = None,
        question_id: int | None = None,
    ):


        # ==================================================
        # SERVER CHECK
        # ==================================================


        if interaction.guild is None:

            await interaction.response.send_message(
                (
                    "This command must be used "
                    "inside a server."
                ),
                ephemeral=True,
            )

            return


        if interaction.channel_id is None:

            await interaction.response.send_message(
                (
                    "M.A.R.T.Y. could not determine "
                    "which channel to use."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # DO NOT ALLOW CATEGORY + ID
        # ==================================================


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
        # SPECIFIC QUESTION
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
                        "is currently inactive."
                    ),
                    ephemeral=True,
                )

                return


        # ==================================================
        # RANDOM QUESTION
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
                        "There are no active "
                        "questions matching "
                        "that selection."
                    ),
                    ephemeral=True,
                )

                return


        # ==================================================
        # QUESTION INFORMATION
        # ==================================================


        selected_question_id = (
            question_data["id"]
        )

        category_code = (
            question_data["category"]
        )

        question_text = (
            question_data["question"]
        )

        category_name = (
            CATEGORY_NAMES.get(
                category_code,
                category_code,
            )
        )


        # ==================================================
        # MAKE QUESTION ACTIVE
        # ==================================================


        await set_active_speed_question(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            question_id=selected_question_id,
        )


        # ==================================================
        # POST QUESTION
        # ==================================================


        await interaction.response.send_message(
            (
                "## 🚑 M.A.R.T.Y. Question "
                f"#{selected_question_id}\n"
                f"**Category:** "
                f"{category_name}\n\n"
                f"{question_text}"
            )
        )
