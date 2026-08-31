from datetime import (
    datetime,
    timezone,
)

import discord

from questions.q_attempts import (
    record_question_attempt,
)

from questions.q_flag_ui import (
    open_question_flag_modal,
)

from points.mechanics.question_of_the_day.qotd import (
    submit_qotd_answer,
)

from points.mechanics.question_of_the_day.qotd_questions import (
    get_qotd,
)

from points.mechanics.question_of_the_day.qotd_completions import (
    has_completed_qotd,
)

from points.mechanics.question_of_the_day.qotd_config import (
    QOTD_ANSWER_MAX_LENGTH,
)

from points.mechanics.question_of_the_day.qotd_display import (
    build_qotd_correct_embed,
    build_qotd_incorrect_embed,
    build_qotd_uncertain_embed,
    build_qotd_completed_embed,
    build_qotd_expired_embed,
    build_qotd_unavailable_embed,
)

from points.progressions.levels.level_up_display import (
    build_level_up_embed,
)

from points.progressions.ranks.rank_up_display import (
    build_rank_up_embed,
)


# ==================================================
# QOTD CONTEXT KEY
# ==================================================


def build_qotd_context_key(
    qotd_id: int,
) -> str:

    return (
        f"qotd:{qotd_id}"
    )


# ==================================================
# QOTD OPEN / CLOSED
# ==================================================


def _qotd_is_open(
    expires_at: str,
) -> bool:

    expiration = (
        datetime.fromisoformat(
            expires_at
        )
    )

    if expiration.tzinfo is None:

        expiration = (
            expiration.replace(
                tzinfo=timezone.utc
            )
        )

    return (
        datetime.now(
            timezone.utc
        )
        < expiration
    )


# ==================================================
# ANSWER MODAL
# ==================================================


