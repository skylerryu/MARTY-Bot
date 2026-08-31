import asyncio

from datetime import (
    datetime,
    time,
    timedelta,
    timezone,
)
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks

from data.patient_assessment_db import (
    count_active_sessions_for_scenario,
    get_active_scenario_for_date,
    get_expired_posted_assessment_scenarios,
    set_assessment_message_id,
    supersede_assessment_scenario,
)
from points.mechanics.patient_assessment.assessment_config import (
    ASSESSMENT_ENABLED,
    ASSESSMENT_POST_HOUR,
    ASSESSMENT_POST_MINUTE,
    ASSESSMENT_RECOVERY_CHECK_SECONDS,
    ASSESSMENT_TIMEZONE,
    ASSESSMENT_VISIBLE_MESSAGE_COUNT,
)
from points.mechanics.patient_assessment.assessment_display import (
    build_assessment_public_embed,
)
from points.mechanics.patient_assessment.assessment_scenarios import (
    generate_and_save_daily_scenario,
)
from points.mechanics.patient_assessment.assessment_ui import (
    AssessmentPublicView,
)


ASSESSMENT_TIMEZONE_INFO = ZoneInfo(
    ASSESSMENT_TIMEZONE
)

ASSESSMENT_POST_TIME = time(
    hour=ASSESSMENT_POST_HOUR,
    minute=ASSESSMENT_POST_MINUTE,
    tzinfo=ASSESSMENT_TIMEZONE_INFO,
)


if ASSESSMENT_VISIBLE_MESSAGE_COUNT < 1:
    raise ValueError(
        "ASSESSMENT_VISIBLE_MESSAGE_COUNT must be at least 1."
    )


# ==================================================
# PERIOD HELPERS
# ==================================================


def get_current_assessment_local_time() -> datetime:
    return datetime.now(
        ASSESSMENT_TIMEZONE_INFO
    )


def get_next_assessment_deadline(
    now: datetime | None = None,
) -> datetime:
    if now is None:
        now = get_current_assessment_local_time()

    deadline = datetime.combine(
        now.date(),
        time(
            ASSESSMENT_POST_HOUR,
            ASSESSMENT_POST_MINUTE,
        ),
        tzinfo=ASSESSMENT_TIMEZONE_INFO,
    )

    if now >= deadline:
        deadline += timedelta(days=1)

    return deadline


def get_current_assessment_period() -> tuple[str, str]:
    deadline = get_next_assessment_deadline()

    scenario_date = (
        deadline
        - timedelta(days=1)
    ).date().isoformat()

    expires_at = deadline.astimezone(
        timezone.utc
    ).isoformat()

    return scenario_date, expires_at


# ==================================================
# SCHEDULER
# ==================================================


