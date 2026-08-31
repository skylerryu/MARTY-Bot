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

from points.mechanics.random_speed_questions.rsq import (
    SpeedQuestionTooSoonError,
    choose_speed_question,
    get_latest_rsq_post,
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
    RSQ_DISTRIBUTION_SMOOTHING,
    RSQ_MIN_INTERVAL_MINUTES,
    RSQ_MISSED_SLOT_GRACE_MINUTES,
    RSQ_SCHEDULER_POLL_SECONDS,
)


# ==================================================
# SLOT STATUSES
# ==================================================


RSQ_SLOT_PENDING = "pending"
RSQ_SLOT_POSTED = "posted"
RSQ_SLOT_MISSED = "missed"
RSQ_SLOT_SKIPPED_COOLDOWN = "skipped_cooldown"
RSQ_SLOT_SKIPPED_NO_QUESTION = "skipped_no_question"


# ==================================================
# TIMEZONE
# ==================================================


RSQ_ZONE = ZoneInfo(
    RSQ_TIMEZONE
)


# ==================================================
# TIME HELPERS
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


def _parse_datetime(
    value: str,
) -> datetime:

    value = str(
        value
    ).strip()

    if value.endswith("Z"):

        value = (
            value[:-1]
            + "+00:00"
        )

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

    return parsed


# ==================================================
# DAILY TARGET
# ==================================================


def _generate_daily_target() -> int:

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

    target = max(
        RSQ_ABSOLUTE_MIN_DAILY,
        target,
    )

    target = min(
        RSQ_ABSOLUTE_MAX_DAILY,
        target,
    )

    return target


# ==================================================
# MAXIMUM CAPACITY
# ==================================================


def _get_maximum_capacity(
    start: datetime,
    end: datetime,
) -> int:

    if end < start:

        return 0

    available_seconds = (
        end
        - start
    ).total_seconds()

    minimum_gap_seconds = (
        RSQ_MIN_INTERVAL_MINUTES
        * 60
    )

    return (
        int(
            available_seconds
            // minimum_gap_seconds
        )
        + 1
    )


# ==================================================
# GENERATE RANDOM SCHEDULE BETWEEN TWO TIMES
# ==================================================


def _generate_schedule_times_between(
    start: datetime,
    end: datetime,
    target_count: int,
) -> list[datetime]:
    """
    Generate randomized times between start/end.

    Guarantees the configured minimum interval
    between generated slots.

    Randomness controls unpredictability.

    Distribution smoothing controls how strongly
    MARTY resists excessive clustering.
    """

    if target_count <= 0:

        return []

    if end < start:

        return []

    maximum_capacity = (
        _get_maximum_capacity(
            start=start,
            end=end,
        )
    )

    target_count = min(
        target_count,
        maximum_capacity,
    )

    if target_count <= 0:

        return []


    # ==================================================
    # AVAILABLE WINDOW
    # ==================================================


    window_seconds = (
        end
        - start
    ).total_seconds()

    minimum_gap_seconds = (
        RSQ_MIN_INTERVAL_MINUTES
        * 60
    )

    required_gap_seconds = (
        max(
            0,
            target_count - 1,
        )
        * minimum_gap_seconds
    )

    slack_seconds = (
        window_seconds
        - required_gap_seconds
    )

    if slack_seconds < 0:

        return []


    # ==================================================
    # RANDOM FLEXIBLE SPACE
    # ==================================================
    #
    # There are target_count + 1 flexible spaces:
    #
    #     before first slot
    #     between slots
    #     after final slot
    #
    # Minimum gaps are added separately.
    #
    # ==================================================


    space_count = (
        target_count
        + 1
    )

    if RSQ_TIMING_RANDOMNESS <= 0:

        raw_weights = [
            1.0
            for _ in range(
                space_count
            )
        ]

    else:

        alpha = (
            0.35
            + (
                8.0
                * RSQ_DISTRIBUTION_SMOOTHING
            )
            + (
                8.0
                * (
                    1.0
                    - RSQ_TIMING_RANDOMNESS
                )
            )
        )

        alpha = max(
            0.10,
            alpha,
        )

        raw_weights = [
            random.gammavariate(
                alpha,
                1.0,
            )
            for _ in range(
                space_count
            )
        ]

    total_weight = sum(
        raw_weights
    )

    if total_weight <= 0:

        raw_weights = [
            1.0
            for _ in range(
                space_count
            )
        ]

        total_weight = float(
            space_count
        )

    extra_spaces = [
        (
            slack_seconds
            * weight
            / total_weight
        )
        for weight
        in raw_weights
    ]


    # ==================================================
    # BUILD TIMES
    # ==================================================


    schedule_times = []

    elapsed_seconds = (
        extra_spaces[0]
    )

    for index in range(
        target_count
    ):

        if index > 0:

            elapsed_seconds += (
                minimum_gap_seconds
            )

            elapsed_seconds += (
                extra_spaces[index]
            )

        scheduled_time = (
            start
            + timedelta(
                seconds=(
                    elapsed_seconds
                )
            )
        )

        schedule_times.append(
            scheduled_time
        )

    return schedule_times


