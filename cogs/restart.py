import asyncio
import os
from datetime import datetime, time
import sys
from discord.ext import commands

class BotRestartManager(commands.Cog):
    def __init__(self, bot: commands.Bot, restart_time: str) -> None:
        self.bot = bot
        self.restart_hour, self.restart_minute = map(int, restart_time.split(":"))
        self.restart_task = self.bot.loop.create_task(self.restart_check_loop())

    async def restart_check_loop(self):
        while True:
            now = datetime.now()
            if now.time() >= time(self.restart_hour, self.restart_minute) and now.time() < time(self.restart_hour, self.restart_minute + 1):
                print("Restarting bot...")
                await self.restart_bot()
            await asyncio.sleep(60)  # Check every minute

    async def restart_bot(self):
        print("Performing cleanup before restart...")
        await self.bot.close()
        os.execv(sys.executable, ["python"] + sys.argv)

async def setup(bot: commands.Bot):
    restart_time = "03:00"
    await bot.add_cog(BotRestartManager(bot, restart_time))