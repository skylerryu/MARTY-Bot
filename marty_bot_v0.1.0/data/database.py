from pathlib import Path

import aiosqlite


# ==================================================
# DATABASE PATH
# ==================================================


DB_PATH = Path(__file__).with_name(
    "marty.db"
)


# ==================================================
# INITIALIZE DATABASE
# ==================================================


async def init_db():
    """
    Create all database tables and indexes
    required by M.A.R.T.Y.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        # ==================================================
        # USERS
        # ==================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,

                PRIMARY KEY (
                    guild_id,
                    user_id
                )
            )
            """
        )


        # ==================================================
        # POINT TRANSACTIONS
        # ==================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS point_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,

                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,

                source_key TEXT,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Add source_key to older databases that were
        # created before this column existed.
        await _ensure_column(
            db=db,
            table_name="point_transactions",
            column_name="source_key",
            column_definition="TEXT",
        )


        # ==================================================
        # POINT TRANSACTION INDEXES
        # ==================================================

        await db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
                idx_point_transactions_source_key

            ON point_transactions (
                guild_id,
                user_id,
                source_key
            )

            WHERE source_key IS NOT NULL
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_point_transactions_user

            ON point_transactions (
                guild_id,
                user_id
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_point_transactions_week

            ON point_transactions (
                guild_id,
                created_at
            )
            """
        )


        # ==================================================
        # GOLDEN SPATULAS
        # ==================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS golden_spatulas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,

                awarded_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        # ==================================================
        # ACTIVITY STREAKS
        # ==================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_streaks (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,

                current_streak INTEGER NOT NULL,
                last_active_week TEXT NOT NULL,

                PRIMARY KEY (
                    guild_id,
                    user_id
                )
            )
            """
        )


        # ==================================================
        # QOTD QUESTIONS
        # ==================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS qotd_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,

                question_date TEXT NOT NULL,
                question_text TEXT NOT NULL,

                accepted_answers TEXT NOT NULL,
                explanation TEXT,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    guild_id,
                    question_date
                )
            )
            """
        )


        # ==================================================
        # QOTD COMPLETIONS
        # ==================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS qotd_completions (
                qotd_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,

                completed_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY (
                    qotd_id,
                    user_id
                )
            )
            """
        )


        # ==================================================
        # QOTD STREAKS
        # ==================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS qotd_streaks (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,

                current_streak INTEGER NOT NULL,
                last_completion_date TEXT NOT NULL,

                PRIMARY KEY (
                    guild_id,
                    user_id
                )
            )
            """
        )


        # ==================================================
        # QOTD INDEXES
        # ==================================================

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_qotd_questions_guild_date

            ON qotd_questions (
                guild_id,
                question_date
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_qotd_completions_user

            ON qotd_completions (
                guild_id,
                user_id
            )
            """
        )


        # ==================================================
        # SAVE
        # ==================================================

        await db.commit()


    print(
        f"Database initialized: {DB_PATH}"
    )


# ==================================================
# DATABASE MIGRATION HELPER
# ==================================================


async def _ensure_column(
    db: aiosqlite.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
):
    """
    Add a column to an existing table if that
    column does not already exist.

    This allows older M.A.R.T.Y. databases to
    be upgraded without deleting their data.
    """

    cursor = await db.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = await cursor.fetchall()

    column_exists = any(
        row[1] == column_name
        for row in columns
    )

    if column_exists:
        return

    await db.execute(
        f"""
        ALTER TABLE {table_name}
        ADD COLUMN {column_name}
        {column_definition}
        """
    )