from pathlib import Path

import aiosqlite


# ==================================================
# DATABASE PATHS
# ==================================================


USER_DB_PATH = Path(__file__).with_name(
    "user.db"
)

LEGACY_DB_PATH = Path(__file__).with_name(
    "marty.db"
)


# ==================================================
# LEGACY MIGRATION
# ==================================================


async def _copy_legacy_table(
    db: aiosqlite.Connection,
    table_name: str,
):
    """
    Copy compatible columns from the old marty.db
    table into user.db.

    This is only used the first time user.db is
    created. The old marty.db is never modified.
    """

    cursor = await db.execute(
        """
        SELECT 1
        FROM legacy.sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1
        """,
        (
            table_name,
        ),
    )

    if await cursor.fetchone() is None:
        return

    target_cursor = await db.execute(
        f"PRAGMA main.table_info({table_name})"
    )

    legacy_cursor = await db.execute(
        f"PRAGMA legacy.table_info({table_name})"
    )

    target_columns = [
        row[1]
        for row in await target_cursor.fetchall()
    ]

    legacy_columns = {
        row[1]
        for row in await legacy_cursor.fetchall()
    }

    common_columns = [
        column
        for column in target_columns
        if column in legacy_columns
    ]

    if not common_columns:
        return

    columns_sql = ", ".join(
        f'"{column}"'
        for column in common_columns
    )

    await db.execute(
        f"""
        INSERT OR IGNORE INTO "{table_name}" (
            {columns_sql}
        )
        SELECT
            {columns_sql}
        FROM legacy."{table_name}"
        """
    )


async def _migrate_legacy_user_data(
    db: aiosqlite.Connection,
):
    """
    Copy user-related data from the old marty.db
    into a newly created user.db.
    """

    if not LEGACY_DB_PATH.exists():
        return

    await db.execute(
        "ATTACH DATABASE ? AS legacy",
        (
            str(LEGACY_DB_PATH),
        ),
    )

    try:

        for table_name in (
            "users",
            "point_transactions",
            "golden_spatulas",
            "activity_streaks",
            "qotd_completions",
            "qotd_streaks",
        ):

            await _copy_legacy_table(
                db=db,
                table_name=table_name,
            )

    finally:

        # Finish any copied rows before detaching
        # the legacy database.
        await db.commit()

        await db.execute(
            "DETACH DATABASE legacy"
        )


# ==================================================
# INITIALIZE USER DATABASE
# ==================================================


async def init_user_db():
    """
    Create the persistent database containing
    information MARTY remembers about users.

    If user.db does not yet exist and the old
    marty.db does exist, compatible user data is
    copied into user.db automatically.
    """

    database_is_new = (
        not USER_DB_PATH.exists()
    )

    async with aiosqlite.connect(
        USER_DB_PATH
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
        # LEGACY MIGRATION
        # ==================================================


        if database_is_new:

            await _migrate_legacy_user_data(
                db
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
        init_user_db()
    )

    print(
        "M.A.R.T.Y. user database initialized at: "
        f"{USER_DB_PATH}"
    )
