import discord
from discord import app_commands

from commands.command_helpers import (
    make_command,
)
from data.patient_assessment_db import (
    get_recent_completed_assessment_sessions,
)
from points.mechanics.patient_assessment.assessment_display import (
    build_assessment_history_embed,
)
from points.mechanics.patient_assessment.assessment_ui import (
    open_assessment_entry,
)


# ==================================================
# REGISTER
# ==================================================


def register_assessment_commands(
    tree: app_commands.CommandTree,
    guild: discord.Object,
):
    command = make_command(
        tree=tree,
        guild=guild,
    )

    @command(
        name="assessment",
        description=(
            "Open or resume today's private patient assessment."
        ),
    )
    async def assessment(
        interaction: discord.Interaction,
    ):
        await open_assessment_entry(
            interaction
        )

    @command(
        name="assessmenthistory",
        description=(
            "View your recent patient assessment scores."
        ),
    )
    async def assessment_history(
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command must be used in the server.",
                ephemeral=True,
            )
            return

        sessions = (
            await get_recent_completed_assessment_sessions(
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                limit=5,
            )
        )

        await interaction.response.send_message(
            embed=build_assessment_history_embed(
                sessions
            ),
            ephemeral=True,
        )
