import asyncio
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

from bot_config import (
    RANDOM_QUESTION_CHANNEL_ID,
)

from data.system_db import (
    SYSTEM_DB_PATH,
)

from questions.q_manager import (
    CATEGORY_NAMES,
    get_all_questions,
    get_question_by_id,
)

from questions.q_attempts import (
    record_question_attempt,
)

from questions.q_flag_ui import (
    QuestionFlagView,
)

from points.points_operations.add_points import (
    add_points,
)

from points.progressions.ranks.rank_up_display import (
    build_rank_up_embed,
)

from points.mechanics.random_speed_questions.rsq_config import (
    RSQ_TIMEZONE,
    RSQ_MIN_INTERVAL_MINUTES,
    RSQ_RECENT_QUESTION_AVOID_COUNT,
    RSQ_EXCLUDED_CATEGORIES,
)

from services.llm import (
    grade_answer_with_llm,
)


# ==================================================
# POINT VALUES
# ==================================================


SPEED_QUESTION_BASE_POINTS = 25

SPEED_QUESTION_30_SECOND_BONUS = 25
SPEED_QUESTION_1_MINUTE_BONUS = 10
SPEED_QUESTION_3_MINUTE_BONUS = 5


# ==================================================
# ERRORS
# ==================================================


class SpeedQuestionTooSoonError(
    Exception
):

    def __init__(
        self,
        remaining_seconds: float,
    ):

        self.remaining_seconds = max(
            0.0,
            remaining_seconds,
        )

        super().__init__(
            (
                "Another RSQ was posted "
                "too recently."
            )
        )


# ==================================================
# LOCKS
# ==================================================


_grading_locks = {}
_posting_locks = {}


def _get_grading_lock(
    guild_id: int,
    channel_id: int,
) -> asyncio.Lock:

    key = (
        guild_id,
        channel_id,
    )

    if key not in _grading_locks:

        _grading_locks[key] = (
            asyncio.Lock()
        )

    return _grading_locks[key]


def _get_posting_lock(
    guild_id: int,
    channel_id: int,
) -> asyncio.Lock:

    key = (
        guild_id,
        channel_id,
    )

    if key not in _posting_locks:

        _posting_locks[key] = (
            asyncio.Lock()
        )

    return _posting_locks[key]


# ==================================================
# DATETIME HELPER
# ==================================================


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
# CONTEXT KEY
# ==================================================


def build_speed_question_context_key(
    guild_id: int,
    channel_id: int,
    question_id: int,
    posted_at: str,
) -> str:

    return (
        f"rsq:{guild_id}:"
        f"{channel_id}:"
        f"{question_id}:"
        f"{posted_at}"
    )


# ==================================================
# ACTIVE QUESTION
# ==================================================


async def get_active_speed_question(
    guild_id: int,
    channel_id: int,
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
                question_id,
                message_id,
                posted_at,
                answered_by,
                answered_at

            FROM active_speed_questions

            WHERE guild_id = ?
              AND channel_id = ?
            """,
            (
                guild_id,
                channel_id,
            ),
        )

        row = await cursor.fetchone()

    if row is None:

        return None

    return {
        "question_id": (
            row["question_id"]
        ),
        "message_id": (
            row["message_id"]
        ),
        "posted_at": (
            row["posted_at"]
        ),
        "answered_by": (
            row["answered_by"]
        ),
        "answered_at": (
            row["answered_at"]
        ),
    }


# ==================================================
# LATEST POST
# ==================================================


async def get_latest_rsq_post(
    guild_id: int,
    channel_id: int,
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
                id,
                question_id,
                message_id,
                automatic,
                posted_at

            FROM rsq_post_history

            WHERE guild_id = ?
              AND channel_id = ?

            ORDER BY id DESC

            LIMIT 1
            """,
            (
                guild_id,
                channel_id,
            ),
        )

        row = await cursor.fetchone()

    if row is None:

        return None

    return {
        "id": row["id"],
        "question_id": (
            row["question_id"]
        ),
        "message_id": (
            row["message_id"]
        ),
        "automatic": bool(
            row["automatic"]
        ),
        "posted_at": (
            row["posted_at"]
        ),
    }


# ==================================================
# RECENT RSQ QUESTION IDS
# ==================================================


async def get_recent_rsq_question_ids(
    guild_id: int,
    channel_id: int,
    limit: int,
) -> list[int]:

    if limit <= 0:

        return []

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
                limit,
            ),
        )

        rows = await cursor.fetchall()

    return [
        int(row[0])
        for row in rows
    ]


