import json
import sqlite3

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

import aiosqlite


# ==================================================
# DATABASE PATH
# ==================================================


PATIENT_ASSESSMENT_DB_PATH = (
    Path(__file__).with_name(
        "patient_assessment.db"
    )
)


# ==================================================
# CONNECTION
# ==================================================


async def _connect() -> aiosqlite.Connection:
    db = await aiosqlite.connect(
        PATIENT_ASSESSMENT_DB_PATH
    )

    await db.execute(
        "PRAGMA foreign_keys = ON"
    )
    await db.execute(
        "PRAGMA journal_mode = WAL"
    )
    await db.execute(
        "PRAGMA busy_timeout = 5000"
    )

    db.row_factory = aiosqlite.Row

    return db


# ==================================================
# INITIALIZE
# ==================================================


async def init_patient_assessment_db():
    db = await _connect()

    try:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,

                scenario_date TEXT NOT NULL,
                scenario_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',

                title TEXT NOT NULL,
                dispatch_text TEXT NOT NULL,
                opening_scene TEXT NOT NULL,

                scenario_json TEXT NOT NULL,

                expires_at TEXT NOT NULL,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_assessment_scenario_active_date

            ON assessment_scenarios (
                guild_id,
                scenario_date
            )

            WHERE status = 'active'
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_assessment_scenarios_active

            ON assessment_scenarios (
                guild_id,
                status,
                expires_at
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,

                scenario_id INTEGER NOT NULL,
                attempt_number INTEGER NOT NULL,

                status TEXT NOT NULL DEFAULT 'active',
                current_phase TEXT NOT NULL
                    DEFAULT 'scene_size_up',

                patient_state_json TEXT NOT NULL,

                turn_number INTEGER NOT NULL DEFAULT 0,

                started_at TEXT NOT NULL,
                last_interaction_at TEXT NOT NULL,
                ended_at TEXT,

                transport_called_at TEXT,

                final_raw_points REAL,
                final_max_points REAL,
                critical_fail_count INTEGER
                    NOT NULL DEFAULT 0,
                critical_fail_deduction REAL,
                final_points REAL,
                final_percent REAL,

                FOREIGN KEY (scenario_id)
                    REFERENCES assessment_scenarios(id)
            )
            """
        )

        await db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_assessment_one_active_session

            ON assessment_sessions (
                guild_id,
                user_id,
                scenario_id
            )

            WHERE status = 'active'
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_assessment_sessions_user

            ON assessment_sessions (
                guild_id,
                user_id,
                id
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                session_id INTEGER NOT NULL,
                turn_number INTEGER NOT NULL,

                student_input TEXT NOT NULL,
                marty_response TEXT NOT NULL,
                response_role TEXT NOT NULL,

                elapsed_seconds REAL NOT NULL,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    session_id,
                    turn_number
                ),

                FOREIGN KEY (session_id)
                    REFERENCES assessment_sessions(id)
                    ON DELETE CASCADE
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_assessment_turns_session

            ON assessment_turns (
                session_id,
                turn_number
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_rubric_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                session_id INTEGER NOT NULL,
                rubric_key TEXT NOT NULL,

                points REAL NOT NULL,
                max_points REAL NOT NULL,

                evidence_turn_id INTEGER,
                grader_reason TEXT,

                awarded_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    session_id,
                    rubric_key
                ),

                FOREIGN KEY (session_id)
                    REFERENCES assessment_sessions(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (evidence_turn_id)
                    REFERENCES assessment_turns(id)
                    ON DELETE SET NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_critical_fails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                session_id INTEGER NOT NULL,
                critical_fail_key TEXT NOT NULL,
                description TEXT NOT NULL,

                evidence_turn_id INTEGER,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    session_id,
                    critical_fail_key
                ),

                FOREIGN KEY (session_id)
                    REFERENCES assessment_sessions(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (evidence_turn_id)
                    REFERENCES assessment_turns(id)
                    ON DELETE SET NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_llm_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                scenario_id INTEGER,
                session_id INTEGER,
                turn_id INTEGER,

                purpose TEXT NOT NULL,
                model TEXT NOT NULL,

                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (scenario_id)
                    REFERENCES assessment_scenarios(id)
                    ON DELETE SET NULL,

                FOREIGN KEY (session_id)
                    REFERENCES assessment_sessions(id)
                    ON DELETE SET NULL,

                FOREIGN KEY (turn_id)
                    REFERENCES assessment_turns(id)
                    ON DELETE SET NULL
            )
            """
        )

        await db.commit()

    finally:
        await db.close()


