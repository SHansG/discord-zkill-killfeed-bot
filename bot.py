import discord
from discord.ext import commands
import sys
import os
import config
import traceback

config.init()

class Miku(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_message(self, message: discord.Message, /) -> None:
        if message.author.bot or not message.guild:
            return False
        
        if self.user.id in message.raw_mentions and not message.mention_everyone:
            prefix = await self.command_prefix(self,message)
            if not prefix:
                return await message.channel.send("I don't have prefix set")
            await message.channel.send(f"My prefix is `{prefix}`")
        
        await self.process_commands(message)

    async def on_guild_join(self, guild):
        """Triggered when the bot joins a new guild."""
        config.add_settings(guild.id)
        print(f"The bot was added to {guild.name} server (ID: {guild.id})")

    async def on_guild_remove(self, guild):
        """Triggered when the bot is removed from a guild."""
        config.delete_settings(guild.id)
        print(f"The bot was removed from {guild.name} server (ID: {guild.id})")

    # async def on_guild_channel_delete(self, channel):
    #     """Triggered when a channel is deleted from a guild."""
    #     print(f"Channel '{channel.name}' was deleted from guild '{channel.guild.name}'")\
        
    #     if channel.guild.id in config.GUILD_SETTINGS:
    #         guild_settings = config.GUILD_SETTINGS[channel.guild.id]
    #         # killfeed_channels = guild_settings.get("killfeed_channel", {})

    #         if str(channel.id) in guild_settings["killfeed_channels"]:
    #             del guild_settings["killfeed_channels"][str(channel.id)]
    #             config.update_settings(channel.guild.id, guild_settings)

    # async def validate_killfeed_channels(self):
    #     """Validate killfeed channels across all guilds on startup."""
    #     for guild in self.guilds:
    #         if guild.id in config.GUILD_SETTINGS:
    #             guild_settings = config.GUILD_SETTINGS[guild.id]
    #             killfeed_channels = guild_settings.get("killfeed_channels", {})
    #             to_remove = []

    #             # Check if each channel in killfeed_channels exists in the guild
    #             for channel_id in list(killfeed_channels.keys()):
    #                 channel = guild.get_channel(int(channel_id))  # Check if channel exists
    #                 if not channel:  # If the channel is None, it doesn't exist
    #                     to_remove.append(channel_id)

    #             # Remove non-existent channels from the settings
    #             for channel_id in to_remove:
    #                 del killfeed_channels[channel_id]
    #                 print(f"Removed non-existent channel {channel_id} from killfeed settings for guild {guild.name}")

    #             # Update the settings if changes were made
    #             if to_remove:
    #                 config.update_settings(guild.id, guild_settings)
    #                 print(f"Updated settings for guild {guild.name}")

    async def setup_hook(self):
        for module in os.listdir(f"{config.ROOT_DIR}/cogs"):
            if module.endswith('.py'):
                try:
                    await self.load_extension(f"cogs.{module[:-3]}")
                    # print(f"cogs.{module[:-3]}")
                    print(f"Registered {module[:-3]} cog")
                except Exception as e:
                    print(traceback.format_exc())

        synced = await self.tree.sync()
        print(f"Total synced command(s): {len(synced)}")

    def get_guilds_list(self):
        return [guild.id for guild in self.guilds]

    async def on_ready(self):
        print("------------------")
        print(f"Logging As {self.user}")
        print(f"Bot ID: {self.user.id}")
        print("------------------")
        print(f"Discord Version: {discord.__version__}")
        print(f"Python Version: {sys.version}")
        print("------------------")

        config.tokens.client_id = self.user.id
        config.load_guilds_settings(self.get_guilds_list())
        # await self.validate_killfeed_channels()
        

class CommandCheck(discord.app_commands.CommandTree):
    
    async def interaction_check(self, interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in guilds!")

        return await super().interaction_check(interaction)

async def get_prefix(bot, message: discord.Message):
    settings = config.get_settings(message.guild.id)
    return settings.get("prefix", config.settings.bot_prefix)

intents = discord.Intents.default()
intents.message_content = True if config.settings.bot_prefix else False

bot = Miku(
    command_prefix=get_prefix,
    help_command=None,
    tree_cls=CommandCheck,
    activity=discord.Activity(type=discord.ActivityType.listening, name="Starting..."),
    case_insensitive=True,
    intents=intents
)

if __name__ == "__main__":
    bot.run(config.tokens.token, log_handler=None)