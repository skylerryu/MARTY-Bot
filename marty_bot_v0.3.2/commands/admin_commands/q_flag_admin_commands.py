from datetime import (
    datetime,
    timezone,
)

import discord

from discord import (
    app_commands,
)

from commands.command_helpers import (
    make_command,
)

from questions.q_manager import (
    CATEGORY_NAMES,
    get_question_by_id,
    update_question,
)

from questions.q_flag import (
    QuestionFlagNotFoundError,
    dismiss_question_flag,
    get_open_flagged_question_ids,
    get_open_question_flag_summary,
    get_open_flags_for_question,
)

from questions.q_edit_queue import (
    get_questions_needing_edit,
    mark_question_for_edit_from_flag,
    resolve_question_edit,
)


# ==================================================
# DISPLAY HELPERS
# ==================================================


def _truncate(
    text: str,
    limit: int,
) -> str:

    text = str(text)

    if len(text) <= limit:
        return text

    return (
        text[:limit - 3]
        + "..."
    )


def _quote(
    text: str,
) -> str:

    text = str(
        text
    ).strip()

    if not text:
        return "> None"

    return "\n".join(
        f"> {line}"
        for line in text.splitlines()
    )


def _answers_display(
    answers: list[str],
) -> str:

    if not answers:
        return "No accepted answer recorded."

    if len(answers) == 1:
        return answers[0]

    return "\n".join(
        f"• {answer}"
        for answer in answers
    )


def _user_answers_display(
    answers: list[str],
) -> str:

    if not answers:
        return "> No answer attempts recorded."

    return "\n".join(
        _quote(
            _truncate(
                answer,
                600,
            )
        )
        for answer in answers[:3]
    )


def _timestamp(
    created_at: str | None,
) -> str:

    if not created_at:
        return "Unknown time"

    value = str(
        created_at
    ).strip()

    if value.endswith("Z"):

        value = (
            value[:-1]
            + "+00:00"
        )

    try:

        parsed = (
            datetime.fromisoformat(
                value
            )
        )

    except ValueError:

        try:

            parsed = (
                datetime.strptime(
                    value,
                    "%Y-%m-%d %H:%M:%S",
                )
            )

        except ValueError:

            return value

    if parsed.tzinfo is None:

        parsed = (
            parsed.replace(
                tzinfo=timezone.utc
            )
        )

    unix = int(
        parsed.timestamp()
    )

    return (
        f"<t:{unix}:f>"
    )


def _parse_answers(
    text: str,
) -> list[str]:

    return [
        answer.strip()
        for answer in text.split("|")
        if answer.strip()
    ]


# ==================================================
# PAGE PICKER
# ==================================================


class PagePickerModal(
    discord.ui.Modal
):

    def __init__(
        self,
        browser,
    ):

        super().__init__(
            title="Go to Page"
        )

        self.browser = (
            browser
        )

        self.page_input = discord.ui.TextInput(
            label="Page Number",
            placeholder="Enter a page number",
            required=True,
            max_length=6,
        )

        self.add_item(
            self.page_input
        )


    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):

        if (
            interaction.user.id
            != self.browser.owner_id
        ):

            await interaction.response.send_message(
                "This menu belongs to another administrator.",
                ephemeral=True,
            )

            return

        try:

            requested = int(
                str(
                    self.page_input.value
                )
            )

        except ValueError:

            await interaction.response.send_message(
                "Enter a valid page number.",
                ephemeral=True,
            )

            return

        count = (
            await self.browser
            .get_page_count()
        )

        if (
            requested < 1
            or requested > count
        ):

            await interaction.response.send_message(
                (
                    f"Enter a page from "
                    f"1 to {count}."
                ),
                ephemeral=True,
            )

            return

        self.browser.page = (
            requested - 1
        )

        embed = (
            await self.browser.render()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self.browser,
        )


# ==================================================
# BASE BROWSER
# ==================================================


class AdminBrowser(
    discord.ui.View
):

    def __init__(
        self,
        owner_id: int,
    ):

        super().__init__(
            timeout=600
        )

        self.owner_id = (
            owner_id
        )

        self.page = 0

        self.original_message = (
            None
        )


    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if (
            interaction.user.id
            == self.owner_id
        ):
            return True

        await interaction.response.send_message(
            "This menu belongs to another administrator.",
            ephemeral=True,
        )

        return False


    async def refresh_original_message(
        self,
    ):

        if self.original_message is None:
            return

        try:

            embed = (
                await self.render()
            )

            await self.original_message.edit(
                embed=embed,
                view=self,
            )

        except discord.HTTPException:
            pass


