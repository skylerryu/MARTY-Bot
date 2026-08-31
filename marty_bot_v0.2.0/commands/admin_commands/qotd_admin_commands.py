import discord

from discord import app_commands

from commands.command_helpers import (
    make_command,
)

from points.mechanics.question_of_the_day.qotd_questions import (
    delete_qotd as delete_qotd_record,
    get_active_qotd,
)


# ==================================================
# REGISTER ADMIN QOTD COMMANDS
# ==================================================


def register_qotd_admin_commands(
    tree: app_commands.CommandTree,
    guild: discord.Object,
):

    command = make_command(
        tree=tree,
        guild=guild,
    )


    # ==================================================
    # DELETE QOTD
    # ==================================================


    @command(
        name="deleteqotd",
        description=(
            "Delete the currently active "
            "Question of the Day."
        ),
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def delete_qotd(
        interaction: discord.Interaction,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                (
                    "This command must be used "
                    "in a server."
                ),
                ephemeral=True,
            )

            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )


        # ==================================================
        # ACTIVE QOTD
        # ==================================================


        qotd = await get_active_qotd(
            guild_id=interaction.guild.id,
        )

        if qotd is None:

            await interaction.followup.send(
                (
                    "There is no active "
                    "Question of the Day to delete."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # DELETE DISCORD MESSAGE
        # ==================================================


        message_id = (
            qotd["message_id"]
        )

        if message_id is not None:

            channel = (
                interaction.client.get_channel(
                    qotd["channel_id"]
                )
            )

            if channel is None:

                try:

                    channel = (
                        await interaction.client.fetch_channel(
                            qotd["channel_id"]
                        )
                    )

                except (
                    discord.Forbidden,
                    discord.NotFound,
                    discord.HTTPException,
                ) as error:

                    print(
                        "Delete QoTD channel error: "
                        f"{error!r}"
                    )

                    await interaction.followup.send(
                        (
                            "I couldn't access the "
                            "QoTD channel, so I did "
                            "not delete the database "
                            "record."
                        ),
                        ephemeral=True,
                    )

                    return

            try:

                message = (
                    await channel.fetch_message(
                        message_id
                    )
                )

                await message.delete()

            except discord.NotFound:

                pass

            except (
                discord.Forbidden,
                discord.HTTPException,
            ) as error:

                print(
                    "Delete QoTD message error: "
                    f"{error!r}"
                )

                await interaction.followup.send(
                    (
                        "I couldn't delete the "
                        "QoTD Discord message, so "
                        "I did not delete its "
                        "database record."
                    ),
                    ephemeral=True,
                )

                return


        # ==================================================
        # DELETE DATABASE RECORD
        # ==================================================


        await delete_qotd_record(
            qotd_id=qotd["id"]
        )

        await interaction.followup.send(
            (
                f"Deleted the active QoTD "
                f"(QoTD #{qotd['id']})."
            ),
            ephemeral=True,
        )


    # ==================================================
    # NEW QOTD
    # ==================================================


    @command(
        name="newqotd",
        description=(
            "Immediately generate a new "
            "Question of the Day."
        ),
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def new_qotd(
        interaction: discord.Interaction,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                (
                    "This command must be used "
                    "in a server."
                ),
                ephemeral=True,
            )

            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )


        # ==================================================
        # EXISTING ACTIVE QOTD
        # ==================================================


        existing_qotd = (
            await get_active_qotd(
                guild_id=interaction.guild.id,
            )
        )

        if existing_qotd is not None:

            await interaction.followup.send(
                (
                    "A Question of the Day is "
                    "already active.\n\n"
                    "Use `/deleteqotd` first, then "
                    "run `/newqotd`."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # SCHEDULER
        # ==================================================


        scheduler = getattr(
            interaction.client,
            "qotd_scheduler",
            None,
        )

        if scheduler is None:

            await interaction.followup.send(
                (
                    "The QoTD scheduler could not "
                    "be found on the bot."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # CREATE NOW
        # ==================================================


        try:

            posted = (
                await scheduler.ensure_today_qotd_posted(
                    require_post_time=False,
                )
            )

        except Exception as error:

            print(
                "New QoTD admin command error: "
                f"{error!r}"
            )

            await interaction.followup.send(
                (
                    "Something went wrong while "
                    "generating the new QoTD."
                ),
                ephemeral=True,
            )

            return

        if not posted:

            await interaction.followup.send(
                (
                    "M.A.R.T.Y. did not post "
                    "a new QoTD."
                ),
                ephemeral=True,
            )

            return


        # ==================================================
        # GET NEW ACTIVE QOTD
        # ==================================================


        new_qotd = (
            await get_active_qotd(
                guild_id=interaction.guild.id,
            )
        )

        if new_qotd is None:

            await interaction.followup.send(
                "New QoTD posted.",
                ephemeral=True,
            )

            return

        await interaction.followup.send(
            (
                f"Generated and posted a new QoTD "
                f"(QoTD #{new_qotd['id']})."
            ),
            ephemeral=True,
        )