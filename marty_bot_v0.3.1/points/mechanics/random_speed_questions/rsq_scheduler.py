import math
import random

from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone,
)

from zoneinfo import (
    ZoneInfo,
)

import aiosqlite
import discord

from discord.ext import (
    tasks,
)

from data.system_db import (
    SYSTEM_DB_PATH,
)

from questions.q_manager import (
    get_all_questions,
)

from points.mechanics.random_speed_questions.rsq import (
    SpeedQuestionTooSoonError,
    post_speed_question,
)

from points.mechanics.random_speed_questions.rsq_config import (
    RSQ_ENABLED,
    RSQ_TIMEZONE,
    RSQ_WINDOW_START_HOUR,
    RSQ_WINDOW_START_MINUTE,
    RSQ_WINDOW_END_HOUR,
    RSQ_WINDOW_END_MINUTE,
    RSQ_DAILY_QUESTION_MEAN,
    RSQ_DAILY_QUESTION_STD_DEV,
    RSQ_ABSOLUTE_MIN_DAILY,
    RSQ_ABSOLUTE_MAX_DAILY,
    RSQ_TIMING_RANDOMNESS,
    RSQ_MIN_INTERVAL_MINUTES,
    RSQ_MISSED_SLOT_GRACE_MINUTES,
    RSQ_RECENT_QUESTION_AVOID_COUNT,
    RSQ_EXCLUDED_CATEGORIES,
    RSQ_SCHEDULER_POLL_SECONDS,
)


# ==================================================
# TIMEZONE
# ==================================================


RSQ_ZONE = ZoneInfo(
    RSQ_TIMEZONE
)


# ==================================================
# DATETIME HELPERS
# ==================================================


def _now_local() -> datetime:

    return (
        datetime.now(
            timezone.utc
        ).astimezone(
            RSQ_ZONE
        )
    )


def _window_for_date(
    calendar_date: date,
) -> tuple[datetime, datetime]:

    start = datetime.combine(
        calendar_date,
        time(
            hour=(
                RSQ_WINDOW_START_HOUR
            ),
            minute=(
                RSQ_WINDOW_START_MINUTE
            ),
        ),
        tzinfo=(
            RSQ_ZONE
        ),
    )

    end = datetime.combine(
        calendar_date,
        time(
            hour=(
                RSQ_WINDOW_END_HOUR
            ),
            minute=(
                RSQ_WINDOW_END_MINUTE
            ),
        ),
        tzinfo=(
            RSQ_ZONE
        ),
    )

    if end <= start:

        raise ValueError(
            "The RSQ posting window must "
            "end after it starts."
        )

    return (
        start,
        end,
    )


def _parse_utc(
    value: str,
) -> datetime:

    parsed = (
        datetime.fromisoformat(
            value
        )
    )

    if parsed.tzinfo is None:

        parsed = (
            parsed.replace(
                tzinfo=timezone.utc
            )
        )

    return (
        parsed.astimezone(
            timezone.utc
        )
    )


# ==================================================
# DAILY TARGET
# ==================================================


def _generate_daily_target() -> int:
    """
    Draw today's target from a normal distribution.

    Mean 16 / SD 2.5 means MARTY usually lands
    around 12–20, but those are not hard limits.
    """

    raw_target = (
        random.gauss(
            RSQ_DAILY_QUESTION_MEAN,
            RSQ_DAILY_QUESTION_STD_DEV,
        )
    )

    target = int(
        round(
            raw_target
        )
    )

    return max(
        RSQ_ABSOLUTE_MIN_DAILY,
        min(
            RSQ_ABSOLUTE_MAX_DAILY,
            target,
        ),
    )


# ==================================================
# INITIAL PROCESSED SLOT ESTIMATE
# ==================================================


