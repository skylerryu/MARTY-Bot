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
    """
    Convert a database row into the QoTD
    dictionary used by the rest of M.A.R.T.Y.
    """

    return {
        "id": row["id"],
        "guild_id": row["guild_id"],
        "channel_id": row["channel_id"],
        "message_id": row["message_id"],
        "question_date": row["question_date"],
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
) -> dict:
    """
    Store a new Question of the Day.

    Only one QoTD may exist for a guild
    on a particular calendar date.
    """

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
                    question_text,
                    accepted_answers,
                    explanation
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    channel_id,
                    question_date.isoformat(),
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
    """
    Retrieve a Question of the Day by ID.
    """

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
    """
    Retrieve the Question of the Day for
    a guild on a particular date.
    """

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
# SET MESSAGE ID
# ==================================================


async def set_qotd_message_id(
    qotd_id: int,
    message_id: int,
):
    """
    Store the Discord message ID for a QoTD.

    This is used to restore the Answer Question
    button after M.A.R.T.Y. restarts.
    """

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
    """
    Delete a QoTD.

    This is mainly used if the database record
    is created but the Discord message fails
    to post.
    """

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
    """
    Return recently posted QoTD messages so
    their persistent Discord buttons can be
    restored after a bot restart.
    """

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