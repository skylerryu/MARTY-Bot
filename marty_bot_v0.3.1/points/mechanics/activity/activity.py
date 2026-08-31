import time
import discord

from points.points_operations.add_points import (
    add_points,
)

from points.progressions.levels.level_up_display import (
    build_level_up_embed,
)

from points.progressions.ranks.rank_up_display import (
    build_rank_up_embed,
)

from points.progressions.progressions import (
    combine_progression_changes,
)

from points.mechanics.activity.activity_config import (
    ACTIVITY_POINTS,
    ACTIVITY_COOLDOWN_SECONDS,
    MINIMUM_MESSAGE_LENGTH,
)

from points.mechanics.activity.activity_streaks import (
    process_activity_streak,
)


class ActivityTracker:
    def __init__(self):
        self.last_award_times = {}


    # ==================================================
    # PROCESS MESSAGE
    # ==================================================


    async def process_message(
        self,
        message: discord.Message,
    ):
        """
        Process a Discord message and determine
        whether it qualifies for Activity points.
        """

        # Ignore bot messages.
        if message.author.bot:
            return

        # Ignore direct messages.
        if message.guild is None:
            return

        content = message.content.strip()

        # Ignore empty messages.
        if not content:
            return

        # Ignore messages that are too short.
        if len(content) < MINIMUM_MESSAGE_LENGTH:
            return

        # Ignore messages containing no
        # letters or numbers.
        if not any(
            character.isalnum()
            for character in content
        ):
            return

        user_key = (
            message.guild.id,
            message.author.id,
        )

        current_time = time.monotonic()

        last_award_time = (
            self.last_award_times.get(
                user_key
            )
        )

        # --------------------------------------------------
        # COOLDOWN
        # --------------------------------------------------

        if last_award_time is not None:

            seconds_since_last_award = (
                current_time
                - last_award_time
            )

            if (
                seconds_since_last_award
                < ACTIVITY_COOLDOWN_SECONDS
            ):
                return

        # --------------------------------------------------
        # NORMAL ACTIVITY POINT
        # --------------------------------------------------

        activity_progression = await add_points(
            guild_id=message.guild.id,
            user_id=message.author.id,
            username=message.author.display_name,
            amount=ACTIVITY_POINTS,
            reason="activity",
        )

        # Start the normal Activity cooldown
        # immediately after the point is awarded.
        self.last_award_times[
            user_key
        ] = current_time

        progression = activity_progression

        # --------------------------------------------------
        # HIDDEN WEEKLY STREAK
        # --------------------------------------------------

        streak_bonus = (
            await process_activity_streak(
                guild_id=message.guild.id,
                user_id=message.author.id,
            )
        )

        if streak_bonus > 0:

            streak_progression = (
                await add_points(
                    guild_id=message.guild.id,
                    user_id=message.author.id,
                    username=(
                        message.author.display_name
                    ),
                    amount=streak_bonus,
                    reason="activity_streak",
                )
            )

            progression = (
                combine_progression_changes(
                    activity_progression,
                    streak_progression,
                )
            )

        # --------------------------------------------------
        # PRIVATE LEVEL UP
        # --------------------------------------------------

        if progression["leveled_up"]:

            level_up_embed = (
                build_level_up_embed(
                    old_level=progression[
                        "old_level"
                    ],
                    new_level=progression[
                        "new_level"
                    ],
                )
            )

            try:
                await message.author.send(
                    embed=level_up_embed
                )

            except discord.Forbidden:
                pass

        # --------------------------------------------------
        # PUBLIC RANK UP
        # --------------------------------------------------

        if progression["ranked_up"]:

            rank_up_embed = (
                build_rank_up_embed(
                    username=(
                        message.author.display_name
                    ),
                    new_rank=progression[
                        "new_rank"
                    ],
                    new_level=progression[
                        "new_level"
                    ],
                )
            )

            try:
                await message.channel.send(
                    embed=rank_up_embed
                )

            except discord.Forbidden:
                pass