def _estimate_elapsed_slots(
    now_local: datetime,
    target_count: int,
) -> int:
    """
    If MARTY first starts halfway through the day,
    do not try to cram an entire day's target into
    the remaining hours.

    We treat the approximate earlier portion of
    today's schedule as already missed.
    """

    window_start, window_end = (
        _window_for_date(
            now_local.date()
        )
    )

    if now_local <= window_start:

        return 0

    if now_local >= window_end:

        return (
            target_count
        )

    total_seconds = (
        window_end
        - window_start
    ).total_seconds()

    elapsed_seconds = (
        now_local
        - window_start
    ).total_seconds()

    fraction = (
        elapsed_seconds
        / total_seconds
    )

    estimated = math.floor(
        target_count
        * fraction
    )

    return max(
        0,
        min(
            target_count,
            estimated,
        ),
    )


# ==================================================
# NEXT RANDOM POST TIME
# ==================================================


def _calculate_next_post_time(
    reference_local: datetime,
    target_count: int,
    slots_processed: int,
) -> datetime | None:
    """
    Calculate the next randomized posting time.

    The system uses the remaining time in the day
    and the number of remaining question slots to
    estimate the correct average pacing.

    RSQ_TIMING_RANDOMNESS then perturbs that pacing.

    Randomness 0:
        approximately even spacing.

    Randomness 1:
        significantly more variable spacing.
    """

    window_start, window_end = (
        _window_for_date(
            reference_local.date()
        )
    )

    remaining_slots = (
        target_count
        - slots_processed
    )

    if remaining_slots <= 0:

        return None

    if reference_local < window_start:

        reference_local = (
            window_start
        )

    if reference_local >= window_end:

        return None

    available_seconds = (
        window_end
        - reference_local
    ).total_seconds()

    if available_seconds <= 0:

        return None

    minimum_gap_seconds = (
        RSQ_MIN_INTERVAL_MINUTES
        * 60
    )


    # ==================================================
    # IDEAL AVERAGE GAP
    # ==================================================


    average_gap_seconds = (
        available_seconds
        / remaining_slots
    )

    average_gap_seconds = max(
        minimum_gap_seconds,
        average_gap_seconds,
    )


    # ==================================================
    # RANDOM MULTIPLIER
    # ==================================================
    #
    # lognormal gives us asymmetric real-world-looking
    # gaps:
    #
    #     sometimes considerably shorter
    #     sometimes considerably longer
    #
    # while never producing a negative interval.
    #
    # The -sigma²/2 adjustment keeps the multiplier's
    # mean approximately around 1.
    #
    # ==================================================


    if (
        RSQ_TIMING_RANDOMNESS
        <= 0
    ):

        multiplier = 1.0

    else:

        sigma = (
            1.0
            * RSQ_TIMING_RANDOMNESS
        )

        multiplier = (
            random.lognormvariate(
                (
                    -0.5
                    * sigma
                    * sigma
                ),
                sigma,
            )
        )


    # ==================================================
    # RANDOMIZED GAP
    # ==================================================


    randomized_gap = (
        average_gap_seconds
        * multiplier
    )

    randomized_gap = max(
        minimum_gap_seconds,
        randomized_gap,
    )

    candidate = (
        reference_local
        + timedelta(
            seconds=(
                randomized_gap
            )
        )
    )


    # ==================================================
    # DO NOT MAKE IT IMPOSSIBLE TO FIT
    # THE REMAINING SLOTS
    # ==================================================


    later_slots = (
        remaining_slots
        - 1
    )

    latest_reasonable_time = (
        window_end
        - timedelta(
            seconds=(
                later_slots
                * minimum_gap_seconds
            )
        )
    )

    earliest_allowed_time = (
        reference_local
        + timedelta(
            seconds=(
                minimum_gap_seconds
            )
        )
    )

    if (
        latest_reasonable_time
        >= earliest_allowed_time
    ):

        candidate = min(
            candidate,
            latest_reasonable_time,
        )

    candidate = max(
        candidate,
        earliest_allowed_time,
    )

    if candidate > window_end:

        return None

    return candidate


# ==================================================
# STATE DATABASE HELPERS
# ==================================================


