import discord
from discord import app_commands


def make_command(
    tree: app_commands.CommandTree,
    guild: discord.Object,
):
    """
    Create M.A.R.T.Y.'s command decorator.

    The Discord command tree and development
    server are supplied automatically.
    """

    def command(
        name: str,
        description: str,
    ):
        return tree.command(
            name=name,
            description=description,
            guild=guild,
        )

    return command