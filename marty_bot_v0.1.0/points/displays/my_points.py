import discord
import aiosqlite

from data.database import DB_PATH
from points.time_helpers import get_current_week_start_utc

from points.displays.displays_helpers import (
    build_progress_bar,
)

from points.progressions.levels.levels import (
    get_level_progress,
)

from points.progressions.ranks.ranks import (
    get_rank_for_level,
)


# ==================================================
# DISPLAY
# ==================================================


async def build_my_points_embed(
    guild_id: int,
    user_id: int,
    username: str,
) -> discord.Embed:
    """
    Build the embed displayed by /mypoints.
    """

    points = await get_my_points(
        guild_id=guild_id,
        user_id=user_id,
    )

    all_time_points = points[
        "all_time_points"
    ]

    level_progress = get_level_progress(
        all_time_points
    )

    level = level_progress[
        "level"
    ]

    rank = get_rank_for_level(
        level
    )

    progress_bar = build_progress_bar(
        level_progress[
            "progress_percent"
        ]
    )

    embed = discord.Embed(
        title=(
            f"🏆 {username}'s "
            f"M.A.R.T.Y. Progress"
        ),
        description=(
            f"**{rank['name']}**\n"
            f"Level **{level}**"
        ),
    )

    # --------------------------------------------------
    # LEVEL PROGRESS
    # --------------------------------------------------

    embed.add_field(
        name=(
            f"Progress to Level "
            f"{level + 1}"
        ),
        value=(
            f"`{progress_bar}`\n"
            f"**"
            f"{level_progress['points_into_level']}"
            f" / "
            f"{level_progress['points_required']}"
            f" XP"
            f"** "
            f"• "
            f"{level_progress['progress_percent']:.0f}%"
        ),
        inline=False,
    )

    # --------------------------------------------------
    # STATS
    # --------------------------------------------------

    embed.add_field(
        name="Stats",
        value=(
            f"📅 **This Week:** "
            f"**{points['weekly_points']} pts**\n"
            f"🏆 **All-Time:** "
            f"**{all_time_points} pts**\n"
            f"🍴 **Golden Spatulas:** "
            f"**{points['golden_spatulas']}**"
        ),
        inline=False,
    )

    return embed


# ==================================================
# POINT DATA
# ==================================================


async def get_my_points(
    guild_id: int,
    user_id: int,
) -> dict:
    """
    Return all point information needed
    for the /mypoints display.
    """

    weekly_points = await get_weekly_points(
        guild_id=guild_id,
        user_id=user_id,
    )

    all_time_points = await get_all_time_points(
        guild_id=guild_id,
        user_id=user_id,
    )

    golden_spatulas = await get_golden_spatulas(
        guild_id=guild_id,
        user_id=user_id,
    )

    return {
        "weekly_points": weekly_points,
        "all_time_points": all_time_points,
        "golden_spatulas": golden_spatulas,
    }


async def get_weekly_points(
    guild_id: int,
    user_id: int,
) -> int:
    """
    Return the user's points earned during
    the current Chicago week.
    """

    week_start_utc = (
        get_current_week_start_utc()
    )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM point_transactions
            WHERE guild_id = ?
              AND user_id = ?
              AND created_at >= ?
            """,
            (
                guild_id,
                user_id,
                week_start_utc,
            ),
        )

        row = await cursor.fetchone()

    return int(row[0])


async def get_all_time_points(
    guild_id: int,
    user_id: int,
) -> int:
    """
    Return the user's total M.A.R.T.Y. points.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
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


async def get_golden_spatulas(
    guild_id: int,
    user_id: int,
) -> int:
    """
    Return the total number of Golden Spatulas
    earned by the user.
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