async def _get_daily_state(
    guild_id: int,
    channel_id: int,
    schedule_date: date,
) -> dict | None:

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        db.row_factory = (
            aiosqlite.Row
        )

        cursor = await db.execute(
            """
            SELECT
                target_count,
                slots_processed,
                next_post_at

            FROM rsq_daily_state

            WHERE guild_id = ?
              AND channel_id = ?
              AND schedule_date = ?
            """,
            (
                guild_id,
                channel_id,
                schedule_date.isoformat(),
            ),
        )

        row = await cursor.fetchone()

    if row is None:

        return None

    return {
        "target_count": (
            row["target_count"]
        ),
        "slots_processed": (
            row["slots_processed"]
        ),
        "next_post_at": (
            row["next_post_at"]
        ),
    }


async def _create_daily_state(
    guild_id: int,
    channel_id: int,
    now_local: datetime,
) -> dict:

    target_count = (
        _generate_daily_target()
    )

    slots_processed = (
        _estimate_elapsed_slots(
            now_local=(
                now_local
            ),
            target_count=(
                target_count
            ),
        )
    )

    next_local = (
        _calculate_next_post_time(
            reference_local=(
                now_local
            ),
            target_count=(
                target_count
            ),
            slots_processed=(
                slots_processed
            ),
        )
    )

    if next_local is None:

        next_post_at = None

    else:

        next_post_at = (
            next_local.astimezone(
                timezone.utc
            ).isoformat()
        )

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        await db.execute(
            """
            INSERT OR IGNORE INTO rsq_daily_state (
                guild_id,
                channel_id,
                schedule_date,
                target_count,
                slots_processed,
                next_post_at
            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                channel_id,
                now_local.date().isoformat(),
                target_count,
                slots_processed,
                next_post_at,
            ),
        )

        await db.commit()

    state = await _get_daily_state(
        guild_id=(
            guild_id
        ),
        channel_id=(
            channel_id
        ),
        schedule_date=(
            now_local.date()
        ),
    )

    if state is None:

        raise RuntimeError(
            "RSQ daily state could not "
            "be created."
        )

    print(
        "RSQ scheduler: "
        f"Today's target is "
        f"{state['target_count']} questions."
    )

    if state["next_post_at"]:

        print(
            "RSQ scheduler: "
            "Next automatic RSQ at "
            f"{state['next_post_at']}."
        )

    return state


async def _save_daily_state(
    guild_id: int,
    channel_id: int,
    schedule_date: date,
    slots_processed: int,
    next_post_at: str | None,
):

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        await db.execute(
            """
            UPDATE rsq_daily_state

            SET
                slots_processed = ?,
                next_post_at = ?,
                updated_at = CURRENT_TIMESTAMP

            WHERE guild_id = ?
              AND channel_id = ?
              AND schedule_date = ?
            """,
            (
                slots_processed,
                next_post_at,
                guild_id,
                channel_id,
                schedule_date.isoformat(),
            ),
        )

        await db.commit()


# ==================================================
# RECENT QUESTION IDS
# ==================================================


async def _get_recent_question_ids(
    guild_id: int,
    channel_id: int,
) -> set[int]:

    if (
        RSQ_RECENT_QUESTION_AVOID_COUNT
        <= 0
    ):

        return set()

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            SELECT question_id

            FROM rsq_post_history

            WHERE guild_id = ?
              AND channel_id = ?

            ORDER BY id DESC

            LIMIT ?
            """,
            (
                guild_id,
                channel_id,
                (
                    RSQ_RECENT_QUESTION_AVOID_COUNT
                ),
            ),
        )

        rows = await cursor.fetchall()

    return {
        int(row[0])
        for row in rows
    }


# ==================================================
# SELECT QUESTION
# ==================================================


async def _select_random_question(
    guild_id: int,
    channel_id: int,
) -> dict | None:

    questions = (
        get_all_questions(
            active_only=True
        )
    )

    eligible = [
        question
        for question in questions
        if (
            question.get(
                "category"
            )
            not in RSQ_EXCLUDED_CATEGORIES
        )
    ]

    if not eligible:

        return None

    recent_ids = (
        await _get_recent_question_ids(
            guild_id=(
                guild_id
            ),
            channel_id=(
                channel_id
            ),
        )
    )

    non_recent = [
        question
        for question in eligible
        if (
            int(
                question["id"]
            )
            not in recent_ids
        )
    ]


    # ==================================================
    # PREFER NON-RECENT QUESTIONS
    # ==================================================


    if non_recent:

        return random.choice(
            non_recent
        )


    # ==================================================
    # BANK TOO SMALL — ALLOW REUSE
    # ==================================================


    return random.choice(
        eligible
    )


