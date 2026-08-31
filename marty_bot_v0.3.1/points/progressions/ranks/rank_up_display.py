import discord


# ==================================================
# RANK UP DISPLAY
# ==================================================


def build_rank_up_embed(
    username: str,
    new_rank: dict,
    new_level: int,
) -> discord.Embed:
    """
    Build the public display shown when
    a user ranks up.
    """

    embed = discord.Embed(
        title="🎉 RANK UP!",
        description=(
            f"**{username}** has been promoted to\n"
            f"**{new_rank['name']}**!"
        ),
    )

    embed.add_field(
        name="Level",
        value=f"**{new_level}**",
        inline=True,
    )

    return embed