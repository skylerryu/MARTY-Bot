import discord


# ==================================================
# LEVEL UP DISPLAY
# ==================================================


def build_level_up_embed(
    old_level: int,
    new_level: int,
) -> discord.Embed:
    """
    Build the display shown when
    a user levels up.
    """

    if new_level == old_level + 1:
        description = (
            "You've earned enough XP to advance!\n\n"
            f"## 🎉 Level {new_level}"
        )

    else:
        description = (
            "You've earned enough XP to advance "
            "multiple levels!\n\n"
            f"## 🎉 Level {old_level} → Level {new_level}"
        )

    embed = discord.Embed(
        title="⬆️ LEVEL UP!",
        description=description,
        color=discord.Color.gold(),
    )

    embed.add_field(
        name="Previous Level",
        value=f"**Level {old_level}**",
        inline=True,
    )

    embed.add_field(
        name="New Level",
        value=f"**Level {new_level}**",
        inline=True,
    )

    embed.set_footer(
        text="Keep earning M.A.R.T.Y. points!"
    )

    return embed