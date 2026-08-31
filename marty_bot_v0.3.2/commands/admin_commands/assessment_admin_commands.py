import discord
from discord import app_commands

from commands.command_helpers import (
    make_command,
)
from data.patient_assessment_db import (
    count_active_sessions_for_scenario,
    get_active_assessment_scenario,
)


# ==================================================
# REGISTER
# ==================================================


def register_assessment_admin_commands(
    tree: app_commands.CommandTree,
    guild: discord.Object,
):
    command = make_command(
        tree=tree,
        guild=guild,
    )

    @command(
        name="newassessment",
        description=(
            "Regenerate and post today's patient assessment."
        ),
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def new_assessment(
        interaction: discord.Interaction,
    ):
        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        scheduler = getattr(
            interaction.client,
            "assessment_scheduler",
            None,
        )

        if scheduler is None:
            await interaction.followup.send(
                "The patient assessment scheduler is unavailable.",
                ephemeral=True,
            )
            return

        result = await scheduler.regenerate_today()
        status = result["status"]

        if status == "active_sessions":
            await interaction.followup.send(
                (
                    "I did not regenerate the assessment because "
                    f"**{result['count']}** student session(s) are "
                    "currently active on it."
                ),
                ephemeral=True,
            )
            return

        if status != "ok":
            await interaction.followup.send(
                (
                    "MARTY could not regenerate the assessment.\n"
                    f"Status: `{status}`"
                ),
                ephemeral=True,
            )
            return

        scenario = result["scenario"]

        await interaction.followup.send(
            (
                "Generated and posted a new patient assessment "
                f"(Scenario #{scenario['id']}, "
                f"type `{scenario['scenario_type']}`)."
            ),
            ephemeral=True,
        )

    @command(
        name="assessmentstatus",
        description=(
            "Show the current patient assessment system status."
        ),
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def assessment_status(
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command must be used in a server.",
                ephemeral=True,
            )
            return

        scenario = (
            await get_active_assessment_scenario(
                interaction.guild.id
            )
        )

        if scenario is None:
            await interaction.response.send_message(
                "There is no currently active patient assessment.",
                ephemeral=True,
            )
            return

        active_sessions = (
            await count_active_sessions_for_scenario(
                scenario["id"]
            )
        )

        await interaction.response.send_message(
            (
                f"**Scenario:** #{scenario['id']}\n"
                f"**Type:** `{scenario['scenario_type']}`\n"
                f"**Date:** {scenario['scenario_date']}\n"
                f"**Message ID:** {scenario['message_id']}\n"
                f"**Active Student Sessions:** {active_sessions}\n"
                f"**Expires:** {scenario['expires_at']}"
            ),
            ephemeral=True,
        )
