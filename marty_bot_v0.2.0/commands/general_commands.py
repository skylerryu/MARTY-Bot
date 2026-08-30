import discord
from discord import app_commands

from commands.command_helpers import make_command


def register_general_commands(
    tree: app_commands.CommandTree,
    guild: discord.Object,
):
    command = make_command(
        tree=tree,
        guild=guild,
    )

    @command(
        name="ping",
        description="Check whether M.A.R.T.Y. is online.",
    )
    async def ping(
        interaction: discord.Interaction,
    ):
        await interaction.response.send_message(
            "M.A.R.T.Y. is online.",
            ephemeral=False,
        )