# ==================================================
# AVOIDANCE LEVELS
# ==================================================


def _build_avoidance_levels(
    maximum: int,
) -> list[int]:

    if maximum <= 0:

        return [0]

    levels = []

    current = (
        maximum
    )

    while current > 1:

        if current not in levels:

            levels.append(
                current
            )

        current = max(
            1,
            current // 2,
        )

    if 1 not in levels:

        levels.append(
            1
        )

    levels.append(
        0
    )

    return levels


# ==================================================
# CHOOSE RSQ QUESTION
# ==================================================


async def choose_speed_question(
    guild_id: int,
    channel_id: int,
    category: str | None = None,
    automatic: bool = True,
) -> dict | None:
    """
    Pick an RSQ at posting time.

    get_all_questions(active_only=True) already
    excludes:
        inactive questions
        /flaggededit questions

    Automatic random selection also excludes
    RSQ_EXCLUDED_CATEGORIES.

    Explicit manual category selection can still
    access a category that is excluded from
    automatic RSQs.
    """

    all_questions = (
        get_all_questions(
            active_only=True
        )
    )

    eligible = []

    for question in all_questions:

        question_category = (
            question.get(
                "category"
            )
        )

        if category is not None:

            if (
                question_category
                != category
            ):

                continue

        else:

            if (
                question_category
                in RSQ_EXCLUDED_CATEGORIES
            ):

                continue

        eligible.append(
            question
        )

    if not eligible:

        return None


    # ==================================================
    # RECENT HISTORY
    # ==================================================


    recent_ids = (
        await get_recent_rsq_question_ids(
            guild_id=(
                guild_id
            ),
            channel_id=(
                channel_id
            ),
            limit=(
                RSQ_RECENT_QUESTION_AVOID_COUNT
            ),
        )
    )


    # ==================================================
    # PROGRESSIVELY RELAX AVOIDANCE
    # ==================================================


    avoidance_levels = (
        _build_avoidance_levels(
            RSQ_RECENT_QUESTION_AVOID_COUNT
        )
    )

    for avoidance_count in avoidance_levels:

        recent_set = set(
            recent_ids[
                :avoidance_count
            ]
        )

        candidates = [
            question
            for question in eligible
            if (
                int(
                    question["id"]
                )
                not in recent_set
            )
        ]

        if candidates:

            return random.choice(
                candidates
            )

    return None


# ==================================================
# POST COUNTS FOR DATE
# ==================================================


async def get_rsq_post_counts_for_date(
    guild_id: int,
    channel_id: int,
    calendar_date: date,
) -> dict:

    zone = ZoneInfo(
        RSQ_TIMEZONE
    )

    local_start = datetime.combine(
        calendar_date,
        time.min,
        tzinfo=zone,
    )

    local_end = (
        local_start
        + timedelta(days=1)
    )

    utc_start = (
        local_start.astimezone(
            timezone.utc
        ).isoformat()
    )

    utc_end = (
        local_end.astimezone(
            timezone.utc
        ).isoformat()
    )

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            SELECT
                COUNT(*),

                SUM(
                    CASE
                        WHEN automatic = 1
                        THEN 1
                        ELSE 0
                    END
                ),

                SUM(
                    CASE
                        WHEN automatic = 0
                        THEN 1
                        ELSE 0
                    END
                )

            FROM rsq_post_history

            WHERE guild_id = ?
              AND channel_id = ?
              AND posted_at >= ?
              AND posted_at < ?
            """,
            (
                guild_id,
                channel_id,
                utc_start,
                utc_end,
            ),
        )

        row = await cursor.fetchone()

    return {
        "total": int(
            row[0] or 0
        ),
        "automatic": int(
            row[1] or 0
        ),
        "manual": int(
            row[2] or 0
        ),
    }


# ==================================================
# COOLDOWN
# ==================================================


async def get_speed_question_cooldown_remaining(
    guild_id: int,
    channel_id: int,
) -> float:
    """
    Use both post history and the active-question
    row so this remains safe during migration from
    older MARTY versions.
    """

    timestamps = []

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

        timestamps.append(
            _parse_datetime(
                latest_post[
                    "posted_at"
                ]
            )
        )

    active_question = (
        await get_active_speed_question(
            guild_id=(
                guild_id
            ),
            channel_id=(
                channel_id
            ),
        )
    )

    if active_question is not None:

        timestamps.append(
            _parse_datetime(
                active_question[
                    "posted_at"
                ]
            )
        )

    if not timestamps:

        return 0.0

    latest_timestamp = max(
        timestamps
    ).astimezone(
        timezone.utc
    )

    elapsed_seconds = (
        datetime.now(
            timezone.utc
        )
        - latest_timestamp
    ).total_seconds()

    required_seconds = (
        RSQ_MIN_INTERVAL_MINUTES
        * 60
    )

    return max(
        0.0,
        required_seconds
        - elapsed_seconds,
    )


# ==================================================
# ACTIVATE + HISTORY
# ==================================================


async def _activate_and_record_post(
    guild_id: int,
    channel_id: int,
    question_id: int,
    message_id: int,
    posted_at: str,
    automatic: bool,
):

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        await db.execute(
            """
            INSERT INTO active_speed_questions (
                guild_id,
                channel_id,
                question_id,
                message_id,
                posted_at,
                answered_by,
                answered_at
            )

            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                NULL,
                NULL
            )

            ON CONFLICT (
                guild_id,
                channel_id
            )

            DO UPDATE SET
                question_id = excluded.question_id,
                message_id = excluded.message_id,
                posted_at = excluded.posted_at,
                answered_by = NULL,
                answered_at = NULL
            """,
            (
                guild_id,
                channel_id,
                question_id,
                message_id,
                posted_at,
            ),
        )

        await db.execute(
            """
            INSERT INTO rsq_post_history (
                guild_id,
                channel_id,
                question_id,
                message_id,
                automatic,
                posted_at
            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                channel_id,
                question_id,
                message_id,
                (
                    1
                    if automatic
                    else 0
                ),
                posted_at,
            ),
        )

        await db.commit()


