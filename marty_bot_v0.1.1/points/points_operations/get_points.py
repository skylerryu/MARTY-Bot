import aiosqlite

from data.database import (
    DB_PATH,
)

from points.points_operations.operations_helpers import (
    get_point_total_from_db,
)


# ==================================================
# GET POINTS
# ==================================================


async def get_points(
    guild_id: int,
    user_id: int,
) -> int:
    """
    Return a user's total number of points.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        return await get_point_total_from_db(
            db=db,
            guild_id=guild_id,
            user_id=user_id,
        )