# ==================================================
# ROW HELPERS
# ==================================================


def _scenario_row(row: aiosqlite.Row) -> dict:
    data = json.loads(row["scenario_json"])

    return {
        "id": row["id"],
        "guild_id": row["guild_id"],
        "channel_id": row["channel_id"],
        "message_id": row["message_id"],
        "scenario_date": row["scenario_date"],
        "scenario_type": row["scenario_type"],
        "status": row["status"],
        "title": row["title"],
        "dispatch_text": row["dispatch_text"],
        "opening_scene": row["opening_scene"],
        "expires_at": row["expires_at"],
        "created_at": row["created_at"],
        **data,
    }


def _session_row(row: aiosqlite.Row) -> dict:
    return {
        "id": row["id"],
        "guild_id": row["guild_id"],
        "user_id": row["user_id"],
        "username": row["username"],
        "scenario_id": row["scenario_id"],
        "attempt_number": row["attempt_number"],
        "status": row["status"],
        "current_phase": row["current_phase"],
        "patient_state": json.loads(
            row["patient_state_json"]
        ),
        "turn_number": row["turn_number"],
        "started_at": row["started_at"],
        "last_interaction_at": row["last_interaction_at"],
        "ended_at": row["ended_at"],
        "transport_called_at": row["transport_called_at"],
        "final_raw_points": row["final_raw_points"],
        "final_max_points": row["final_max_points"],
        "critical_fail_count": row["critical_fail_count"],
        "critical_fail_deduction": row["critical_fail_deduction"],
        "final_points": row["final_points"],
        "final_percent": row["final_percent"],
    }


# ==================================================
# SCENARIOS
# ==================================================


