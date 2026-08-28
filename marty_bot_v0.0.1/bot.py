import os

import discord

from discord import app_commands

from bot_config import (
    DEV_GUILD_ID,
    ON_DUTY_NAME,
    OFF_DUTY_NAME,
)

from data.database import (
    init_db,
    ensure_user,
)

from commands.commands import (
    register_commands,
)

from quiz.question_system import (
    handle_question_message,
)

from quiz.scheduler import (
    start_question_scheduler,
)


# ==================================================
# DISCORD INTENTS
# ==================================================

intents = discord.Intents.default()

# Required so M.A.R.T.Y. can read student answers.
intents.message_content = True


# ==================================================
# M.A.R.T.Y. CLIENT
# ==================================================

class MartyClient(discord.Client):

    def __init__(self):

        super().__init__(
            intents=intents
        )

        self.tree = app_commands.CommandTree(
            self
        )

    # ==================================================
    # STARTUP
    # ==================================================

    async def setup_hook(self):

        # ------------------------------------------
        # DATABASE
        # ------------------------------------------

        await init_db()

        # ------------------------------------------
        # DEVELOPMENT SERVER
        # ------------------------------------------

        guild = discord.Object(
            id=DEV_GUILD_ID
        )

        # ------------------------------------------
        # REGISTER COMMANDS
        # ------------------------------------------

        register_commands(
            client=self,
            guild=guild
        )

        # ------------------------------------------
        # SYNC COMMANDS
        # ------------------------------------------

        synced = await self.tree.sync(
            guild=guild
        )

        print(
            f"Synced {len(synced)} commands "
            f"to development server."
        )

        for command in synced:
            print(
                f"  /{command.name}"
            )

        # ------------------------------------------
        # START QUESTION SCHEDULER
        # ------------------------------------------

        start_question_scheduler(
            self
        )

    # ==================================================
    # SHUTDOWN
    # ==================================================

    async def close(self):

        guild = self.get_guild(
            DEV_GUILD_ID
        )

        if (
            guild is not None
            and guild.me is not None
        ):

            try:

                await guild.me.edit(
                    nick=OFF_DUTY_NAME
                )

                print(
                    "M.A.R.T.Y. marked OFF-DUTY."
                )

            except discord.HTTPException as error:

                print(
                    "Could not set OFF-DUTY "
                    f"nickname: {error}"
                )

        await super().close()


# ==================================================
# CLIENT
# ==================================================

client = MartyClient()


# ==================================================
# READY EVENT
# ==================================================

@client.event
async def on_ready():

    guild = client.get_guild(
        DEV_GUILD_ID
    )

    # ------------------------------------------
    # SET ON-DUTY NICKNAME
    # ------------------------------------------

    if (
        guild is not None
        and guild.me is not None
    ):

        try:

            await guild.me.edit(
                nick=ON_DUTY_NAME
            )

            print(
                "M.A.R.T.Y. marked ON-DUTY."
            )

        except discord.HTTPException as error:

            print(
                "Could not set ON-DUTY "
                f"nickname: {error}"
            )

    # ------------------------------------------
    # TERMINAL STATUS
    # ------------------------------------------

    print()
    print("=" * 45)
    print("M.A.R.T.Y. IS ONLINE")
    print("=" * 45)

    print(
        f"Bot: {client.user}"
    )

    print(
        f"Process ID: {os.getpid()}"
    )

    print("=" * 45)
    print()


# ==================================================
# MESSAGE EVENT
# ==================================================

@client.event
async def on_message(
    message: discord.Message
):

    # ------------------------------------------
    # IGNORE BOTS
    # ------------------------------------------

    if message.author.bot:
        return

    # ------------------------------------------
    # IGNORE DIRECT MESSAGES
    # ------------------------------------------

    if message.guild is None:
        return

    # ------------------------------------------
    # REGISTER / UPDATE STUDENT
    # ------------------------------------------

    await ensure_user(
        guild_id=message.guild.id,
        user_id=message.author.id,
        username=message.author.display_name
    )

    # ------------------------------------------
    # HAND OFF MESSAGE
    # ------------------------------------------

    await handle_question_message(
        client=client,
        message=message
    )