# ==================================================
# SCHEDULER
# ==================================================


class RsqScheduler:

    def __init__(
        self,
        bot: discord.Client,
        guild_id: int,
        channel_id: int,
    ):

        self.bot = bot

        self.guild_id = (
            guild_id
        )

        self.channel_id = (
            channel_id
        )


    # ==================================================
    # START
    # ==================================================


    def start(
        self,
    ):

        if not RSQ_ENABLED:

            print(
                "RSQ scheduler disabled "
                "in rsq_config.py."
            )

            return

        if not self.rsq_loop.is_running():

            self.rsq_loop.start()


    # ==================================================
    # STOP
    # ==================================================


    def stop(
        self,
    ):

        if self.rsq_loop.is_running():

            self.rsq_loop.cancel()


    # ==================================================
    # LOOP
    # ==================================================


    @tasks.loop(
        seconds=(
            RSQ_SCHEDULER_POLL_SECONDS
        )
    )
    async def rsq_loop(
        self,
    ):

        await self._tick()


    # ==================================================
    # BEFORE LOOP
    # ==================================================


    @rsq_loop.before_loop
    async def before_rsq_loop(
        self,
    ):

        await self.bot.wait_until_ready()

        await self._tick()


    # ==================================================
    # ERROR
    # ==================================================


    @rsq_loop.error
    async def rsq_loop_error(
        self,
        error: Exception,
    ):

        print(
            "RSQ scheduler error: "
            f"{error!r}"
        )


    # ==================================================
    # TICK
    # ==================================================


    async def _tick(
        self,
    ):

        now_local = (
            _now_local()
        )

        window_start, window_end = (
            _window_for_date(
                now_local.date()
            )
        )


        # ==================================================
        # GET / CREATE TODAY'S STATE
        # ==================================================


        state = (
            await _get_daily_state(
                guild_id=(
                    self.guild_id
                ),
                channel_id=(
                    self.channel_id
                ),
                schedule_date=(
                    now_local.date()
                ),
            )
        )

        if state is None:

            state = (
                await _create_daily_state(
                    guild_id=(
                        self.guild_id
                    ),
                    channel_id=(
                        self.channel_id
                    ),
                    now_local=(
                        now_local
                    ),
                )
            )


        # ==================================================
        # OUTSIDE ACTIVE WINDOW
        # ==================================================


        if now_local < window_start:

            return

        if now_local > window_end:

            return


        # ==================================================
        # DAY FINISHED
        # ==================================================


        if (
            state["slots_processed"]
            >= state["target_count"]
        ):

            return


        # ==================================================
        # NO NEXT TIME
        # ==================================================


        next_post_at = (
            state["next_post_at"]
        )

        if next_post_at is None:

            return


        # ==================================================
        # NOT DUE YET
        # ==================================================


        next_post_utc = (
            _parse_utc(
                next_post_at
            )
        )

        now_utc = (
            datetime.now(
                timezone.utc
            )
        )

        if now_utc < next_post_utc:

            return


        # ==================================================
        # TOO OLD / BOT WAS OFFLINE
        # ==================================================


        lateness_seconds = (
            now_utc
            - next_post_utc
        ).total_seconds()

        grace_seconds = (
            RSQ_MISSED_SLOT_GRACE_MINUTES
            * 60
        )

        if (
            lateness_seconds
            > grace_seconds
        ):

            await self._skip_missed_slot(
                state=state,
                now_local=(
                    now_local
                ),
            )

            return


        # ==================================================
        # GET CHANNEL
        # ==================================================


        channel = self.bot.get_channel(
            self.channel_id
        )

        if channel is None:

            try:

                channel = (
                    await self.bot.fetch_channel(
                        self.channel_id
                    )
                )

            except (
                discord.Forbidden,
                discord.NotFound,
                discord.HTTPException,
            ) as error:

                print(
                    "RSQ scheduler could not "
                    "access channel: "
                    f"{error!r}"
                )

                return


        # ==================================================
        # SELECT QUESTION
        # ==================================================


        question = (
            await _select_random_question(
                guild_id=(
                    self.guild_id
                ),
                channel_id=(
                    self.channel_id
                ),
            )
        )

        if question is None:

            print(
                "RSQ scheduler: "
                "No eligible question exists."
            )

            return


        # ==================================================
        # POST
        # ==================================================


        try:

            result = (
                await post_speed_question(
                    channel=channel,
                    guild_id=(
                        self.guild_id
                    ),
                    question_data=(
                        question
                    ),
                    automatic=True,
                )
            )

        except SpeedQuestionTooSoonError:

            # A manual RSQ or another posting
            # happened within the last 15 minutes.
            #
            # Treat this automatic slot as used
            # instead of crowding another question
            # immediately afterward.

            print(
                "RSQ scheduler: "
                "Skipped automatic slot because "
                "another RSQ was posted within "
                "the minimum interval."
            )

            await self._advance_state(
                state=state,
                now_local=(
                    now_local
                ),
            )

            return

        except (
            discord.Forbidden,
            discord.HTTPException,
        ) as error:

            print(
                "RSQ scheduler could not "
                "post question: "
                f"{error!r}"
            )

            return


        # ==================================================
        # SUCCESS
        # ==================================================


        print(
            "RSQ scheduler: "
            f"Posted QBank "
            f"#{result['question_id']}."
        )

        await self._advance_state(
            state=state,
            now_local=(
                now_local
            ),
        )


    # ==================================================
    # ADVANCE ONE SLOT
    # ==================================================


    async def _advance_state(
        self,
        state: dict,
        now_local: datetime,
    ):

        new_processed = (
            state["slots_processed"]
            + 1
        )

        next_local = (
            _calculate_next_post_time(
                reference_local=(
                    now_local
                ),
                target_count=(
                    state["target_count"]
                ),
                slots_processed=(
                    new_processed
                ),
            )
        )

        if next_local is None:

            next_post_at = None

        else:

            next_post_at = (
                next_local.astimezone(
                    timezone.utc
                ).isoformat()
            )

        await _save_daily_state(
            guild_id=(
                self.guild_id
            ),
            channel_id=(
                self.channel_id
            ),
            schedule_date=(
                now_local.date()
            ),
            slots_processed=(
                new_processed
            ),
            next_post_at=(
                next_post_at
            ),
        )

        if next_local is not None:

            print(
                "RSQ scheduler: "
                "Next automatic question at "
                f"{next_local.isoformat()}."
            )


    # ==================================================
    # SKIP OLD MISSED SLOT
    # ==================================================


    async def _skip_missed_slot(
        self,
        state: dict,
        now_local: datetime,
    ):
        """
        If the bot was offline, estimate how much
        of today's schedule has already passed.

        This prevents MARTY from trying to catch up
        by firing questions every 15 minutes.
        """

        expected_processed = (
            _estimate_elapsed_slots(
                now_local=(
                    now_local
                ),
                target_count=(
                    state[
                        "target_count"
                    ]
                ),
            )
        )

        new_processed = max(
            (
                state[
                    "slots_processed"
                ]
                + 1
            ),
            expected_processed,
        )

        new_processed = min(
            state[
                "target_count"
            ],
            new_processed,
        )

        next_local = (
            _calculate_next_post_time(
                reference_local=(
                    now_local
                ),
                target_count=(
                    state[
                        "target_count"
                    ]
                ),
                slots_processed=(
                    new_processed
                ),
            )
        )

        if next_local is None:

            next_post_at = None

        else:

            next_post_at = (
                next_local.astimezone(
                    timezone.utc
                ).isoformat()
            )

        await _save_daily_state(
            guild_id=(
                self.guild_id
            ),
            channel_id=(
                self.channel_id
            ),
            schedule_date=(
                now_local.date()
            ),
            slots_processed=(
                new_processed
            ),
            next_post_at=(
                next_post_at
            ),
        )

        print(
            "RSQ scheduler: "
            "Skipped an overdue automatic "
            "question slot."
        )