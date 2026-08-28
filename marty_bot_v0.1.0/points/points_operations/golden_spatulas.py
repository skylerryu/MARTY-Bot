import aiosqlite

from data.database import (
    DB_PATH,
)

from points.points_operations.operations_helpers import (
    ensure_user_in_db,
)


# ==================================================
# AWARD GOLDEN SPATULA
# ==================================================


async def award_golden_spatula(
    guild_id: int,
    user_id: int,
    username: str | None = None,
):
    """
    Record a Golden Spatula award for a user.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        if username is not None:

            await ensure_user_in_db(
                db=db,
                guild_id=guild_id,
                user_id=user_id,
                username=username,
            )

        await db.execute(
            """
            INSERT INTO golden_spatulas (
                guild_id,
                user_id
            )
            VALUES (?, ?)
            """,
            (
                guild_id,
                user_id,
            ),
        )

        await db.commit()


# ==================================================
# GET GOLDEN SPATULAS
# ==================================================


async def get_golden_spatulas(
    guild_id: int,
    user_id: int,
) -> int:
    """
    Return the number of Golden Spatulas
    awarded to a user.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM golden_spatulas
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