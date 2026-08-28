import aiosqlite

from data.database import DB_PATH


# ==================================================
# CHECK COMPLETION
# ==================================================


async def has_completed_qotd(
    qotd_id: int,
    user_id: int,
) -> bool:
    """
    Return True if the user has already
    completed this Question of the Day.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            SELECT 1
            FROM qotd_completions
            WHERE qotd_id = ?
              AND user_id = ?
            LIMIT 1
            """,
            (
                qotd_id,
                user_id,
            ),
        )

        row = await cursor.fetchone()

    return row is not None


# ==================================================
# RECORD COMPLETION
# ==================================================


async def record_qotd_completion(
    qotd_id: int,
    guild_id: int,
    user_id: int,
) -> bool:
    """
    Record that a user completed a QoTD.

    Returns True if this is a new completion.

    Returns False if the user had already
    completed the question.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO qotd_completions (
                qotd_id,
                guild_id,
                user_id
            )
            VALUES (?, ?, ?)
            """,
            (
                qotd_id,
                guild_id,
                user_id,
            ),
        )

        await db.commit()

        return cursor.rowcount > 0