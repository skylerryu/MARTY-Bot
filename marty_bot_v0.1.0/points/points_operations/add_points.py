import aiosqlite

from data.database import (
    DB_PATH,
)

from points.points_operations.operations_helpers import (
    ensure_user_in_db,
    get_point_total_from_db,
)

from points.progressions.progressions import (
    get_progression_change,
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

    source_key may be supplied when a point
    award must only be given once.

    For example:

        qotd:15:correct

    prevents the same QoTD reward from being
    awarded more than once.
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

            await ensure_user_in_db(
                db=db,
                guild_id=guild_id,
                user_id=user_id,
                username=username,
            )


        # ==================================================
        # OLD POINT TOTAL
        # ==================================================

        old_points = await get_point_total_from_db(
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

        awarded = cursor.rowcount > 0

        await db.commit()


    # ==================================================
    # NEW POINT TOTAL
    # ==================================================

    if awarded:
        new_points = old_points + amount

    else:
        new_points = old_points


    # ==================================================
    # PROGRESSION
    # ==================================================

    progression = get_progression_change(
        old_points=old_points,
        new_points=new_points,
    )

    progression["awarded"] = awarded

    progression["points_awarded"] = (
        amount
        if awarded
        else 0
    )

    return progression