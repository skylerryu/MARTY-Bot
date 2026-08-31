import discord


# ==================================================
# PERMISSION HELPERS
# ==================================================


def _permissions_match(
    overwrite: discord.PermissionOverwrite,
    desired_permissions: dict,
) -> bool:
    for permission_name, desired_value in (
        desired_permissions.items()
    ):
        if getattr(
            overwrite,
            permission_name,
        ) != desired_value:
            return False

    return True


def _apply_permissions(
    overwrite: discord.PermissionOverwrite,
    desired_permissions: dict,
):
    for permission_name, desired_value in (
        desired_permissions.items()
    ):
        setattr(
            overwrite,
            permission_name,
            desired_value,
        )


# ==================================================
# CONFIGURE CHANNEL
# ==================================================


async def configure_assessment_channel(
    bot: discord.Client,
    guild_id: int,
    channel_id: int,
) -> bool:
    """
    Make the patient-assessment channel read-only for
    normal members while preserving button interaction.
    """
    guild = bot.get_guild(
        guild_id
    )

    if guild is None:
        print(
            "Assessment channel setup: guild could not be found."
        )
        return False

    channel = guild.get_channel(
        channel_id
    )

    if channel is None:
        try:
            channel = await bot.fetch_channel(
                channel_id
            )
        except (
            discord.Forbidden,
            discord.NotFound,
            discord.HTTPException,
        ) as error:
            print(
                "Assessment channel setup: could not access channel: "
                f"{error!r}"
            )
            return False

    if not isinstance(
        channel,
        discord.TextChannel,
    ):
        print(
            "Assessment channel setup: configured channel is not a text channel."
        )
        return False

    marty = guild.me

    if marty is None:
        print(
            "Assessment channel setup: could not find MARTY in guild."
        )
        return False

    member_permissions = {
        "view_channel": True,
        "read_message_history": True,
        "send_messages": False,
        "create_public_threads": False,
        "create_private_threads": False,
        "send_messages_in_threads": False,
    }

    marty_permissions = {
        "view_channel": True,
        "read_message_history": True,
        "send_messages": True,
        "embed_links": True,
    }

    everyone = guild.default_role

    everyone_overwrite = channel.overwrites_for(
        everyone
    )
    marty_overwrite = channel.overwrites_for(
        marty
    )

    members_correct = _permissions_match(
        everyone_overwrite,
        member_permissions,
    )
    marty_correct = _permissions_match(
        marty_overwrite,
        marty_permissions,
    )

    if members_correct and marty_correct:
        print(
            "Assessment channel setup: permissions already configured."
        )
        return True

    if not members_correct:
        _apply_permissions(
            everyone_overwrite,
            member_permissions,
        )

        try:
            await channel.set_permissions(
                everyone,
                overwrite=everyone_overwrite,
                reason=(
                    "M.A.R.T.Y. automatic patient assessment "
                    "channel configuration"
                ),
            )
        except discord.Forbidden:
            print(
                "Assessment channel setup: MARTY needs Manage Channels."
            )
            return False
        except discord.HTTPException as error:
            print(
                "Assessment channel setup member error: "
                f"{error!r}"
            )
            return False

        print(
            "Assessment channel setup: member permissions updated."
        )

    if not marty_correct:
        _apply_permissions(
            marty_overwrite,
            marty_permissions,
        )

        try:
            await channel.set_permissions(
                marty,
                overwrite=marty_overwrite,
                reason=(
                    "M.A.R.T.Y. automatic patient assessment "
                    "channel configuration"
                ),
            )
        except discord.Forbidden:
            print(
                "Assessment channel setup: MARTY could not configure its own permissions."
            )
            return False
        except discord.HTTPException as error:
            print(
                "Assessment channel setup MARTY error: "
                f"{error!r}"
            )
            return False

        print(
            "Assessment channel setup: MARTY permissions updated."
        )

    print(
        "Assessment channel setup complete."
    )
    return True
