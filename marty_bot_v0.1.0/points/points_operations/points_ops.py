import aiosqlite

from data.database import (
    DB_PATH,
)

from points.progressions.progressions import (
    get_progression_change,
)


# ==================================================
# ENSURE USER
# ==================================================


async def ensure_user(
    guild_id: int,
    user_id: int,
    username: str,
):
    """
    Make sure a user exists in the users table.

    If the user already exists, update their
    stored username.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await _ensure_user(
            db=db,
            guild_id=guild_id,
            user_id=user_id,
            username=username,
        )

        await db.commit()


# ==================================================
# GET POINTS
# ==================================================


async def get_points(
    guild_id: int,
    user_id: int,
) -> int:
    """
    Return a user's total points.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        return await _get_point_total(
            db=db,
            guild_id=guild_id,
            user_id=user_id,
        )


# ==================================================
# ADD POINTS
# ==================================================


async def add_points(
    guild_id: int,
    user_id: int,
    amount: int,
    reason: str,
    username: str | None = None,
    source_key: str | None = None,
) -> dict:
    """
    Add points to a user.

    source_key may be supplied when an award
    must only happen once.

    For example:

        qotd:15:correct

    prevents the same QoTD completion reward
    from being awarded twice.
    """

    if amount <= 0:

        raise ValueError(
            "add_points() requires an amount "
            "greater than 0."
        )


    async with aiosqlite.connect(
        DB_PATH
    ) as db:


        # ==================================================
        # USER
        # ==================================================


        if username is not None:

            await _ensure_user(
                db=db,
                guild_id=guild_id,
                user_id=user_id,
                username=username,
            )


        # ==================================================
        # OLD POINT TOTAL
        # ==================================================


        old_points = await _get_point_total(
            db=db,
            guild_id=guild_id,
            user_id=user_id,
        )


        # ==================================================
        # POINT TRANSACTION
        # ==================================================


        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO point_transactions (
                guild_id,
                user_id,
                amount,
                reason,
                source_key
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                amount,
                reason,
                source_key,
            ),
        )

        awarded = (
            cursor.rowcount > 0
        )

        await db.commit()


    # ==================================================
    # NEW POINT TOTAL
    # ==================================================


    if awarded:

        new_points = (
            old_points
            + amount
        )

    else:

        new_points = old_points


    # ==================================================
    # PROGRESSION
    # ==================================================


    progression = get_progression_change(
        old_points=old_points,
        new_points=new_points,
    )

    progression["awarded"] = (
        awarded
    )

    progression["points_awarded"] = (
        amount
        if awarded
        else 0
    )

    return progression


# ==================================================
# REMOVE POINTS
# ==================================================


async def remove_points(
    guild_id: int,
    user_id: int,
    amount: int,
    reason: str,
    username: str | None = None,
) -> dict:
    """
    Remove points from a user.

    The database records the removal as a
    negative point transaction.
    """

    if amount <= 0:

        raise ValueError(
            "remove_points() requires an amount "
            "greater than 0."
        )


    async with aiosqlite.connect(
        DB_PATH
    ) as db:


        # ==================================================
        # USER
        # ==================================================


        if username is not None:

            await _ensure_user(
                db=db,
                guild_id=guild_id,
                user_id=user_id,
                username=username,
            )


        # ==================================================
        # OLD POINT TOTAL
        # ==================================================


        old_points = await _get_point_total(
            db=db,
            guild_id=guild_id,
            user_id=user_id,
        )


        # ==================================================
        # NEW POINT TOTAL
        # ==================================================


        points_removed = min(
            amount,
            old_points,
        )

        new_points = (
            old_points
            - points_removed
        )


        # ==================================================
        # RECORD TRANSACTION
        # ==================================================


        if points_removed > 0:

            await db.execute(
                """
                INSERT INTO point_transactions (
                    guild_id,
                    user_id,
                    amount,
                    reason
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    guild_id,
                    user_id,
                    -points_removed,
                    reason,
                ),
            )

            await db.commit()


    # ==================================================
    # PROGRESSION
    # ==================================================


    progression = get_progression_change(
        old_points=old_points,
        new_points=new_points,
    )

    progression["awarded"] = (
        points_removed > 0
    )

    progression["points_awarded"] = (
        -points_removed
    )

    return progression


# ==================================================
# AWARD GOLDEN SPATULA
# ==================================================


async def award_golden_spatula(
    guild_id: int,
    user_id: int,
    username: str | None = None,
):
    """
    Record a Golden Spatula award.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:


        if username is not None:

            await _ensure_user(
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

    return int(
        row[0]
    )


# ==================================================
# INTERNAL POINT TOTAL
# ==================================================


async def _get_point_total(
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

    return int(
        row[0]
    )


# ==================================================
# INTERNAL ENSURE USER
# ==================================================


async def _ensure_user(
    db: aiosqlite.Connection,
    guild_id: int,
    user_id: int,
    username: str,
):
    """
    Create or update a user using an existing
    database connection.
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