async def create_assessment_scenario(
    guild_id: int,
    channel_id: int,
    scenario_date: str,
    expires_at: str,
    scenario: dict,
) -> dict:
    db = await _connect()

    try:
        cursor = await db.execute(
            """
            INSERT INTO assessment_scenarios (
                guild_id,
                channel_id,
                scenario_date,
                scenario_type,
                status,
                title,
                dispatch_text,
                opening_scene,
                scenario_json,
                expires_at
            )

            VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                channel_id,
                scenario_date,
                scenario["scenario_type"],
                scenario["title"],
                scenario["dispatch_text"],
                scenario["opening_scene"],
                json.dumps(scenario),
                expires_at,
            ),
        )

        await db.commit()

        scenario_id = cursor.lastrowid

    except sqlite3.IntegrityError:
        await db.rollback()
        raise

    finally:
        await db.close()

    if scenario_id is None:
        raise RuntimeError(
            "Assessment scenario was created but no ID was returned."
        )

    return await get_assessment_scenario(
        scenario_id
    )


async def get_assessment_scenario(
    scenario_id: int,
) -> dict | None:
    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT *
            FROM assessment_scenarios
            WHERE id = ?
            """,
            (scenario_id,),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    return (
        _scenario_row(row)
        if row is not None
        else None
    )


async def get_active_assessment_scenario(
    guild_id: int,
) -> dict | None:
    now = datetime.now(
        timezone.utc
    ).isoformat()

    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT *
            FROM assessment_scenarios
            WHERE guild_id = ?
              AND status = 'active'
              AND expires_at > ?
            ORDER BY expires_at ASC
            LIMIT 1
            """,
            (guild_id, now),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    return (
        _scenario_row(row)
        if row is not None
        else None
    )


async def get_active_scenario_for_date(
    guild_id: int,
    scenario_date: str,
) -> dict | None:
    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT *
            FROM assessment_scenarios
            WHERE guild_id = ?
              AND scenario_date = ?
              AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
            """,
            (guild_id, scenario_date),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    return (
        _scenario_row(row)
        if row is not None
        else None
    )


async def set_assessment_message_id(
    scenario_id: int,
    message_id: int | None,
):
    db = await _connect()

    try:
        await db.execute(
            """
            UPDATE assessment_scenarios
            SET message_id = ?
            WHERE id = ?
            """,
            (message_id, scenario_id),
        )
        await db.commit()
    finally:
        await db.close()


async def supersede_assessment_scenario(
    scenario_id: int,
):
    db = await _connect()

    try:
        await db.execute(
            """
            UPDATE assessment_scenarios
            SET status = 'superseded',
                message_id = NULL
            WHERE id = ?
            """,
            (scenario_id,),
        )
        await db.commit()
    finally:
        await db.close()


async def get_expired_posted_assessment_scenarios(
    guild_id: int,
) -> list[dict]:
    now = datetime.now(
        timezone.utc
    ).isoformat()

    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT
                id,
                channel_id,
                message_id,
                scenario_date,
                expires_at
            FROM assessment_scenarios
            WHERE guild_id = ?
              AND message_id IS NOT NULL
              AND expires_at <= ?
            ORDER BY id DESC
            """,
            (guild_id, now),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    return [dict(row) for row in rows]


async def get_recent_assessment_views(
    limit: int,
) -> list[dict]:
    if limit <= 0:
        return []

    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT id, message_id
            FROM assessment_scenarios
            WHERE message_id IS NOT NULL
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    return [dict(row) for row in rows]


async def get_recent_scenario_types(
    guild_id: int,
    limit: int,
) -> list[str]:
    if limit <= 0:
        return []

    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT scenario_type
            FROM assessment_scenarios
            WHERE guild_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (guild_id, limit),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    return [
        str(row["scenario_type"])
        for row in rows
    ]


# ==================================================
# SESSIONS
# ==================================================


async def create_assessment_session(
    guild_id: int,
    user_id: int,
    username: str,
    scenario: dict,
) -> dict:
    now = datetime.now(
        timezone.utc
    ).isoformat()

    initial_state = {
        fact["key"]: {
            "value": fact["value"],
            "source": fact["source"],
        }
        for fact in scenario.get("facts", [])
    }

    db = await _connect()

    try:
        await db.execute(
            "BEGIN IMMEDIATE"
        )

        existing_cursor = await db.execute(
            """
            SELECT *
            FROM assessment_sessions
            WHERE guild_id = ?
              AND user_id = ?
              AND scenario_id = ?
              AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                guild_id,
                user_id,
                scenario["id"],
            ),
        )
        existing = await existing_cursor.fetchone()

        if existing is not None:
            await db.commit()
            return _session_row(existing)

        attempt_cursor = await db.execute(
            """
            SELECT COALESCE(MAX(attempt_number), 0)
            FROM assessment_sessions
            WHERE guild_id = ?
              AND user_id = ?
              AND scenario_id = ?
            """,
            (
                guild_id,
                user_id,
                scenario["id"],
            ),
        )
        attempt_row = await attempt_cursor.fetchone()
        attempt_number = int(attempt_row[0]) + 1

        cursor = await db.execute(
            """
            INSERT INTO assessment_sessions (
                guild_id,
                user_id,
                username,
                scenario_id,
                attempt_number,
                status,
                current_phase,
                patient_state_json,
                started_at,
                last_interaction_at
            )
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                username,
                scenario["id"],
                attempt_number,
                "scene_size_up",
                json.dumps(initial_state),
                now,
                now,
            ),
        )

        session_id = cursor.lastrowid
        await db.commit()

    except Exception:
        await db.rollback()
        raise

    finally:
        await db.close()

    if session_id is None:
        raise RuntimeError(
            "Assessment session was created but no ID was returned."
        )

    session = await get_assessment_session(
        session_id
    )

    if session is None:
        raise RuntimeError(
            "Assessment session could not be reloaded."
        )

    return session


async def get_assessment_session(
    session_id: int,
) -> dict | None:
    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT *
            FROM assessment_sessions
            WHERE id = ?
            """,
            (session_id,),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    return (
        _session_row(row)
        if row is not None
        else None
    )


async def get_active_assessment_session(
    guild_id: int,
    user_id: int,
    scenario_id: int,
) -> dict | None:
    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT *
            FROM assessment_sessions
            WHERE guild_id = ?
              AND user_id = ?
              AND scenario_id = ?
              AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                guild_id,
                user_id,
                scenario_id,
            ),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    return (
        _session_row(row)
        if row is not None
        else None
    )


