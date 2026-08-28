import discord


async def add_reaction(
    message: discord.Message,
    emoji: str
):
    try:
        await message.add_reaction(emoji)
    except discord.HTTPException:
        pass


async def remove_bot_reaction(
    client: discord.Client,
    message: discord.Message,
    emoji: str
):
    try:
        if client.user is not None:
            await message.remove_reaction(
                emoji,
                client.user
            )

    except discord.HTTPException:
        pass