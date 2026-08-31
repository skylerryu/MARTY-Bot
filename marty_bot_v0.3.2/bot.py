import discord

from discord import (
    app_commands,
)

from bot_config import (
    DEV_GUILD_ID,
    PATIENT_ASSESSMENT_CHANNEL_ID,
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
from commands.assessment_commands import (
    register_assessment_commands,
)

from commands.admin_commands.qotd_admin_commands import (
    register_qotd_admin_commands,
)
from commands.admin_commands.q_flag_admin_commands import (
    register_question_flag_admin_commands,
)
from commands.admin_commands.assessment_admin_commands import (
    register_assessment_admin_commands,
)

from data.user_db import (
    init_user_db,
)
from data.system_db import (
    init_system_db,
)
from data.patient_assessment_db import (
    get_recent_assessment_views,
    init_patient_assessment_db,
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

from points.mechanics.patient_assessment.assessment_config import (
    ASSESSMENT_PERSISTENT_VIEW_LIMIT,
)
from points.mechanics.patient_assessment.assessment_scheduler import (
    AssessmentScheduler,
)
from points.mechanics.patient_assessment.assessment_ui import (
    AssessmentPublicView,
)

from setup import (
    configure_assessment_channel,
    configure_qotd_channel,
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
    def __init__(self):
        super().__init__(
            intents=intents
        )

        self.tree = app_commands.CommandTree(
            self
        )

        self.activity_tracker = (
            ActivityTracker()
        )

        self.qotd_scheduler = QotdScheduler(
            bot=self,
            guild_id=DEV_GUILD_ID,
            channel_id=QOTD_CHANNEL_ID,
        )

        self.rsq_scheduler = RsqScheduler(
            bot=self,
            guild_id=DEV_GUILD_ID,
            channel_id=RANDOM_QUESTION_CHANNEL_ID,
        )

        self.assessment_scheduler = (
            AssessmentScheduler(
                bot=self,
                guild_id=DEV_GUILD_ID,
                channel_id=(
                    PATIENT_ASSESSMENT_CHANNEL_ID
                ),
            )
        )

    # ==================================================
    # SETUP
    # ==================================================

    async def setup_hook(self):
        # Databases
        await init_user_db()
        await init_system_db()
        await init_patient_assessment_db()

        guild = discord.Object(
            id=DEV_GUILD_ID
        )

        # Persistent component restoration
        await self._restore_qotd_views()
        await self._restore_assessment_views()

        # Normal commands
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
        register_assessment_commands(
            tree=self.tree,
            guild=guild,
        )

        # Admin commands
        register_qotd_admin_commands(
            tree=self.tree,
            guild=guild,
        )
        register_question_flag_admin_commands(
            tree=self.tree,
            guild=guild,
        )
        register_assessment_admin_commands(
            tree=self.tree,
            guild=guild,
        )

        synced_commands = await self.tree.sync(
            guild=guild
        )

        print(
            "Synced "
            f"{len(synced_commands)} "
            "Discord slash command(s)."
        )

        # RSQs do not depend on a read-only channel
        # configuration step.
        self.rsq_scheduler.start()

    # ==================================================
    # RESTORE QOTD VIEWS
    # ==================================================

    async def _restore_qotd_views(self):
        qotds = await get_recent_qotds_for_views(
            limit=QOTD_PERSISTENT_VIEW_LIMIT
        )

        restored_count = 0

        for qotd in qotds:
            message_id = qotd["message_id"]

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
            "persistent QoTD view(s)."
        )

    # ==================================================
    # RESTORE ASSESSMENT VIEWS
    # ==================================================

    async def _restore_assessment_views(self):
        scenarios = await get_recent_assessment_views(
            limit=ASSESSMENT_PERSISTENT_VIEW_LIMIT
        )

        restored_count = 0

        for scenario in scenarios:
            message_id = scenario["message_id"]

            if message_id is None:
                continue

            self.add_view(
                AssessmentPublicView(
                    scenario_id=scenario["id"]
                ),
                message_id=message_id,
            )
            restored_count += 1

        print(
            "Restored "
            f"{restored_count} "
            "persistent assessment view(s)."
        )

    # ==================================================
    # READY
    # ==================================================

    async def on_ready(self):
        print(
            "M.A.R.T.Y. is online as "
            f"{self.user}"
        )

        # QoTD channel permissions
        try:
            configured = await configure_qotd_channel(
                bot=self,
                guild_id=DEV_GUILD_ID,
                channel_id=QOTD_CHANNEL_ID,
            )

            if not configured:
                print(
                    "QoTD channel setup did not complete successfully."
                )
        except Exception as error:
            print(
                "QoTD channel setup error: "
                f"{error!r}"
            )

        # Patient assessment channel permissions
        try:
            configured = await configure_assessment_channel(
                bot=self,
                guild_id=DEV_GUILD_ID,
                channel_id=(
                    PATIENT_ASSESSMENT_CHANNEL_ID
                ),
            )

            if not configured:
                print(
                    "Assessment channel setup did not complete successfully."
                )
        except Exception as error:
            print(
                "Assessment channel setup error: "
                f"{error!r}"
            )

        # Both start methods are idempotent across reconnects.
        self.qotd_scheduler.start()
        self.assessment_scheduler.start()

    # ==================================================
    # MESSAGE
    # ==================================================

    async def on_message(
        self,
        message: discord.Message,
    ):
        if message.author.bot:
            return

        try:
            await self.activity_tracker.process_message(
                message
            )
        except Exception as error:
            print(
                "Activity processing error: "
                f"{error!r}"
            )

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

    async def close(self):
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

        try:
            self.assessment_scheduler.stop()
        except Exception as error:
            print(
                "Assessment scheduler shutdown error: "
                f"{error!r}"
            )

        await super().close()


# ==================================================
# BOT INSTANCE
# ==================================================


bot = MartyBot()
