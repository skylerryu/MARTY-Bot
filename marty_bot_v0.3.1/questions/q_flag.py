import json
import sqlite3

from datetime import (
    datetime,
    timezone,
)

import aiosqlite

from data.system_db import (
    SYSTEM_DB_PATH,
)


FLAG_STATUS_OPEN = "open"
FLAG_STATUS_DISMISSED = "dismissed"
FLAG_STATUS_MARKED_FOR_EDIT = "marked_for_edit"


class QuestionAlreadyFlaggedError(
    Exception
):
    pass


class QuestionFlagNotFoundError(
    Exception
):
    pass


# ==================================================
# ROW CONVERSION
# ==================================================


def _row_to_flag(
    row: aiosqlite.Row,
) -> dict:

    raw_answers = (
        row["attempted_answers"]
        or "[]"
    )

    try:

        attempted_answers = (
            json.loads(
                raw_answers
            )
        )

    except (
        json.JSONDecodeError,
        TypeError,
    ):

        attempted_answers = []

    return {
        "id": row["id"],
        "guild_id": row["guild_id"],
        "question_bank_id": (
            row["question_bank_id"]
        ),
        "user_id": row["user_id"],
        "context_key": (
            row["context_key"]
        ),
        "reason": row["reason"],
        "attempted_answers": (
            attempted_answers
        ),
        "status": row["status"],
        "created_at": (
            row["created_at"]
        ),
        "reviewed_by": (
            row["reviewed_by"]
        ),
        "reviewed_at": (
            row["reviewed_at"]
        ),
        "resolution_note": (
            row["resolution_note"]
        ),
    }


# ==================================================
# USER HAS OPEN FLAG
# ==================================================


async def user_has_open_question_flag(
    guild_id: int,
    user_id: int,
    question_bank_id: int,
) -> bool:

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            SELECT 1

            FROM question_flags

            WHERE guild_id = ?
              AND user_id = ?
              AND question_bank_id = ?
              AND status = 'open'

            LIMIT 1
            """,
            (
                guild_id,
                user_id,
                question_bank_id,
            ),
        )

        row = await cursor.fetchone()

    return (
        row is not None
    )


# ==================================================
# CREATE FLAG
# ==================================================


async def create_question_flag(
    guild_id: int,
    question_bank_id: int,
    user_id: int,
    context_key: str,
    reason: str,
    attempted_answers: list[str],
) -> dict:

    context_key = (
        context_key.strip()
    )

    reason = (
        reason.strip()
    )

    cleaned_answers = [
        str(answer).strip()
        for answer
        in attempted_answers[:3]
        if str(answer).strip()
    ]

    if not context_key:

        raise ValueError(
            "Question context key cannot be empty."
        )

    if not reason:

        raise ValueError(
            "Flag reason cannot be empty."
        )

    answers_json = (
        json.dumps(
            cleaned_answers
        )
    )

    try:

        async with aiosqlite.connect(
            SYSTEM_DB_PATH
        ) as db:

            cursor = await db.execute(
                """
                INSERT INTO question_flags (
                    guild_id,
                    question_bank_id,
                    user_id,
                    source,
                    context_key,
                    reason,
                    attempted_answers,
                    status
                )

                VALUES (
                    ?,
                    ?,
                    ?,
                    'question',
                    ?,
                    ?,
                    ?,
                    'open'
                )
                """,
                (
                    guild_id,
                    question_bank_id,
                    user_id,
                    context_key,
                    reason,
                    answers_json,
                ),
            )

            await db.commit()

            flag_id = (
                cursor.lastrowid
            )

    except sqlite3.IntegrityError as error:

        raise QuestionAlreadyFlaggedError(
            "You already have an open flag "
            "for this question."
        ) from error

    if flag_id is None:

        raise RuntimeError(
            "No flag ID was returned."
        )

    flag = await get_question_flag(
        flag_id=flag_id,
        guild_id=guild_id,
    )

    if flag is None:

        raise RuntimeError(
            "Created flag could not be retrieved."
        )

    return flag


# ==================================================
# GET FLAG
# ==================================================


async def get_question_flag(
    flag_id: int,
    guild_id: int,
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
                guild_id,
                question_bank_id,
                user_id,
                context_key,
                reason,
                attempted_answers,
                status,
                created_at,
                reviewed_by,
                reviewed_at,
                resolution_note

            FROM question_flags

            WHERE id = ?
              AND guild_id = ?
            """,
            (
                flag_id,
                guild_id,
            ),
        )

        row = await cursor.fetchone()

    if row is None:
        return None

    return _row_to_flag(
        row
    )


# ==================================================
# OPEN FLAGGED QUESTION IDS
# ==================================================


async def get_open_flagged_question_ids(
    guild_id: int,
) -> list[int]:

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            SELECT question_bank_id

            FROM question_flags

            WHERE guild_id = ?
              AND status = 'open'

            GROUP BY question_bank_id

            ORDER BY MAX(id) DESC
            """,
            (
                guild_id,
            ),
        )

        rows = await cursor.fetchall()

    return [
        int(row[0])
        for row in rows
    ]


# ==================================================
# QUESTION SUMMARY
# ==================================================


async def get_open_question_flag_summary(
    guild_id: int,
    question_bank_id: int,
) -> dict | None:

    flags = await get_open_flags_for_question(
        guild_id=guild_id,
        question_bank_id=question_bank_id,
    )

    if not flags:
        return None

    return {
        "question_bank_id": (
            question_bank_id
        ),
        "num_flags": len(flags),
        "latest_flag": flags[0],
    }


# ==================================================
# OPEN FLAGS FOR QUESTION
# ==================================================


async def get_open_flags_for_question(
    guild_id: int,
    question_bank_id: int,
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
                guild_id,
                question_bank_id,
                user_id,
                context_key,
                reason,
                attempted_answers,
                status,
                created_at,
                reviewed_by,
                reviewed_at,
                resolution_note

            FROM question_flags

            WHERE guild_id = ?
              AND question_bank_id = ?
              AND status = 'open'

            ORDER BY id DESC
            """,
            (
                guild_id,
                question_bank_id,
            ),
        )

        rows = await cursor.fetchall()

    return [
        _row_to_flag(
            row
        )
        for row in rows
    ]


# ==================================================
# DISMISS ONE FLAG
# ==================================================


async def dismiss_question_flag(
    flag_id: int,
    guild_id: int,
    reviewed_by: int,
) -> dict:

    now = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            UPDATE question_flags

            SET
                status = 'dismissed',
                reviewed_by = ?,
                reviewed_at = ?,
                resolution_note = ?

            WHERE id = ?
              AND guild_id = ?
              AND status = 'open'
            """,
            (
                reviewed_by,
                now,
                (
                    "Flag dismissed through "
                    "/flaggedreview."
                ),
                flag_id,
                guild_id,
            ),
        )

        await db.commit()

        if cursor.rowcount != 1:

            raise QuestionFlagNotFoundError(
                f"Open flag #{flag_id} "
                "could not be found."
            )

    flag = await get_question_flag(
        flag_id=flag_id,
        guild_id=guild_id,
    )

    if flag is None:

        raise QuestionFlagNotFoundError(
            f"Flag #{flag_id} "
            "could not be retrieved."
        )

    return flag