async def get_latest_completed_assessment_session(
    guild_id: int,
    user_id: int,
    scenario_id: int,
) -> dict | None:
    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT *
            FROM assessment_sessions
            WHERE guild_id = ?
              AND user_id = ?
              AND scenario_id = ?
              AND status = 'completed'
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                guild_id,
                user_id,
                scenario_id,
            ),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    return (
        _session_row(row)
        if row is not None
        else None
    )


async def get_recent_completed_assessment_sessions(
    guild_id: int,
    user_id: int,
    limit: int = 5,
) -> list[dict]:
    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT *
            FROM assessment_sessions
            WHERE guild_id = ?
              AND user_id = ?
              AND status = 'completed'
            ORDER BY id DESC
            LIMIT ?
            """,
            (guild_id, user_id, limit),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    return [
        _session_row(row)
        for row in rows
    ]


async def count_active_sessions_for_scenario(
    scenario_id: int,
) -> int:
    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM assessment_sessions
            WHERE scenario_id = ?
              AND status = 'active'
            """,
            (scenario_id,),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    return int(row[0] or 0)


async def update_assessment_session_state(
    session_id: int,
    patient_state: dict,
    current_phase: str,
):
    now = datetime.now(
        timezone.utc
    ).isoformat()

    db = await _connect()

    try:
        await db.execute(
            """
            UPDATE assessment_sessions
            SET patient_state_json = ?,
                current_phase = ?,
                last_interaction_at = ?
            WHERE id = ?
            """,
            (
                json.dumps(patient_state),
                current_phase,
                now,
                session_id,
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def mark_transport_called(
    session_id: int,
    called_at: str,
):
    db = await _connect()

    try:
        await db.execute(
            """
            UPDATE assessment_sessions
            SET transport_called_at = COALESCE(
                    transport_called_at,
                    ?
                ),
                last_interaction_at = ?
            WHERE id = ?
            """,
            (called_at, called_at, session_id),
        )
        await db.commit()
    finally:
        await db.close()


# ==================================================
# TURNS
# ==================================================


async def append_assessment_turn(
    session_id: int,
    student_input: str,
    marty_response: str,
    response_role: str,
    elapsed_seconds: float,
) -> dict:
    now = datetime.now(
        timezone.utc
    ).isoformat()

    db = await _connect()

    try:
        await db.execute(
            "BEGIN IMMEDIATE"
        )

        cursor = await db.execute(
            """
            SELECT turn_number
            FROM assessment_sessions
            WHERE id = ?
              AND status = 'active'
            """,
            (session_id,),
        )
        row = await cursor.fetchone()

        if row is None:
            raise RuntimeError(
                "Assessment session is no longer active."
            )

        turn_number = int(
            row["turn_number"]
        ) + 1

        turn_cursor = await db.execute(
            """
            INSERT INTO assessment_turns (
                session_id,
                turn_number,
                student_input,
                marty_response,
                response_role,
                elapsed_seconds,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                turn_number,
                student_input,
                marty_response,
                response_role,
                elapsed_seconds,
                now,
            ),
        )

        await db.execute(
            """
            UPDATE assessment_sessions
            SET turn_number = ?,
                last_interaction_at = ?
            WHERE id = ?
            """,
            (turn_number, now, session_id),
        )

        await db.commit()

        turn_id = turn_cursor.lastrowid

    except Exception:
        await db.rollback()
        raise

    finally:
        await db.close()

    return {
        "id": turn_id,
        "session_id": session_id,
        "turn_number": turn_number,
        "student_input": student_input,
        "marty_response": marty_response,
        "response_role": response_role,
        "elapsed_seconds": elapsed_seconds,
        "created_at": now,
    }


async def get_recent_assessment_turns(
    session_id: int,
    limit: int,
) -> list[dict]:
    if limit <= 0:
        return []

    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT *
            FROM assessment_turns
            WHERE session_id = ?
            ORDER BY turn_number DESC
            LIMIT ?
            """,
            (session_id, limit),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    result = [dict(row) for row in rows]
    result.reverse()
    return result


# ==================================================
# RUBRIC EVENTS
# ==================================================


async def award_rubric_item(
    session_id: int,
    rubric_key: str,
    points: float,
    max_points: float,
    evidence_turn_id: int | None,
    grader_reason: str,
) -> bool:
    db = await _connect()

    try:
        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO assessment_rubric_events (
                session_id,
                rubric_key,
                points,
                max_points,
                evidence_turn_id,
                grader_reason
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                rubric_key,
                points,
                max_points,
                evidence_turn_id,
                grader_reason,
            ),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def get_earned_rubric_events(
    session_id: int,
) -> list[dict]:
    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT *
            FROM assessment_rubric_events
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    return [dict(row) for row in rows]


async def get_earned_rubric_keys(
    session_id: int,
) -> set[str]:
    events = await get_earned_rubric_events(
        session_id
    )

    return {
        str(event["rubric_key"])
        for event in events
    }


# ==================================================
# CRITICAL FAILS
# ==================================================


async def add_critical_fail(
    session_id: int,
    critical_fail_key: str,
    description: str,
    evidence_turn_id: int | None = None,
) -> bool:
    db = await _connect()

    try:
        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO assessment_critical_fails (
                session_id,
                critical_fail_key,
                description,
                evidence_turn_id
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                session_id,
                critical_fail_key,
                description,
                evidence_turn_id,
            ),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def get_critical_fails(
    session_id: int,
) -> list[dict]:
    db = await _connect()

    try:
        cursor = await db.execute(
            """
            SELECT *
            FROM assessment_critical_fails
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    return [dict(row) for row in rows]


# ==================================================
# LLM USAGE
# ==================================================


async def record_assessment_llm_usage(
    purpose: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    scenario_id: int | None = None,
    session_id: int | None = None,
    turn_id: int | None = None,
):
    db = await _connect()

    try:
        await db.execute(
            """
            INSERT INTO assessment_llm_usage (
                scenario_id,
                session_id,
                turn_id,
                purpose,
                model,
                input_tokens,
                output_tokens,
                total_tokens
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scenario_id,
                session_id,
                turn_id,
                purpose,
                model,
                input_tokens,
                output_tokens,
                total_tokens,
            ),
        )
        await db.commit()
    finally:
        await db.close()


# ==================================================
# FINALIZE
# ==================================================


async def complete_assessment_session(
    session_id: int,
    raw_points: float,
    max_points: float,
    critical_fail_count: int,
    critical_fail_deduction: float,
    final_points: float,
    final_percent: float,
):
    now = datetime.now(
        timezone.utc
    ).isoformat()

    db = await _connect()

    try:
        await db.execute(
            """
            UPDATE assessment_sessions
            SET status = 'completed',
                ended_at = ?,
                last_interaction_at = ?,
                final_raw_points = ?,
                final_max_points = ?,
                critical_fail_count = ?,
                critical_fail_deduction = ?,
                final_points = ?,
                final_percent = ?
            WHERE id = ?
              AND status = 'active'
            """,
            (
                now,
                now,
                raw_points,
                max_points,
                critical_fail_count,
                critical_fail_deduction,
                final_points,
                final_percent,
                session_id,
            ),
        )
        await db.commit()
    finally:
        await db.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        init_patient_assessment_db()
    )

    print(
        "M.A.R.T.Y. patient assessment database initialized at: "
        f"{PATIENT_ASSESSMENT_DB_PATH}"
    )
