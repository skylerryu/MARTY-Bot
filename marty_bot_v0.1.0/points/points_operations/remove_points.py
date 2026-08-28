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

    Points cannot be removed below zero.
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
        # AMOUNT TO REMOVE
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
        # POINT TRANSACTION
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