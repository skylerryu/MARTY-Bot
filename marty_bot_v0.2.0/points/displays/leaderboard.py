import discord
import aiosqlite

from data.database import DB_PATH
from points.time_helpers import get_current_week_start_utc


# ==================================================
# DISPLAY
# ==================================================


async def build_leaderboard_embed(
    guild_id: int,
    limit: int = 10,
) -> discord.Embed:
    """
    Build the embed displayed by /leaderboard.
    """

    leaderboards = await get_leaderboards(
        guild_id=guild_id,
        limit=limit,
    )

    embed = discord.Embed(
        title="🏆 M.A.R.T.Y. Leaderboard"
    )

    embed.add_field(
        name="📅 This Week",
        value=format_points_leaderboard(
            leaderboards["weekly"]
        ),
        inline=False,
    )

    embed.add_field(
        name="🏆 All-Time",
        value=format_points_leaderboard(
            leaderboards["all_time"]
        ),
        inline=False,
    )

    embed.add_field(
        name="🍴 Golden Spatulas",
        value=format_spatula_leaderboard(
            leaderboards["golden_spatulas"]
        ),
        inline=False,
    )

    return embed


# ==================================================
# LEADERBOARD DATA
# ==================================================


async def get_leaderboards(
    guild_id: int,
    limit: int = 10,
) -> dict:
    """
    Get all leaderboard information needed
    for /leaderboard.
    """

    weekly = await get_weekly_leaderboard(
        guild_id=guild_id,
        limit=limit,
    )

    all_time = await get_all_time_leaderboard(
        guild_id=guild_id,
        limit=limit,
    )

    golden_spatulas = await get_golden_spatula_leaderboard(
        guild_id=guild_id,
        limit=limit,
    )

    return {
        "weekly": weekly,
        "all_time": all_time,
        "golden_spatulas": golden_spatulas,
    }


# ==================================================
# WEEKLY POINTS
# ==================================================


async def get_weekly_leaderboard(
    guild_id: int,
    limit: int = 10,
) -> list:

    week_start_utc = get_current_week_start_utc()

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute(
            """
            SELECT
                users.user_id,
                users.username,
                SUM(point_transactions.amount) AS points

            FROM users

            JOIN point_transactions
                ON users.guild_id = point_transactions.guild_id
                AND users.user_id = point_transactions.user_id

            WHERE users.guild_id = ?
              AND point_transactions.created_at >= ?

            GROUP BY
                users.user_id,
                users.username

            ORDER BY
                points DESC,
                users.username ASC

            LIMIT ?
            """,
            (
                guild_id,
                week_start_utc,
                limit,
            ),
        )

        rows = await cursor.fetchall()

    return rows


# ==================================================
# ALL-TIME POINTS
# ==================================================


async def get_all_time_leaderboard(
    guild_id: int,
    limit: int = 10,
) -> list:

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute(
            """
            SELECT
                users.user_id,
                users.username,
                SUM(point_transactions.amount) AS points

            FROM users

            JOIN point_transactions
                ON users.guild_id = point_transactions.guild_id
                AND users.user_id = point_transactions.user_id

            WHERE users.guild_id = ?

            GROUP BY
                users.user_id,
                users.username

            ORDER BY
                points DESC,
                users.username ASC

            LIMIT ?
            """,
            (
                guild_id,
                limit,
            ),
        )

        rows = await cursor.fetchall()

    return rows


# ==================================================
# GOLDEN SPATULAS
# ==================================================


async def get_golden_spatula_leaderboard(
    guild_id: int,
    limit: int = 10,
) -> list:

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute(
            """
            SELECT
                users.user_id,
                users.username,
                COUNT(golden_spatulas.id) AS spatulas

            FROM users

            JOIN golden_spatulas
                ON users.guild_id = golden_spatulas.guild_id
                AND users.user_id = golden_spatulas.user_id

            WHERE users.guild_id = ?

            GROUP BY
                users.user_id,
                users.username

            ORDER BY
                spatulas DESC,
                users.username ASC

            LIMIT ?
            """,
            (
                guild_id,
                limit,
            ),
        )

        rows = await cursor.fetchall()

    return rows


# ==================================================
# FORMATTING
# ==================================================


def format_points_leaderboard(
    rows: list,
) -> str:

    if not rows:
        return "No points yet."

    lines = []

    for position, row in enumerate(
        rows,
        start=1,
    ):
        user_id, username, points = row

        lines.append(
            f"**{position}.** {username} — {points} pts"
        )

    return "\n".join(lines)


def format_spatula_leaderboard(
    rows: list,
) -> str:

    if not rows:
        return "No Golden Spatulas yet."

    lines = []

    for position, row in enumerate(
        rows,
        start=1,
    ):
        user_id, username, spatulas = row

        lines.append(
            f"**{position}.** {username} — 🍴 {spatulas}"
        )

    return "\n".join(lines)