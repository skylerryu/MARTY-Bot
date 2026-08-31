import os

import discord
from discord import app_commands
from dotenv import load_dotenv


load_dotenv()


TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID_RAW = os.getenv("DEV_GUILD_ID")


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN was not found in .env."
    )

if not DEV_GUILD_ID_RAW:
    raise RuntimeError(
        "DEV_GUILD_ID was not found in .env."
    )


DEV_GUILD_ID = int(DEV_GUILD_ID_RAW)


class ClearCommandsClient(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()

        super().__init__(
            intents=intents
        )

        self.tree = app_commands.CommandTree(self)


    async def setup_hook(self):

        guild = discord.Object(
            id=DEV_GUILD_ID
        )

        # Clear commands registered specifically
        # to your development server.
        self.tree.clear_commands(
            guild=guild
        )

        await self.tree.sync(
            guild=guild
        )

        print("Cleared server commands.")

        # Clear globally registered commands.
        self.tree.clear_commands(
            guild=None
        )

        await self.tree.sync()

        print("Cleared global commands.")


client = ClearCommandsClient()


@client.event
async def on_ready():

    print("Old M.A.R.T.Y. commands removed.")

    await client.close()


client.run(TOKEN)