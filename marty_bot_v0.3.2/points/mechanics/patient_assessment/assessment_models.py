from datetime import datetime

import discord

from points.mechanics.patient_assessment.assessment_engine import (
    get_session_elapsed_seconds,
)


SCENARIO_TYPE_NAMES = {
    "respiratory": "Respiratory",
    "cardiac": "Cardiac",
    "neurological": "Neurological",
    "anaphylaxis": "Anaphylaxis",
    "acute_abdomen": "Acute Abdomen",
    "ob_labor": "OB in Labor",
    "trauma": "Trauma",
    "airway": "Airway Management",
}


def _format_date(
    value: str,
) -> str:
    try:
        parsed = datetime.fromisoformat(
            value
        )
        return parsed.strftime(
            "%m/%d/%Y"
        )
    except ValueError:
        return value


def format_elapsed(
    seconds: float,
) -> str:
    total = max(
        0,
        int(seconds),
    )

    minutes, seconds = divmod(
        total,
        60,
    )

    return (
        f"{minutes:02d}:"
        f"{seconds:02d}"
    )


# ==================================================
# PUBLIC CARD
# ==================================================


def build_assessment_public_embed(
    scenario: dict,
    closed: bool = False,
) -> discord.Embed:
    title_prefix = (
        "🔒 Patient Assessment of the Day"
        if closed
        else "🩺 Patient Assessment of the Day"
    )

    embed = discord.Embed(
        title=(
            f"{title_prefix} "
            f"[{scenario['scenario_date']}]"
        ),
        description=(
            "**Dispatch**\n"
            f"{scenario['dispatch_text']}\n\n"
            "Practice a full EMT patient assessment with "
            "M.A.R.T.Y. acting as your proctor and patient.\n\n"
            "Your assessment is private. Other students in "
            "the channel cannot see your responses."
        ),
        color=discord.Color.blurple(),
    )

    embed.set_footer(
        text=(
            "This assessment is closed. Use /assessment for today's scenario."
            if closed
            else (
                "Click Begin / Resume Assessment. "
                "Your progress is saved if the private message disappears."
            )
        )
    )

    return embed


# ==================================================
# PREVIEW
# ==================================================


def build_assessment_preview_embed(
    scenario: dict,
) -> discord.Embed:
    embed = discord.Embed(
        title="🩺 Patient Assessment",
        description=(
            "**Dispatch**\n"
            f"{scenario['dispatch_text']}\n\n"
            "Press **Start Assessment** when you are ready. "
            "The practical timer begins when you press Start."
        ),
        color=discord.Color.blurple(),
    )

    embed.set_footer(
        text=(
            "Use Speak / Take Action to tell MARTY everything "
            "you say, ask, assess, or do."
        )
    )

    return embed


# ==================================================
# SESSION OPENING / RESUME
# ==================================================


def build_assessment_session_embed(
    session: dict,
    scenario: dict,
    marty_text: str | None = None,
    response_role: str = "proctor",
) -> discord.Embed:
    elapsed = get_session_elapsed_seconds(
        session
    )

    role_names = {
        "patient": "Patient",
        "proctor": "MARTY — Proctor",
        "monitor": "Monitor",
        "dispatch": "Dispatch",
        "mixed": "MARTY / Patient",
    }

    if marty_text is None:
        marty_text = scenario[
            "opening_scene"
        ]

    role_name = role_names.get(
        response_role,
        "MARTY",
    )

    embed = discord.Embed(
        title="🩺 Patient Assessment in Progress",
        description=(
            f"⏱ **Elapsed:** {format_elapsed(elapsed)}\n"
            f"**Attempt:** #{session['attempt_number']}\n\n"
            f"**{role_name}:**\n"
            f"{marty_text}"
        ),
        color=discord.Color.blurple(),
    )

    embed.set_footer(
        text=(
            "MARTY will not coach you during the assessment. "
            "Your rubric score is revealed when you end the attempt."
        )
    )

    return embed