# ==================================================
# FLAG REVIEW BROWSER
# ==================================================


class FlaggedReviewBrowser(
    AdminBrowser
):

    def __init__(
        self,
        guild_id: int,
        owner_id: int,
    ):

        super().__init__(
            owner_id=owner_id
        )

        self.guild_id = (
            guild_id
        )


    async def _question_ids(
        self,
    ) -> list[int]:

        return (
            await get_open_flagged_question_ids(
                guild_id=(
                    self.guild_id
                )
            )
        )


    async def get_page_count(
        self,
    ) -> int:

        ids = (
            await self._question_ids()
        )

        return max(
            1,
            len(ids),
        )


    async def current_question_id(
        self,
    ) -> int | None:

        ids = (
            await self._question_ids()
        )

        if not ids:
            return None

        self.page = max(
            0,
            min(
                self.page,
                len(ids) - 1,
            ),
        )

        return ids[
            self.page
        ]


    async def render(
        self,
    ) -> discord.Embed:

        ids = (
            await self._question_ids()
        )

        if not ids:

            self.clear_items()

            return discord.Embed(
                title="🚩 Flagged Review",
                description=(
                    "✅ **No open flags remain.**"
                ),
                color=(
                    discord.Color.green()
                ),
            )

        question_id = (
            await self
            .current_question_id()
        )

        summary = (
            await get_open_question_flag_summary(
                guild_id=(
                    self.guild_id
                ),
                question_bank_id=(
                    question_id
                ),
            )
        )

        if summary is None:

            self.page = 0

            return (
                await self.render()
            )

        latest = (
            summary[
                "latest_flag"
            ]
        )

        question = (
            get_question_by_id(
                question_id
            )
        )

        if question is None:

            category = "Unknown"
            question_text = "Question no longer exists."
            answer_text = "Unavailable"

        else:

            category_code = (
                question.get(
                    "category",
                    "Unknown",
                )
            )

            category = (
                CATEGORY_NAMES.get(
                    category_code,
                    category_code,
                )
            )

            question_text = (
                question["question"]
            )

            answer_text = (
                _answers_display(
                    question.get(
                        "accepted_answers",
                        [],
                    )
                )
            )

        attempts = (
            latest.get(
                "attempted_answers",
                [],
            )
        )

        if attempts:

            last_answer = (
                attempts[0]
            )

        else:

            last_answer = (
                "No answer attempt recorded."
            )

        question_display = (
            _truncate(
                question_text,
                1200,
            )
        )

        answer_display = (
            _truncate(
                answer_text,
                900,
            )
        )

        last_answer_display = (
            _quote(
                _truncate(
                    last_answer,
                    700,
                )
            )
        )

        reason_display = (
            _quote(
                _truncate(
                    latest["reason"],
                    1000,
                )
            )
        )

        flag_time = (
            _timestamp(
                latest.get(
                    "created_at"
                )
            )
        )

        description = (
            "────────────────────────\n"
            f"**QBank ID:** #{question_id} "
            f"| **Category:** {category}\n\n"

            f"**Question**\n"
            f"{question_display}\n\n"

            f"**Accepted Answer**\n"
            f"{answer_display}\n"

            "────────────────────────\n"

            f"**Open Flags:** "
            f"{summary['num_flags']}\n"

            f"**Latest Flag:** "
            f"#{latest['id']} "
            f"• {flag_time}\n"

            f"**Reported by:** "
            f"<@{latest['user_id']}>\n\n"

            f"**Last User Answer**\n"
            f"{last_answer_display}\n\n"

            f"**Flag Reason**\n"
            f"{reason_display}"
        )

        embed = discord.Embed(
            title="🚩 Flagged Review",
            description=description,
            color=(
                discord.Color.orange()
            ),
        )

        embed.set_footer(
            text=(
                "Open all flags before deciding "
                "how each report should be handled."
            )
        )

        self._configure_buttons(
            len(ids)
        )

        return embed


    def _configure_buttons(
        self,
        page_count: int,
    ):

        self.clear_items()

        see_all = discord.ui.Button(
            label=(
                "See All Flags for "
                "This Question"
            ),
            emoji="🚩",
            style=(
                discord.ButtonStyle.primary
            ),
            row=0,
        )

        see_all.callback = (
            self._see_all
        )

        self.add_item(
            see_all
        )

        previous = discord.ui.Button(
            label="Prev",
            style=(
                discord.ButtonStyle.secondary
            ),
            disabled=(
                self.page <= 0
            ),
            row=1,
        )

        previous.callback = (
            self._previous
        )

        self.add_item(
            previous
        )

        page_button = discord.ui.Button(
            label=(
                f"Page "
                f"{self.page + 1} "
                f"/ {page_count}"
            ),
            style=(
                discord.ButtonStyle.secondary
            ),
            row=1,
        )

        page_button.callback = (
            self._pick_page
        )

        self.add_item(
            page_button
        )

        next_button = discord.ui.Button(
            label="Next",
            style=(
                discord.ButtonStyle.secondary
            ),
            disabled=(
                self.page
                >= page_count - 1
            ),
            row=1,
        )

        next_button.callback = (
            self._next
        )

        self.add_item(
            next_button
        )


    async def _previous(
        self,
        interaction: discord.Interaction,
    ):

        self.page = max(
            0,
            self.page - 1,
        )

        await interaction.response.edit_message(
            embed=(
                await self.render()
            ),
            view=self,
        )


    async def _next(
        self,
        interaction: discord.Interaction,
    ):

        self.page += 1

        await interaction.response.edit_message(
            embed=(
                await self.render()
            ),
            view=self,
        )


    async def _pick_page(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.send_modal(
            PagePickerModal(
                self
            )
        )


    async def _see_all(
        self,
        interaction: discord.Interaction,
    ):

        question_id = (
            await self
            .current_question_id()
        )

        if question_id is None:

            await interaction.response.send_message(
                "There are no open flags.",
                ephemeral=True,
            )

            return

        flags = (
            await get_open_flags_for_question(
                guild_id=(
                    self.guild_id
                ),
                question_bank_id=(
                    question_id
                ),
            )
        )

        report = FlagReport(
            browser=self,
            question_bank_id=(
                question_id
            ),
        )

        await interaction.response.send_message(
            embed=(
                await report
                .build_header()
            ),
            ephemeral=True,
        )

        report.header_message = (
            await interaction
            .original_response()
        )

        for flag in flags:

            view = FlagActionView(
                report=report,
                flag=flag,
            )

            await interaction.followup.send(
                embed=(
                    build_flag_embed(
                        flag
                    )
                ),
                view=view,
                ephemeral=True,
            )


# ==================================================
# FLAG REPORT
# ==================================================


class FlagReport:

    def __init__(
        self,
        browser: FlaggedReviewBrowser,
        question_bank_id: int,
    ):

        self.browser = (
            browser
        )

        self.guild_id = (
            browser.guild_id
        )

        self.owner_id = (
            browser.owner_id
        )

        self.question_bank_id = (
            question_bank_id
        )

        self.header_message = (
            None
        )


    async def build_header(
        self,
    ) -> discord.Embed:

        flags = (
            await get_open_flags_for_question(
                guild_id=(
                    self.guild_id
                ),
                question_bank_id=(
                    self.question_bank_id
                ),
            )
        )

        question = (
            get_question_by_id(
                self.question_bank_id
            )
        )

        if question is None:

            question_text = "Unavailable"
            answer_text = "Unavailable"

        else:

            question_text = (
                question["question"]
            )

            answer_text = (
                _answers_display(
                    question.get(
                        "accepted_answers",
                        [],
                    )
                )
            )

        question_display = (
            _truncate(
                question_text,
                1000,
            )
        )

        answer_display = (
            _truncate(
                answer_text,
                800,
            )
        )

        description = (
            f"**Question**\n"
            f"{question_display}\n\n"

            f"**Accepted Answer**\n"
            f"{answer_display}\n"

            "────────────────────────\n"

            f"**Total Open Flags:** "
            f"{len(flags)}"
        )

        return discord.Embed(
            title=(
                "🚩 All Flags — "
                f"QBank #{self.question_bank_id}"
            ),
            description=description,
            color=(
                discord.Color.orange()
            ),
        )


    async def refresh(
        self,
    ):

        if self.header_message is not None:

            try:

                await self.header_message.edit(
                    embed=(
                        await self
                        .build_header()
                    )
                )

            except discord.HTTPException:
                pass

        await self.browser.refresh_original_message()


# ==================================================
# INDIVIDUAL FLAG CARD
# ==================================================


def build_flag_embed(
    flag: dict,
) -> discord.Embed:

    time_display = (
        _timestamp(
            flag.get(
                "created_at"
            )
        )
    )

    answers_display = (
        _user_answers_display(
            flag.get(
                "attempted_answers",
                [],
            )
        )
    )

    reason_display = (
        _quote(
            _truncate(
                flag["reason"],
                1000,
            )
        )
    )

    description = (
        f"**Flag #{flag['id']}** "
        f"• {time_display}\n"

        f"**Reported by:** "
        f"<@{flag['user_id']}>\n"

        "────────────────────────\n"

        f"**User Answers**\n"
        f"{answers_display}\n\n"

        f"**Flag Reason**\n"
        f"{reason_display}"
    )

    return discord.Embed(
        description=description,
        color=(
            discord.Color.orange()
        ),
    )


# ==================================================
# FLAG ACTION BUTTONS
# ==================================================


class FlagActionView(
    discord.ui.View
):

    def __init__(
        self,
        report: FlagReport,
        flag: dict,
    ):

        super().__init__(
            timeout=600
        )

        self.report = report
        self.flag = flag


    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if (
            interaction.user.id
            == self.report.owner_id
        ):
            return True

        await interaction.response.send_message(
            "This report belongs to another administrator.",
            ephemeral=True,
        )

        return False


    @discord.ui.button(
        label="Dismiss",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
    )
    async def dismiss(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        confirmation = (
            DismissFlagConfirmation(
                report=self.report,
                flag=self.flag,
                flag_message=(
                    interaction.message
                ),
            )
        )

        await interaction.response.send_message(
            embed=discord.Embed(
                title=(
                    f"Dismiss Flag "
                    f"#{self.flag['id']}?"
                ),
                description=(
                    "Use this for spam, accidental, "
                    "duplicate, or otherwise "
                    "non-actionable reports.\n\n"
                    "**Are you sure?**"
                ),
                color=(
                    discord.Color.red()
                ),
            ),
            view=confirmation,
            ephemeral=True,
        )


    @discord.ui.button(
        label="Message User",
        emoji="💬",
        style=discord.ButtonStyle.secondary,
    )
    async def message_user(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.send_modal(
            MessageFlagUserModal(
                report=self.report,
                flag=self.flag,
            )
        )


    @discord.ui.button(
        label="Mark Question for Edit",
        emoji="✏️",
        style=discord.ButtonStyle.primary,
    )
    async def mark_edit(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        view = MarkEditConfirmation(
            report=self.report,
            flag=self.flag,
            flag_message=(
                interaction.message
            ),
        )

        await interaction.response.send_message(
            embed=discord.Embed(
                title=(
                    "Mark Question for Editing?"
                ),
                description=(
                    f"**QBank "
                    f"#{self.flag['question_bank_id']}** "
                    "will immediately be removed "
                    "from all normal question selection.\n\n"
                    "It will remain quarantined until "
                    "an administrator marks it resolved "
                    "in `/flaggededit`."
                ),
                color=(
                    discord.Color.orange()
                ),
            ),
            view=view,
            ephemeral=True,
        )


# ==================================================
# DISMISS CONFIRMATION
# ==================================================


class DismissFlagConfirmation(
    discord.ui.View
):

    def __init__(
        self,
        report: FlagReport,
        flag: dict,
        flag_message,
    ):

        super().__init__(
            timeout=120
        )

        self.report = report
        self.flag = flag
        self.flag_message = (
            flag_message
        )


    @discord.ui.button(
        label="Confirm Dismiss",
        style=discord.ButtonStyle.danger,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        try:

            await dismiss_question_flag(
                flag_id=(
                    self.flag["id"]
                ),
                guild_id=(
                    self.report.guild_id
                ),
                reviewed_by=(
                    interaction.user.id
                ),
            )

        except QuestionFlagNotFoundError:

            await interaction.response.edit_message(
                content=(
                    "This flag is already closed."
                ),
                embed=None,
                view=None,
            )

            return

        await interaction.response.edit_message(
            content=(
                f"✅ Flag "
                f"#{self.flag['id']} dismissed."
            ),
            embed=None,
            view=None,
        )

        try:

            await self.flag_message.edit(
                embed=discord.Embed(
                    title=(
                        f"✅ Flag "
                        f"#{self.flag['id']} Dismissed"
                    ),
                    description=(
                        "This report has been closed."
                    ),
                    color=(
                        discord.Color.green()
                    ),
                ),
                view=None,
            )

        except discord.HTTPException:
            pass

        await self.report.refresh()


    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.edit_message(
            content="Dismissal cancelled.",
            embed=None,
            view=None,
        )


# ==================================================
# MARK EDIT CONFIRMATION
# ==================================================


class MarkEditConfirmation(
    discord.ui.View
):

    def __init__(
        self,
        report: FlagReport,
        flag: dict,
        flag_message,
    ):

        super().__init__(
            timeout=120
        )

        self.report = report
        self.flag = flag
        self.flag_message = (
            flag_message
        )


    @discord.ui.button(
        label="Mark for Edit",
        emoji="✏️",
        style=discord.ButtonStyle.primary,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        try:

            await mark_question_for_edit_from_flag(
                guild_id=(
                    self.report.guild_id
                ),
                question_bank_id=(
                    self.flag[
                        "question_bank_id"
                    ]
                ),
                flag_id=(
                    self.flag["id"]
                ),
                marked_by=(
                    interaction.user.id
                ),
            )

        except ValueError as error:

            await interaction.response.edit_message(
                content=(
                    f"⚠️ {error}"
                ),
                embed=None,
                view=None,
            )

            return

        await interaction.response.edit_message(
            content=(
                f"✅ QBank "
                f"#{self.flag['question_bank_id']} "
                "marked for editing."
            ),
            embed=None,
            view=None,
        )

        try:

            await self.flag_message.edit(
                embed=discord.Embed(
                    title=(
                        f"✏️ Flag "
                        f"#{self.flag['id']} "
                        "Marked for Edit"
                    ),
                    description=(
                        f"QBank "
                        f"#{self.flag['question_bank_id']} "
                        "has been added to "
                        "`/flaggededit`."
                    ),
                    color=(
                        discord.Color.blue()
                    ),
                ),
                view=None,
            )

        except discord.HTTPException:
            pass

        await self.report.refresh()


    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.edit_message(
            content="No changes were made.",
            embed=None,
            view=None,
        )


# ==================================================
# MESSAGE USER MODAL
# ==================================================


class MessageFlagUserModal(
    discord.ui.Modal
):

    def __init__(
        self,
        report: FlagReport,
        flag: dict,
    ):

        super().__init__(
            title=(
                f"Message User — "
                f"Flag #{flag['id']}"
            )
        )

        self.report = report
        self.flag = flag

        self.message_input = (
            discord.ui.TextInput(
                label="Message",
                placeholder=(
                    "Ask for clarification or "
                    "explain the question..."
                ),
                style=(
                    discord.TextStyle.paragraph
                ),
                required=True,
                max_length=2000,
            )
        )

        self.add_item(
            self.message_input
        )


    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):

        message_text = str(
            self.message_input.value
        ).strip()

        try:

            user = (
                interaction.client.get_user(
                    self.flag["user_id"]
                )
            )

            if user is None:

                user = (
                    await interaction.client
                    .fetch_user(
                        self.flag["user_id"]
                    )
                )

            admin_id = (
                interaction.user.id
            )

            dm_embed = discord.Embed(
                title=(
                    "🚑 M.A.R.T.Y. Flag Follow-up"
                ),
                description=(
                    f"An administrator sent you "
                    f"a message about **Flag "
                    f"#{self.flag['id']}** for "
                    f"**QBank "
                    f"#{self.flag['question_bank_id']}**.\n\n"
                    f"{_quote(message_text)}\n\n"
                    f"If a response is requested, "
                    f"you can contact "
                    f"<@{admin_id}> directly."
                ),
                color=(
                    discord.Color.blurple()
                ),
            )

            await user.send(
                embed=dm_embed
            )

        except (
            discord.Forbidden,
            discord.NotFound,
            discord.HTTPException,
        ):

            await interaction.response.send_message(
                (
                    "⚠️ M.A.R.T.Y. could not DM "
                    "this user. They may have "
                    "server DMs disabled."
                ),
                ephemeral=True,
            )

            return

        await interaction.response.send_message(
            (
                f"✅ Message sent to "
                f"<@{self.flag['user_id']}>.\n\n"
                "The flag remains open."
            ),
            ephemeral=True,
        )


# ==================================================
# FLAGGED EDIT BROWSER
# ==================================================


class FlaggedEditBrowser(
    AdminBrowser
):

    def __init__(
        self,
        guild_id: int,
        owner_id: int,
    ):

        super().__init__(
            owner_id=owner_id
        )

        self.guild_id = (
            guild_id
        )


    async def entries(
        self,
    ) -> list[dict]:

        return (
            await get_questions_needing_edit()
        )


    async def get_page_count(
        self,
    ) -> int:

        entries = (
            await self.entries()
        )

        return max(
            1,
            len(entries),
        )


    async def current_entry(
        self,
    ) -> dict | None:

        entries = (
            await self.entries()
        )

        if not entries:
            return None

        self.page = max(
            0,
            min(
                self.page,
                len(entries) - 1,
            ),
        )

        return entries[
            self.page
        ]


    async def render(
        self,
    ) -> discord.Embed:

        entries = (
            await self.entries()
        )

        if not entries:

            self.clear_items()

            return discord.Embed(
                title="✏️ Flagged Edit Queue",
                description=(
                    "✅ **No questions are "
                    "currently waiting for edits.**"
                ),
                color=(
                    discord.Color.green()
                ),
            )

        entry = (
            await self.current_entry()
        )

        question_id = (
            entry[
                "question_bank_id"
            ]
        )

        question = (
            get_question_by_id(
                question_id
            )
        )

        if question is None:

            category = "Unknown"
            question_text = "Question no longer exists."
            answer_text = "Unavailable"

        else:

            category_code = (
                question.get(
                    "category",
                    "Unknown",
                )
            )

            category = (
                CATEGORY_NAMES.get(
                    category_code,
                    category_code,
                )
            )

            question_text = (
                question["question"]
            )

            answer_text = (
                _answers_display(
                    question.get(
                        "accepted_answers",
                        [],
                    )
                )
            )

        open_flags = (
            await get_open_flags_for_question(
                guild_id=(
                    self.guild_id
                ),
                question_bank_id=(
                    question_id
                ),
            )
        )

        marked_time = (
            _timestamp(
                entry.get(
                    "marked_at"
                )
            )
        )

        source_flag = (
            entry.get(
                "source_flag_id"
            )
        )

        source_display = (
            f"#{source_flag}"
            if source_flag is not None
            else "Unknown"
        )

        question_display = (
            _truncate(
                question_text,
                1200,
            )
        )

        answer_display = (
            _truncate(
                answer_text,
                900,
            )
        )

        description = (
            "────────────────────────\n"

            f"**QBank ID:** "
            f"#{question_id} "
            f"| **Category:** "
            f"{category}\n\n"

            f"**Question**\n"
            f"{question_display}\n\n"

            f"**Accepted Answer**\n"
            f"{answer_display}\n"

            "────────────────────────\n"

            f"**Marked for Edit:** "
            f"{marked_time}\n"

            f"**Source Flag:** "
            f"{source_display}\n"

            f"**Marked by:** "
            f"<@{entry['marked_by']}>\n"

            f"**Open Flags Remaining:** "
            f"{len(open_flags)}\n\n"

            "⚠️ **This question is currently "
            "excluded from all normal question "
            "selection.**"
        )

        embed = discord.Embed(
            title="✏️ Flagged Edit Queue",
            description=description,
            color=(
                discord.Color.blue()
            ),
        )

        embed.set_footer(
            text=(
                "Editing does not return the question "
                "to circulation. Use Mark as Resolved "
                "when review is completely finished."
            )
        )

        self._configure_buttons(
            len(entries)
        )

        return embed


    def _configure_buttons(
        self,
        page_count: int,
    ):

        self.clear_items()

        edit_button = discord.ui.Button(
            label="Edit Question",
            emoji="✏️",
            style=(
                discord.ButtonStyle.primary
            ),
            row=0,
        )

        edit_button.callback = (
            self._edit
        )

        self.add_item(
            edit_button
        )

        resolve_button = discord.ui.Button(
            label="Mark as Resolved",
            emoji="✅",
            style=(
                discord.ButtonStyle.success
            ),
            row=0,
        )

        resolve_button.callback = (
            self._resolve
        )

        self.add_item(
            resolve_button
        )

        previous = discord.ui.Button(
            label="Prev",
            disabled=(
                self.page <= 0
            ),
            style=(
                discord.ButtonStyle.secondary
            ),
            row=1,
        )

        previous.callback = (
            self._previous
        )

        self.add_item(
            previous
        )

        page_button = discord.ui.Button(
            label=(
                f"Page "
                f"{self.page + 1} "
                f"/ {page_count}"
            ),
            style=(
                discord.ButtonStyle.secondary
            ),
            row=1,
        )

        page_button.callback = (
            self._pick_page
        )

        self.add_item(
            page_button
        )

        next_button = discord.ui.Button(
            label="Next",
            disabled=(
                self.page
                >= page_count - 1
            ),
            style=(
                discord.ButtonStyle.secondary
            ),
            row=1,
        )

        next_button.callback = (
            self._next
        )

        self.add_item(
            next_button
        )


    async def _edit(
        self,
        interaction: discord.Interaction,
    ):

        entry = (
            await self.current_entry()
        )

        if entry is None:
            return

        question = (
            get_question_by_id(
                entry[
                    "question_bank_id"
                ]
            )
        )

        if question is None:

            await interaction.response.send_message(
                "Question could not be found.",
                ephemeral=True,
            )

            return

        await interaction.response.send_modal(
            EditQueuedQuestionModal(
                browser=self,
                question_data=question,
            )
        )


    async def _resolve(
        self,
        interaction: discord.Interaction,
    ):

        entry = (
            await self.current_entry()
        )

        if entry is None:
            return

        question_id = (
            entry[
                "question_bank_id"
            ]
        )

        open_flags = (
            await get_open_flags_for_question(
                guild_id=(
                    self.guild_id
                ),
                question_bank_id=(
                    question_id
                ),
            )
        )

        if open_flags:

            await interaction.response.send_message(
                embed=discord.Embed(
                    title=(
                        "⚠️ Open Flags Remain"
                    ),
                    description=(
                        f"QBank #{question_id} still "
                        f"has **{len(open_flags)}** "
                        "unreviewed open flag"
                        f"{'' if len(open_flags) == 1 else 's'}.\n\n"
                        "Handle those reports in "
                        "`/flaggedreview` before "
                        "returning this question "
                        "to circulation."
                    ),
                    color=(
                        discord.Color.orange()
                    ),
                ),
                ephemeral=True,
            )

            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="Mark Question as Resolved?",
                description=(
                    f"**QBank #{question_id}** will "
                    "return to the normal question "
                    "selection pool.\n\n"
                    "Are you sure review is complete?"
                ),
                color=(
                    discord.Color.green()
                ),
            ),
            view=ResolveEditConfirmation(
                browser=self,
                question_bank_id=(
                    question_id
                ),
            ),
            ephemeral=True,
        )


    async def _previous(
        self,
        interaction: discord.Interaction,
    ):

        self.page = max(
            0,
            self.page - 1,
        )

        await interaction.response.edit_message(
            embed=(
                await self.render()
            ),
            view=self,
        )


    async def _next(
        self,
        interaction: discord.Interaction,
    ):

        self.page += 1

        await interaction.response.edit_message(
            embed=(
                await self.render()
            ),
            view=self,
        )


    async def _pick_page(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.send_modal(
            PagePickerModal(
                self
            )
        )


# ==================================================
# EDIT QUEUED QUESTION MODAL
# ==================================================


class EditQueuedQuestionModal(
    discord.ui.Modal
):

    def __init__(
        self,
        browser: FlaggedEditBrowser,
        question_data: dict,
    ):

        question_id = (
            question_data["id"]
        )

        super().__init__(
            title=(
                f"Edit QBank #{question_id}"
            )
        )

        self.browser = browser
        self.question_id = (
            question_id
        )

        current_answers = (
            " | ".join(
                question_data.get(
                    "accepted_answers",
                    [],
                )
            )
        )

        self.question_input = (
            discord.ui.TextInput(
                label="Question Wording",
                style=(
                    discord.TextStyle.paragraph
                ),
                default=(
                    str(
                        question_data["question"]
                    )[:4000]
                ),
                required=True,
                max_length=4000,
            )
        )

        self.answer_input = (
            discord.ui.TextInput(
                label="Accepted Answer(s)",
                placeholder=(
                    "Separate alternatives with |"
                ),
                style=(
                    discord.TextStyle.paragraph
                ),
                default=(
                    current_answers[:4000]
                ),
                required=True,
                max_length=4000,
            )
        )

        self.add_item(
            self.question_input
        )

        self.add_item(
            self.answer_input
        )


    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):

        answers = (
            _parse_answers(
                str(
                    self.answer_input.value
                )
            )
        )

        if not answers:

            await interaction.response.send_message(
                "At least one accepted answer is required.",
                ephemeral=True,
            )

            return

        try:

            update_question(
                question_id=(
                    self.question_id
                ),
                question_text=(
                    str(
                        self.question_input.value
                    )
                ),
                accepted_answers=answers,
            )

        except Exception as error:

            await interaction.response.send_message(
                f"⚠️ Could not save question: {error}",
                ephemeral=True,
            )

            return

        await interaction.response.send_message(
            (
                f"✅ **QBank "
                f"#{self.question_id} updated.**\n\n"
                "It remains in `/flaggededit` "
                "and remains excluded from question "
                "selection until you mark it resolved."
            ),
            ephemeral=True,
        )

        await self.browser.refresh_original_message()


# ==================================================
# RESOLVE EDIT CONFIRMATION
# ==================================================


class ResolveEditConfirmation(
    discord.ui.View
):

    def __init__(
        self,
        browser: FlaggedEditBrowser,
        question_bank_id: int,
    ):

        super().__init__(
            timeout=120
        )

        self.browser = browser
        self.question_bank_id = (
            question_bank_id
        )


    @discord.ui.button(
        label="Confirm Resolution",
        emoji="✅",
        style=discord.ButtonStyle.success,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        try:

            await resolve_question_edit(
                question_bank_id=(
                    self.question_bank_id
                ),
                resolved_by=(
                    interaction.user.id
                ),
            )

        except ValueError as error:

            await interaction.response.edit_message(
                content=(
                    f"⚠️ {error}"
                ),
                embed=None,
                view=None,
            )

            return

        await interaction.response.edit_message(
            content=(
                f"✅ **QBank "
                f"#{self.question_bank_id} resolved.**\n\n"
                "It has been returned to normal "
                "question selection."
            ),
            embed=None,
            view=None,
        )

        await self.browser.refresh_original_message()


    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.edit_message(
            content="No changes were made.",
            embed=None,
            view=None,
        )


# ==================================================
# REGISTER ADMIN COMMANDS
# ==================================================


def register_question_flag_admin_commands(
    tree: app_commands.CommandTree,
    guild: discord.Object,
):

    command = make_command(
        tree=tree,
        guild=guild,
    )


    # ==================================================
    # /FLAGGEDREVIEW
    # ==================================================


    @command(
        name="flaggedreview",
        description=(
            "Review individual student "
            "question flags."
        ),
    )
    async def flaggedreview(
        interaction: discord.Interaction,
    ):

        if (
            interaction.guild is None
            or not interaction.user
            .guild_permissions
            .administrator
        ):

            await interaction.response.send_message(
                (
                    "You do not have permission "
                    "to review question flags."
                ),
                ephemeral=True,
            )

            return

        browser = FlaggedReviewBrowser(
            guild_id=(
                interaction.guild.id
            ),
            owner_id=(
                interaction.user.id
            ),
        )

        await interaction.response.send_message(
            embed=(
                await browser.render()
            ),
            view=browser,
            ephemeral=True,
        )

        browser.original_message = (
            await interaction
            .original_response()
        )


    # ==================================================
    # /FLAGGEDEDIT
    # ==================================================


    @command(
        name="flaggededit",
        description=(
            "Review questions currently "
            "quarantined for editing."
        ),
    )
    async def flaggededit(
        interaction: discord.Interaction,
    ):

        if (
            interaction.guild is None
            or not interaction.user
            .guild_permissions
            .administrator
        ):

            await interaction.response.send_message(
                (
                    "You do not have permission "
                    "to edit flagged questions."
                ),
                ephemeral=True,
            )

            return

        browser = FlaggedEditBrowser(
            guild_id=(
                interaction.guild.id
            ),
            owner_id=(
                interaction.user.id
            ),
        )

        await interaction.response.send_message(
            embed=(
                await browser.render()
            ),
            view=browser,
            ephemeral=True,
        )

        browser.original_message = (
            await interaction
            .original_response()
        )