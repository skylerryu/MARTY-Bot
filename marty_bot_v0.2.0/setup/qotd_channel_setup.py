import discord


# ==================================================
# PERMISSION CHECK
# ==================================================


def _permissions_match(
    overwrite: discord.PermissionOverwrite,
    desired_permissions: dict,
) -> bool:
    """
    Return True if all QoTD permissions we care
    about already have the desired values.

    Permissions not managed by this setup are
    ignored.
    """

    for (
        permission_name,
        desired_value,
    ) in desired_permissions.items():

        current_value = getattr(
            overwrite,
            permission_name,
        )

        if current_value != desired_value:

            return False

    return True


# ==================================================
# APPLY DESIRED PERMISSIONS
# ==================================================


def _apply_permissions(
    overwrite: discord.PermissionOverwrite,
    desired_permissions: dict,
):
    """
    Apply the desired values to an existing
    permission overwrite.

    Any unrelated permissions are preserved.
    """

    for (
        permission_name,
        desired_value,
    ) in desired_permissions.items():

        setattr(
            overwrite,
            permission_name,
            desired_value,
        )


# ==================================================
# CONFIGURE QOTD CHANNEL
# ==================================================


async def configure_qotd_channel(
    bot: discord.Client,
    guild_id: int,
    channel_id: int,
) -> bool:
    """
    Verify and, if necessary, configure the
    Question of the Day channel.

    Normal members:
    - can view the channel
    - can read message history
    - cannot send messages
    - cannot create or use threads

    M.A.R.T.Y.:
    - can view the channel
    - can read message history
    - can send messages
    - can send embeds

    Existing unrelated permission settings are
    preserved.

    Discord permissions are only changed when
    the current configuration differs from the
    desired configuration.
    """


    # ==================================================
    # GUILD
    # ==================================================


    guild = bot.get_guild(
        guild_id
    )

    if guild is None:

        print(
            "QoTD channel setup: "
            "Guild could not be found."
        )

        return False


    # ==================================================
    # CHANNEL
    # ==================================================


    channel = guild.get_channel(
        channel_id
    )

    if channel is None:

        try:

            channel = (
                await bot.fetch_channel(
                    channel_id
                )
            )

        except (
            discord.Forbidden,
            discord.NotFound,
            discord.HTTPException,
        ) as error:

            print(
                "QoTD channel setup: "
                "Could not access the channel: "
                f"{error!r}"
            )

            return False


    # ==================================================
    # VERIFY TEXT CHANNEL
    # ==================================================


    if not isinstance(
        channel,
        discord.TextChannel,
    ):

        print(
            "QoTD channel setup: "
            "Configured QoTD channel is "
            "not a text channel."
        )

        return False


    # ==================================================
    # MARTY MEMBER
    # ==================================================


    marty = guild.me

    if marty is None:

        print(
            "QoTD channel setup: "
            "Could not find M.A.R.T.Y. "
            "in the server."
        )

        return False


    # ==================================================
    # DESIRED MEMBER PERMISSIONS
    # ==================================================


    member_permissions = {
        "view_channel": True,
        "read_message_history": True,
        "send_messages": False,
        "create_public_threads": False,
        "create_private_threads": False,
        "send_messages_in_threads": False,
    }


    # ==================================================
    # DESIRED MARTY PERMISSIONS
    # ==================================================


    marty_permissions = {
        "view_channel": True,
        "read_message_history": True,
        "send_messages": True,
        "embed_links": True,
    }


    # ==================================================
    # EVERYONE ROLE
    # ==================================================


    everyone = (
        guild.default_role
    )

    everyone_overwrite = (
        channel.overwrites_for(
            everyone
        )
    )


    # ==================================================
    # CHECK EVERYONE PERMISSIONS
    # ==================================================


    members_correct = (
        _permissions_match(
            overwrite=everyone_overwrite,
            desired_permissions=(
                member_permissions
            ),
        )
    )


    # ==================================================
    # CHECK MARTY PERMISSIONS
    # ==================================================


    marty_overwrite = (
        channel.overwrites_for(
            marty
        )
    )

    marty_correct = (
        _permissions_match(
            overwrite=marty_overwrite,
            desired_permissions=(
                marty_permissions
            ),
        )
    )


    # ==================================================
    # ALREADY CONFIGURED
    # ==================================================


    if (
        members_correct
        and marty_correct
    ):

        print(
            "QoTD channel setup: "
            "Permissions already configured."
        )

        return True


    # ==================================================
    # FIX MEMBER PERMISSIONS
    # ==================================================


    if not members_correct:

        _apply_permissions(
            overwrite=everyone_overwrite,
            desired_permissions=(
                member_permissions
            ),
        )

        try:

            await channel.set_permissions(
                everyone,
                overwrite=everyone_overwrite,
                reason=(
                    "M.A.R.T.Y. automatic QoTD "
                    "channel configuration"
                ),
            )

        except discord.Forbidden:

            print(
                "QoTD channel setup: "
                "M.A.R.T.Y. needs the "
                "Manage Channels permission."
            )

            return False

        except discord.HTTPException as error:

            print(
                "QoTD channel setup error "
                "while configuring members: "
                f"{error!r}"
            )

            return False

        print(
            "QoTD channel setup: "
            "Member permissions updated."
        )


    # ==================================================
    # FIX MARTY PERMISSIONS
    # ==================================================


    if not marty_correct:

        _apply_permissions(
            overwrite=marty_overwrite,
            desired_permissions=(
                marty_permissions
            ),
        )

        try:

            await channel.set_permissions(
                marty,
                overwrite=marty_overwrite,
                reason=(
                    "M.A.R.T.Y. automatic QoTD "
                    "channel configuration"
                ),
            )

        except discord.Forbidden:

            print(
                "QoTD channel setup: "
                "M.A.R.T.Y. could not configure "
                "its own channel permissions."
            )

            return False

        except discord.HTTPException as error:

            print(
                "QoTD channel setup error "
                "while configuring M.A.R.T.Y.: "
                f"{error!r}"
            )

            return False

        print(
            "QoTD channel setup: "
            "M.A.R.T.Y. permissions updated."
        )


    # ==================================================
    # SUCCESS
    # ==================================================


    print(
        "QoTD channel setup complete."
    )

    return True