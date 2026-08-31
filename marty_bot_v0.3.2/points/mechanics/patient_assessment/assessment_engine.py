from datetime import (
    datetime,
    timezone,
)

import discord

from data.patient_assessment_db import (
    get_active_assessment_scenario,
    get_active_assessment_session,
    get_assessment_scenario,
    get_latest_completed_assessment_session,
)
from points.mechanics.patient_assessment.assessment_config import (
    ASSESSMENT_INPUT_MAX_LENGTH,
)
from points.mechanics.patient_assessment.assessment_display import (
    build_assessment_completed_status_embed,
    build_assessment_preview_embed,
    build_assessment_result_embed,
    build_assessment_session_embed,
)
from points.mechanics.patient_assessment.assessment_engine import (
    build_assessment_result,
    finalize_assessment_session,
    process_assessment_turn,
    start_assessment_session,
)


# ==================================================
# HELPERS
# ==================================================


def _scenario_is_open(
    scenario: dict,
) -> bool:
    expiration = datetime.fromisoformat(
        scenario["expires_at"]
    )

    if expiration.tzinfo is None:
        expiration = expiration.replace(
            tzinfo=timezone.utc
        )

    return (
        scenario.get("status") == "active"
        and datetime.now(timezone.utc)
        < expiration.astimezone(timezone.utc)
    )


async def _wrong_user(
    interaction: discord.Interaction,
    user_id: int,
) -> bool:
    if interaction.user.id == user_id:
        return False

    if interaction.response.is_done():
        await interaction.followup.send(
            "This private assessment control belongs to another user.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "This private assessment control belongs to another user.",
            ephemeral=True,
        )

    return True


# ==================================================
# ENTRY POINT
# ==================================================


async def open_assessment_entry(
    interaction: discord.Interaction,
    scenario_id: int | None = None,
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "Patient assessments can only be used in the server.",
            ephemeral=True,
        )
        return

    if scenario_id is None:
        scenario = (
            await get_active_assessment_scenario(
                interaction.guild.id
            )
        )
    else:
        scenario = await get_assessment_scenario(
            scenario_id
        )

    if scenario is None:
        await interaction.response.send_message(
            "There is no patient assessment available right now.",
            ephemeral=True,
        )
        return

    if scenario["guild_id"] != interaction.guild.id:
        await interaction.response.send_message(
            "That patient assessment is not available in this server.",
            ephemeral=True,
        )
        return

    if not _scenario_is_open(scenario):
        await interaction.response.send_message(
            "That patient assessment has closed. Use `/assessment` for the current assessment.",
            ephemeral=True,
        )
        return

    active_session = (
        await get_active_assessment_session(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            scenario_id=scenario["id"],
        )
    )

    if active_session is not None:
        await interaction.response.send_message(
            embed=build_assessment_session_embed(
                session=active_session,
                scenario=scenario,
                marty_text=(
                    "Your saved assessment is still in progress. "
                    "Continue from where you left off."
                ),
                response_role="proctor",
            ),
            view=AssessmentSessionView(
                session_id=active_session["id"],
                user_id=interaction.user.id,
            ),
            ephemeral=True,
        )
        return

    completed = (
        await get_latest_completed_assessment_session(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            scenario_id=scenario["id"],
        )
    )

    if completed is not None:
        await interaction.response.send_message(
            embed=build_assessment_completed_status_embed(
                session=completed,
                scenario=scenario,
            ),
            view=CompletedAssessmentView(
                user_id=interaction.user.id,
                scenario_id=scenario["id"],
                completed_session_id=completed["id"],
            ),
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        embed=build_assessment_preview_embed(
            scenario
        ),
        view=AssessmentStartView(
            scenario_id=scenario["id"],
            user_id=interaction.user.id,
        ),
        ephemeral=True,
    )


# ==================================================
# PUBLIC PERSISTENT VIEW
# ==================================================


