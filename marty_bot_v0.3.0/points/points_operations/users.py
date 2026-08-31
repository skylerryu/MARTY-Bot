import aiosqlite

from data.user_db import (
    USER_DB_PATH,
)

from points.points_operations.operations_helpers import (
    ensure_user_in_db,
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
    Make sure a Discord user exists in the
    M.A.R.T.Y. users table.

    Existing usernames are updated automatically.
    """

    async with aiosqlite.connect(
        USER_DB_PATH
    ) as db:

        await ensure_user_in_db(
            db=db,
            guild_id=guild_id,
            user_id=user_id,
            username=username,
        )

        await db.commit()
