import discord

from discord import app_commands

from bot_config import (
    DEV_GUILD_ID,
    QOTD_CHANNEL_ID,
)

from commands.points_commands import (
    register_points_commands,
)

from commands.qotd_commands import (
    register_qotd_commands,
)

from commands.q_commands import (
    register_question_commands,
)

from commands.admin_commands.qotd_admin_commands import (
    register_qotd_admin_commands,
)

from data.user_db import (
    init_user_db,
)

from data.system_db import (
    init_system_db,
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

from points.mechanics.random_speed_questions.random_speed_questions import (
    process_speed_question_message,
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


        # ==================================================
        # COMMAND TREE
        # ==================================================


        self.tree = (
            app_commands.CommandTree(
                self
            )
        )


        # ==================================================
        # ACTIVITY TRACKER
        # ==================================================


        self.activity_tracker = (
            ActivityTracker()
        )


        # ==================================================
        # QOTD SCHEDULER
        # ==================================================


        self.qotd_scheduler = (
            QotdScheduler(
                bot=self,
                guild_id=DEV_GUILD_ID,
                channel_id=QOTD_CHANNEL_ID,
            )
        )


    # ==================================================
    # SETUP
    # ==================================================


    async def setup_hook(
        self,
    ):


        # ==================================================
        # USER DATABASE
        # ==================================================


        await init_user_db()


        # ==================================================
        # SYSTEM DATABASE
        # ==================================================


        await init_system_db()


        # ==================================================
        # DEVELOPMENT GUILD
        # ==================================================


        guild = discord.Object(
            id=DEV_GUILD_ID
        )


        # ==================================================
        # RESTORE PERSISTENT QOTD VIEWS
        # ==================================================


        await self._restore_qotd_views()


        # ==================================================
        # NORMAL COMMANDS
        # ==================================================


        register_points_commands(
            tree=self.tree,
            guild=guild,
        )

        register_qotd_commands(
            tree=self.tree,
            guild=guild,
        )

        register_question_commands(
            tree=self.tree,
            guild=guild,
        )


        # ==================================================
        # ADMIN COMMANDS
        # ==================================================


        register_qotd_admin_commands(
            tree=self.tree,
            guild=guild,
        )


        # ==================================================
        # SYNC COMMANDS
        # ==================================================


        synced_commands = (
            await self.tree.sync(
                guild=guild
            )
        )

        print(
            "Synced "
            f"{len(synced_commands)} "
            "Discord slash command(s)."
        )


        # ==================================================
        # START QOTD SCHEDULER
        # ==================================================


        self.qotd_scheduler.start()


    # ==================================================
    # RESTORE QOTD VIEWS
    # ==================================================


    async def _restore_qotd_views(
        self,
    ):

        qotds = (
            await get_recent_qotds_for_views(
                limit=(
                    QOTD_PERSISTENT_VIEW_LIMIT
                )
            )
        )

        restored_count = 0

        for qotd in qotds:

            qotd_id = (
                qotd["id"]
            )

            message_id = (
                qotd["message_id"]
            )

            if message_id is None:

                continue

            self.add_view(
                QotdAnswerView(
                    qotd_id=qotd_id
                ),
                message_id=message_id,
            )

            restored_count += 1

        print(
            "Restored "
            f"{restored_count} "
            "persistent QoTD view(s)."
        )


    # ==================================================
    # READY
    # ==================================================


    async def on_ready(
        self,
    ):

        print(
            "M.A.R.T.Y. is online as "
            f"{self.user}"
        )


    # ==================================================
    # MESSAGE
    # ==================================================


    async def on_message(
        self,
        message: discord.Message,
    ):

        if message.author.bot:

            return


        # ==================================================
        # ACTIVITY
        # ==================================================


        try:

            await (
                self.activity_tracker
                .process_message(
                    message
                )
            )

        except Exception as error:

            print(
                "Activity processing error: "
                f"{error!r}"
            )


        # ==================================================
        # SPEED QUESTION
        # ==================================================


        try:

            await process_speed_question_message(
                message=message,
                bot_user=self.user,
            )

        except Exception as error:

            print(
                "Speed question processing error: "
                f"{error!r}"
            )


    # ==================================================
    # SHUTDOWN
    # ==================================================


    async def close(
        self,
    ):

        try:

            self.qotd_scheduler.stop()

        except Exception as error:

            print(
                "QoTD scheduler shutdown error: "
                f"{error!r}"
            )

        await super().close()


# ==================================================
# BOT INSTANCE
# ==================================================


bot = MartyBot()