from discord.ext import commands
import config

class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.description = "Utility commands"
    
    @commands.hybrid_command(name='ping', aliases=(["pong"]))
    # @app_commands.describe(value="returns pong")
    async def ping(self, ctx: commands.Context):
        """Displays bot's latency"""
        await ctx.send(f"Latency: {self.bot.latency} ms")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))