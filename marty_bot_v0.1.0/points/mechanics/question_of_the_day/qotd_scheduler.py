import asyncio
from datetime import time
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks

from points.time_helpers import (
    get_current_chicago_date,
)

from points.mechanics.question_of_the_day.qotd_config import (
    QOTD_TIMEZONE,
    QOTD_POST_HOUR,
    QOTD_POST_MINUTE,
)

from points.mechanics.question_of_the_day.qotd_questions import (
    get_qotd_for_date,
    set_qotd_message_id,
)

from points.mechanics.question_of_the_day.qotd_display import (
    build_qotd_question_embed,
)

from points.mechanics.question_of_the_day.qotd_modal import (
    QotdAnswerView,
)


# ==================================================
# POSTING TIME
# ==================================================


QOTD_TIMEZONE_INFO = ZoneInfo(
    QOTD_TIMEZONE
)


QOTD_POST_TIME = time(
    hour=QOTD_POST_HOUR,
    minute=QOTD_POST_MINUTE,
    tzinfo=QOTD_TIMEZONE_INFO,
)


# ==================================================
# QOTD SCHEDULER
# ==================================================


class QotdScheduler:
    """
    Automatically posts the Question of the Day
    at the configured Chicago time.

    The question must already exist in the database
    for the current date.

    If M.A.R.T.Y. starts after the normal posting
    time and today's question has not been posted,
    it will post it when the bot starts.
    """

    def __init__(
        self,
        bot: discord.Client,
        guild_id: int,
    ):
        self.bot = bot
        self.guild_id = guild_id

        self._post_lock = asyncio.Lock()


    # ==================================================
    # START
    # ==================================================


    def start(self):
        """
        Start the daily QoTD scheduler.
        """

        if not self.daily_qotd_post.is_running():
            self.daily_qotd_post.start()


    # ==================================================
    # STOP
    # ==================================================


    def stop(self):
        """
        Stop the daily QoTD scheduler.
        """

        if self.daily_qotd_post.is_running():
            self.daily_qotd_post.cancel()


    # ==================================================
    # DAILY POST
    # ==================================================


    @tasks.loop(
        time=QOTD_POST_TIME
    )
    async def daily_qotd_post(
        self,
    ):
        """
        Run every day at the configured
        Question of the Day posting time.
        """

        await self.ensure_today_qotd_posted(
            require_post_time=False,
        )


    # ==================================================
    # STARTUP
    # ==================================================


    @daily_qotd_post.before_loop
    async def before_daily_qotd_post(
        self,
    ):
        """
        Wait until Discord is ready.

        If M.A.R.T.Y. started after today's normal
        posting time, attempt to catch up and post
        today's question.
        """

        await self.bot.wait_until_ready()

        await self.ensure_today_qotd_posted(
            require_post_time=True,
        )


    # ==================================================
    # ERROR HANDLER
    # ==================================================


    @daily_qotd_post.error
    async def daily_qotd_post_error(
        self,
        error: Exception,
    ):
        """
        Log unexpected scheduler errors.
        """

        print(
            "QoTD scheduler error: "
            f"{error!r}"
        )


    # ==================================================
    # ENSURE TODAY'S QOTD IS POSTED
    # ==================================================


    async def ensure_today_qotd_posted(
        self,
        require_post_time: bool = True,
    ) -> bool:
        """
        Make sure today's QoTD has been posted.

        Returns True if a question was posted.

        Returns False if:
        - it is too early,
        - no question exists for today, or
        - today's question was already posted.
        """

        async with self._post_lock:

            # ==================================================
            # POSTING TIME CHECK
            # ==================================================

            if (
                require_post_time
                and not self._post_time_has_arrived()
            ):
                return False


            # ==================================================
            # GET TODAY'S QUESTION
            # ==================================================

            current_date = (
                get_current_chicago_date()
            )

            qotd = await get_qotd_for_date(
                guild_id=self.guild_id,
                question_date=current_date,
            )

            if qotd is None:

                print(
                    "QoTD scheduler: "
                    f"No question is scheduled for "
                    f"{current_date.isoformat()}."
                )

                return False


            # ==================================================
            # ALREADY POSTED
            # ==================================================

            if qotd["message_id"] is not None:
                return False


            # ==================================================
            # GET CHANNEL
            # ==================================================

            channel = self.bot.get_channel(
                qotd["channel_id"]
            )

            if channel is None:

                try:

                    channel = await self.bot.fetch_channel(
                        qotd["channel_id"]
                    )

                except (
                    discord.Forbidden,
                    discord.NotFound,
                    discord.HTTPException,
                ) as error:

                    print(
                        "QoTD scheduler could not "
                        "access the QoTD channel: "
                        f"{error!r}"
                    )

                    return False


            # ==================================================
            # POST QUESTION
            # ==================================================

            try:

                message = await channel.send(
                    embed=build_qotd_question_embed(
                        qotd["question_text"]
                    ),
                    view=QotdAnswerView(
                        qotd_id=qotd["id"]
                    ),
                )

            except (
                discord.Forbidden,
                discord.HTTPException,
            ) as error:

                print(
                    "QoTD scheduler could not "
                    "post today's question: "
                    f"{error!r}"
                )

                return False


            # ==================================================
            # SAVE MESSAGE ID
            # ==================================================

            try:

                await set_qotd_message_id(
                    qotd_id=qotd["id"],
                    message_id=message.id,
                )

            except Exception:

                # If Discord received the message but the
                # database could not save its ID, remove the
                # message so a later retry does not create
                # duplicate QoTD posts.

                try:
                    await message.delete()

                except (
                    discord.Forbidden,
                    discord.HTTPException,
                ):
                    pass

                raise


            # ==================================================
            # SUCCESS
            # ==================================================

            print(
                "QoTD scheduler: "
                f"Posted QoTD #{qotd['id']} "
                f"for {current_date.isoformat()}."
            )

            return True


    # ==================================================
    # POST TIME CHECK
    # ==================================================


    def _post_time_has_arrived(
        self,
    ) -> bool:
        """
        Return True once the configured QoTD
        posting time has been reached today.
        """

        from datetime import datetime

        now = datetime.now(
            QOTD_TIMEZONE_INFO
        )

        return (
            now.hour,
            now.minute,
        ) >= (
            QOTD_POST_HOUR,
            QOTD_POST_MINUTE,
        )