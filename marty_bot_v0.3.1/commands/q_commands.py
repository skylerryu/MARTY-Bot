import math

import discord

from discord import (
    app_commands,
)

from bot_config import (
    RANDOM_QUESTION_CHANNEL_ID,
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

from points.mechanics.random_speed_questions.rsq import (
    SpeedQuestionTooSoonError,
    post_speed_question,
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
# PARSE ANSWERS
# ==================================================


def _parse_accepted_answers(
    accepted_answers: str,
) -> list[str]:

    return [
        answer.strip()
        for answer
        in accepted_answers.split("|")
        if answer.strip()
    ]


# ==================================================
# REGISTER COMMANDS
# ==================================================


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
    @app_commands.describe(
        category="Question category.",
        question=(
            "Question shown to students."
        ),
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

        if interaction.guild is None:

            await interaction.response.send_message(
                (
                    "This command must be used "
                    "inside a server."
                ),
                ephemeral=True,
            )

            return

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

        try:

            new_question = (
                add_question(
                    category=(
                        category.value
                    ),
                    question_text=(
                        question
                    ),
                    accepted_answers=(
                        parsed_answers
                    ),
                    explanation=(
                        explanation
                    ),
                )
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

        await interaction.response.send_message(
            (
                f"✅ **Question "
                f"#{new_question['id']} added.**\n\n"
                f"Category: "
                f"**{category.name}**\n"
                f"Accepted answers: "
                f"**{len(new_question['accepted_answers'])}**"
            ),
            ephemeral=True,
        )


    # ==================================================
    # MANUAL RSQ
    # ==================================================


    @command(
        name="question",
        description=(
            "Manually post a Random "
            "Speed Question."
        ),
    )
    @app_commands.choices(
        category=QUESTION_CATEGORIES
    )
    @app_commands.describe(
        category=(
            "Optionally choose a category."
        ),
        question_id=(
            "Optionally choose a specific "
            "question-bank ID."
        ),
    )
    async def question(
        interaction: discord.Interaction,
        category: (
            app_commands.Choice[str]
            | None
        ) = None,
        question_id: int | None = None,
    ):


        # ==================================================
        # SERVER
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
        # ADMIN ONLY
        # ==================================================


        if (
            not interaction.user
            .guild_permissions
            .administrator
        ):

            await interaction.response.send_message(
                (
                    "You do not have permission "
                    "to manually post RSQs."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # CORRECT CHANNEL
        # ==================================================


        if (
            interaction.channel_id
            != RANDOM_QUESTION_CHANNEL_ID
        ):

            await interaction.response.send_message(
                (
                    "Manual RSQs must be posted "
                    "in the configured RSQ channel:\n"
                    f"<#{RANDOM_QUESTION_CHANNEL_ID}>"
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # CATEGORY + ID CONFLICT
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

            if (
                is_question_marked_for_edit(
                    question_id
                )
            ):

                await interaction.response.send_message(
                    (
                        f"⚠️ **Question "
                        f"#{question_id} is currently "
                        "marked for editing.**\n\n"
                        "It cannot be posted until "
                        "it is resolved through "
                        "`/flaggededit`."
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
                    category=(
                        category_value
                    )
                )
            )

            if question_data is None:

                await interaction.response.send_message(
                    (
                        "There are no eligible "
                        "questions matching that "
                        "selection."
                    ),
                    ephemeral=True,
                )

                return


        # ==================================================
        # DEFER
        # ==================================================


        await interaction.response.defer(
            ephemeral=True
        )

        channel = (
            interaction.channel
        )

        if channel is None:

            await interaction.followup.send(
                (
                    "M.A.R.T.Y. could not access "
                    "the current channel."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # POST
        # ==================================================


        try:

            result = (
                await post_speed_question(
                    channel=channel,
                    guild_id=(
                        interaction.guild.id
                    ),
                    question_data=(
                        question_data
                    ),
                    automatic=False,
                )
            )

        except SpeedQuestionTooSoonError as error:

            minutes = math.ceil(
                error.remaining_seconds
                / 60
            )

            await interaction.followup.send(
                (
                    "⏳ **Another RSQ was posted "
                    "too recently.**\n\n"
                    "M.A.R.T.Y. will not replace "
                    "an RSQ within 15 minutes of "
                    "the previous one.\n\n"
                    f"Try again in about "
                    f"**{minutes} minute"
                    f"{'' if minutes == 1 else 's'}**."
                ),
                ephemeral=True,
            )

            return

        except (
            discord.Forbidden,
            discord.HTTPException,
        ) as error:

            print(
                "Manual RSQ post error: "
                f"{error!r}"
            )

            await interaction.followup.send(
                (
                    "⚠️ M.A.R.T.Y. could not "
                    "post the question."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # SUCCESS
        # ==================================================


        await interaction.followup.send(
            (
                f"✅ Posted Random Speed Question "
                f"**#{result['question_id']}**."
            ),
            ephemeral=True,
        )