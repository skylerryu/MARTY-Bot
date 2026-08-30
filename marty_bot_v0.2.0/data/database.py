from pathlib import Path

import aiosqlite


# ==================================================
# DATABASE PATH
# ==================================================


DB_PATH = Path(__file__).with_name(
    "marty.db"
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
    Add a column to an existing table if the
    column does not already exist.

    This lets M.A.R.T.Y. upgrade an older
    database without deleting it.
    """

    cursor = await db.execute(
        f"PRAGMA table_info({table_name})"
    )

    rows = await cursor.fetchall()

    existing_columns = {
        row[1]
        for row in rows
    }

    if column_name in existing_columns:
        return

    await db.execute(
        f"""
        ALTER TABLE {table_name}
        ADD COLUMN {column_name}
        {column_definition}
        """
    )


# ==================================================
# INITIALIZE DATABASE
# ==================================================


async def init_db():
    """
    Create all persistent M.A.R.T.Y. tables
    and indexes.

    Existing data is preserved.
    """

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await db.execute(
            "PRAGMA foreign_keys = ON"
        )


        # ==================================================
        # USERS
        # ==================================================


        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

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


        # ==================================================
        # POINT TRANSACTION MIGRATIONS
        # ==================================================


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
            idx_point_transactions_created_at

            ON point_transactions (
                guild_id,
                created_at
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_point_transactions_user_created_at

            ON point_transactions (
                guild_id,
                user_id,
                created_at
            )
            """
        )


        # ==================================================
        # UNIQUE POINT SOURCE
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


        # ==================================================
        # GOLDEN SPATULAS
        # ==================================================


        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS golden_spatulas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,

                week_start TEXT NOT NULL,

                username TEXT,
                weekly_points INTEGER,

                awarded_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    guild_id,
                    week_start
                )
            )
            """
        )


        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_golden_spatulas_user

            ON golden_spatulas (
                guild_id,
                user_id
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

                current_streak INTEGER NOT NULL
                    DEFAULT 0,

                last_active_week TEXT,

                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

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

                question_bank_id INTEGER,

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
        # QOTD QUESTION MIGRATIONS
        # ==================================================


        await _ensure_column(
            db=db,
            table_name="qotd_questions",
            column_name="question_bank_id",
            column_definition="INTEGER",
        )


        # ==================================================
        # QOTD QUESTION INDEXES
        # ==================================================


        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_qotd_questions_date

            ON qotd_questions (
                guild_id,
                question_date
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_qotd_questions_message

            ON qotd_questions (
                message_id
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_qotd_questions_bank_id

            ON qotd_questions (
                guild_id,
                question_bank_id
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
        # QOTD COMPLETION INDEXES
        # ==================================================


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

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_qotd_completions_qotd

            ON qotd_completions (
                qotd_id
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
        # ACTIVE SPEED QUESTIONS
        # ==================================================


        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS
            active_speed_questions (
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,

                question_id INTEGER NOT NULL,

                posted_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                answered_by INTEGER,
                answered_at TEXT,

                PRIMARY KEY (
                    guild_id,
                    channel_id
                )
            )
            """
        )


        # ==================================================
        # ACTIVE SPEED QUESTION INDEX
        # ==================================================


        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_active_speed_questions_question

            ON active_speed_questions (
                question_id
            )
            """
        )


        # ==================================================
        # SAVE DATABASE CHANGES
        # ==================================================


        await db.commit()


# ==================================================
# DIRECT DATABASE TEST
# ==================================================


if __name__ == "__main__":

    import asyncio

    asyncio.run(
        init_db()
    )

    print(
        "M.A.R.T.Y. database initialized at: "
        f"{DB_PATH}"
    )
