import asyncio
import random

from datetime import (
    datetime,
    time,
    timedelta,
)

from zoneinfo import (
    ZoneInfo,
)

import discord

from discord.ext import (
    tasks,
)

from questions.q_manager import (
    get_all_questions,
)

from points.time_helpers import (
    get_chicago_datetime,
    get_current_chicago_datetime,
)

from points.mechanics.question_of_the_day.qotd_config import (
    QOTD_TIMEZONE,
    QOTD_POST_HOUR,
    QOTD_POST_MINUTE,
)

from points.mechanics.question_of_the_day.qotd_questions import (
    QotdAlreadyExistsError,
    create_qotd,
    get_active_qotd,
    get_qotd_for_date,
    get_used_qotd_question_bank_ids,
    get_expired_posted_qotds,
    set_qotd_message_id,
)

from points.mechanics.question_of_the_day.qotd_display import (
    build_qotd_question_embed,
    get_qotd_time_remaining_text,
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
# COUNTDOWN REFRESH
# ==================================================
#
# MARTY checks frequently, but only edits the
# Discord message when the DISPLAYED countdown
# actually changes.
#
# That means:
#
#     hours:
#         about once per hour
#
#     under 1 hour:
#         every 15 minutes
#
#     under 15 minutes:
#         every 5 minutes
#
#     under 1 minute:
#         every 15 / 5 seconds
#
# ==================================================


QOTD_COUNTDOWN_CHECK_SECONDS = 5


# ==================================================
# NEXT QOTD DEADLINE
# ==================================================


def get_next_qotd_deadline(
    now: datetime | None = None,
) -> datetime:
    """
    Return the next upcoming configured QoTD
    posting time.

    Example with a 6:00 AM posting time:

    12:30 AM today
        -> today at 6:00 AM

    5:59 AM today
        -> today at 6:00 AM

    6:00 AM today
        -> tomorrow at 6:00 AM

    4:00 PM today
        -> tomorrow at 6:00 AM
    """

    if now is None:

        now = (
            get_current_chicago_datetime()
        )

    deadline = (
        get_chicago_datetime(
            calendar_date=(
                now.date()
            ),
            hour=(
                QOTD_POST_HOUR
            ),
            minute=(
                QOTD_POST_MINUTE
            ),
        )
    )

    if now >= deadline:

        deadline = (
            deadline
            + timedelta(
                days=1
            )
        )

    return deadline


# ==================================================
# LOGICAL QOTD DATE
# ==================================================


def _get_question_date_from_deadline(
    deadline: datetime,
):
    """
    Return the logical date for the QoTD period.

    This is used for streaks and the displayed
    QoTD date.

    The actual expiration is always controlled
    directly by expires_at.
    """

    return (
        deadline
        - timedelta(
            days=1
        )
    ).date()


# ==================================================
# QUESTION SELECTION
# ==================================================


def _get_random_qotd_question(
    excluded_ids: set[int] | None = None,
) -> dict | None:

    if excluded_ids is None:

        excluded_ids = set()

    eligible_questions = [
        question
        for question
        in get_all_questions(
            active_only=True
        )
        if (
            question.get(
                "category"
            )
            not in QOTD_EXCLUDED_CATEGORIES

            and question[
                "id"
            ]
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

        self.bot = (
            bot
        )

        self.guild_id = (
            guild_id
        )

        self.channel_id = (
            channel_id
        )

        self._post_lock = (
            asyncio.Lock()
        )


        # ==================================================
        # COUNTDOWN CACHE
        # ==================================================
        #
        # The refresh loop runs every few seconds.
        #
        # We remember what countdown text is currently
        # displayed so Discord is only contacted when
        # that text actually needs to change.
        #
        # ==================================================


        self._countdown_qotd_id = None

        self._countdown_text = None


    # ==================================================
    # START
    # ==================================================


    def start(
        self,
    ):

        if (
            not self.daily_qotd_post
            .is_running()
        ):

            self.daily_qotd_post.start()

        if (
            not self.qotd_countdown_refresh
            .is_running()
        ):

            self.qotd_countdown_refresh.start()


    # ==================================================
    # STOP
    # ==================================================


    def stop(
        self,
    ):

        if (
            self.daily_qotd_post
            .is_running()
        ):

            self.daily_qotd_post.cancel()

        if (
            self.qotd_countdown_refresh
            .is_running()
        ):

            self.qotd_countdown_refresh.cancel()


    # ==================================================
    # DAILY POST
    # ==================================================


    @tasks.loop(
        time=(
            QOTD_POST_TIME
        )
    )
    async def daily_qotd_post(
        self,
    ):

        await self.ensure_today_qotd_posted(
            require_post_time=False,
        )


    # ==================================================
    # DAILY POST STARTUP
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
    # DAILY POST ERROR
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
    # COUNTDOWN REFRESH LOOP
    # ==================================================


    @tasks.loop(
        seconds=(
            QOTD_COUNTDOWN_CHECK_SECONDS
        )
    )
    async def qotd_countdown_refresh(
        self,
    ):

        await self._refresh_qotd_countdown()


    # ==================================================
    # COUNTDOWN STARTUP
    # ==================================================


    @qotd_countdown_refresh.before_loop
    async def before_qotd_countdown_refresh(
        self,
    ):

        await self.bot.wait_until_ready()


    # ==================================================
    # COUNTDOWN ERROR
    # ==================================================


    @qotd_countdown_refresh.error
    async def qotd_countdown_refresh_error(
        self,
        error: Exception,
    ):

        print(
            "QoTD countdown refresh error: "
            f"{error!r}"
        )


    # ==================================================
    # REFRESH COUNTDOWN
    # ==================================================


    async def _refresh_qotd_countdown(
        self,
    ):


        # ==================================================
        # ACTIVE QOTD
        # ==================================================


        qotd = (
            await get_active_qotd(
                guild_id=(
                    self.guild_id
                ),
            )
        )

        if qotd is None:

            self._countdown_qotd_id = None
            self._countdown_text = None

            return


        # ==================================================
        # MESSAGE MUST EXIST
        # ==================================================


        message_id = (
            qotd[
                "message_id"
            ]
        )

        if message_id is None:

            return


        # ==================================================
        # CURRENT DISPLAY TEXT
        # ==================================================


        countdown_text = (
            get_qotd_time_remaining_text(
                expires_at=(
                    qotd[
                        "expires_at"
                    ]
                )
            )
        )


        # ==================================================
        # NOTHING CHANGED
        # ==================================================
        #
        # This is the important part.
        #
        # The loop may run every 5 seconds, but if:
        #
        #     "< 18 hrs"
        #
        # is still:
        #
        #     "< 18 hrs"
        #
        # MARTY does absolutely nothing.
        #
        # ==================================================


        if (
            self._countdown_qotd_id
            == qotd["id"]

            and self._countdown_text
            == countdown_text
        ):

            return


        # ==================================================
        # CHANNEL
        # ==================================================


        channel = (
            self.bot.get_channel(
                qotd[
                    "channel_id"
                ]
            )
        )

        if channel is None:

            try:

                channel = (
                    await self.bot.fetch_channel(
                        qotd[
                            "channel_id"
                        ]
                    )
                )

            except (
                discord.Forbidden,
                discord.NotFound,
                discord.HTTPException,
            ) as error:

                print(
                    "QoTD countdown could not "
                    "access the QoTD channel: "
                    f"{error!r}"
                )

                return


        # ==================================================
        # MESSAGE
        # ==================================================


        try:

            message = (
                await channel.fetch_message(
                    message_id
                )
            )

        except discord.NotFound:

            # Prevent MARTY from repeatedly trying
            # to fetch a message that no longer exists
            # every 5 seconds.

            self._countdown_qotd_id = (
                qotd[
                    "id"
                ]
            )

            self._countdown_text = (
                countdown_text
            )

            return

        except discord.Forbidden as error:

            print(
                "QoTD countdown cannot access "
                "the QoTD message: "
                f"{error!r}"
            )

            return

        except discord.HTTPException:

            # Temporary Discord problem.
            #
            # Do not update the cache so MARTY
            # automatically retries shortly.

            return


        # ==================================================
        # UPDATE EMBED
        # ==================================================


        try:

            await message.edit(
                embed=(
                    build_qotd_question_embed(
                        question_text=(
                            qotd[
                                "question_text"
                            ]
                        ),
                        question_date=(
                            qotd[
                                "question_date"
                            ]
                        ),
                        expires_at=(
                            qotd[
                                "expires_at"
                            ]
                        ),
                    )
                )
            )

        except discord.NotFound:

            self._countdown_qotd_id = (
                qotd[
                    "id"
                ]
            )

            self._countdown_text = (
                countdown_text
            )

            return

        except discord.Forbidden as error:

            print(
                "QoTD countdown cannot edit "
                "the QoTD message: "
                f"{error!r}"
            )

            return

        except discord.HTTPException:

            # Retry automatically on the next
            # countdown check.

            return


        # ==================================================
        # SAVE DISPLAY STATE
        # ==================================================


        self._countdown_qotd_id = (
            qotd[
                "id"
            ]
        )

        self._countdown_text = (
            countdown_text
        )


    # ==================================================
    # ENSURE QOTD IS POSTED
    # ==================================================


    async def ensure_today_qotd_posted(
        self,
        require_post_time: bool = True,
    ) -> bool:

        async with self._post_lock:


            # ==================================================
            # STARTUP TIME CHECK
            # ==================================================


            if (
                require_post_time

                and not self._post_time_has_arrived()
            ):

                return False


            # ==================================================
            # REMOVE EXPIRED BUTTONS
            # ==================================================


            await (
                self._remove_expired_qotd_buttons()
            )


            # ==================================================
            # EXISTING ACTIVE QOTD
            # ==================================================


            qotd = (
                await get_active_qotd(
                    guild_id=(
                        self.guild_id
                    ),
                )
            )

            if qotd is not None:

                if (
                    qotd[
                        "message_id"
                    ]
                    is not None
                ):

                    return False


            # ==================================================
            # CREATE NEW QOTD
            # ==================================================


            if qotd is None:

                qotd = (
                    await self._create_qotd()
                )

                if qotd is None:

                    return False


            # ==================================================
            # GET CHANNEL
            # ==================================================


            channel = (
                self.bot.get_channel(
                    qotd[
                        "channel_id"
                    ]
                )
            )

            if channel is None:

                try:

                    channel = (
                        await self.bot.fetch_channel(
                            qotd[
                                "channel_id"
                            ]
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

                message = (
                    await channel.send(
                        embed=(
                            build_qotd_question_embed(
                                question_text=(
                                    qotd[
                                        "question_text"
                                    ]
                                ),
                                question_date=(
                                    qotd[
                                        "question_date"
                                    ]
                                ),
                                expires_at=(
                                    qotd[
                                        "expires_at"
                                    ]
                                ),
                            )
                        ),
                        view=(
                            QotdAnswerView(
                                qotd_id=(
                                    qotd[
                                        "id"
                                    ]
                                )
                            )
                        ),
                    )
                )

            except (
                discord.Forbidden,
                discord.HTTPException,
            ) as error:

                print(
                    "QoTD scheduler could not "
                    "post the question: "
                    f"{error!r}"
                )

                return False


            # ==================================================
            # SAVE MESSAGE ID
            # ==================================================


            try:

                await set_qotd_message_id(
                    qotd_id=(
                        qotd[
                            "id"
                        ]
                    ),
                    message_id=(
                        message.id
                    ),
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
            # COUNTDOWN CACHE
            # ==================================================
            #
            # We just posted the correct countdown,
            # so tell the refresh loop what Discord
            # currently displays.
            #
            # ==================================================


            self._countdown_qotd_id = (
                qotd[
                    "id"
                ]
            )

            self._countdown_text = (
                get_qotd_time_remaining_text(
                    expires_at=(
                        qotd[
                            "expires_at"
                        ]
                    )
                )
            )


            # ==================================================
            # SUCCESS
            # ==================================================


            print(
                "QoTD scheduler: "
                f"Posted QoTD #{qotd['id']} "
                f"with deadline "
                f"{qotd['expires_at']} "
                f"using bank question "
                f"#{qotd['question_bank_id']}."
            )

            return True


    # ==================================================
    # CREATE QOTD
    # ==================================================


    async def _create_qotd(
        self,
    ) -> dict | None:

        deadline = (
            get_next_qotd_deadline()
        )

        question_date = (
            _get_question_date_from_deadline(
                deadline
            )
        )

        used_question_ids = (
            await get_used_qotd_question_bank_ids(
                guild_id=(
                    self.guild_id
                ),
            )
        )


        # ==================================================
        # SELECT QUESTION
        # ==================================================


        question = (
            _get_random_qotd_question(
                excluded_ids=(
                    used_question_ids
                )
            )
        )


        # ==================================================
        # START NEW CYCLE IF NEEDED
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
                "All eligible questions have "
                "already been used. "
                "Starting a new cycle."
            )


        # ==================================================
        # CREATE DATABASE RECORD
        # ==================================================


        try:

            qotd = (
                await create_qotd(
                    guild_id=(
                        self.guild_id
                    ),
                    channel_id=(
                        self.channel_id
                    ),
                    question_date=(
                        question_date
                    ),
                    expires_at=(
                        deadline
                    ),
                    question_bank_id=(
                        question[
                            "id"
                        ]
                    ),
                    question_text=(
                        question[
                            "question"
                        ]
                    ),
                    accepted_answers=(
                        question[
                            "accepted_answers"
                        ]
                    ),
                    explanation=(
                        question.get(
                            "explanation"
                        )
                    ),
                )
            )

        except QotdAlreadyExistsError:

            existing = (
                await get_qotd_for_date(
                    guild_id=(
                        self.guild_id
                    ),
                    question_date=(
                        question_date
                    ),
                )
            )

            return existing

        print(
            "QoTD scheduler: "
            f"Selected bank question "
            f"#{question['id']} with deadline "
            f"{deadline.isoformat()}."
        )

        return qotd


    # ==================================================
    # REMOVE EXPIRED BUTTONS
    # ==================================================


    async def _remove_expired_qotd_buttons(
        self,
    ):

        expired_qotds = (
            await get_expired_posted_qotds(
                guild_id=(
                    self.guild_id
                ),
            )
        )

        for old_qotd in expired_qotds:

            channel = (
                self.bot.get_channel(
                    old_qotd[
                        "channel_id"
                    ]
                )
            )

            if channel is None:

                try:

                    channel = (
                        await self.bot.fetch_channel(
                            old_qotd[
                                "channel_id"
                            ]
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
                        old_qotd[
                            "message_id"
                        ]
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
                    "QoTD scheduler could not "
                    "remove an expired Answer "
                    "Question button: "
                    f"{error!r}"
                )


    # ==================================================
    # POST TIME CHECK
    # ==================================================


    def _post_time_has_arrived(
        self,
    ) -> bool:

        now = (
            get_current_chicago_datetime()
        )

        return (
            now.hour,
            now.minute,
        ) >= (
            QOTD_POST_HOUR,
            QOTD_POST_MINUTE,
        )