import discord


# ==================================================
# LEVEL UP DISPLAY
# ==================================================


def build_level_up_embed(
    old_level: int,
    new_level: int,
) -> discord.Embed:
    """
    Build the private display shown when
    a user levels up.
    """

    if new_level == old_level + 1:
        description = (
            f"You reached **Level {new_level}**!"
        )

    else:
        description = (
            f"You advanced from **Level {old_level}** "
            f"to **Level {new_level}**!"
        )

    embed = discord.Embed(
        title="⬆️ LEVEL UP!",
        description=description,
    )

    return embed