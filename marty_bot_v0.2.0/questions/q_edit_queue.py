import sqlite3

from datetime import (
    datetime,
    timezone,
)

import aiosqlite

from data.system_db import (
    SYSTEM_DB_PATH,
)


# ==================================================
# EDIT QUEUE STATUS
# ==================================================


EDIT_STATUS_NEEDS_EDIT = "needs_edit"
EDIT_STATUS_RESOLVED = "resolved"


# ==================================================
# SYNC QUESTION-SELECTION HELPERS
# ==================================================


def get_question_edit_hold_ids() -> set[int]:
    """
    Return every question currently quarantined
    because it needs editing.

    This function is intentionally synchronous
    because q_manager.py is synchronous.
    """

    try:

        with sqlite3.connect(
            SYSTEM_DB_PATH
        ) as db:

            cursor = db.execute(
                """
                SELECT question_bank_id

                FROM question_edit_queue

                WHERE status = 'needs_edit'
                """
            )

            rows = cursor.fetchall()

    except sqlite3.OperationalError:

        # Database/table may not exist yet during
        # very early startup.
        return set()

    return {
        int(row[0])
        for row in rows
    }


def is_question_marked_for_edit(
    question_bank_id: int,
) -> bool:

    return (
        question_bank_id
        in get_question_edit_hold_ids()
    )


# ==================================================
# ROW CONVERSION
# ==================================================


def _row_to_edit_entry(
    row: aiosqlite.Row,
) -> dict:

    return {
        "question_bank_id": (
            row["question_bank_id"]
        ),
        "status": row["status"],
        "marked_at": row["marked_at"],
        "marked_by": row["marked_by"],
        "source_flag_id": (
            row["source_flag_id"]
        ),
        "resolved_at": (
            row["resolved_at"]
        ),
        "resolved_by": (
            row["resolved_by"]
        ),
    }


# ==================================================
# MARK QUESTION FROM FLAG
# ==================================================


async def mark_question_for_edit_from_flag(
    guild_id: int,
    question_bank_id: int,
    flag_id: int,
    marked_by: int,
) -> dict:
    """
    Atomically:

    1. Mark the individual flag as handled by
       escalating it for question editing.

    2. Put the question into the edit queue.

    If the question is already in the queue,
    the existing queue entry is preserved.
    """

    now = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        db.row_factory = (
            aiosqlite.Row
        )


        # ==================================================
        # VERIFY FLAG IS STILL OPEN
        # ==================================================


        cursor = await db.execute(
            """
            SELECT
                id,
                guild_id,
                question_bank_id,
                status

            FROM question_flags

            WHERE id = ?
              AND guild_id = ?
              AND question_bank_id = ?
              AND status = 'open'
            """,
            (
                flag_id,
                guild_id,
                question_bank_id,
            ),
        )

        flag_row = (
            await cursor.fetchone()
        )

        if flag_row is None:

            raise ValueError(
                f"Open flag #{flag_id} "
                "could not be found."
            )


        # ==================================================
        # EXISTING EDIT QUEUE ENTRY
        # ==================================================


        cursor = await db.execute(
            """
            SELECT
                question_bank_id,
                status

            FROM question_edit_queue

            WHERE question_bank_id = ?
            """,
            (
                question_bank_id,
            ),
        )

        existing_entry = (
            await cursor.fetchone()
        )


        # ==================================================
        # CREATE / REOPEN EDIT QUEUE ENTRY
        # ==================================================


        if existing_entry is None:

            await db.execute(
                """
                INSERT INTO question_edit_queue (
                    question_bank_id,
                    status,
                    marked_at,
                    marked_by,
                    source_flag_id,
                    resolved_at,
                    resolved_by
                )

                VALUES (
                    ?,
                    'needs_edit',
                    ?,
                    ?,
                    ?,
                    NULL,
                    NULL
                )
                """,
                (
                    question_bank_id,
                    now,
                    marked_by,
                    flag_id,
                ),
            )

        elif (
            existing_entry["status"]
            == EDIT_STATUS_RESOLVED
        ):

            await db.execute(
                """
                UPDATE question_edit_queue

                SET
                    status = 'needs_edit',
                    marked_at = ?,
                    marked_by = ?,
                    source_flag_id = ?,
                    resolved_at = NULL,
                    resolved_by = NULL

                WHERE question_bank_id = ?
                """,
                (
                    now,
                    marked_by,
                    flag_id,
                    question_bank_id,
                ),
            )


        # ==================================================
        # CLOSE THIS INDIVIDUAL FLAG
        # ==================================================


        await db.execute(
            """
            UPDATE question_flags

            SET
                status = 'marked_for_edit',
                reviewed_by = ?,
                reviewed_at = ?,
                resolution_note = ?

            WHERE id = ?
              AND guild_id = ?
              AND status = 'open'
            """,
            (
                marked_by,
                now,
                (
                    "Question marked for editing "
                    "through /flaggedreview."
                ),
                flag_id,
                guild_id,
            ),
        )

        await db.commit()


    entry = await get_question_edit_entry(
        question_bank_id
    )

    if entry is None:

        raise RuntimeError(
            "Question was marked for editing, "
            "but its edit-queue entry could not "
            "be retrieved."
        )

    return entry


# ==================================================
# GET EDIT ENTRY
# ==================================================


async def get_question_edit_entry(
    question_bank_id: int,
) -> dict | None:

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        db.row_factory = (
            aiosqlite.Row
        )

        cursor = await db.execute(
            """
            SELECT
                question_bank_id,
                status,
                marked_at,
                marked_by,
                source_flag_id,
                resolved_at,
                resolved_by

            FROM question_edit_queue

            WHERE question_bank_id = ?
            """,
            (
                question_bank_id,
            ),
        )

        row = await cursor.fetchone()

    if row is None:

        return None

    return _row_to_edit_entry(
        row
    )


# ==================================================
# GET QUESTIONS NEEDING EDITS
# ==================================================


async def get_questions_needing_edit() -> list[dict]:

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        db.row_factory = (
            aiosqlite.Row
        )

        cursor = await db.execute(
            """
            SELECT
                question_bank_id,
                status,
                marked_at,
                marked_by,
                source_flag_id,
                resolved_at,
                resolved_by

            FROM question_edit_queue

            WHERE status = 'needs_edit'

            ORDER BY marked_at DESC
            """
        )

        rows = await cursor.fetchall()

    return [
        _row_to_edit_entry(
            row
        )
        for row in rows
    ]


# ==================================================
# RESOLVE EDIT QUEUE QUESTION
# ==================================================


async def resolve_question_edit(
    question_bank_id: int,
    resolved_by: int,
) -> dict:

    now = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    async with aiosqlite.connect(
        SYSTEM_DB_PATH
    ) as db:

        cursor = await db.execute(
            """
            UPDATE question_edit_queue

            SET
                status = 'resolved',
                resolved_at = ?,
                resolved_by = ?

            WHERE question_bank_id = ?
              AND status = 'needs_edit'
            """,
            (
                now,
                resolved_by,
                question_bank_id,
            ),
        )

        await db.commit()

        if cursor.rowcount != 1:

            raise ValueError(
                f"Question #{question_bank_id} "
                "is not currently marked for editing."
            )

    entry = await get_question_edit_entry(
        question_bank_id
    )

    if entry is None:

        raise RuntimeError(
            "Resolved edit entry could not "
            "be retrieved."
        )

    return entry