# ==================================================
# GENERATE FULL-DAY SCHEDULE
# ==================================================


def _generate_daily_schedule_times(
    calendar_date: date,
    target_count: int,
) -> list[datetime]:

    start, end = (
        _window_for_date(
            calendar_date
        )
    )

    return (
        _generate_schedule_times_between(
            start=start,
            end=end,
            target_count=target_count,
        )
    )


# ==================================================
# GET SCHEDULE DAY
# ==================================================


async def get_rsq_schedule_day(
    guild_id: int,
    channel_id: int,
    calendar_date: date,
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
                schedule_date,
                target_count,
                generated_at

            FROM rsq_schedule_days

            WHERE guild_id = ?
              AND channel_id = ?
              AND schedule_date = ?
            """,
            (
                guild_id,
                channel_id,
                calendar_date.isoformat(),
            ),
        )

        row = (
            await cursor.fetchone()
        )

    if row is None:

        return None

    return {
        "schedule_date": (
            row["schedule_date"]
        ),
        "target_count": (
            row["target_count"]
        ),
        "generated_at": (
            row["generated_at"]
        ),
    }


# ==================================================
# GET SCHEDULE SLOTS
# ==================================================


async def get_rsq_schedule_slots(
    guild_id: int,
    channel_id: int,
    calendar_date: date,
) -> list[dict]:

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        db.row_factory = (
            aiosqlite.Row
        )

        cursor = await db.execute(
            """
            SELECT
                id,
                slot_number,
                scheduled_at,
                status,
                question_id,
                message_id,
                posted_at

            FROM rsq_schedule_slots

            WHERE guild_id = ?
              AND channel_id = ?
              AND schedule_date = ?

            ORDER BY scheduled_at ASC
            """,
            (
                guild_id,
                channel_id,
                calendar_date.isoformat(),
            ),
        )

        rows = (
            await cursor.fetchall()
        )

    return [
        dict(row)
        for row in rows
    ]


# ==================================================
# CREATE DAILY SCHEDULE
# ==================================================


async def create_rsq_daily_schedule(
    guild_id: int,
    channel_id: int,
    calendar_date: date,
) -> dict:

    existing = (
        await get_rsq_schedule_day(
            guild_id=(
                guild_id
            ),
            channel_id=(
                channel_id
            ),
            calendar_date=(
                calendar_date
            ),
        )
    )

    if existing is not None:

        return existing

    target_count = (
        _generate_daily_target()
    )

    schedule_times = (
        _generate_daily_schedule_times(
            calendar_date=(
                calendar_date
            ),
            target_count=(
                target_count
            ),
        )
    )

    target_count = len(
        schedule_times
    )

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        await db.execute(
            "BEGIN IMMEDIATE"
        )

        cursor = await db.execute(
            """
            SELECT 1

            FROM rsq_schedule_days

            WHERE guild_id = ?
              AND channel_id = ?
              AND schedule_date = ?
            """,
            (
                guild_id,
                channel_id,
                calendar_date.isoformat(),
            ),
        )

        already_exists = (
            await cursor.fetchone()
        )

        if already_exists is not None:

            await db.rollback()

            result = (
                await get_rsq_schedule_day(
                    guild_id=(
                        guild_id
                    ),
                    channel_id=(
                        channel_id
                    ),
                    calendar_date=(
                        calendar_date
                    ),
                )
            )

            if result is None:

                raise RuntimeError(
                    "Could not retrieve existing "
                    "RSQ schedule."
                )

            return result

        await db.execute(
            """
            INSERT INTO rsq_schedule_days (
                guild_id,
                channel_id,
                schedule_date,
                target_count
            )

            VALUES (?, ?, ?, ?)
            """,
            (
                guild_id,
                channel_id,
                calendar_date.isoformat(),
                target_count,
            ),
        )

        for slot_number, scheduled_local in enumerate(
            schedule_times,
            start=1,
        ):

            await db.execute(
                """
                INSERT INTO rsq_schedule_slots (
                    guild_id,
                    channel_id,
                    schedule_date,
                    slot_number,
                    scheduled_at,
                    status
                )

                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    'pending'
                )
                """,
                (
                    guild_id,
                    channel_id,
                    calendar_date.isoformat(),
                    slot_number,
                    (
                        scheduled_local
                        .astimezone(
                            timezone.utc
                        )
                        .isoformat()
                    ),
                ),
            )

        await db.commit()

    print(
        "RSQ scheduler: "
        f"Generated {target_count} slots "
        f"for {calendar_date.isoformat()}."
    )

    for slot_number, scheduled_local in enumerate(
        schedule_times,
        start=1,
    ):

        print(
            "RSQ scheduler: "
            f"Slot {slot_number}: "
            f"{scheduled_local.isoformat()}"
        )

    result = (
        await get_rsq_schedule_day(
            guild_id=(
                guild_id
            ),
            channel_id=(
                channel_id
            ),
            calendar_date=(
                calendar_date
            ),
        )
    )

    if result is None:

        raise RuntimeError(
            "RSQ schedule was created but "
            "could not be retrieved."
        )

    return result


# ==================================================
# ENSURE SCHEDULE
# ==================================================


async def ensure_rsq_daily_schedule(
    guild_id: int,
    channel_id: int,
    calendar_date: date,
):

    existing = (
        await get_rsq_schedule_day(
            guild_id=(
                guild_id
            ),
            channel_id=(
                channel_id
            ),
            calendar_date=(
                calendar_date
            ),
        )
    )

    if existing is not None:

        return existing

    return (
        await create_rsq_daily_schedule(
            guild_id=(
                guild_id
            ),
            channel_id=(
                channel_id
            ),
            calendar_date=(
                calendar_date
            ),
        )
    )


# ==================================================
# REGENERATE REMAINING SCHEDULE
# ==================================================


async def regenerate_remaining_rsq_schedule(
    guild_id: int,
    channel_id: int,
) -> dict:
    """
    Regenerate only today's REMAINING RSQ schedule.

    Existing posted/missed/skipped slots remain
    untouched for audit/history.

    Existing pending slots are removed.

    A fresh daily target is drawn using the current
    rsq_config.py values.

    The number of already-processed slots is
    subtracted from that new target.

    New remaining slots are scheduled from now
    through the end of today's configured window.
    """

    now_local = (
        _now_local()
    )

    calendar_date = (
        now_local.date()
    )

    window_start, window_end = (
        _window_for_date(
            calendar_date
        )
    )


    # ==================================================
    # IF TODAY'S WINDOW IS ALREADY OVER
    # ==================================================


    if now_local >= window_end:

        return {
            "schedule_date": (
                calendar_date.isoformat()
            ),
            "target_count": 0,
            "processed_count": 0,
            "remaining_count": 0,
            "times": [],
            "window_over": True,
        }


    # ==================================================
    # GET EXISTING SLOTS
    # ==================================================


    existing_slots = (
        await get_rsq_schedule_slots(
            guild_id=(
                guild_id
            ),
            channel_id=(
                channel_id
            ),
            calendar_date=(
                calendar_date
            ),
        )
    )

    processed_slots = [
        slot
        for slot
        in existing_slots
        if (
            slot["status"]
            != RSQ_SLOT_PENDING
        )
    ]

    processed_count = len(
        processed_slots
    )


    # ==================================================
    # DRAW A NEW DAILY TARGET
    # ==================================================


    new_daily_target = (
        _generate_daily_target()
    )

    desired_remaining = max(
        0,
        (
            new_daily_target
            - processed_count
        ),
    )


    # ==================================================
    # EARLIEST NEW SLOT
    # ==================================================
    #
    # Start from "now".
    #
    # If an RSQ was posted recently, also respect
    # the hard minimum interval while creating the
    # replacement schedule.
    #
    # ==================================================


    earliest_start = max(
        now_local,
        window_start,
    )

    latest_post = (
        await get_latest_rsq_post(
            guild_id=(
                guild_id
            ),
            channel_id=(
                channel_id
            ),
        )
    )

    if latest_post is not None:

        latest_post_datetime = (
            _parse_datetime(
                latest_post[
                    "posted_at"
                ]
            )
            .astimezone(
                RSQ_ZONE
            )
        )

        cooldown_end = (
            latest_post_datetime
            + timedelta(
                minutes=(
                    RSQ_MIN_INTERVAL_MINUTES
                )
            )
        )

        earliest_start = max(
            earliest_start,
            cooldown_end,
        )


    # ==================================================
    # GENERATE NEW REMAINING TIMES
    # ==================================================


    if (
        desired_remaining <= 0
        or earliest_start > window_end
    ):

        new_times = []

    else:

        new_times = (
            _generate_schedule_times_between(
                start=(
                    earliest_start
                ),
                end=(
                    window_end
                ),
                target_count=(
                    desired_remaining
                ),
            )
        )


    # ==================================================
    # FINAL TARGET
    # ==================================================


    final_target_count = (
        processed_count
        + len(
            new_times
        )
    )


    # ==================================================
    # NEXT SLOT NUMBER
    # ==================================================


    if processed_slots:

        next_slot_number = (
            max(
                int(
                    slot[
                        "slot_number"
                    ]
                )
                for slot
                in processed_slots
            )
            + 1
        )

    else:

        next_slot_number = 1


    # ==================================================
    # SAVE ATOMICALLY
    # ==================================================


    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        await db.execute(
            "BEGIN IMMEDIATE"
        )


        # ==================================================
        # DELETE ONLY PENDING SLOTS
        # ==================================================


        await db.execute(
            """
            DELETE FROM rsq_schedule_slots

            WHERE guild_id = ?
              AND channel_id = ?
              AND schedule_date = ?
              AND status = 'pending'
            """,
            (
                guild_id,
                channel_id,
                calendar_date.isoformat(),
            ),
        )


        # ==================================================
        # UPSERT DAY
        # ==================================================


        await db.execute(
            """
            INSERT INTO rsq_schedule_days (
                guild_id,
                channel_id,
                schedule_date,
                target_count,
                generated_at
            )

            VALUES (
                ?,
                ?,
                ?,
                ?,
                CURRENT_TIMESTAMP
            )

            ON CONFLICT (
                guild_id,
                channel_id,
                schedule_date
            )

            DO UPDATE SET
                target_count = excluded.target_count,
                generated_at = CURRENT_TIMESTAMP
            """,
            (
                guild_id,
                channel_id,
                calendar_date.isoformat(),
                final_target_count,
            ),
        )


        # ==================================================
        # INSERT NEW PENDING SLOTS
        # ==================================================


        for offset, scheduled_local in enumerate(
            new_times
        ):

            slot_number = (
                next_slot_number
                + offset
            )

            scheduled_utc = (
                scheduled_local
                .astimezone(
                    timezone.utc
                )
                .isoformat()
            )

            await db.execute(
                """
                INSERT INTO rsq_schedule_slots (
                    guild_id,
                    channel_id,
                    schedule_date,
                    slot_number,
                    scheduled_at,
                    status
                )

                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    'pending'
                )
                """,
                (
                    guild_id,
                    channel_id,
                    calendar_date.isoformat(),
                    slot_number,
                    scheduled_utc,
                ),
            )

        await db.commit()


    # ==================================================
    # CONSOLE OUTPUT
    # ==================================================


    print(
        "\n"
        "========================================\n"
        "RSQ SCHEDULE REGENERATED\n"
        "========================================"
    )

    print(
        "Date: "
        f"{calendar_date.isoformat()}"
    )

    print(
        "New daily target: "
        f"{new_daily_target}"
    )

    print(
        "Already processed: "
        f"{processed_count}"
    )

    print(
        "New remaining slots: "
        f"{len(new_times)}"
    )

    for index, scheduled_local in enumerate(
        new_times,
        start=1,
    ):

        print(
            f"New slot {index}: "
            f"{scheduled_local.isoformat()}"
        )

    print(
        "========================================\n"
    )


    # ==================================================
    # RETURN
    # ==================================================


    return {
        "schedule_date": (
            calendar_date.isoformat()
        ),
        "target_count": (
            final_target_count
        ),
        "drawn_target": (
            new_daily_target
        ),
        "processed_count": (
            processed_count
        ),
        "remaining_count": (
            len(
                new_times
            )
        ),
        "times": [
            (
                scheduled_time
                .astimezone(
                    timezone.utc
                )
                .isoformat()
            )
            for scheduled_time
            in new_times
        ],
        "window_over": False,
    }


# ==================================================
# GET DUE SLOTS
# ==================================================


async def _get_due_pending_slots(
    guild_id: int,
    channel_id: int,
    now_utc: datetime,
) -> list[dict]:

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        db.row_factory = (
            aiosqlite.Row
        )

        cursor = await db.execute(
            """
            SELECT
                id,
                schedule_date,
                slot_number,
                scheduled_at,
                status

            FROM rsq_schedule_slots

            WHERE guild_id = ?
              AND channel_id = ?
              AND status = 'pending'
              AND scheduled_at <= ?

            ORDER BY scheduled_at ASC
            """,
            (
                guild_id,
                channel_id,
                now_utc.isoformat(),
            ),
        )

        rows = (
            await cursor.fetchall()
        )

    return [
        dict(row)
        for row in rows
    ]


# ==================================================
# UPDATE SLOT
# ==================================================


async def _set_slot_status(
    slot_id: int,
    status: str,
    question_id: int | None = None,
    message_id: int | None = None,
    posted_at: str | None = None,
):

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        await db.execute(
            """
            UPDATE rsq_schedule_slots

            SET
                status = ?,
                question_id = ?,
                message_id = ?,
                posted_at = ?

            WHERE id = ?
            """,
            (
                status,
                question_id,
                message_id,
                posted_at,
                slot_id,
            ),
        )

        await db.commit()


# ==================================================
# GET DISCORD CHANNEL
# ==================================================


async def _get_channel(
    bot: discord.Client,
    channel_id: int,
):

    channel = (
        bot.get_channel(
            channel_id
        )
    )

    if channel is not None:

        return channel

    try:

        return (
            await bot.fetch_channel(
                channel_id
            )
        )

    except (
        discord.Forbidden,
        discord.NotFound,
        discord.HTTPException,
    ) as error:

        print(
            "RSQ scheduler could not access "
            "the configured RSQ channel: "
            f"{error!r}"
        )

        return None


# ==================================================
# RSQ SCHEDULER
# ==================================================


class RsqScheduler:

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


        # ==================================================
        # REGISTER RSQ ADMIN COMMANDS
        # ==================================================
        #
        # Your current bot.py creates RsqScheduler
        # before tree.sync(), so this lets the scheduler
        # register its admin commands without another
        # bot.py edit.
        #
        # ==================================================


        from commands.admin_commands.rsq_admin_commands import (
            register_rsq_admin_commands,
        )

        register_rsq_admin_commands(
            tree=(
                self.bot.tree
            ),
            guild=discord.Object(
                id=(
                    self.guild_id
                )
            ),
            scheduler=self,
        )


    # ==================================================
    # REGENERATE TODAY
    # ==================================================


    async def regenerate_today(
        self,
    ) -> dict:

        return (
            await regenerate_remaining_rsq_schedule(
                guild_id=(
                    self.guild_id
                ),
                channel_id=(
                    self.channel_id
                ),
            )
        )

    async def get_schedule_day(
        self,
        calendar_date: date,
    ) -> dict | None:

        return (
            await get_rsq_schedule_day(
                guild_id=(
                    self.guild_id
                ),
                channel_id=(
                    self.channel_id
                ),
                calendar_date=(
                    calendar_date
                ),
            )
        )


    async def get_schedule_slots(
        self,
        calendar_date: date,
    ) -> list[dict]:

        return (
            await get_rsq_schedule_slots(
                guild_id=(
                    self.guild_id
                ),
                channel_id=(
                    self.channel_id
                ),
                calendar_date=(
                    calendar_date
                ),
            )
        )


    # ==================================================
    # START
    # ==================================================


    def start(
        self,
    ):

        if not RSQ_ENABLED:

            print(
                "RSQ scheduler is disabled "
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


    # ==================================================
    # LOOP ERROR
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

        if not RSQ_ENABLED:

            return

        now_local = (
            _now_local()
        )

        now_utc = (
            datetime.now(
                timezone.utc
            )
        )


        # ==================================================
        # ENSURE TODAY'S SCHEDULE
        # ==================================================


        await ensure_rsq_daily_schedule(
            guild_id=(
                self.guild_id
            ),
            channel_id=(
                self.channel_id
            ),
            calendar_date=(
                now_local.date()
            ),
        )


        # ==================================================
        # GET DUE SLOTS
        # ==================================================


        due_slots = (
            await _get_due_pending_slots(
                guild_id=(
                    self.guild_id
                ),
                channel_id=(
                    self.channel_id
                ),
                now_utc=(
                    now_utc
                ),
            )
        )

        if not due_slots:

            return

        for slot in due_slots:

            await self._process_slot(
                slot=slot,
                now_utc=(
                    datetime.now(
                        timezone.utc
                    )
                ),
            )


    # ==================================================
    # PROCESS SLOT
    # ==================================================


    async def _process_slot(
        self,
        slot: dict,
        now_utc: datetime,
    ):

        scheduled_at = (
            _parse_datetime(
                slot[
                    "scheduled_at"
                ]
            )
            .astimezone(
                timezone.utc
            )
        )

        lateness_seconds = (
            now_utc
            - scheduled_at
        ).total_seconds()

        grace_seconds = (
            RSQ_MISSED_SLOT_GRACE_MINUTES
            * 60
        )


        # ==================================================
        # MISSED
        # ==================================================


        if (
            lateness_seconds
            > grace_seconds
        ):

            await _set_slot_status(
                slot_id=(
                    slot[
                        "id"
                    ]
                ),
                status=(
                    RSQ_SLOT_MISSED
                ),
            )

            print(
                "RSQ scheduler: "
                f"Slot {slot['slot_number']} "
                "was missed."
            )

            return


        # ==================================================
        # SELECT QUESTION AT POST TIME
        # ==================================================


        question = (
            await choose_speed_question(
                guild_id=(
                    self.guild_id
                ),
                channel_id=(
                    self.channel_id
                ),
                category=None,
                automatic=True,
            )
        )

        if question is None:

            await _set_slot_status(
                slot_id=(
                    slot[
                        "id"
                    ]
                ),
                status=(
                    RSQ_SLOT_SKIPPED_NO_QUESTION
                ),
            )

            print(
                "RSQ scheduler: "
                f"Slot {slot['slot_number']} "
                "skipped because no eligible "
                "question was available."
            )

            return


        # ==================================================
        # CHANNEL
        # ==================================================


        channel = (
            await _get_channel(
                bot=(
                    self.bot
                ),
                channel_id=(
                    self.channel_id
                ),
            )
        )

        if channel is None:

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

            await _set_slot_status(
                slot_id=(
                    slot[
                        "id"
                    ]
                ),
                status=(
                    RSQ_SLOT_SKIPPED_COOLDOWN
                ),
            )

            print(
                "RSQ scheduler: "
                f"Slot {slot['slot_number']} "
                "skipped because another RSQ "
                "was posted too recently."
            )

            return

        except (
            discord.Forbidden,
            discord.HTTPException,
        ) as error:

            print(
                "RSQ scheduler Discord error: "
                f"{error!r}"
            )

            return

        except Exception as error:

            print(
                "RSQ scheduler posting error: "
                f"{error!r}"
            )

            return


        # ==================================================
        # POSTED
        # ==================================================


        await _set_slot_status(
            slot_id=(
                slot[
                    "id"
                ]
            ),
            status=(
                RSQ_SLOT_POSTED
            ),
            question_id=(
                result[
                    "question_id"
                ]
            ),
            message_id=(
                result[
                    "message_id"
                ]
            ),
            posted_at=(
                result[
                    "posted_at"
                ]
            ),
        )

        print(
            "RSQ scheduler: "
            f"Posted slot "
            f"{slot['slot_number']} "
            f"using QBank "
            f"#{result['question_id']}."
        )