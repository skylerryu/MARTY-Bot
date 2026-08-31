import asyncio

from datetime import (
    date,
    datetime,
    timezone,
)

from points.mechanics.question_of_the_day.qotd_questions import (
    get_qotd,
)

from points.mechanics.question_of_the_day.qotd_completions import (
    has_completed_qotd,
    record_qotd_completion,
)

from points.mechanics.question_of_the_day.qotd_grading import (
    grade_qotd_answer,
)

from points.mechanics.question_of_the_day.qotd_streaks import (
    get_qotd_streak,
    calculate_next_qotd_streak,
    get_qotd_streak_bonus,
    update_qotd_streak,
)

from points.mechanics.question_of_the_day.qotd_points import (
    award_qotd_points,
)


# ==================================================
# SUBMISSION LOCKS
# ==================================================


_submission_locks = {}


def _get_submission_lock(
    qotd_id: int,
    user_id: int,
) -> asyncio.Lock:

    key = (
        qotd_id,
        user_id,
    )

    if key not in _submission_locks:

        _submission_locks[
            key
        ] = asyncio.Lock()

    return _submission_locks[
        key
    ]


# ==================================================
# QOTD DATE
# ==================================================


def _get_qotd_date(
    question_date: str,
) -> date:

    return date.fromisoformat(
        question_date
    )


# ==================================================
# QOTD OPEN / CLOSED
# ==================================================


def _qotd_is_open(
    expires_at: str,
) -> bool:

    expiration = (
        datetime.fromisoformat(
            expires_at
        )
    )

    if expiration.tzinfo is None:

        expiration = (
            expiration.replace(
                tzinfo=timezone.utc
            )
        )

    return (
        datetime.now(
            timezone.utc
        )
        < expiration
    )


# ==================================================
# SUBMIT QOTD ANSWER
# ==================================================


async def submit_qotd_answer(
    qotd_id: int,
    guild_id: int,
    user_id: int,
    username: str,
    submitted_answer: str,
) -> dict:

    submitted_answer = (
        submitted_answer.strip()
    )

    if not submitted_answer:

        return {
            "status": "incorrect",
        }


    # ==================================================
    # LOCK
    # ==================================================


    lock = _get_submission_lock(
        qotd_id=qotd_id,
        user_id=user_id,
    )

    async with lock:


        # ==================================================
        # QUESTION
        # ==================================================


        qotd = await get_qotd(
            qotd_id
        )

        if qotd is None:

            return {
                "status": "not_found",
            }


        # ==================================================
        # SERVER
        # ==================================================


        if (
            qotd["guild_id"]
            != guild_id
        ):

            return {
                "status": "not_found",
            }


        # ==================================================
        # EXPIRATION
        # ==================================================


        if not _qotd_is_open(
            qotd["expires_at"]
        ):

            return {
                "status": "expired",
            }


        # ==================================================
        # COMPLETION
        # ==================================================


        if await has_completed_qotd(
            qotd_id=qotd_id,
            user_id=user_id,
        ):

            return {
                "status": "already_completed",
            }


        # ==================================================
        # GRADING
        # ==================================================


        grade = await grade_qotd_answer(
            question=(
                qotd["question_text"]
            ),
            accepted_answers=(
                qotd["accepted_answers"]
            ),
            student_answer=(
                submitted_answer
            ),
        )

        if grade["status"] == "uncertain":

            return {
                "status": "uncertain",
            }

        if grade["status"] == "incorrect":

            return {
                "status": "incorrect",
            }

        if grade["status"] != "correct":

            raise RuntimeError(
                "Unknown QoTD grading status: "
                f"{grade['status']}"
            )


        # ==================================================
        # LOGICAL COMPLETION DATE
        # ==================================================


        completion_date = (
            _get_qotd_date(
                qotd["question_date"]
            )
        )


        # ==================================================
        # STREAK
        # ==================================================


        (
            current_streak,
            last_completion_date,
        ) = await get_qotd_streak(
            guild_id=guild_id,
            user_id=user_id,
        )

        new_streak = (
            calculate_next_qotd_streak(
                current_streak=current_streak,
                last_completion_date=(
                    last_completion_date
                ),
                completion_date=(
                    completion_date
                ),
            )
        )

        streak_bonus = (
            get_qotd_streak_bonus(
                new_streak
            )
        )


        # ==================================================
        # POINTS
        # ==================================================


        point_result = (
            await award_qotd_points(
                qotd_id=qotd_id,
                guild_id=guild_id,
                user_id=user_id,
                username=username,
                streak_bonus=(
                    streak_bonus
                ),
            )
        )


        # ==================================================
        # STREAK UPDATE
        # ==================================================


        await update_qotd_streak(
            guild_id=guild_id,
            user_id=user_id,
            streak_days=new_streak,
            completion_date=(
                completion_date
            ),
        )


        # ==================================================
        # RECORD COMPLETION
        # ==================================================


        completion_recorded = (
            await record_qotd_completion(
                qotd_id=qotd_id,
                guild_id=guild_id,
                user_id=user_id,
            )
        )

        if not completion_recorded:

            return {
                "status": "already_completed",
            }


        # ==================================================
        # SUCCESS
        # ==================================================


        return {
            "status": "correct",

            "accepted_answers": (
                qotd["accepted_answers"]
            ),

            "submitted_answer": (
                submitted_answer
            ),

            "explanation": (
                qotd["explanation"]
            ),

            "base_points": (
                point_result[
                    "base_points"
                ]
            ),

            "streak_bonus": (
                point_result[
                    "streak_bonus"
                ]
            ),

            "total_points_awarded": (
                point_result[
                    "total_points"
                ]
            ),

            "streak_days": (
                new_streak
            ),

            "channel_id": (
                qotd["channel_id"]
            ),

            "progression": (
                point_result[
                    "progression"
                ]
            ),
        }