# ==================================================
# COMPLETED STATUS
# ==================================================


def build_assessment_completed_status_embed(
    session: dict,
    scenario: dict,
) -> discord.Embed:
    percent = float(
        session.get("final_percent")
        or 0.0
    )

    embed = discord.Embed(
        title="✅ Assessment Completed",
        description=(
            "You already completed today's assessment.\n\n"
            f"**Final Score:** {percent:.1f}%\n"
            f"**Attempt:** #{session['attempt_number']}\n\n"
            "You can review this result or start another "
            "practice attempt on the same patient."
        ),
        color=discord.Color.green(),
    )

    return embed


# ==================================================
# FINAL SCORE
# ==================================================


def build_assessment_result_embed(
    result: dict,
) -> discord.Embed:
    session = result["session"]
    scenario = result["scenario"]

    raw_points = float(
        session["final_raw_points"]
        or 0.0
    )
    max_points = float(
        session["final_max_points"]
        or 0.0
    )
    final_points = float(
        session["final_points"]
        or 0.0
    )
    final_percent = float(
        session["final_percent"]
        or 0.0
    )
    deduction = float(
        session["critical_fail_deduction"]
        or 0.0
    )

    embed = discord.Embed(
        title="🩺 Patient Assessment Complete",
        description=(
            f"**Final Score:** {final_points:.1f} / "
            f"{max_points:.1f} (**{final_percent:.1f}%**)\n"
            f"**Rubric Points Earned Before Critical Fails:** "
            f"{raw_points:.1f} / {max_points:.1f}\n"
            f"**Critical-Fail Deduction:** -{deduction:.1f}\n\n"
            f"**Field Impression / Scenario:** "
            f"{scenario['field_impression']}"
        ),
        color=(
            discord.Color.green()
            if final_percent >= 80
            else discord.Color.orange()
        ),
    )

    # Keep the embed within Discord's 25-field limit.
    section_items = list(
        result["section_scores"].items()
    )

    for section, score in section_items[:18]:
        embed.add_field(
            name=section,
            value=(
                f"**{score['earned']:.0f} / "
                f"{score['max']:.0f}**"
            ),
            inline=True,
        )

    critical_fails = result[
        "critical_fails"
    ]

    if critical_fails:
        critical_text = "\n".join(
            f"• {failure['description']}"
            for failure in critical_fails[:6]
        )

        if len(critical_fails) > 6:
            critical_text += (
                f"\n• ...and {len(critical_fails) - 6} more"
            )

        embed.add_field(
            name=(
                "🚨 Critical Fails "
                f"({len(critical_fails)})"
            ),
            value=critical_text[:1024],
            inline=False,
        )
    else:
        embed.add_field(
            name="🚨 Critical Fails",
            value="None",
            inline=False,
        )

    missed = result["missed_items"]

    if missed:
        missed_text = "\n".join(
            f"• {item['label']}"
            for item in missed[:10]
        )

        if len(missed) > 10:
            missed_text += (
                f"\n• ...and {len(missed) - 10} more"
            )

        embed.add_field(
            name="Missed Rubric Items",
            value=missed_text[:1024],
            inline=False,
        )

    embed.set_footer(
        text=(
            "Each critical fail deducts 20% of the total "
            "applicable rubric value."
        )
    )

    return embed


# ==================================================
# HISTORY
# ==================================================


def build_assessment_history_embed(
    sessions: list[dict],
) -> discord.Embed:
    embed = discord.Embed(
        title="🩺 Your Recent Patient Assessments",
        color=discord.Color.blurple(),
    )

    if not sessions:
        embed.description = (
            "You have not completed a patient assessment yet."
        )
        return embed

    lines = []

    for session in sessions:
        percent = float(
            session.get("final_percent")
            or 0.0
        )

        lines.append(
            f"• Session #{session['id']} — "
            f"Attempt #{session['attempt_number']} — "
            f"**{percent:.1f}%**"
        )

    embed.description = "\n".join(lines)

    return embed
