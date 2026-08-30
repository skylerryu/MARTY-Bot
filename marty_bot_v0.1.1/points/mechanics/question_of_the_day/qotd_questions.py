import json
import sqlite3
from datetime import date

import aiosqlite

from data.database import DB_PATH


# ==================================================
# EXCEPTIONS
# ==================================================


class QotdAlreadyExistsError(Exception):
    """
    Raised when a QoTD already exists for
    the requested guild and date.
    """


# ==================================================
# ROW CONVERSION
# ==================================================


def _row_to_qotd(
    row: aiosqlite.Row,
) -> dict:

    return {
        "id": row["id"],
        "guild_id": row["guild_id"],
        "channel_id": row["channel_id"],
        "message_id": row["message_id"],
        "question_date": row["question_date"],
        "question_bank_id": (
            row["question_bank_id"]
        ),
        "question_text": row["question_text"],
        "accepted_answers": json.loads(
            row["accepted_answers"]
        ),
        "explanation": row["explanation"],
    }


# ==================================================
# CREATE QUESTION
# ==================================================


async def create_qotd(
    guild_id: int,
    channel_id: int,
    question_date: date,
    question_text: str,
    accepted_answers: list[str],
    explanation: str | None = None,
    question_bank_id: int | None = None,
) -> dict:

    question_text = question_text.strip()

    if not question_text:

        raise ValueError(
            "Question text cannot be empty."
        )

    cleaned_answers = [
        answer.strip()
        for answer in accepted_answers
        if answer.strip()
    ]

    if not cleaned_answers:

        raise ValueError(
            "At least one accepted answer "
            "must be provided."
        )

    accepted_answers_json = json.dumps(
        cleaned_answers
    )

    try:

        async with aiosqlite.connect(
            DB_PATH
        ) as db:

            cursor = await db.execute(
                """
                INSERT INTO qotd_questions (
                    guild_id,
                    channel_id,
                    question_date,
                    question_bank_id,
                    question_text,
                    accepted_answers,
                    explanation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    channel_id,
                    question_date.isoformat(),
                    question_bank_id,
                    question_text,
                    accepted_answers_json,
                    explanation,
                ),
            )

            await db.commit()

            qotd_id = cursor.lastrowid

    except sqlite3.IntegrityError as error:

        raise QotdAlreadyExistsError(
            "A Question of the Day already "
            "exists for this server on this date."
        ) from error

    if qotd_id is None:

        raise RuntimeError(
            "QoTD was created but no database "
            "ID was returned."
        )

    return {
        "id": qotd_id,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "message_id": None,
        "question_date": question_date.isoformat(),
        "question_bank_id": question_bank_id,
        "question_text": question_text,
        "accepted_answers": cleaned_answers,
        "explanation": explanation,
    }


# ==================================================
# GET QUESTION
# ==================================================


async def get_qotd(
    qotd_id: int,
) -> dict | None:

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                id,
                guild_id,
                channel_id,
                message_id,
                question_date,
                question_bank_id,
                question_text,
                accepted_answers,
                explanation
            FROM qotd_questions
            WHERE id = ?
            """,
            (
                qotd_id,
            ),
        )

        row = await cursor.fetchone()

    if row is None:
        return None

    return _row_to_qotd(
        row
    )


# ==================================================
# GET QUESTION FOR DATE
# ==================================================


async def get_qotd_for_date(
    guild_id: int,
    question_date: date,
) -> dict | None:

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                id,
                guild_id,
                channel_id,
                message_id,
                question_date,
                question_bank_id,
                question_text,
                accepted_answers,
                explanation
            FROM qotd_questions
            WHERE guild_id = ?
              AND question_date = ?
            """,
            (
                guild_id,
                question_date.isoformat(),
            ),
        )

        row = await cursor.fetchone()

    if row is None:
        return None

    return _row_to_qotd(
        row
    )


# ==================================================
# USED QUESTION BANK IDS
# ==================================================


async def get_used_qotd_question_bank_ids(
    guild_id: int,
) -> set[int]:

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            SELECT DISTINCT
                question_bank_id

            FROM qotd_questions

            WHERE guild_id = ?
              AND question_bank_id IS NOT NULL
            """,
            (
                guild_id,
            ),
        )

        rows = await cursor.fetchall()

    return {
        int(row[0])
        for row in rows
    }


# ==================================================
# OLDER POSTED QOTDS
# ==================================================


async def get_older_posted_qotds(
    guild_id: int,
    before_date: date,
) -> list[dict]:
    """
    Get old QoTD messages so their buttons
    can be removed when the next QoTD posts.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                id,
                channel_id,
                message_id,
                question_date

            FROM qotd_questions

            WHERE guild_id = ?
              AND question_date < ?
              AND message_id IS NOT NULL

            ORDER BY question_date DESC
            """,
            (
                guild_id,
                before_date.isoformat(),
            ),
        )

        rows = await cursor.fetchall()

    return [
        {
            "id": row["id"],
            "channel_id": row["channel_id"],
            "message_id": row["message_id"],
            "question_date": row["question_date"],
        }
        for row in rows
    ]


# ==================================================
# SET MESSAGE ID
# ==================================================


async def set_qotd_message_id(
    qotd_id: int,
    message_id: int,
):

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await db.execute(
            """
            UPDATE qotd_questions

            SET message_id = ?

            WHERE id = ?
            """,
            (
                message_id,
                qotd_id,
            ),
        )

        await db.commit()


# ==================================================
# DELETE QUESTION
# ==================================================


async def delete_qotd(
    qotd_id: int,
):

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await db.execute(
            """
            DELETE FROM qotd_questions
            WHERE id = ?
            """,
            (
                qotd_id,
            ),
        )

        await db.commit()


# ==================================================
# RECENT QUESTIONS
# ==================================================


async def get_recent_qotds_for_views(
    limit: int,
) -> list[dict]:

    if limit <= 0:
        return []

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                id,
                message_id

            FROM qotd_questions

            WHERE message_id IS NOT NULL

            ORDER BY id DESC

            LIMIT ?
            """,
            (
                limit,
            ),
        )

        rows = await cursor.fetchall()

    return [
        {
            "id": row["id"],
            "message_id": row["message_id"],
        }
        for row in rows
    ]