# ==================================================
# MARK ANSWERED
# ==================================================


async def mark_speed_question_answered(
    guild_id: int,
    channel_id: int,
    question_id: int,
    user_id: int,
) -> bool:

    answered_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            UPDATE active_speed_questions

            SET
                answered_by = ?,
                answered_at = ?

            WHERE guild_id = ?
              AND channel_id = ?
              AND question_id = ?
              AND answered_by IS NULL
            """,
            (
                user_id,
                answered_at,
                guild_id,
                channel_id,
                question_id,
            ),
        )

        await db.commit()

        return (
            cursor.rowcount > 0
        )


# ==================================================
# RSQ EMBED
# ==================================================


def build_speed_question_embed(
    question_data: dict,
    active: bool = True,
) -> discord.Embed:

    question_id = (
        question_data["id"]
    )

    category_code = (
        question_data[
            "category"
        ]
    )

    category_name = (
        CATEGORY_NAMES.get(
            category_code,
            category_code,
        )
    )

    if active:

        title = (
            "⚡ Random Speed Question "
            f"#{question_id}"
        )

        footer_text = (
            "Send your answer in this channel. "
            "The first correct answer wins."
        )

        color = (
            discord.Color.blurple()
        )

    else:

        title = (
            "🔒 Random Speed Question "
            f"#{question_id} — Closed"
        )

        footer_text = (
            "This RSQ has been retired. "
            "A newer question is active."
        )

        color = (
            discord.Color.dark_grey()
        )

    embed = discord.Embed(
        title=title,
        description=(
            question_data[
                "question"
            ]
        ),
        color=color,
    )

    embed.add_field(
        name="Category",
        value=(
            category_name
        ),
        inline=False,
    )

    embed.set_footer(
        text=(
            footer_text
        )
    )

    return embed


# ==================================================
# RETIRE PREVIOUS MESSAGE
# ==================================================


async def _retire_previous_message(
    channel,
    guild_id: int,
    previous_question: dict | None,
):

    if previous_question is None:

        return

    message_id = (
        previous_question.get(
            "message_id"
        )
    )

    if message_id is None:

        return

    question_id = (
        previous_question[
            "question_id"
        ]
    )

    question_data = (
        get_question_by_id(
            question_id
        )
    )

    if question_data is None:

        return

    try:

        old_message = (
            await channel.fetch_message(
                message_id
            )
        )

    except (
        AttributeError,
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException,
    ):

        return

    context_key = (
        build_speed_question_context_key(
            guild_id=(
                guild_id
            ),
            channel_id=(
                channel.id
            ),
            question_id=(
                question_id
            ),
            posted_at=(
                previous_question[
                    "posted_at"
                ]
            ),
        )
    )

    try:

        await old_message.edit(
            content=None,
            embed=(
                build_speed_question_embed(
                    question_data=(
                        question_data
                    ),
                    active=False,
                )
            ),
            view=(
                QuestionFlagView(
                    question_bank_id=(
                        question_id
                    ),
                    context_key=(
                        context_key
                    ),
                )
            ),
        )

    except discord.HTTPException:

        pass


# ==================================================
# POST RSQ
# ==================================================


async def post_speed_question(
    channel,
    guild_id: int,
    question_data: dict,
    automatic: bool,
) -> dict:
    """
    Shared posting path for:

        automatic scheduled RSQs
        manual /question RSQs

    This function guarantees:
        minimum 15-minute separation
        one active question
        previous question retirement
        post history
        stable flag/attempt context key
    """

    channel_id = (
        channel.id
    )

    lock = (
        _get_posting_lock(
            guild_id=(
                guild_id
            ),
            channel_id=(
                channel_id
            ),
        )
    )

    async with lock:


        # ==================================================
        # HARD MINIMUM INTERVAL
        # ==================================================


        remaining_seconds = (
            await get_speed_question_cooldown_remaining(
                guild_id=(
                    guild_id
                ),
                channel_id=(
                    channel_id
                ),
            )
        )

        if remaining_seconds > 0:

            raise SpeedQuestionTooSoonError(
                remaining_seconds=(
                    remaining_seconds
                )
            )


        # ==================================================
        # PREVIOUS QUESTION
        # ==================================================


        previous_question = (
            await get_active_speed_question(
                guild_id=(
                    guild_id
                ),
                channel_id=(
                    channel_id
                ),
            )
        )


        # ==================================================
        # NEW CONTEXT
        # ==================================================


        posted_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        question_id = int(
            question_data[
                "id"
            ]
        )

        context_key = (
            build_speed_question_context_key(
                guild_id=(
                    guild_id
                ),
                channel_id=(
                    channel_id
                ),
                question_id=(
                    question_id
                ),
                posted_at=(
                    posted_at
                ),
            )
        )


        # ==================================================
        # SEND
        # ==================================================


        message = await channel.send(
            embed=(
                build_speed_question_embed(
                    question_data=(
                        question_data
                    ),
                    active=True,
                )
            ),
            view=(
                QuestionFlagView(
                    question_bank_id=(
                        question_id
                    ),
                    context_key=(
                        context_key
                    ),
                )
            ),
        )


        # ==================================================
        # DATABASE
        # ==================================================


        try:

            await _activate_and_record_post(
                guild_id=(
                    guild_id
                ),
                channel_id=(
                    channel_id
                ),
                question_id=(
                    question_id
                ),
                message_id=(
                    message.id
                ),
                posted_at=(
                    posted_at
                ),
                automatic=(
                    automatic
                ),
            )

        except Exception:

            try:

                await message.delete()

            except discord.HTTPException:

                pass

            raise


        # ==================================================
        # RETIRE PREVIOUS QUESTION
        # ==================================================


        await _retire_previous_message(
            channel=channel,
            guild_id=(
                guild_id
            ),
            previous_question=(
                previous_question
            ),
        )

        return {
            "question_id": (
                question_id
            ),
            "message_id": (
                message.id
            ),
            "posted_at": (
                posted_at
            ),
            "context_key": (
                context_key
            ),
        }


# ==================================================
# ANSWER KEY
# ==================================================


def _build_answer_key(
    accepted_answers: list[str],
) -> str:

    if len(
        accepted_answers
    ) == 1:

        return (
            accepted_answers[0]
        )

    answers = "\n".join(
        f"- {answer}"
        for answer
        in accepted_answers
    )

    return (
        "Any ONE of the following answers "
        "should be considered acceptable:\n"
        f"{answers}"
    )


def _build_answer_display(
    accepted_answers: list[str],
) -> str:

    if len(
        accepted_answers
    ) == 1:

        return (
            accepted_answers[0]
        )

    return "\n".join(
        f"- {answer}"
        for answer
        in accepted_answers
    )


# ==================================================
# RESPONSE TIME
# ==================================================


def _get_response_seconds(
    posted_at: str,
    message_created_at: datetime,
) -> float:

    posted_datetime = (
        _parse_datetime(
            posted_at
        )
    )

    response_seconds = (
        message_created_at
        - posted_datetime
    ).total_seconds()

    return max(
        0.0,
        response_seconds,
    )


# ==================================================
# SPEED BONUS
# ==================================================


def get_speed_question_bonus(
    response_seconds: float,
) -> int:

    if response_seconds <= 30:

        return (
            SPEED_QUESTION_30_SECOND_BONUS
        )

    if response_seconds <= 60:

        return (
            SPEED_QUESTION_1_MINUTE_BONUS
        )

    if response_seconds <= 180:

        return (
            SPEED_QUESTION_3_MINUTE_BONUS
        )

    return 0


# ==================================================
# REMOVE REACTION
# ==================================================


async def _remove_reaction(
    message: discord.Message,
    emoji: str,
    bot_user,
):

    if bot_user is None:

        return

    try:

        await message.remove_reaction(
            emoji,
            bot_user,
        )

    except discord.HTTPException:

        pass


# ==================================================
# PROCESS ANSWER MESSAGE
# ==================================================


async def process_speed_question_message(
    message: discord.Message,
    bot_user,
):


    # ==================================================
    # BASIC CHECKS
    # ==================================================


    if message.author.bot:

        return

    if message.guild is None:

        return

    if (
        message.channel.id
        != RANDOM_QUESTION_CHANNEL_ID
    ):

        return

    content = (
        message.content.strip()
    )

    if not content:

        return

    if not any(
        character.isalnum()
        for character in content
    ):

        return


    # ==================================================
    # ACTIVE QUESTION
    # ==================================================


    active_question = (
        await get_active_speed_question(
            guild_id=(
                message.guild.id
            ),
            channel_id=(
                message.channel.id
            ),
        )
    )

    if active_question is None:

        return

    if (
        active_question[
            "answered_by"
        ]
        is not None
    ):

        return


    # ==================================================
    # GRADING LOCK
    # ==================================================


    lock = (
        _get_grading_lock(
            guild_id=(
                message.guild.id
            ),
            channel_id=(
                message.channel.id
            ),
        )
    )

    async with lock:


        # ==================================================
        # RECHECK
        # ==================================================


        active_question = (
            await get_active_speed_question(
                guild_id=(
                    message.guild.id
                ),
                channel_id=(
                    message.channel.id
                ),
            )
        )

        if active_question is None:

            return

        if (
            active_question[
                "answered_by"
            ]
            is not None
        ):

            return


        # ==================================================
        # QUESTION
        # ==================================================


        question_id = (
            active_question[
                "question_id"
            ]
        )

        question_data = (
            get_question_by_id(
                question_id
            )
        )

        if question_data is None:

            return

        question_text = (
            question_data[
                "question"
            ]
        )

        accepted_answers = (
            question_data[
                "accepted_answers"
            ]
        )

        explanation = (
            question_data.get(
                "explanation",
                "",
            )
        )

        correct_answer = (
            _build_answer_key(
                accepted_answers
            )
        )

        response_seconds = (
            _get_response_seconds(
                posted_at=(
                    active_question[
                        "posted_at"
                    ]
                ),
                message_created_at=(
                    message.created_at
                ),
            )
        )

        context_key = (
            build_speed_question_context_key(
                guild_id=(
                    message.guild.id
                ),
                channel_id=(
                    message.channel.id
                ),
                question_id=(
                    question_id
                ),
                posted_at=(
                    active_question[
                        "posted_at"
                    ]
                ),
            )
        )


        # ==================================================
        # GRADING INDICATOR
        # ==================================================


        try:

            await message.add_reaction(
                "⏳"
            )

        except discord.HTTPException:

            pass


        # ==================================================
        # LLM GRADING
        # ==================================================


        try:

            grade = (
                await grade_answer_with_llm(
                    question=(
                        question_text
                    ),
                    correct_answer=(
                        correct_answer
                    ),
                    student_answer=(
                        content
                    ),
                )
            )

        except Exception as error:

            print(
                "RSQ grading error: "
                f"{error!r}"
            )

            try:

                await message.add_reaction(
                    "⚠️"
                )

            except discord.HTTPException:

                pass

            await _remove_reaction(
                message=message,
                emoji="⏳",
                bot_user=bot_user,
            )

            return


        # ==================================================
        # RECORD ATTEMPT
        # ==================================================


        attempt_result = (
            "correct"
            if grade.correct
            else "incorrect"
        )

        try:

            await record_question_attempt(
                guild_id=(
                    message.guild.id
                ),
                user_id=(
                    message.author.id
                ),
                question_bank_id=(
                    question_id
                ),
                context_key=(
                    context_key
                ),
                answer_text=(
                    content
                ),
                result=(
                    attempt_result
                ),
            )

        except Exception as error:

            print(
                "RSQ attempt recording error: "
                f"{error!r}"
            )


        # ==================================================
        # LOG
        # ==================================================


        print(
            "\n"
            "Random Speed Question Answer\n"
            f"Question #{question_id}\n"
            f"Student: "
            f"{message.author.display_name}\n"
            f"Answer: {content}\n"
            f"Response Time: "
            f"{response_seconds:.2f} seconds\n"
            f"Correct: {grade.correct}\n"
            f"Confidence: {grade.confidence}\n"
            f"Reason: {grade.reason}\n"
        )


        # ==================================================
        # INCORRECT
        # ==================================================


        if not grade.correct:

            try:

                await message.add_reaction(
                    "❌"
                )

            except discord.HTTPException:

                pass

            await _remove_reaction(
                message=message,
                emoji="⏳",
                bot_user=bot_user,
            )

            return


        # ==================================================
        # FIRST CORRECT ANSWER WINS
        # ==================================================


        won = (
            await mark_speed_question_answered(
                guild_id=(
                    message.guild.id
                ),
                channel_id=(
                    message.channel.id
                ),
                question_id=(
                    question_id
                ),
                user_id=(
                    message.author.id
                ),
            )
        )

        if not won:

            await _remove_reaction(
                message=message,
                emoji="⏳",
                bot_user=bot_user,
            )

            return


        # ==================================================
        # POINTS
        # ==================================================


        speed_bonus = (
            get_speed_question_bonus(
                response_seconds
            )
        )

        total_points = (
            SPEED_QUESTION_BASE_POINTS
            + speed_bonus
        )

        progression = None

        try:

            progression = (
                await add_points(
                    guild_id=(
                        message.guild.id
                    ),
                    user_id=(
                        message.author.id
                    ),
                    amount=(
                        total_points
                    ),
                    reason=(
                        "Random speed question"
                    ),
                    username=(
                        message.author.display_name
                    ),
                    source_key=(
                        context_key
                    ),
                )
            )

        except Exception as error:

            print(
                "RSQ point award error: "
                f"{error!r}"
            )


        # ==================================================
        # REACTION
        # ==================================================


        try:

            await message.add_reaction(
                "✅"
            )

        except discord.HTTPException:

            pass

        await _remove_reaction(
            message=message,
            emoji="⏳",
            bot_user=bot_user,
        )


        # ==================================================
        # WINNER EMBED
        # ==================================================


        answer_display = (
            _build_answer_display(
                accepted_answers
            )
        )

        winner_embed = discord.Embed(
            title=(
                "✅ Correct!  "
                f"+{total_points} Points"
            ),
            description=(
                f"{message.author.mention} "
                "answered in "
                f"**{response_seconds:.1f} seconds**."
            ),
            color=(
                discord.Color.green()
            ),
        )

        winner_embed.add_field(
            name="💡 Answer",
            value=(
                answer_display
            ),
            inline=False,
        )

        winner_embed.add_field(
            name="🏆 Base",
            value=(
                f"**+"
                f"{SPEED_QUESTION_BASE_POINTS}**"
            ),
            inline=True,
        )

        winner_embed.add_field(
            name="⚡ Speed Bonus",
            value=(
                f"**+{speed_bonus}**"
            ),
            inline=True,
        )

        winner_embed.add_field(
            name="🎯 Total",
            value=(
                f"**+{total_points} pts**"
            ),
            inline=True,
        )

        if explanation:

            winner_embed.add_field(
                name="📚 Explanation",
                value=(
                    explanation
                ),
                inline=False,
            )

        await message.reply(
            embed=(
                winner_embed
            )
        )


        # ==================================================
        # PUBLIC RANK UP
        # ==================================================
        #
        # RSQ level-ups remain silent.
        #
        # Rank-ups are public.
        #
        # ==================================================


        if (
            progression is not None
            and progression.get(
                "awarded",
                False,
            )
            and progression.get(
                "ranked_up",
                False,
            )
        ):

            rank_embed = (
                build_rank_up_embed(
                    username=(
                        message.author.display_name
                    ),
                    new_rank=(
                        progression[
                            "new_rank"
                        ]
                    ),
                    new_level=(
                        progression[
                            "new_level"
                        ]
                    ),
                )
            )

            await message.channel.send(
                embed=(
                    rank_embed
                )
            )