import discord


# ==================================================
# M.A.R.T.Y. CHANNEL LOCKS
# ==================================================

# Keeps track of permission changes made by M.A.R.T.Y.
#
# Key:
# (guild_id, channel_id, user_id)
#
# Value:
# The student's original Send Messages setting:
#
# True  = explicitly allowed
# False = explicitly denied
# None  = inherited from roles

marty_channel_locks = {}


# ==================================================
# LOCK STUDENT
# ==================================================

async def lock_member_from_question_channel(
    channel: discord.TextChannel,
    member: discord.Member
) -> bool:
    """
    Prevent a student from sending additional messages
    in the question channel after using their attempts.

    Returns True if the lock succeeded.
    """

    key = (
        channel.guild.id,
        channel.id,
        member.id
    )

    # M.A.R.T.Y. already locked this student.
    if key in marty_channel_locks:
        return True

    # Get the student's existing channel-specific
    # permission overwrite.
    overwrite = channel.overwrites_for(
        member
    )

    # Remember what Send Messages was before
    # M.A.R.T.Y. changes it.
    original_send_messages = (
        overwrite.send_messages
    )

    # Prevent further messages.
    overwrite.send_messages = False

    try:

        await channel.set_permissions(
            member,
            overwrite=overwrite,
            reason=(
                "M.A.R.T.Y. question attempt "
                "limit reached"
            )
        )

    except discord.HTTPException as error:

        print(
            f"Could not lock "
            f"{member.display_name} "
            f"from #{channel.name}: "
            f"{error}"
        )

        return False

    # Only save the lock after Discord confirms
    # that the permission change succeeded.
    marty_channel_locks[key] = (
        original_send_messages
    )

    print(
        f"Locked {member.display_name} "
        f"from #{channel.name}."
    )

    return True


# ==================================================
# RESTORE STUDENTS
# ==================================================

async def restore_question_channel_locks(
    guild: discord.Guild,
    channel: discord.TextChannel
) -> list[int]:
    """
    Restore everyone M.A.R.T.Y. locked in this channel.

    This should run before the next question is posted.

    Returns a list of user IDs that could not
    be restored.
    """

    matching_keys = [
        key
        for key in marty_channel_locks
        if (
            key[0] == guild.id
            and key[1] == channel.id
        )
    ]

    failed_restores = []

    for key in matching_keys:

        (
            guild_id,
            channel_id,
            user_id
        ) = key

        original_send_messages = (
            marty_channel_locks[key]
        )

        # ------------------------------------------
        # FIND MEMBER
        # ------------------------------------------

        member = guild.get_member(
            user_id
        )

        # If they are not cached, ask Discord.
        if member is None:

            try:

                member = await guild.fetch_member(
                    user_id
                )

            except discord.NotFound:

                # Student left the server.
                # Nothing needs to be restored.
                del marty_channel_locks[key]

                continue

            except discord.HTTPException as error:

                print(
                    f"Could not retrieve member "
                    f"{user_id}: {error}"
                )

                failed_restores.append(
                    user_id
                )

                continue

        # ------------------------------------------
        # RESTORE ORIGINAL PERMISSION
        # ------------------------------------------

        overwrite = channel.overwrites_for(
            member
        )

        overwrite.send_messages = (
            original_send_messages
        )

        try:

            # If M.A.R.T.Y.'s change was the only
            # channel-specific permission, remove
            # the now-empty overwrite entirely.
            if overwrite.is_empty():

                await channel.set_permissions(
                    member,
                    overwrite=None,
                    reason=(
                        "New M.A.R.T.Y. question "
                        "released"
                    )
                )

            else:

                await channel.set_permissions(
                    member,
                    overwrite=overwrite,
                    reason=(
                        "New M.A.R.T.Y. question "
                        "released"
                    )
                )

        except discord.HTTPException as error:

            print(
                f"Could not unlock "
                f"{member.display_name} "
                f"in #{channel.name}: "
                f"{error}"
            )

            failed_restores.append(
                user_id
            )

            continue

        print(
            f"Unlocked {member.display_name} "
            f"in #{channel.name}."
        )

        del marty_channel_locks[key]

    return failed_restores


# ==================================================
# DELETE EXTRA MESSAGES
# ==================================================

async def delete_extra_question_message(
    message: discord.Message
) -> bool:
    """
    Delete a message sent after the student has
    already used their allowed question attempts.

    This catches messages that slip through before
    Discord finishes applying the channel lock.
    """

    try:

        await message.delete()

        print(
            f"Deleted extra question message from "
            f"{message.author.display_name}."
        )

        return True

    except discord.HTTPException as error:

        print(
            f"Could not delete extra message from "
            f"{message.author.display_name}: "
            f"{error}"
        )

        return False