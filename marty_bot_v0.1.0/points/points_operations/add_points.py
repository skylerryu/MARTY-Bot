from contextvars import ContextVar

import aiosqlite
import discord

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

from points.progressions.levels.level_up_display import (
    build_level_up_embed,
)

from points.progressions.ranks.rank_up_display import (
    build_rank_up_embed,
)


# ==================================================
# DISCORD NOTIFICATION CONTEXT
# ==================================================


_point_notification_context = ContextVar(
    "point_notification_context",
    default=None,
)


def set_point_notification_context(
    user,
    channel,
):
    """
    Store the Discord user and channel associated
    with point awards in the current async task.

    This allows add_points() to automatically send
    progression notifications without every mechanic
    needing to handle them individually.
    """

    return _point_notification_context.set(
        {
            "user": user,
            "channel": channel,
        }
    )


def reset_point_notification_context(
    token,
):
    """
    Restore the previous Discord notification
    context.
    """

    _point_notification_context.reset(
        token
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

    Whenever a successful point award causes a
    level-up or rank-up, the appropriate public
    Discord notification is automatically sent.

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


    # ==================================================
    # PROGRESSION NOTIFICATIONS
    # ==================================================

    if awarded:

        await _handle_progression_notifications(
            progression=progression,
            username=username,
        )


    return progression


# ==================================================
# HANDLE PROGRESSION
# ==================================================


async def _handle_progression_notifications(
    progression: dict,
    username: str | None,
):
    """
    Automatically send any progression
    notifications caused by a point award.
    """

    context = (
        _point_notification_context.get()
    )

    if context is None:

        if (
            progression.get(
                "leveled_up",
                False,
            )
            or progression.get(
                "ranked_up",
                False,
            )
        ):

            print(
                "Progression notification skipped: "
                "no Discord notification context."
            )

        return


    user = context.get(
        "user"
    )

    channel = context.get(
        "channel"
    )


    # ==================================================
    # LEVEL UP
    # ==================================================

    if progression.get(
        "leveled_up",
        False,
    ):

        await _send_level_up_notification(
            progression=progression,
            user=user,
            channel=channel,
        )


    # ==================================================
    # RANK UP
    # ==================================================

    if progression.get(
        "ranked_up",
        False,
    ):

        await _send_rank_up_notification(
            progression=progression,
            user=user,
            channel=channel,
            username=username,
        )


# ==================================================
# LEVEL UP NOTIFICATION
# ==================================================


async def _send_level_up_notification(
    progression: dict,
    user,
    channel,
):
    """
    Send a public Level Up notification in the
    channel where the points were earned.
    """

    if channel is None:
        return


    level_up_embed = (
        build_level_up_embed(
            old_level=(
                progression[
                    "old_level"
                ]
            ),
            new_level=(
                progression[
                    "new_level"
                ]
            ),
        )
    )


    # ==================================================
    # SEND
    # ==================================================

    try:

        if (
            user is not None
            and hasattr(
                user,
                "mention",
            )
        ):

            await channel.send(
                content=user.mention,
                embed=level_up_embed,
            )

        else:

            await channel.send(
                embed=level_up_embed
            )

    except (
        discord.Forbidden,
        discord.HTTPException,
    ):

        pass


# ==================================================
# RANK UP NOTIFICATION
# ==================================================


async def _send_rank_up_notification(
    progression: dict,
    user,
    channel,
    username: str | None,
):
    """
    Send a public Rank Up notification in the
    channel where the points were earned.
    """

    if channel is None:
        return


    # ==================================================
    # DISPLAY NAME
    # ==================================================

    if username is not None:

        display_name = (
            username
        )

    elif (
        user is not None
        and hasattr(
            user,
            "display_name",
        )
    ):

        display_name = (
            user.display_name
        )

    else:

        display_name = (
            "A M.A.R.T.Y. user"
        )


    # ==================================================
    # BUILD EMBED
    # ==================================================

    rank_up_embed = (
        build_rank_up_embed(
            username=display_name,
            new_rank=(
                progression[
                    "new_rank"
                ]
            ),
            new_level=(
                progression[
                    "new_level"
                ]
            ),
        )
    )


    # ==================================================
    # SEND
    # ==================================================

    try:

        await channel.send(
            embed=rank_up_embed
        )

    except (
        discord.Forbidden,
        discord.HTTPException,
    ):

        pass