class AssessmentPublicView(
    discord.ui.View
):
    def __init__(
        self,
        scenario_id: int,
    ):
        super().__init__(
            timeout=None
        )

        self.scenario_id = scenario_id

        button = discord.ui.Button(
            label="Begin / Resume Assessment",
            style=discord.ButtonStyle.primary,
            emoji="🩺",
            custom_id=(
                "assessment:begin:"
                f"{scenario_id}"
            ),
        )

        button.callback = self.begin_button
        self.add_item(button)

    async def begin_button(
        self,
        interaction: discord.Interaction,
    ):
        await open_assessment_entry(
            interaction=interaction,
            scenario_id=self.scenario_id,
        )


# ==================================================
# START VIEW
# ==================================================


class AssessmentStartView(
    discord.ui.View
):
    def __init__(
        self,
        scenario_id: int,
        user_id: int,
    ):
        super().__init__(
            timeout=900
        )

        self.scenario_id = scenario_id
        self.user_id = user_id

    @discord.ui.button(
        label="Start Assessment",
        style=discord.ButtonStyle.success,
        emoji="▶️",
    )
    async def start_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if await _wrong_user(
            interaction,
            self.user_id,
        ):
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                "This assessment must be started in the server.",
                ephemeral=True,
            )
            return

        scenario = await get_assessment_scenario(
            self.scenario_id
        )

        if (
            scenario is None
            or not _scenario_is_open(scenario)
        ):
            await interaction.response.send_message(
                "This assessment is no longer available.",
                ephemeral=True,
            )
            return

        session = await start_assessment_session(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            scenario_id=self.scenario_id,
        )

        await interaction.response.send_message(
            embed=build_assessment_session_embed(
                session=session,
                scenario=scenario,
                marty_text=scenario["opening_scene"],
                response_role="proctor",
            ),
            view=AssessmentSessionView(
                session_id=session["id"],
                user_id=self.user_id,
            ),
            ephemeral=True,
        )


# ==================================================
# ACTIVE SESSION VIEW
# ==================================================


class AssessmentSessionView(
    discord.ui.View
):
    def __init__(
        self,
        session_id: int,
        user_id: int,
    ):
        super().__init__(
            timeout=900
        )

        self.session_id = session_id
        self.user_id = user_id

    @discord.ui.button(
        label="Speak / Take Action",
        style=discord.ButtonStyle.primary,
        emoji="✏️",
    )
    async def action_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if await _wrong_user(
            interaction,
            self.user_id,
        ):
            return

        await interaction.response.send_modal(
            AssessmentActionModal(
                session_id=self.session_id,
                user_id=self.user_id,
            )
        )

    @discord.ui.button(
        label="End Assessment",
        style=discord.ButtonStyle.danger,
        emoji="⏹️",
    )
    async def end_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if await _wrong_user(
            interaction,
            self.user_id,
        ):
            return

        await interaction.response.send_message(
            (
                "End this assessment and calculate your final score? "
                "You cannot add more actions to this attempt afterward."
            ),
            view=AssessmentEndConfirmationView(
                session_id=self.session_id,
                user_id=self.user_id,
            ),
            ephemeral=True,
        )


# ==================================================
# ACTION MODAL
# ==================================================


