from datetime import (
    date,
    datetime,
    timezone,
)

from zoneinfo import (
    ZoneInfo,
)

import discord

from discord import (
    app_commands,
)

from bot_config import (
    RANDOM_QUESTION_CHANNEL_ID,
)

from commands.command_helpers import (
    make_command,
)

from points.mechanics.random_speed_questions.rsq import (
    get_latest_rsq_post,
    get_rsq_post_counts_for_date,
)

from points.mechanics.random_speed_questions.rsq_config import (
    RSQ_ENABLED,
    RSQ_TIMEZONE,
    RSQ_WINDOW_START_HOUR,
    RSQ_WINDOW_START_MINUTE,
    RSQ_WINDOW_END_HOUR,
    RSQ_WINDOW_END_MINUTE,
    RSQ_DAILY_QUESTION_MEAN,
    RSQ_DAILY_QUESTION_STD_DEV,
    RSQ_TIMING_RANDOMNESS,
    RSQ_DISTRIBUTION_SMOOTHING,
    RSQ_MIN_INTERVAL_MINUTES,
    RSQ_RECENT_QUESTION_AVOID_COUNT,
)


# ==================================================
# TIMEZONE
# ==================================================


RSQ_ZONE = ZoneInfo(
    RSQ_TIMEZONE
)


# ==================================================
# STATUS DISPLAY
# ==================================================


STATUS_ICONS = {
    "pending": "○",
    "posted": "✅",
    "missed": "⌛",
    "skipped_cooldown": "⏭️",
    "skipped_no_question": "⚠️",
}


STATUS_NAMES = {
    "pending": "Pending",
    "posted": "Posted",
    "missed": "Missed",
    "skipped_cooldown": (
        "Skipped — cooldown"
    ),
    "skipped_no_question": (
        "Skipped — no question"
    ),
}


# ==================================================
# TIME HELPERS
# ==================================================


def _now_local() -> datetime:

    return (
        datetime.now(
            timezone.utc
        ).astimezone(
            RSQ_ZONE
        )
    )


