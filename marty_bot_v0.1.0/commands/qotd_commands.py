import discord
from discord import app_commands

from commands.command_helpers import (
    make_command,
)

from points.time_helpers import (
    get_current_chicago_date,
)

from points.mechanics.question_of_the_day.qotd_questions import (
    QotdAlreadyExistsError,
    create_qotd,
    delete_qotd,
    set_qotd_message_id,
)

from points.mechanics.question_of_the_day.qotd_display import (
    build_qotd_question_embed,
)

from points.mechanics.question_of_the_day.qotd_modal import (
    QotdAnswerView,
)


# ==================================================
# HELPERS
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


def register_qotd_commands(
    tree: app_commands.CommandTree,
    guild: discord.Object,
):

    command = make_command(
        tree=tree,
        guild=guild,
    )


    # ==================================================
    # POST QOTD
    # ==================================================


    @command(
        name="postqotd",
        description=(
            "Post today's Question of the Day."
        ),
    )
    @app_commands.describe(
        question=(
            "The Question of the Day."
        ),
        accepted_answers=(
            "Accepted answers separated by |"
        ),
        explanation=(
            "Optional explanation shown after "
            "a correct answer."
        ),
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def post_qotd(
        interaction: discord.Interaction,
        question: str,
        accepted_answers: str,
        explanation: str | None = None,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                (
                    "This command must be used "
                    "in a server."
                ),
                ephemeral=True,
            )

            return


        if interaction.channel is None:

            await interaction.response.send_message(
                (
                    "I couldn't determine the "
                    "current channel."
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
                    "You must provide at least one "
                    "accepted answer."
                ),
                ephemeral=True,
            )

            return


        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )


        try:

            qotd = await create_qotd(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                question_date=(
                    get_current_chicago_date()
                ),
                question_text=question,
                accepted_answers=parsed_answers,
                explanation=explanation,
            )

        except QotdAlreadyExistsError:

            await interaction.followup.send(
                (
                    "A Question of the Day already "
                    "exists for today."
                ),
                ephemeral=True,
            )

            return


        except ValueError as error:

            await interaction.followup.send(
                str(error),
                ephemeral=True,
            )

            return


        try:

            message = await interaction.channel.send(
                embed=build_qotd_question_embed(
                    question_text=(
                        qotd["question_text"]
                    ),
                    question_date=(
                        qotd["question_date"]
                    ),
                ),
                view=QotdAnswerView(
                    qotd_id=qotd["id"]
                ),
            )


        except (
            discord.Forbidden,
            discord.HTTPException,
        ) as error:

            await delete_qotd(
                qotd_id=qotd["id"]
            )

            print(
                "QoTD posting error: "
                f"{error!r}"
            )

            await interaction.followup.send(
                (
                    "I created the QoTD record but "
                    "couldn't post the Discord message."
                ),
                ephemeral=True,
            )

            return


        await set_qotd_message_id(
            qotd_id=qotd["id"],
            message_id=message.id,
        )


        await interaction.followup.send(
            "Question of the Day posted.",
            ephemeral=True,
        )