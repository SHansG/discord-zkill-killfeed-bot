import discord
import config
from discord import app_commands
from discord.ext import commands


class Settings(commands.Cog, name="settings"):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.description = "This category is only available to admins."
    
    @commands.hybrid_group(
        name="settings",
        aliases=["sett"],
        invoke_without_command=True
    )
    async def settings(self, ctx: commands.Context):
        await ctx.send(f"test", ephemeral=True)

    @settings.command(name="prefix", aliases=["pre"])
    @commands.has_permissions(manage_guild=True)
    # @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def prefix(self, ctx: commands.Context, prefix: str):
        """Change default prefix for message commands"""
        old_prefix = config.settings.bot_prefix
        config.update_settings(ctx.guild.id, {"prefix":prefix})
        await ctx.send(f"changing prefix: {old_prefix} -> {prefix}", ephemeral=True)

    @settings.command(name='view', aliases=['v'])
    @commands.has_permissions(manage_guild=True)
    async def view(self, ctx: commands.Context) -> None:
        """Show bot's settings"""
        settings = config.get_settings(ctx.guild.id)
        await ctx.send(f"```py\n{settings}```", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Settings(bot))