def _parse_datetime(
    value: str | None,
) -> datetime | None:

    if not value:

        return None

    value = str(
        value
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

            return None

    if parsed.tzinfo is None:

        parsed = (
            parsed.replace(
                tzinfo=timezone.utc
            )
        )

    return parsed


def _discord_timestamp(
    value: str | None,
    style: str = "t",
) -> str:

    parsed = (
        _parse_datetime(
            value
        )
    )

    if parsed is None:

        return "Unknown"

    return (
        f"<t:{int(parsed.timestamp())}:{style}>"
    )


def _format_clock(
    hour: int,
    minute: int,
) -> str:

    fake_datetime = datetime(
        2000,
        1,
        1,
        hour,
        minute,
    )

    return (
        fake_datetime
        .strftime(
            "%I:%M %p"
        )
        .lstrip("0")
    )


# ==================================================
# BUILD SLOT LINE
# ==================================================


def _build_slot_line(
    slot: dict,
    next_pending_id: int | None,
) -> str:

    status = (
        slot[
            "status"
        ]
    )

    slot_number = int(
        slot[
            "slot_number"
        ]
    )

    scheduled_display = (
        _discord_timestamp(
            slot[
                "scheduled_at"
            ],
            "t",
        )
    )

    if status == "posted":

        question_id = (
            slot.get(
                "question_id"
            )
        )

        if question_id is None:

            detail = "Posted"

        else:

            detail = (
                f"QBank #{question_id}"
            )

        return (
            f"✅ **#{slot_number:02d}** "
            f"• {scheduled_display} "
            f"— {detail}"
        )

    if (
        status == "pending"
        and slot["id"]
        == next_pending_id
    ):

        return (
            f"⏳ **#{slot_number:02d}** "
            f"• {scheduled_display} "
            "— **NEXT**"
        )

    if status == "pending":

        return (
            f"○ **#{slot_number:02d}** "
            f"• {scheduled_display}"
        )

    icon = (
        STATUS_ICONS.get(
            status,
            "•",
        )
    )

    name = (
        STATUS_NAMES.get(
            status,
            status,
        )
    )

    return (
        f"{icon} **#{slot_number:02d}** "
        f"• {scheduled_display} "
        f"— {name}"
    )


# ==================================================
# NEXT PENDING SLOT
# ==================================================


def _get_next_pending_slot(
    slots: list[dict],
) -> dict | None:

    pending = [
        slot
        for slot in slots
        if (
            slot[
                "status"
            ]
            == "pending"
        )
    ]

    if not pending:

        return None

    pending.sort(
        key=lambda slot: (
            _parse_datetime(
                slot[
                    "scheduled_at"
                ]
            )
            or datetime.max.replace(
                tzinfo=timezone.utc
            )
        )
    )

    return (
        pending[0]
    )


# ==================================================
# BUILD SCHEDULE EMBED
# ==================================================


async def build_rsq_schedule_embed(
    guild_id: int,
    scheduler,
) -> discord.Embed:

    calendar_date = (
        _now_local()
        .date()
    )

    schedule_day = (
        await scheduler.get_schedule_day(
            calendar_date
        )
    )

    slots = (
        await scheduler.get_schedule_slots(
            calendar_date
        )
    )

    post_counts = (
        await get_rsq_post_counts_for_date(
            guild_id=(
                guild_id
            ),
            channel_id=(
                RANDOM_QUESTION_CHANNEL_ID
            ),
            calendar_date=(
                calendar_date
            ),
        )
    )

    latest_post = (
        await get_latest_rsq_post(
            guild_id=(
                guild_id
            ),
            channel_id=(
                RANDOM_QUESTION_CHANNEL_ID
            ),
        )
    )


    # ==================================================
    # STATUS
    # ==================================================


    if RSQ_ENABLED:

        status_display = (
            "🟢 Enabled"
        )

        color = (
            discord.Color.green()
        )

    else:

        status_display = (
            "🔴 Disabled"
        )

        color = (
            discord.Color.red()
        )


    # ==================================================
    # EMBED
    # ==================================================


    embed = discord.Embed(
        title=(
            "⚡ RSQ Schedule "
            f"[{calendar_date.strftime('%m/%d/%Y')}]"
        ),
        description=(
            f"**Status:** {status_display}\n"
            f"**Channel:** "
            f"<#{RANDOM_QUESTION_CHANNEL_ID}>"
        ),
        color=color,
    )


    # ==================================================
    # NO SCHEDULE
    # ==================================================


    if (
        schedule_day is None
        or not slots
    ):

        embed.add_field(
            name="📅 Today's Schedule",
            value=(
                "No schedule has been "
                "generated yet."
            ),
            inline=False,
        )

        return embed


    # ==================================================
    # COUNTS
    # ==================================================


    target_count = int(
        schedule_day[
            "target_count"
        ]
    )

    pending_count = sum(
        1
        for slot
        in slots
        if (
            slot[
                "status"
            ]
            == "pending"
        )
    )

    processed_count = (
        len(slots)
        - pending_count
    )

    next_slot = (
        _get_next_pending_slot(
            slots
        )
    )

    next_slot_id = (
        next_slot["id"]
        if next_slot is not None
        else None
    )

    embed.add_field(
        name="🎯 Today's Target",
        value=(
            f"**{target_count}** "
            "automatic RSQs"
        ),
        inline=True,
    )

    embed.add_field(
        name="📊 Progress",
        value=(
            f"**{processed_count} / "
            f"{len(slots)}** slots processed"
        ),
        inline=True,
    )

    embed.add_field(
        name="📨 Actual RSQs Today",
        value=(
            f"**{post_counts['total']}** total\n"
            f"{post_counts['automatic']} automatic\n"
            f"{post_counts['manual']} manual"
        ),
        inline=True,
    )


    # ==================================================
    # NEXT
    # ==================================================


    if next_slot is None:

        next_display = (
            "No pending automatic "
            "slots remain today."
        )

    else:

        next_display = (
            f"{_discord_timestamp(next_slot['scheduled_at'], 'F')}\n"
            f"{_discord_timestamp(next_slot['scheduled_at'], 'R')}"
        )

    embed.add_field(
        name="⏭️ Next Automatic RSQ",
        value=(
            next_display
        ),
        inline=False,
    )


    # ==================================================
    # FULL SCHEDULE
    # ==================================================


    schedule_lines = [
        _build_slot_line(
            slot=slot,
            next_pending_id=(
                next_slot_id
            ),
        )
        for slot
        in slots
    ]

    embed.add_field(
        name="📅 Full Daily Schedule",
        value=(
            "\n".join(
                schedule_lines
            )
            or "No slots."
        ),
        inline=False,
    )


    # ==================================================
    # CONFIG
    # ==================================================


    randomness = round(
        RSQ_TIMING_RANDOMNESS
        * 100
    )

    smoothing = round(
        RSQ_DISTRIBUTION_SMOOTHING
        * 100
    )

    embed.add_field(
        name="⚙️ Configuration",
        value=(
            f"Window: **"
            f"{_format_clock(RSQ_WINDOW_START_HOUR, RSQ_WINDOW_START_MINUTE)}"
            f" – "
            f"{_format_clock(RSQ_WINDOW_END_HOUR, RSQ_WINDOW_END_MINUTE)}"
            f"**\n"
            f"Randomness: **{randomness}%**\n"
            f"Smoothing: **{smoothing}%**\n"
            f"Minimum Gap: "
            f"**{RSQ_MIN_INTERVAL_MINUTES} min**"
        ),
        inline=True,
    )

    embed.add_field(
        name="🔁 Rotation",
        value=(
            f"Avoid last "
            f"**{RSQ_RECENT_QUESTION_AVOID_COUNT}** "
            "questions when possible.\n"
            f"μ = **{RSQ_DAILY_QUESTION_MEAN:g}**\n"
            f"σ = **{RSQ_DAILY_QUESTION_STD_DEV:g}**"
        ),
        inline=True,
    )


    # ==================================================
    # LATEST
    # ==================================================


    if latest_post is not None:

        latest_type = (
            "Automatic"
            if latest_post[
                "automatic"
            ]
            else "Manual"
        )

        embed.add_field(
            name="⚡ Most Recent RSQ",
            value=(
                f"**QBank "
                f"#{latest_post['question_id']}** "
                f"• {latest_type}\n"
                f"{_discord_timestamp(latest_post['posted_at'], 'F')}\n"
                f"{_discord_timestamp(latest_post['posted_at'], 'R')}"
            ),
            inline=False,
        )

    embed.set_footer(
        text=(
            "Question IDs are selected only when "
            "each scheduled slot actually arrives."
        )
    )

    return embed


# ==================================================
# SCHEDULE VIEW
# ==================================================


class RsqScheduleView(
    discord.ui.View
):

    def __init__(
        self,
        guild_id: int,
        owner_id: int,
        scheduler,
    ):

        super().__init__(
            timeout=600
        )

        self.guild_id = (
            guild_id
        )

        self.owner_id = (
            owner_id
        )

        self.scheduler = (
            scheduler
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
            (
                "This schedule belongs to "
                "another administrator."
            ),
            ephemeral=True,
        )

        return False


    @discord.ui.button(
        label="Refresh Schedule",
        emoji="🔄",
        style=(
            discord.ButtonStyle.secondary
        ),
    )
    async def refresh_schedule(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        embed = (
            await build_rsq_schedule_embed(
                guild_id=(
                    self.guild_id
                ),
                scheduler=(
                    self.scheduler
                ),
            )
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self,
        )


# ==================================================
# REGENERATE CONFIRMATION
# ==================================================


class RsqRegenerateConfirmView(
    discord.ui.View
):

    def __init__(
        self,
        scheduler,
        owner_id: int,
    ):

        super().__init__(
            timeout=120
        )

        self.scheduler = (
            scheduler
        )

        self.owner_id = (
            owner_id
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
            (
                "Only the administrator who "
                "started this regeneration can "
                "confirm it."
            ),
            ephemeral=True,
        )

        return False


    # ==================================================
    # CONFIRM
    # ==================================================


    @discord.ui.button(
        label="Confirm Regeneration",
        emoji="🎲",
        style=(
            discord.ButtonStyle.danger
        ),
    )
    async def confirm_regeneration(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.defer()

        try:

            result = (
                await self.scheduler
                .regenerate_today()
            )

        except Exception as error:

            print(
                "RSQ regeneration error: "
                f"{error!r}"
            )

            await interaction.edit_original_response(
                content=(
                    "⚠️ M.A.R.T.Y. could not "
                    "regenerate today's RSQ schedule."
                ),
                embed=None,
                view=None,
            )

            return


        # ==================================================
        # WINDOW OVER
        # ==================================================


        if result[
            "window_over"
        ]:

            await interaction.edit_original_response(
                content=(
                    "⚠️ Today's configured RSQ "
                    "window has already ended."
                ),
                embed=None,
                view=None,
            )

            return


        # ==================================================
        # RESULT
        # ==================================================


        times = (
            result[
                "times"
            ]
        )

        if times:

            time_lines = [
                (
                    f"• "
                    f"{_discord_timestamp(value, 'F')} "
                    f"({_discord_timestamp(value, 'R')})"
                )
                for value
                in times
            ]

            times_display = "\n".join(
                time_lines
            )

        else:

            times_display = (
                "No new automatic slots "
                "remain today."
            )

        embed = discord.Embed(
            title=(
                "🎲 RSQ Schedule Regenerated"
            ),
            description=(
                "Today's **pending** RSQ slots "
                "were replaced using the current "
                "`rsq_config.py` settings."
            ),
            color=(
                discord.Color.orange()
            ),
        )

        embed.add_field(
            name="New Drawn Target",
            value=(
                f"**{result['drawn_target']}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="Already Processed",
            value=(
                f"**{result['processed_count']}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="New Remaining Slots",
            value=(
                f"**{result['remaining_count']}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="New Remaining Schedule",
            value=(
                times_display
            ),
            inline=False,
        )

        embed.set_footer(
            text=(
                "Already-posted, missed, and "
                "skipped slots were preserved."
            )
        )

        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=None,
        )


    # ==================================================
    # CANCEL
    # ==================================================


    @discord.ui.button(
        label="Cancel",
        style=(
            discord.ButtonStyle.secondary
        ),
    )
    async def cancel_regeneration(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        await interaction.response.edit_message(
            content=(
                "RSQ schedule regeneration "
                "cancelled."
            ),
            embed=None,
            view=None,
        )


# ==================================================
# REGISTER COMMANDS
# ==================================================


def register_rsq_admin_commands(
    tree: app_commands.CommandTree,
    guild: discord.Object,
    scheduler,
):


    # ==================================================
    # AVOID DUPLICATE REGISTRATION
    # ==================================================


    existing_schedule = (
        tree.get_command(
            "rsqschedule",
            guild=guild,
        )
    )

    existing_regenerate = (
        tree.get_command(
            "rsqregenerate",
            guild=guild,
        )
    )

    command = make_command(
        tree=tree,
        guild=guild,
    )


    # ==================================================
    # /RSQSCHEDULE
    # ==================================================


    if existing_schedule is None:

        @command(
            name="rsqschedule",
            description=(
                "View today's Random Speed "
                "Question schedule."
            ),
        )
        async def rsqschedule(
            interaction: discord.Interaction,
        ):

            if interaction.guild is None:

                await interaction.response.send_message(
                    (
                        "This command must be used "
                        "inside a server."
                    ),
                    ephemeral=True,
                )

                return

            if (
                not interaction.user
                .guild_permissions
                .administrator
            ):

                await interaction.response.send_message(
                    (
                        "You do not have permission "
                        "to view the RSQ schedule."
                    ),
                    ephemeral=True,
                )

                return

            embed = (
                await build_rsq_schedule_embed(
                    guild_id=(
                        interaction.guild.id
                    ),
                    scheduler=(
                        scheduler
                    ),
                )
            )

            view = RsqScheduleView(
                guild_id=(
                    interaction.guild.id
                ),
                owner_id=(
                    interaction.user.id
                ),
                scheduler=(
                    scheduler
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True,
            )


    # ==================================================
    # /RSQREGENERATE
    # ==================================================


    if existing_regenerate is None:

        @command(
            name="rsqregenerate",
            description=(
                "Regenerate today's remaining "
                "automatic RSQ schedule."
            ),
        )
        async def rsqregenerate(
            interaction: discord.Interaction,
        ):

            if interaction.guild is None:

                await interaction.response.send_message(
                    (
                        "This command must be used "
                        "inside a server."
                    ),
                    ephemeral=True,
                )

                return

            if (
                not interaction.user
                .guild_permissions
                .administrator
            ):

                await interaction.response.send_message(
                    (
                        "You do not have permission "
                        "to regenerate the RSQ schedule."
                    ),
                    ephemeral=True,
                )

                return

            embed = discord.Embed(
                title=(
                    "🎲 Regenerate RSQ Schedule?"
                ),
                description=(
                    "This will delete today's "
                    "**remaining pending RSQ slots** "
                    "and generate new ones using the "
                    "current `rsq_config.py` settings.\n\n"
                    "**It will NOT remove:**\n"
                    "• already-posted RSQs\n"
                    "• missed slots\n"
                    "• skipped slots\n"
                    "• RSQ history\n\n"
                    "Are you sure?"
                ),
                color=(
                    discord.Color.orange()
                ),
            )

            view = (
                RsqRegenerateConfirmView(
                    scheduler=(
                        scheduler
                    ),
                    owner_id=(
                        interaction.user.id
                    ),
                )
            )

            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True,
            )