class QotdAnswerModal(
    discord.ui.Modal
):

    def __init__(
        self,
        qotd_id: int,
    ):

        super().__init__(
            title="Question of the Day"
        )

        self.qotd_id = (
            qotd_id
        )

        self.answer_input = (
            discord.ui.TextInput(
                label="Your Answer",
                placeholder=(
                    "Enter your answer here..."
                ),
                style=(
                    discord.TextStyle.paragraph
                ),
                required=True,
                max_length=(
                    QOTD_ANSWER_MAX_LENGTH
                ),
            )
        )

        self.add_item(
            self.answer_input
        )


    # ==================================================
    # SUBMIT ANSWER
    # ==================================================


    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )


        # ==================================================
        # SERVER CHECK
        # ==================================================


        if interaction.guild is None:

            await interaction.followup.send(
                (
                    "This question can only "
                    "be answered in the server."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # ANSWER
        # ==================================================


        submitted_answer = str(
            self.answer_input.value
        )


        # ==================================================
        # GET QOTD
        # ==================================================


        qotd = await get_qotd(
            self.qotd_id
        )


        # ==================================================
        # SUBMIT
        # ==================================================


        try:

            result = (
                await submit_qotd_answer(
                    qotd_id=(
                        self.qotd_id
                    ),
                    guild_id=(
                        interaction.guild.id
                    ),
                    user_id=(
                        interaction.user.id
                    ),
                    username=(
                        interaction.user.display_name
                    ),
                    submitted_answer=(
                        submitted_answer
                    ),
                )
            )

        except Exception as error:

            print(
                "QoTD submission error: "
                f"{error!r}"
            )

            await interaction.followup.send(
                (
                    "⚠️ Something went wrong while "
                    "processing your answer. "
                    "Please try again."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # STATUS
        # ==================================================


        status = (
            result["status"]
        )


        # ==================================================
        # RECORD ATTEMPT
        # ==================================================


        if (
            status in {
                "correct",
                "incorrect",
                "uncertain",
            }
            and qotd is not None
            and qotd.get(
                "question_bank_id"
            ) is not None
        ):

            try:

                await record_question_attempt(
                    guild_id=(
                        interaction.guild.id
                    ),
                    user_id=(
                        interaction.user.id
                    ),
                    question_bank_id=(
                        qotd[
                            "question_bank_id"
                        ]
                    ),
                    context_key=(
                        build_qotd_context_key(
                            self.qotd_id
                        )
                    ),
                    answer_text=(
                        submitted_answer
                    ),
                    result=status,
                )

            except Exception as error:

                print(
                    "QoTD attempt recording error: "
                    f"{error!r}"
                )


        # ==================================================
        # NOT FOUND
        # ==================================================


        if status == "not_found":

            await interaction.followup.send(
                embed=(
                    build_qotd_unavailable_embed()
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # EXPIRED
        # ==================================================


        if status == "expired":

            await interaction.followup.send(
                embed=(
                    build_qotd_expired_embed()
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # ALREADY COMPLETED
        # ==================================================


        if status == "already_completed":

            await interaction.followup.send(
                embed=(
                    build_qotd_completed_embed()
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # UNCERTAIN
        # ==================================================


        if status == "uncertain":

            await interaction.followup.send(
                embed=(
                    build_qotd_uncertain_embed(
                        submitted_answer=(
                            submitted_answer
                        ),
                    )
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # INCORRECT
        # ==================================================


        if status == "incorrect":

            await interaction.followup.send(
                embed=(
                    build_qotd_incorrect_embed(
                        submitted_answer=(
                            submitted_answer
                        ),
                    )
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # UNKNOWN STATUS
        # ==================================================


        if status != "correct":

            raise RuntimeError(
                "Unknown QoTD result status: "
                f"{status}"
            )


        # ==================================================
        # CORRECT
        # ==================================================


        await interaction.followup.send(
            embed=(
                build_qotd_correct_embed(
                    accepted_answers=(
                        result[
                            "accepted_answers"
                        ]
                    ),
                    submitted_answer=(
                        result[
                            "submitted_answer"
                        ]
                    ),
                    base_points=(
                        result[
                            "base_points"
                        ]
                    ),
                    streak_bonus=(
                        result[
                            "streak_bonus"
                        ]
                    ),
                    streak_days=(
                        result[
                            "streak_days"
                        ]
                    ),
                    explanation=(
                        result[
                            "explanation"
                        ]
                    ),
                )
            ),
            ephemeral=True,
        )


        # ==================================================
        # PROGRESSION
        # ==================================================


        progression = (
            result.get(
                "progression",
                {},
            )
        )


        # ==================================================
        # LEVEL UP
        # ==================================================


        if progression.get(
            "leveled_up",
            False,
        ):

            level_up_embed = (
                build_level_up_embed(
                    old_level=(
                        progression[
                            "old_level"
                        ]
                    ),
                    new_level=(
                        progression[
                            "new_level"
                        ]
                    ),
                )
            )

            await interaction.followup.send(
                embed=level_up_embed,
                ephemeral=True,
            )


        # ==================================================
        # RANK UP
        # ==================================================


        if progression.get(
            "ranked_up",
            False,
        ):

            rank_up_embed = (
                build_rank_up_embed(
                    username=(
                        interaction.user.display_name
                    ),
                    new_rank=(
                        progression[
                            "new_rank"
                        ]
                    ),
                    new_level=(
                        progression[
                            "new_level"
                        ]
                    ),
                )
            )

            await interaction.followup.send(
                embed=rank_up_embed,
                ephemeral=True,
            )


# ==================================================
# PERSISTENT QOTD VIEW
# ==================================================


class QotdAnswerView(
    discord.ui.View
):

    def __init__(
        self,
        qotd_id: int,
    ):

        super().__init__(
            timeout=None
        )

        self.qotd_id = (
            qotd_id
        )


        # ==================================================
        # ANSWER BUTTON
        # ==================================================


        answer_button = (
            discord.ui.Button(
                label="Answer Question",
                style=(
                    discord.ButtonStyle.primary
                ),
                emoji="✏️",
                custom_id=(
                    f"qotd:answer:"
                    f"{qotd_id}"
                ),
            )
        )

        answer_button.callback = (
            self.answer_button
        )

        self.add_item(
            answer_button
        )


        # ==================================================
        # FLAG BUTTON
        # ==================================================


        flag_button = (
            discord.ui.Button(
                label="Flag Question",
                style=(
                    discord.ButtonStyle.secondary
                ),
                emoji="🚩",
                custom_id=(
                    f"qotd:flag:"
                    f"{qotd_id}"
                ),
            )
        )

        flag_button.callback = (
            self.flag_button
        )

        self.add_item(
            flag_button
        )


    # ==================================================
    # ANSWER BUTTON
    # ==================================================


    async def answer_button(
        self,
        interaction: discord.Interaction,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                (
                    "This question can only "
                    "be answered in the server."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # GET QOTD
        # ==================================================


        qotd = await get_qotd(
            self.qotd_id
        )

        if qotd is None:

            await interaction.response.send_message(
                embed=(
                    build_qotd_unavailable_embed()
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # VERIFY SERVER
        # ==================================================


        if (
            qotd["guild_id"]
            != interaction.guild.id
        ):

            await interaction.response.send_message(
                embed=(
                    build_qotd_unavailable_embed()
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # VERIFY OPEN
        # ==================================================


        if not _qotd_is_open(
            qotd["expires_at"]
        ):

            await interaction.response.send_message(
                embed=(
                    build_qotd_expired_embed()
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # COMPLETION
        # ==================================================


        if await has_completed_qotd(
            qotd_id=(
                self.qotd_id
            ),
            user_id=(
                interaction.user.id
            ),
        ):

            await interaction.response.send_message(
                embed=(
                    build_qotd_completed_embed()
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # OPEN ANSWER MODAL
        # ==================================================


        await interaction.response.send_modal(
            QotdAnswerModal(
                qotd_id=(
                    self.qotd_id
                )
            )
        )


    # ==================================================
    # FLAG BUTTON
    # ==================================================


    async def flag_button(
        self,
        interaction: discord.Interaction,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                (
                    "Questions can only be flagged "
                    "inside the server."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # GET QOTD
        # ==================================================


        qotd = await get_qotd(
            self.qotd_id
        )

        if qotd is None:

            await interaction.response.send_message(
                embed=(
                    build_qotd_unavailable_embed()
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # VERIFY SERVER
        # ==================================================


        if (
            qotd["guild_id"]
            != interaction.guild.id
        ):

            await interaction.response.send_message(
                embed=(
                    build_qotd_unavailable_embed()
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # QUESTION BANK ID
        # ==================================================


        question_bank_id = (
            qotd.get(
                "question_bank_id"
            )
        )

        if question_bank_id is None:

            await interaction.response.send_message(
                (
                    "⚠️ This Question of the Day "
                    "does not have a question-bank "
                    "ID and cannot be flagged."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # GENERIC FLAG ENTRY POINT
        # ==================================================


        await open_question_flag_modal(
            interaction=interaction,
            question_bank_id=(
                question_bank_id
            ),
            context_key=(
                build_qotd_context_key(
                    self.qotd_id
                )
            ),
        )