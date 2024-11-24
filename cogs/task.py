from typing import Any, Coroutine
import discord


from discord.ext import commands, tasks
import config

class Task(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.activity_update.start()

        self.act_type = {
             "play": discord.ActivityType.playing,
             "listen": discord.ActivityType.listening,
             "watch": discord.ActivityType.watching,
             "stream": discord.ActivityType.streaming
        }
        
        self.current_act = 0
        # self.placeholder = Placeholders(bot)

    def cog_unload(self):
         self.activity_update.cancel()

    @tasks.loop(minutes=1.0)
    async def activity_update(self):
        await self.bot.wait_until_ready()

        try:
                act_data = config.settings.activity[(self.current_act + 1) % len(config.settings.activity) - 1]
                act_original = self.bot.activity
                act_type = self.act_type.get(list(act_data.keys())[0].lower(), discord.ActivityType.playing)
                act_name = list(act_data.values())[0]

                if act_original.type != act_type or act_original.name != act_name:
                    new_act = discord.Activity(type=act_type, name=act_name)
                    await self.bot.change_presence(activity=new_act)
                    self.current_act = (self.current_act + 1) % len(config.settings.activity)

        except Exception as e:
            print(f"Error in activity_update: {e}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Task(bot))