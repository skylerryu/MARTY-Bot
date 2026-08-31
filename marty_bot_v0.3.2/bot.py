import discord

from discord import (
    app_commands,
)

from bot_config import (
    DEV_GUILD_ID,
    QOTD_CHANNEL_ID,
    RANDOM_QUESTION_CHANNEL_ID,
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

from commands.admin_commands.q_flag_admin_commands import (
    register_question_flag_admin_commands,
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

from points.mechanics.random_speed_questions.rsq import (
    process_speed_question_message,
)

from points.mechanics.random_speed_questions.rsq_scheduler import (
    RsqScheduler,
)

from setup import (
    configure_qotd_channel,
)


# ==================================================
# DISCORD INTENTS
# ==================================================


intents = (
    discord.Intents.default()
)

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
        # ACTIVITY
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
                guild_id=(
                    DEV_GUILD_ID
                ),
                channel_id=(
                    QOTD_CHANNEL_ID
                ),
            )
        )


        # ==================================================
        # RSQ SCHEDULER
        # ==================================================


        self.rsq_scheduler = (
            RsqScheduler(
                bot=self,
                guild_id=(
                    DEV_GUILD_ID
                ),
                channel_id=(
                    RANDOM_QUESTION_CHANNEL_ID
                ),
            )
        )


    # ==================================================
    # SETUP
    # ==================================================


    async def setup_hook(
        self,
    ):


        # ==================================================
        # DATABASES
        # ==================================================


        await init_user_db()

        await init_system_db()


        # ==================================================
        # DEVELOPMENT GUILD
        # ==================================================


        guild = discord.Object(
            id=(
                DEV_GUILD_ID
            )
        )


        # ==================================================
        # RESTORE QOTD VIEWS
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

        register_question_flag_admin_commands(
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
        # START RSQ SCHEDULER
        # ==================================================
        #
        # RSQ does not require the QoTD channel
        # configuration step, so it can start here.
        #
        # The QoTD scheduler is started in on_ready()
        # AFTER the QoTD channel permissions have
        # been checked.
        #
        # ==================================================


        self.rsq_scheduler.start()


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
                qotd[
                    "message_id"
                ]
            )

            if message_id is None:

                continue

            self.add_view(
                QotdAnswerView(
                    qotd_id=(
                        qotd_id
                    )
                ),
                message_id=(
                    message_id
                ),
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
        # CONFIGURE QOTD CHANNEL
        # ==================================================
        #
        # on_ready() runs after Discord has populated
        # the guild/channel cache.
        #
        # Every time MARTY becomes ready, it checks
        # the configured QOTD_CHANNEL_ID.
        #
        # If you change the ID in .env and restart
        # MARTY, the new channel will automatically
        # receive the QoTD permission configuration.
        #
        # ==================================================


        try:

            configured = (
                await configure_qotd_channel(
                    bot=self,
                    guild_id=(
                        DEV_GUILD_ID
                    ),
                    channel_id=(
                        QOTD_CHANNEL_ID
                    ),
                )
            )

            if not configured:

                print(
                    "QoTD channel setup did not "
                    "complete successfully."
                )

        except Exception as error:

            print(
                "QoTD channel setup error: "
                f"{error!r}"
            )


        # ==================================================
        # START QOTD SCHEDULER
        # ==================================================
        #
        # QotdScheduler.start() already checks whether
        # its loops are running, so this is safe even
        # if Discord fires on_ready() again after a
        # reconnect.
        #
        # ==================================================


        self.qotd_scheduler.start()


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
        # RANDOM SPEED QUESTION ANSWERS
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

        try:

            self.rsq_scheduler.stop()

        except Exception as error:

            print(
                "RSQ scheduler shutdown error: "
                f"{error!r}"
            )

        await super().close()


# ==================================================
# BOT INSTANCE
# ==================================================


bot = MartyBot()