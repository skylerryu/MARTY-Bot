import aiosqlite

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo


DB_PATH = "marty.db"


# ==================================================
# DATABASE INITIALIZATION
# ==================================================

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:

        # ------------------------------------------
        # USERS
        # ------------------------------------------

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,

                PRIMARY KEY (guild_id, user_id)
            )
        """)

        # ------------------------------------------
        # POINT TRANSACTIONS
        # ------------------------------------------

        await db.execute("""
            CREATE TABLE IF NOT EXISTS point_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Makes point lookups faster
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_point_transactions_user
            ON point_transactions (
                guild_id,
                user_id
            )
        """)

        # Useful for weekly leaderboard queries
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_point_transactions_time
            ON point_transactions (
                guild_id,
                created_at
            )
        """)

        # ------------------------------------------
        # WEEKLY WINNERS / GOLDEN SPATULAS
        # ------------------------------------------

        await db.execute("""
            CREATE TABLE IF NOT EXISTS weekly_winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                weekly_points INTEGER NOT NULL,
                week_start TEXT NOT NULL,
                awarded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Prevent more than one Chef of the Week
        # from being recorded for the same week
        await db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_weekly_winner
            ON weekly_winners (
                guild_id,
                week_start
            )
        """)

        # ------------------------------------------
        # ACTIVE QUESTIONS
        #
        # The actual question content lives in
        # questions.json.
        #
        # SQLite only remembers which question ID
        # is currently active in each channel.
        # ------------------------------------------

        await db.execute("""
            CREATE TABLE IF NOT EXISTS active_questions (
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                posted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                answered_by INTEGER,
                answered_at TEXT,

                PRIMARY KEY (guild_id, channel_id)
            )
        """)

        await db.commit()


# ==================================================
# USERS
# ==================================================

async def ensure_user(
    guild_id: int,
    user_id: int,
    username: str
):
    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("""
            INSERT INTO users (
                guild_id,
                user_id,
                username
            )
            VALUES (?, ?, ?)

            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                username = excluded.username
        """, (
            guild_id,
            user_id,
            username
        ))

        await db.commit()


# ==================================================
# POINTS
# ==================================================

async def add_points(
    guild_id: int,
    user_id: int,
    amount: int,
    reason: str
):
    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("""
            INSERT INTO point_transactions (
                guild_id,
                user_id,
                amount,
                reason
            )
            VALUES (?, ?, ?, ?)
        """, (
            guild_id,
            user_id,
            amount,
            reason
        ))

        await db.commit()


async def get_points(
    guild_id: int,
    user_id: int
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM point_transactions
            WHERE guild_id = ?
            AND user_id = ?
        """, (
            guild_id,
            user_id
        ))

        row = await cursor.fetchone()

        return row[0]


# ==================================================
# WEEKLY POINTS
# ==================================================

def get_current_week_start_utc():
    """
    Returns the start of the current M.A.R.T.Y. week.

    Competition week:
    Monday 12:00 AM Chicago time
    through Sunday 11:59:59 PM Chicago time.

    Database timestamps are stored in UTC.
    """

    chicago = ZoneInfo("America/Chicago")

    now_chicago = datetime.now(chicago)

    start_of_week = (
        now_chicago.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
        - timedelta(days=now_chicago.weekday())
    )

    return start_of_week.astimezone(timezone.utc)


async def get_weekly_points(
    guild_id: int,
    user_id: int
) -> int:

    start_utc = get_current_week_start_utc()

    start_string = start_utc.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM point_transactions
            WHERE guild_id = ?
            AND user_id = ?
            AND created_at >= ?
        """, (
            guild_id,
            user_id,
            start_string
        ))

        row = await cursor.fetchone()

        return row[0]


# ==================================================
# ALL-TIME LEADERBOARD
# ==================================================

async def get_leaderboard(
    guild_id: int,
    limit: int = 10
):
    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute("""
            SELECT
                users.user_id,
                users.username,
                COALESCE(
                    SUM(point_transactions.amount),
                    0
                ) AS total_points

            FROM users

            LEFT JOIN point_transactions
                ON users.guild_id = point_transactions.guild_id
                AND users.user_id = point_transactions.user_id

            WHERE users.guild_id = ?

            GROUP BY
                users.user_id,
                users.username

            ORDER BY
                total_points DESC,
                users.user_id ASC

            LIMIT ?
        """, (
            guild_id,
            limit
        ))

        return await cursor.fetchall()


# ==================================================
# WEEKLY LEADERBOARD
# ==================================================

