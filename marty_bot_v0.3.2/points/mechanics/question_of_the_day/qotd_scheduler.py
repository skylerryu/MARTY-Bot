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
    QOTD_VISIBLE_MESSAGE_COUNT,
)

from points.mechanics.question_of_the_day.qotd_questions import (
    QotdAlreadyExistsError,
    create_qotd,
    get_active_qotd,
    get_qotd,
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
# CONFIG VALIDATION
# ==================================================


if QOTD_VISIBLE_MESSAGE_COUNT < 1:

    raise ValueError(
        "QOTD_VISIBLE_MESSAGE_COUNT "
        "must be at least 1."
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
# COUNTDOWN REFRESH
# ==================================================
#
# MARTY checks frequently, but only edits the
# Discord message when the DISPLAYED countdown
# actually changes.
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

        self.bot = bot

        self.guild_id = guild_id

        self.channel_id = channel_id

        self._post_lock = (
            asyncio.Lock()
        )

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
        time=QOTD_POST_TIME
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
    # COUNTDOWN LOOP
    # ==================================================


    @tasks.loop(
        seconds=QOTD_COUNTDOWN_CHECK_SECONDS
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
    # GET CHANNEL
    # ==================================================


    async def _get_channel(
        self,
        channel_id: int,
    ):

        channel = (
            self.bot.get_channel(
                channel_id
            )
        )

        if channel is not None:

            return channel

        try:

            return (
                await self.bot.fetch_channel(
                    channel_id
                )
            )

        except (
            discord.Forbidden,
            discord.NotFound,
            discord.HTTPException,
        ):

            return None


    # ==================================================
    # REFRESH COUNTDOWN
    # ==================================================


    async def _refresh_qotd_countdown(
        self,
    ):

        qotd = (
            await get_active_qotd(
                guild_id=self.guild_id,
            )
        )

        if qotd is None:

            self._countdown_qotd_id = None
            self._countdown_text = None

            return

        message_id = (
            qotd["message_id"]
        )

        if message_id is None:

            return

        countdown_text = (
            get_qotd_time_remaining_text(
                expires_at=(
                    qotd["expires_at"]
                )
            )
        )

        if (
            self._countdown_qotd_id
            == qotd["id"]

            and self._countdown_text
            == countdown_text
        ):

            return

        channel = (
            await self._get_channel(
                qotd["channel_id"]
            )
        )

        if channel is None:

            return

        try:

            message = (
                await channel.fetch_message(
                    message_id
                )
            )

        except discord.NotFound:

            self._countdown_qotd_id = (
                qotd["id"]
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

            return

        try:

            await message.edit(
                embed=(
                    build_qotd_question_embed(
                        question_text=(
                            qotd["question_text"]
                        ),
                        question_date=(
                            qotd["question_date"]
                        ),
                        expires_at=(
                            qotd["expires_at"]
                        ),
                    )
                )
            )

        except discord.NotFound:

            return

        except discord.Forbidden as error:

            print(
                "QoTD countdown cannot edit "
                "the QoTD message: "
                f"{error!r}"
            )

            return

        except discord.HTTPException:

            return

        self._countdown_qotd_id = (
            qotd["id"]
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
            # EXISTING ACTIVE QOTD
            # ==================================================


            qotd = (
                await get_active_qotd(
                    guild_id=self.guild_id,
                )
            )

            if (
                qotd is not None
                and qotd["message_id"] is not None
            ):

                # A current QoTD already exists.
                #
                # Because we know the new/current
                # message is safely posted, we can
                # now enforce the retention limit.

                await self._enforce_message_retention()

                return False


            # ==================================================
            # CREATE QOTD
            # ==================================================


            if qotd is None:

                qotd = (
                    await self._create_qotd()
                )

                if qotd is None:

                    return False


            # ==================================================
            # CHANNEL
            # ==================================================


            channel = (
                await self._get_channel(
                    qotd["channel_id"]
                )
            )

            if channel is None:

                print(
                    "QoTD scheduler could not "
                    "access the QoTD channel."
                )

                return False


            # ==================================================
            # POST NEW QOTD FIRST
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
                                    qotd["id"]
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
            # SAVE NEW MESSAGE
            # ==================================================


            try:

                await set_qotd_message_id(
                    qotd_id=qotd["id"],
                    message_id=message.id,
                )

            except Exception:

                # Do not leave an orphaned Discord
                # message if the DB write failed.

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


            self._countdown_qotd_id = (
                qotd["id"]
            )

            self._countdown_text = (
                get_qotd_time_remaining_text(
                    expires_at=(
                        qotd["expires_at"]
                    )
                )
            )


            # ==================================================
            # RETENTION
            # ==================================================
            #
            # THIS HAPPENS ONLY AFTER THE NEW QOTD
            # WAS SUCCESSFULLY POSTED AND SAVED.
            #
            # ==================================================


            await self._enforce_message_retention()


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
                guild_id=self.guild_id,
            )
        )

        question = (
            _get_random_qotd_question(
                excluded_ids=(
                    used_question_ids
                )
            )
        )

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
                        question["id"]
                    ),
                    question_text=(
                        question["question"]
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
    # ENFORCE MESSAGE RETENTION
    # ==================================================


    async def _enforce_message_retention(
        self,
    ):
        """
        Keep only the configured number of QoTD
        Discord messages.

        Example:

        QOTD_VISIBLE_MESSAGE_COUNT = 1

            current QoTD
                kept

            all expired QoTD messages
                deleted


        QOTD_VISIBLE_MESSAGE_COUNT = 3

            current QoTD
                kept

            newest 2 expired QoTDs
                kept

            anything older
                deleted


        Historical database rows are never deleted.
        """

        expired_qotds = (
            await get_expired_posted_qotds(
                guild_id=self.guild_id,
            )
        )

        # The active QoTD occupies one visible slot.
        #
        # Therefore:
        #
        # visible count 1 -> keep 0 expired
        # visible count 3 -> keep 2 expired

        expired_messages_to_keep = max(
            0,
            QOTD_VISIBLE_MESSAGE_COUNT - 1,
        )

        retained_expired_qotds = (
            expired_qotds[
                :expired_messages_to_keep
            ]
        )

        qotds_to_delete = (
            expired_qotds[
                expired_messages_to_keep:
            ]
        )


        # ==================================================
        # RETAINED EXPIRED QOTDS
        # ==================================================
        #
        # If the configuration is later increased
        # to 2, 3, etc., the previous QoTDs remain
        # visible.
        #
        # Rebuilding the embed causes its countdown
        # to display "Closed".
        #
        # We intentionally DO NOT replace the view.
        # This preserves the Flag Question button.
        #
        # The Answer button will safely report that
        # the QoTD has expired.
        #
        # ==================================================


        for old_qotd in retained_expired_qotds:

            await self._mark_retained_qotd_closed(
                old_qotd
            )


        # ==================================================
        # DELETE EVERYTHING BEYOND THE LIMIT
        # ==================================================


        for old_qotd in qotds_to_delete:

            await self._delete_old_qotd_message(
                old_qotd
            )


    # ==================================================
    # MARK RETAINED QOTD CLOSED
    # ==================================================


    async def _mark_retained_qotd_closed(
        self,
        old_qotd: dict,
    ):

        qotd = (
            await get_qotd(
                old_qotd["id"]
            )
        )

        if qotd is None:

            return

        message_id = (
            qotd["message_id"]
        )

        if message_id is None:

            return

        channel = (
            await self._get_channel(
                qotd["channel_id"]
            )
        )

        if channel is None:

            return

        try:

            message = (
                await channel.fetch_message(
                    message_id
                )
            )

        except discord.NotFound:

            # The message is already gone.
            #
            # Clear the stale message ID so MARTY
            # does not keep trying to restore it.

            await set_qotd_message_id(
                qotd_id=qotd["id"],
                message_id=None,
            )

            return

        except (
            discord.Forbidden,
            discord.HTTPException,
        ):

            return

        try:

            await message.edit(
                embed=(
                    build_qotd_question_embed(
                        question_text=(
                            qotd["question_text"]
                        ),
                        question_date=(
                            qotd["question_date"]
                        ),
                        expires_at=(
                            qotd["expires_at"]
                        ),
                    )
                )
            )

        except discord.NotFound:

            await set_qotd_message_id(
                qotd_id=qotd["id"],
                message_id=None,
            )

        except (
            discord.Forbidden,
            discord.HTTPException,
        ):

            return


    # ==================================================
    # DELETE OLD QOTD MESSAGE
    # ==================================================


    async def _delete_old_qotd_message(
        self,
        old_qotd: dict,
    ):

        qotd_id = (
            old_qotd["id"]
        )

        message_id = (
            old_qotd["message_id"]
        )

        if message_id is None:

            return

        channel = (
            await self._get_channel(
                old_qotd["channel_id"]
            )
        )

        if channel is None:

            return

        message_is_gone = False

        try:

            message = (
                await channel.fetch_message(
                    message_id
                )
            )

            await message.delete()

            message_is_gone = True

        except discord.NotFound:

            # The message was already manually
            # deleted from Discord.

            message_is_gone = True

        except (
            discord.Forbidden,
            discord.HTTPException,
        ) as error:

            print(
                "QoTD scheduler could not "
                "delete old QoTD "
                f"#{qotd_id}: "
                f"{error!r}"
            )

            return


        # ==================================================
        # CLEAR MESSAGE ID
        # ==================================================
        #
        # The database record itself remains.
        #
        # This prevents:
        #
        #     repeated deletion attempts
        #     stale persistent-view restoration
        #
        # ==================================================


        if message_is_gone:

            await set_qotd_message_id(
                qotd_id=qotd_id,
                message_id=None,
            )

            print(
                "QoTD scheduler: "
                f"Removed old QoTD "
                f"#{qotd_id} from Discord."
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