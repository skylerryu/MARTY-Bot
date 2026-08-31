import aiosqlite

from data.user_db import (
    USER_DB_PATH,
)


# ==================================================
# RECORD QUESTION ATTEMPT
# ==================================================


async def record_question_attempt(
    guild_id: int,
    user_id: int,
    question_bank_id: int,
    context_key: str,
    answer_text: str,
    result: str,
):
    """
    Record one answer attempt.

    context_key identifies the particular
    occurrence of the question.

    The attempt system does not care which
    question mechanic produced the attempt.
    """

    context_key = context_key.strip()
    answer_text = answer_text.strip()
    result = result.strip().lower()

    if not context_key:
        raise ValueError(
            "Question context key cannot be empty."
        )

    if not answer_text:
        return

    async with aiosqlite.connect(
        USER_DB_PATH
    ) as db:

        await db.execute(
            """
            INSERT INTO question_attempts (
                guild_id,
                user_id,
                question_bank_id,
                context_key,
                answer_text,
                result
            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                question_bank_id,
                context_key,
                answer_text,
                result,
            ),
        )

        await db.commit()


# ==================================================
# RECENT QUESTION ATTEMPTS
# ==================================================


async def get_recent_question_attempts(
    guild_id: int,
    user_id: int,
    question_bank_id: int,
    context_key: str,
    limit: int = 3,
) -> list[dict]:
    """
    Return the user's most recent attempts for
    one particular occurrence of a question.

    Most recent attempt is returned first.
    """

    if limit <= 0:
        return []

    async with aiosqlite.connect(
        USER_DB_PATH
    ) as db:

        db.row_factory = (
            aiosqlite.Row
        )

        cursor = await db.execute(
            """
            SELECT
                id,
                answer_text,
                result,
                created_at

            FROM question_attempts

            WHERE guild_id = ?
              AND user_id = ?
              AND question_bank_id = ?
              AND context_key = ?

            ORDER BY id DESC

            LIMIT ?
            """,
            (
                guild_id,
                user_id,
                question_bank_id,
                context_key,
                limit,
            ),
        )

        rows = await cursor.fetchall()

    return [
        dict(row)
        for row in rows
    ]