class AssessmentActionModal(
    discord.ui.Modal
):
    def __init__(
        self,
        session_id: int,
        user_id: int,
    ):
        super().__init__(
            title="Patient Assessment"
        )

        self.session_id = session_id
        self.user_id = user_id

        self.action_input = discord.ui.TextInput(
            label="What do you say or do?",
            placeholder=(
                "Example: BSI, scene safe. I determine the number "
                "of patients and approach the patient..."
            ),
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=ASSESSMENT_INPUT_MAX_LENGTH,
        )

        self.add_item(
            self.action_input
        )

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        if await _wrong_user(
            interaction,
            self.user_id,
        ):
            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        student_input = str(
            self.action_input.value
        ).strip()

        try:
            result = await process_assessment_turn(
                session_id=self.session_id,
                user_id=interaction.user.id,
                student_input=student_input,
            )

        except Exception as error:
            print(
                "Patient assessment turn error: "
                f"{error!r}"
            )

            await interaction.followup.send(
                (
                    "⚠️ MARTY could not process that assessment "
                    "turn. Your previous saved progress is intact. "
                    "Please try again."
                ),
                ephemeral=True,
            )
            return

        turn_result = result[
            "turn_result"
        ]

        await interaction.followup.send(
            embed=build_assessment_session_embed(
                session=result["session"],
                scenario=result["scenario"],
                marty_text=(
                    turn_result["response_text"]
                ),
                response_role=(
                    turn_result["response_role"]
                ),
            ),
            view=AssessmentSessionView(
                session_id=self.session_id,
                user_id=self.user_id,
            ),
            ephemeral=True,
        )


# ==================================================
# END CONFIRMATION
# ==================================================


class AssessmentEndConfirmationView(
    discord.ui.View
):
    def __init__(
        self,
        session_id: int,
        user_id: int,
    ):
        super().__init__(
            timeout=300
        )

        self.session_id = session_id
        self.user_id = user_id

    @discord.ui.button(
        label="End and Grade",
        style=discord.ButtonStyle.danger,
    )
    async def confirm_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if await _wrong_user(
            interaction,
            self.user_id,
        ):
            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        try:
            result = await finalize_assessment_session(
                session_id=self.session_id,
                user_id=interaction.user.id,
            )

        except Exception as error:
            print(
                "Patient assessment finalization error: "
                f"{error!r}"
            )

            await interaction.followup.send(
                "⚠️ MARTY could not finalize this assessment. Please try again.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            embed=build_assessment_result_embed(
                result
            ),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Continue Assessment",
        style=discord.ButtonStyle.secondary,
    )
    async def continue_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if await _wrong_user(
            interaction,
            self.user_id,
        ):
            return

        await interaction.response.send_message(
            "Assessment continues. Use your saved assessment controls to submit the next action.",
            ephemeral=True,
        )


# ==================================================
# COMPLETED VIEW
# ==================================================


class CompletedAssessmentView(
    discord.ui.View
):
    def __init__(
        self,
        user_id: int,
        scenario_id: int,
        completed_session_id: int,
    ):
        super().__init__(
            timeout=900
        )

        self.user_id = user_id
        self.scenario_id = scenario_id
        self.completed_session_id = (
            completed_session_id
        )

    @discord.ui.button(
        label="Review Score",
        style=discord.ButtonStyle.secondary,
        emoji="📋",
    )
    async def review_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if await _wrong_user(
            interaction,
            self.user_id,
        ):
            return

        result = await build_assessment_result(
            self.completed_session_id
        )

        await interaction.response.send_message(
            embed=build_assessment_result_embed(
                result
            ),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Start New Attempt",
        style=discord.ButtonStyle.success,
        emoji="🔁",
    )
    async def retry_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if await _wrong_user(
            interaction,
            self.user_id,
        ):
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                "This assessment must be used in the server.",
                ephemeral=True,
            )
            return

        scenario = await get_assessment_scenario(
            self.scenario_id
        )

        if (
            scenario is None
            or not _scenario_is_open(scenario)
        ):
            await interaction.response.send_message(
                "This daily assessment has closed.",
                ephemeral=True,
            )
            return

        session = await start_assessment_session(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            scenario_id=self.scenario_id,
        )

        await interaction.response.send_message(
            embed=build_assessment_session_embed(
                session=session,
                scenario=scenario,
                marty_text=scenario["opening_scene"],
                response_role="proctor",
            ),
            view=AssessmentSessionView(
                session_id=session["id"],
                user_id=self.user_id,
            ),
            ephemeral=True,
        )
