import discord
from discord import app_commands

from bot_config import (
    DEV_GUILD_ID,
)

from commands.points_commands import (
    register_points_commands,
)

from commands.qotd_commands import (
    register_qotd_commands,
)

from data.database import (
    init_db,
)

from points.mechanics.activity.activity import (
    ActivityTracker,
)

from points.mechanics.question_of_the_day.qotd_config import (
    QOTD_PERSISTENT_VIEW_LIMIT,
)

from points.mechanics.question_of_the_day.qotd_modal import (
    QotdAnswerView,
)

from points.mechanics.question_of_the_day.qotd_questions import (
    get_recent_qotds_for_views,
)

from points.mechanics.question_of_the_day.qotd_scheduler import (
    QotdScheduler,
)

from points.progressions.levels.levels import (
    initialize_level_cache,
)

from points.progressions.progressions_validator import (
    validate_progression_config,
)

from points.progressions.progressions_table import (
    generate_progressions_reference,
)


# ==================================================
# DISCORD INTENTS
# ==================================================


intents = discord.Intents.default()

intents.message_content = True


# ==================================================
# M.A.R.T.Y. BOT
# ==================================================


class MartyBot(
    discord.Client
):

    def __init__(
        self,
    ):
        super().__init__(
            intents=intents
        )

        # Discord slash commands.
        self.tree = app_commands.CommandTree(
            self
        )

        # Activity points mechanic.
        self.activity_tracker = (
            ActivityTracker()
        )

        # Daily Question of the Day scheduler.
        self.qotd_scheduler = (
            QotdScheduler(
                bot=self,
                guild_id=DEV_GUILD_ID,
            )
        )


    # ==================================================
    # SETUP
    # ==================================================


    async def setup_hook(
        self,
    ):
        """
        Prepare M.A.R.T.Y. before the bot
        becomes fully connected to Discord.
        """

        # ==================================================
        # PROGRESSION SYSTEM
        # ==================================================

        initialize_level_cache()

        validate_progression_config()

        generate_progressions_reference()


        # ==================================================
        # DATABASE
        # ==================================================

        await init_db()


        # ==================================================
        # RESTORE QOTD BUTTONS
        # ==================================================

        await self._restore_qotd_views()


        # ==================================================
        # COMMANDS
        # ==================================================

        guild = discord.Object(
            id=DEV_GUILD_ID
        )

        register_points_commands(
            tree=self.tree,
            guild=guild,
        )

        register_qotd_commands(
            tree=self.tree,
            guild=guild,
        )


        # ==================================================
        # COMMAND SYNC
        # ==================================================

        synced = await self.tree.sync(
            guild=guild
        )

        print(
            f"Synced {len(synced)} "
            "slash commands."
        )


        # ==================================================
        # QOTD SCHEDULER
        # ==================================================

        self.qotd_scheduler.start()


    # ==================================================
    # RESTORE QOTD VIEWS
    # ==================================================


    async def _restore_qotd_views(
        self,
    ):
        """
        Restore persistent Answer Question
        buttons after M.A.R.T.Y. restarts.
        """

        recent_qotds = (
            await get_recent_qotds_for_views(
                limit=QOTD_PERSISTENT_VIEW_LIMIT,
            )
        )

        restored_count = 0

        for qotd in recent_qotds:

            message_id = qotd[
                "message_id"
            ]

            if message_id is None:
                continue

            self.add_view(
                QotdAnswerView(
                    qotd_id=qotd["id"]
                ),
                message_id=message_id,
            )

            restored_count += 1

        print(
            "Restored "
            f"{restored_count} "
            "QoTD persistent views."
        )


    # ==================================================
    # READY
    # ==================================================


    async def on_ready(
        self,
    ):
        """
        Called when M.A.R.T.Y. is connected
        to Discord.
        """

        if self.user is None:
            return

        print(
            "M.A.R.T.Y. connected as "
            f"{self.user}"
        )

        print(
            f"Bot ID: {self.user.id}"
        )


    # ==================================================
    # MESSAGE ACTIVITY
    # ==================================================


    async def on_message(
        self,
        message: discord.Message,
    ):
        """
        Pass Discord messages to the activity
        points mechanic.
        """

        await self.activity_tracker.process_message(
            message
        )


# ==================================================
# BOT INSTANCE
# ==================================================


bot = MartyBot()