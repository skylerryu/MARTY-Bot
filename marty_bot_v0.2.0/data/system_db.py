from datetime import (
    date,
    timedelta,
    timezone,
)

from pathlib import Path

import aiosqlite

from points.time_helpers import (
    get_chicago_datetime,
)

from points.mechanics.question_of_the_day.qotd_config import (
    QOTD_POST_HOUR,
    QOTD_POST_MINUTE,
)


# ==================================================
# DATABASE PATH
# ==================================================


SYSTEM_DB_PATH = Path(__file__).with_name(
    "system.db"
)


# ==================================================
# ENSURE COLUMN
# ==================================================


async def _ensure_column(
    db: aiosqlite.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
):

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
# BACKFILL OLD QOTD EXPIRATIONS
# ==================================================


async def _backfill_qotd_expirations(
    db: aiosqlite.Connection,
):

    cursor = await db.execute(
        """
        SELECT
            id,
            question_date

        FROM qotd_questions

        WHERE expires_at IS NULL
        """
    )

    rows = await cursor.fetchall()

    for row in rows:

        qotd_id = row[0]

        question_date = (
            date.fromisoformat(
                row[1]
            )
        )

        deadline_chicago = (
            get_chicago_datetime(
                calendar_date=(
                    question_date
                    + timedelta(days=1)
                ),
                hour=QOTD_POST_HOUR,
                minute=QOTD_POST_MINUTE,
            )
        )

        deadline_utc = (
            deadline_chicago.astimezone(
                timezone.utc
            )
        )

        await db.execute(
            """
            UPDATE qotd_questions

            SET expires_at = ?

            WHERE id = ?
            """,
            (
                deadline_utc.isoformat(),
                qotd_id,
            ),
        )


# ==================================================
# INITIALIZE SYSTEM DATABASE
# ==================================================


async def init_system_db():

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        await db.execute(
            "PRAGMA foreign_keys = ON"
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

                expires_at TEXT,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    guild_id,
                    question_date
                )
            )
            """
        )

        await _ensure_column(
            db=db,
            table_name="qotd_questions",
            column_name="question_bank_id",
            column_definition="INTEGER",
        )

        await _ensure_column(
            db=db,
            table_name="qotd_questions",
            column_name="expires_at",
            column_definition="TEXT",
        )

        await _backfill_qotd_expirations(
            db
        )

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
            idx_qotd_questions_expiration

            ON qotd_questions (
                guild_id,
                expires_at
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
        # ACTIVE SPEED QUESTIONS
        # ==================================================


        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS active_speed_questions (
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
        # QUESTION FLAGS
        # ==================================================


        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS question_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                guild_id INTEGER NOT NULL,
                question_bank_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,

                source TEXT NOT NULL
                    DEFAULT 'question',

                context_key TEXT,

                reason TEXT NOT NULL,

                attempted_answers TEXT NOT NULL
                    DEFAULT '[]',

                status TEXT NOT NULL
                    DEFAULT 'open',

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                reviewed_by INTEGER,
                reviewed_at TEXT,
                resolution_note TEXT
            )
            """
        )

        await _ensure_column(
            db=db,
            table_name="question_flags",
            column_name="context_key",
            column_definition="TEXT",
        )

        await _ensure_column(
            db=db,
            table_name="question_flags",
            column_name="attempted_answers",
            column_definition=(
                "TEXT NOT NULL DEFAULT '[]'"
            ),
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_question_flags_question

            ON question_flags (
                guild_id,
                question_bank_id
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_question_flags_status

            ON question_flags (
                guild_id,
                status
            )
            """
        )

        await db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_question_flags_unique_open

            ON question_flags (
                guild_id,
                question_bank_id,
                user_id
            )

            WHERE status = 'open'
            """
        )


        # ==================================================
        # QUESTION EDIT QUEUE
        # ==================================================


        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS question_edit_queue (
                question_bank_id INTEGER PRIMARY KEY,

                status TEXT NOT NULL
                    DEFAULT 'needs_edit',

                marked_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                marked_by INTEGER NOT NULL,

                source_flag_id INTEGER,

                resolved_at TEXT,
                resolved_by INTEGER
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_question_edit_queue_status

            ON question_edit_queue (
                status,
                marked_at
            )
            """
        )


        # ==================================================
        # SAVE
        # ==================================================


        await db.commit()


# ==================================================
# DIRECT TEST
# ==================================================


if __name__ == "__main__":

    import asyncio

    asyncio.run(
        init_system_db()
    )

    print(
        "M.A.R.T.Y. system database initialized at: "
        f"{SYSTEM_DB_PATH}"
    )