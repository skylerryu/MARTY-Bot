import asyncio
import random
from datetime import time
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks

from data.question_manager import (
    get_all_questions,
)

from points.time_helpers import (
    get_current_chicago_date,
)

from points.mechanics.question_of_the_day.qotd_config import (
    QOTD_TIMEZONE,
    QOTD_POST_HOUR,
    QOTD_POST_MINUTE,
)

from points.mechanics.question_of_the_day.qotd_questions import (
    QotdAlreadyExistsError,
    create_qotd,
    get_qotd_for_date,
    get_used_qotd_question_bank_ids,
    get_older_posted_qotds,
    set_qotd_message_id,
)

from points.mechanics.question_of_the_day.qotd_display import (
    build_qotd_question_embed,
)

from points.mechanics.question_of_the_day.qotd_modal import (
    QotdAnswerView,
)


# ==================================================
# QOTD QUESTION CATEGORIES
# ==================================================


QOTD_EXCLUDED_CATEGORIES = {
    "cet_fun_fact",
}


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
# QOTD QUESTION SELECTION
# ==================================================


def _get_random_qotd_question(
    excluded_ids: set[int] | None = None,
) -> dict | None:
    """
    Select a random active question that is
    eligible for Question of the Day.

    CET Fun Facts are intentionally excluded
    from QoTD selection.
    """

    if excluded_ids is None:

        excluded_ids = set()


    eligible_questions = [
        question
        for question in get_all_questions(
            active_only=True
        )
        if (
            question.get("category")
            not in QOTD_EXCLUDED_CATEGORIES
            and question["id"]
            not in excluded_ids
        )
    ]


    if not eligible_questions:

        return None


    return random.choice(
        eligible_questions
    )


# ==================================================
# QOTD SCHEDULER
# ==================================================


class QotdScheduler:

    def __init__(
        self,
        bot: discord.Client,
        guild_id: int,
        channel_id: int,
    ):

        self.bot = bot
        self.guild_id = guild_id
        self.channel_id = channel_id

        self._post_lock = asyncio.Lock()


    # ==================================================
    # START
    # ==================================================


    def start(self):

        if not self.daily_qotd_post.is_running():

            self.daily_qotd_post.start()


    # ==================================================
    # STOP
    # ==================================================


    def stop(self):

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
            # TODAY
            # ==================================================


            current_date = (
                get_current_chicago_date()
            )


            # ==================================================
            # GET EXISTING QOTD
            # ==================================================


            qotd = await get_qotd_for_date(
                guild_id=self.guild_id,
                question_date=current_date,
            )


            # ==================================================
            # CREATE TODAY'S QOTD
            # ==================================================


            if qotd is None:

                qotd = (
                    await self._create_today_qotd(
                        current_date=current_date,
                    )
                )

                if qotd is None:

                    return False


            # ==================================================
            # ALREADY POSTED
            # ==================================================


            if qotd["message_id"] is not None:

                await self._remove_old_qotd_buttons(
                    current_date=current_date,
                )

                return False


            # ==================================================
            # GET CHANNEL
            # ==================================================


            channel = self.bot.get_channel(
                qotd["channel_id"]
            )

            if channel is None:

                try:

                    channel = (
                        await self.bot.fetch_channel(
                            qotd["channel_id"]
                        )
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
                        question_text=(
                            qotd["question_text"]
                        ),
                        question_date=(
                            qotd["question_date"]
                        ),
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

                try:

                    await message.delete()

                except (
                    discord.Forbidden,
                    discord.HTTPException,
                ):

                    pass

                raise


            # ==================================================
            # REMOVE OLD BUTTONS
            # ==================================================


            await self._remove_old_qotd_buttons(
                current_date=current_date,
            )


            # ==================================================
            # SUCCESS
            # ==================================================


            print(
                "QoTD scheduler: "
                f"Posted QoTD #{qotd['id']} "
                f"for {current_date.isoformat()} "
                f"using bank question "
                f"#{qotd['question_bank_id']}."
            )

            return True


    # ==================================================
    # CREATE TODAY'S QOTD
    # ==================================================


    async def _create_today_qotd(
        self,
        current_date,
    ) -> dict | None:

        used_question_ids = (
            await get_used_qotd_question_bank_ids(
                guild_id=self.guild_id,
            )
        )


        # ==================================================
        # SELECT UNUSED ELIGIBLE QUESTION
        # ==================================================


        question = (
            _get_random_qotd_question(
                excluded_ids=used_question_ids
            )
        )


        # ==================================================
        # START NEW CYCLE
        # ==================================================


        if question is None:

            question = (
                _get_random_qotd_question()
            )

            if question is None:

                print(
                    "QoTD scheduler: "
                    "The question bank contains "
                    "no active QoTD-eligible "
                    "questions."
                )

                return None

            print(
                "QoTD scheduler: "
                "All active QoTD-eligible questions "
                "have already been used. "
                "Starting a new cycle."
            )


        # ==================================================
        # CREATE DATABASE RECORD
        # ==================================================


        try:

            qotd = await create_qotd(
                guild_id=self.guild_id,
                channel_id=self.channel_id,
                question_date=current_date,
                question_bank_id=question["id"],
                question_text=question["question"],
                accepted_answers=(
                    question["accepted_answers"]
                ),
                explanation=(
                    question.get(
                        "explanation"
                    )
                ),
            )

        except QotdAlreadyExistsError:

            return await get_qotd_for_date(
                guild_id=self.guild_id,
                question_date=current_date,
            )


        print(
            "QoTD scheduler: "
            f"Selected bank question "
            f"#{question['id']} for "
            f"{current_date.isoformat()}."
        )

        return qotd


    # ==================================================
    # REMOVE OLD QOTD BUTTONS
    # ==================================================


    async def _remove_old_qotd_buttons(
        self,
        current_date,
    ):
        """
        Remove the Answer Question button from
        every QoTD older than today's question.

        The old message itself remains visible.
        """

        old_qotds = (
            await get_older_posted_qotds(
                guild_id=self.guild_id,
                before_date=current_date,
            )
        )

        for old_qotd in old_qotds:

            channel = self.bot.get_channel(
                old_qotd["channel_id"]
            )

            if channel is None:

                try:

                    channel = (
                        await self.bot.fetch_channel(
                            old_qotd["channel_id"]
                        )
                    )

                except (
                    discord.Forbidden,
                    discord.NotFound,
                    discord.HTTPException,
                ):

                    continue


            try:

                message = (
                    await channel.fetch_message(
                        old_qotd["message_id"]
                    )
                )

                await message.edit(
                    view=None
                )


            except discord.NotFound:

                continue


            except (
                discord.Forbidden,
                discord.HTTPException,
            ) as error:

                print(
                    "QoTD scheduler could not remove "
                    "an old Answer Question button: "
                    f"{error!r}"
                )


    # ==================================================
    # POST TIME CHECK
    # ==================================================


    def _post_time_has_arrived(
        self,
    ) -> bool:

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