async def get_weekly_leaderboard(
    guild_id: int,
    limit: int = 10
):

    start_utc = get_current_week_start_utc()

    start_string = start_utc.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute("""
            SELECT
                users.user_id,
                users.username,
                COALESCE(
                    SUM(point_transactions.amount),
                    0
                ) AS weekly_points

            FROM users

            LEFT JOIN point_transactions
                ON users.guild_id = point_transactions.guild_id
                AND users.user_id = point_transactions.user_id
                AND point_transactions.created_at >= ?

            WHERE users.guild_id = ?

            GROUP BY
                users.user_id,
                users.username

            ORDER BY
                weekly_points DESC,
                users.user_id ASC

            LIMIT ?
        """, (
            start_string,
            guild_id,
            limit
        ))

        return await cursor.fetchall()


async def get_weekly_winner(guild_id: int):

    rows = await get_weekly_leaderboard(
        guild_id=guild_id,
        limit=1
    )

    if not rows:
        return None

    return rows[0]


# ==================================================
# PREVIOUS WEEK WINNER
# ==================================================

async def get_previous_week_winner(
    guild_id: int
):

    chicago = ZoneInfo("America/Chicago")

    now_chicago = datetime.now(chicago)

    # Current Monday at midnight
    current_week_start = (
        now_chicago.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
        - timedelta(days=now_chicago.weekday())
    )

    # Previous Monday
    previous_week_start = (
        current_week_start
        - timedelta(days=7)
    )

    previous_week_end = current_week_start

    # Convert to UTC for SQLite
    start_utc = previous_week_start.astimezone(
        timezone.utc
    )

    end_utc = previous_week_end.astimezone(
        timezone.utc
    )

    start_string = start_utc.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    end_string = end_utc.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute("""
            SELECT
                users.user_id,
                users.username,
                SUM(
                    point_transactions.amount
                ) AS weekly_points

            FROM users

            JOIN point_transactions
                ON users.guild_id = point_transactions.guild_id
                AND users.user_id = point_transactions.user_id

            WHERE users.guild_id = ?
            AND point_transactions.created_at >= ?
            AND point_transactions.created_at < ?

            GROUP BY
                users.user_id,
                users.username

            ORDER BY
                weekly_points DESC,
                users.user_id ASC

            LIMIT 1
        """, (
            guild_id,
            start_string,
            end_string
        ))

        row = await cursor.fetchone()

        if row is None:
            return None

        return {
            "user_id": row[0],
            "username": row[1],
            "points": row[2],
            "week_start": (
                previous_week_start
                .date()
                .isoformat()
            )
        }


# ==================================================
# GOLDEN SPATULA / CHEF OF THE WEEK
# ==================================================

async def record_weekly_winner(
    guild_id: int,
    user_id: int,
    username: str,
    weekly_points: int,
    week_start: str
):

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute("""
            INSERT OR IGNORE INTO weekly_winners (
                guild_id,
                user_id,
                username,
                weekly_points,
                week_start
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            guild_id,
            user_id,
            username,
            weekly_points,
            week_start
        ))

        await db.commit()

        return cursor.rowcount > 0


async def award_previous_week_winner(
    guild_id: int
):

    winner = await get_previous_week_winner(
        guild_id
    )

    if winner is None:
        return None

    awarded = await record_weekly_winner(
        guild_id=guild_id,
        user_id=winner["user_id"],
        username=winner["username"],
        weekly_points=winner["points"],
        week_start=winner["week_start"]
    )

    return {
        **winner,
        "awarded": awarded
    }


async def get_golden_spatulas(
    guild_id: int,
    user_id: int
) -> int:

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute("""
            SELECT COUNT(*)
            FROM weekly_winners
            WHERE guild_id = ?
            AND user_id = ?
        """, (
            guild_id,
            user_id
        ))

        row = await cursor.fetchone()

        return row[0]


# ==================================================
# ACTIVE QUESTION STATE
# ==================================================

async def set_active_question(
    guild_id: int,
    channel_id: int,
    question_id: int
):

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("""
            INSERT INTO active_questions (
                guild_id,
                channel_id,
                question_id
            )
            VALUES (?, ?, ?)

            ON CONFLICT(guild_id, channel_id)
            DO UPDATE SET
                question_id = excluded.question_id,
                posted_at = CURRENT_TIMESTAMP,
                answered_by = NULL,
                answered_at = NULL
        """, (
            guild_id,
            channel_id,
            question_id
        ))

        await db.commit()


async def get_active_question(
    guild_id: int,
    channel_id: int
):

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute("""
            SELECT
                question_id,
                posted_at,
                answered_by

            FROM active_questions

            WHERE guild_id = ?
            AND channel_id = ?
        """, (
            guild_id,
            channel_id
        ))

        return await cursor.fetchone()


async def mark_question_answered(
    guild_id: int,
    channel_id: int,
    user_id: int
) -> bool:

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute("""
            UPDATE active_questions

            SET
                answered_by = ?,
                answered_at = CURRENT_TIMESTAMP

            WHERE guild_id = ?
            AND channel_id = ?
            AND answered_by IS NULL
        """, (
            user_id,
            guild_id,
            channel_id
        ))

        await db.commit()

        return cursor.rowcount > 0