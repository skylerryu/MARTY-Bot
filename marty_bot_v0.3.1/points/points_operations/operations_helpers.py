import aiosqlite


# ==================================================
# GET POINT TOTAL
# ==================================================


async def get_point_total_from_db(
    db: aiosqlite.Connection,
    guild_id: int,
    user_id: int,
) -> int:
    """
    Return a user's total points using an
    existing database connection.
    """

    cursor = await db.execute(
        """
        SELECT COALESCE(
            SUM(amount),
            0
        )
        FROM point_transactions
        WHERE guild_id = ?
          AND user_id = ?
        """,
        (
            guild_id,
            user_id,
        ),
    )

    row = await cursor.fetchone()

    return int(row[0])


# ==================================================
# ENSURE USER
# ==================================================


async def ensure_user_in_db(
    db: aiosqlite.Connection,
    guild_id: int,
    user_id: int,
    username: str,
):
    """
    Create a user if they do not exist.

    If they already exist, update their
    stored username.
    """

    await db.execute(
        """
        INSERT INTO users (
            guild_id,
            user_id,
            username
        )
        VALUES (?, ?, ?)

        ON CONFLICT(guild_id, user_id)
        DO UPDATE SET
            username = excluded.username
        """,
        (
            guild_id,
            user_id,
            username,
        ),
    )