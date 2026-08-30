import discord
from discord import app_commands

from commands.command_helpers import make_command
from points.displays.my_points import build_my_points_embed
from points.displays.leaderboard import build_leaderboard_embed


def register_points_commands(
    tree: app_commands.CommandTree,
    guild: discord.Object,
):
    command = make_command(
        tree=tree,
        guild=guild,
    )

    # ==================================================
    # /mypoints
    # ==================================================

    @command(
        name="mypoints",
        description="View your M.A.R.T.Y. points.",
    )
    async def mypoints(
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in the server.",
                ephemeral=True,
            )
            return

        embed = await build_my_points_embed(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            username=interaction.user.display_name,
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=False,
        )

    # ==================================================
    # /leaderboard
    # ==================================================

    @command(
        name="leaderboard",
        description="View the M.A.R.T.Y. leaderboard.",
    )
    async def leaderboard(
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in the server.",
                ephemeral=True,
            )
            return

        embed = await build_leaderboard_embed(
            guild_id=interaction.guild.id,
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=False,
        )