class AssessmentScheduler:
    def __init__(
        self,
        bot: discord.Client,
        guild_id: int,
        channel_id: int,
    ):
        self.bot = bot
        self.guild_id = guild_id
        self.channel_id = channel_id
        self._post_lock = asyncio.Lock()

    def start(self):
        if not ASSESSMENT_ENABLED:
            return

        if not self.daily_assessment_post.is_running():
            self.daily_assessment_post.start()

        if not self.assessment_recovery_loop.is_running():
            self.assessment_recovery_loop.start()

    def stop(self):
        if self.daily_assessment_post.is_running():
            self.daily_assessment_post.cancel()

        if self.assessment_recovery_loop.is_running():
            self.assessment_recovery_loop.cancel()

    @tasks.loop(time=ASSESSMENT_POST_TIME)
    async def daily_assessment_post(self):
        await self.ensure_today_assessment_posted(
            require_post_time=False
        )

    @daily_assessment_post.before_loop
    async def before_daily_assessment_post(self):
        await self.bot.wait_until_ready()

        await self.ensure_today_assessment_posted(
            require_post_time=True
        )

    @daily_assessment_post.error
    async def daily_assessment_post_error(
        self,
        error: Exception,
    ):
        print(
            "Patient assessment scheduler error: "
            f"{error!r}"
        )

    @tasks.loop(
        seconds=ASSESSMENT_RECOVERY_CHECK_SECONDS
    )
    async def assessment_recovery_loop(self):
        if self._post_time_has_arrived():
            await self.ensure_today_assessment_posted(
                require_post_time=False
            )

    @assessment_recovery_loop.before_loop
    async def before_assessment_recovery_loop(self):
        await self.bot.wait_until_ready()

    @assessment_recovery_loop.error
    async def assessment_recovery_loop_error(
        self,
        error: Exception,
    ):
        print(
            "Patient assessment recovery loop error: "
            f"{error!r}"
        )

    async def _get_channel(self):
        channel = self.bot.get_channel(
            self.channel_id
        )

        if channel is not None:
            return channel

        try:
            return await self.bot.fetch_channel(
                self.channel_id
            )
        except (
            discord.Forbidden,
            discord.NotFound,
            discord.HTTPException,
        ) as error:
            print(
                "Patient assessment scheduler could not "
                "access the channel: "
                f"{error!r}"
            )
            return None

    def _post_time_has_arrived(self) -> bool:
        now = get_current_assessment_local_time()

        return (
            now.hour,
            now.minute,
        ) >= (
            ASSESSMENT_POST_HOUR,
            ASSESSMENT_POST_MINUTE,
        )

    async def ensure_today_assessment_posted(
        self,
        require_post_time: bool = True,
    ) -> bool:
        if not ASSESSMENT_ENABLED:
            return False

        async with self._post_lock:
            if (
                require_post_time
                and not self._post_time_has_arrived()
            ):
                return False

            scenario_date, expires_at = (
                get_current_assessment_period()
            )

            scenario = (
                await get_active_scenario_for_date(
                    guild_id=self.guild_id,
                    scenario_date=scenario_date,
                )
            )

            if scenario is None:
                try:
                    scenario = (
                        await generate_and_save_daily_scenario(
                            guild_id=self.guild_id,
                            channel_id=self.channel_id,
                            scenario_date=scenario_date,
                            expires_at=expires_at,
                        )
                    )
                except Exception as error:
                    print(
                        "Patient assessment scenario generation error: "
                        f"{error!r}"
                    )
                    return False

            if scenario["message_id"] is not None:
                await self._enforce_message_retention()
                return False

            posted = await self._post_scenario(
                scenario
            )

            if not posted:
                return False

            await self._enforce_message_retention()
            return True

    async def _post_scenario(
        self,
        scenario: dict,
    ) -> bool:
        channel = await self._get_channel()

        if channel is None:
            return False

        try:
            message = await channel.send(
                embed=build_assessment_public_embed(
                    scenario
                ),
                view=AssessmentPublicView(
                    scenario_id=scenario["id"]
                ),
            )
        except (
            discord.Forbidden,
            discord.HTTPException,
        ) as error:
            print(
                "Patient assessment scheduler could not post: "
                f"{error!r}"
            )
            return False

        try:
            await set_assessment_message_id(
                scenario_id=scenario["id"],
                message_id=message.id,
            )
        except Exception:
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            raise

        scenario["message_id"] = message.id

        print(
            "Patient assessment scheduler: "
            f"posted scenario #{scenario['id']} "
            f"({scenario['scenario_type']})."
        )

        return True

    async def _enforce_message_retention(self):
        expired = (
            await get_expired_posted_assessment_scenarios(
                guild_id=self.guild_id
            )
        )

        # One slot is occupied by the current assessment.
        keep_expired = max(
            0,
            ASSESSMENT_VISIBLE_MESSAGE_COUNT - 1,
        )

        retained = expired[:keep_expired]
        remove = expired[keep_expired:]

        for old in retained:
            await self._mark_old_message_closed(
                old
            )

        for old in remove:
            await self._delete_old_message(
                old
            )

    async def _mark_old_message_closed(
        self,
        old: dict,
    ):
        from data.patient_assessment_db import (
            get_assessment_scenario,
        )

        scenario = await get_assessment_scenario(
            old["id"]
        )

        if scenario is None:
            return

        channel = self.bot.get_channel(
            old["channel_id"]
        )

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(
                    old["channel_id"]
                )
            except (
                discord.Forbidden,
                discord.NotFound,
                discord.HTTPException,
            ):
                return

        try:
            message = await channel.fetch_message(
                old["message_id"]
            )

            await message.edit(
                embed=build_assessment_public_embed(
                    scenario,
                    closed=True,
                )
            )
        except discord.NotFound:
            await set_assessment_message_id(
                scenario_id=old["id"],
                message_id=None,
            )
        except (
            discord.Forbidden,
            discord.HTTPException,
        ):
            return

    async def _delete_old_message(
        self,
        old: dict,
    ):
        channel = self.bot.get_channel(
            old["channel_id"]
        )

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(
                    old["channel_id"]
                )
            except (
                discord.Forbidden,
                discord.NotFound,
                discord.HTTPException,
            ):
                return

        gone = False

        try:
            message = await channel.fetch_message(
                old["message_id"]
            )
            await message.delete()
            gone = True
        except discord.NotFound:
            gone = True
        except (
            discord.Forbidden,
            discord.HTTPException,
        ) as error:
            print(
                "Patient assessment scheduler could not "
                f"delete old scenario #{old['id']}: "
                f"{error!r}"
            )

        if gone:
            await set_assessment_message_id(
                scenario_id=old["id"],
                message_id=None,
            )

    async def regenerate_today(self) -> dict:
        """
        Replace today's public scenario for admin testing.

        Regeneration is refused while any student has an
        active session on the current scenario so their
        assessment cannot be orphaned.
        """
        async with self._post_lock:
            scenario_date, expires_at = (
                get_current_assessment_period()
            )

            existing = (
                await get_active_scenario_for_date(
                    guild_id=self.guild_id,
                    scenario_date=scenario_date,
                )
            )

            if existing is not None:
                active_sessions = (
                    await count_active_sessions_for_scenario(
                        existing["id"]
                    )
                )

                if active_sessions > 0:
                    return {
                        "status": "active_sessions",
                        "count": active_sessions,
                        "scenario": existing,
                    }

                if existing["message_id"] is not None:
                    channel = await self._get_channel()

                    if channel is not None:
                        try:
                            message = await channel.fetch_message(
                                existing["message_id"]
                            )
                            await message.delete()
                        except discord.NotFound:
                            pass
                        except (
                            discord.Forbidden,
                            discord.HTTPException,
                        ) as error:
                            return {
                                "status": "discord_error",
                                "error": repr(error),
                            }

                await supersede_assessment_scenario(
                    existing["id"]
                )

            try:
                scenario = (
                    await generate_and_save_daily_scenario(
                        guild_id=self.guild_id,
                        channel_id=self.channel_id,
                        scenario_date=scenario_date,
                        expires_at=expires_at,
                    )
                )
            except Exception as error:
                return {
                    "status": "generation_error",
                    "error": repr(error),
                }

            if not await self._post_scenario(
                scenario
            ):
                return {
                    "status": "post_error",
                }

            await self._enforce_message_retention()

            return {
                "status": "ok",
                "scenario": scenario,
            }
