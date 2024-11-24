from discord.ext import commands
import config

class ChannelEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Triggered when a channel is deleted from a guild."""
        print(f"Channel '{channel.name}' was deleted from guild '{channel.guild.name}'")
        
        if channel.guild.id in config.GUILD_SETTINGS:
            guild_settings = config.GUILD_SETTINGS[channel.guild.id]
            if str(channel.id) in guild_settings["killfeed_channels"]:
                del guild_settings["killfeed_channels"][str(channel.id)]
                config.update_settings(channel.guild.id, guild_settings)
                print(f"Removed channel {channel.id} from killfeed settings.")

    @commands.Cog.listener()
    async def on_ready(self):
        """Triggered when the bot is ready to validate killfeed channels."""
        await self.validate_killfeed_channels()

    async def validate_killfeed_channels(self):
        """Validate killfeed channels across all guilds on startup."""
        for guild in self.bot.guilds:
            if guild.id in config.GUILD_SETTINGS:
                guild_settings = config.GUILD_SETTINGS[guild.id]
                killfeed_channels = guild_settings.get("killfeed_channels", {})
                to_remove = []

                # Check if each channel in killfeed_channels exists in the guild
                for channel_id in list(killfeed_channels.keys()):
                    channel = guild.get_channel(int(channel_id))  # Check if channel exists
                    if not channel:  # If the channel is None, it doesn't exist
                        to_remove.append(channel_id)

                # Remove non-existent channels from the settings
                for channel_id in to_remove:
                    del killfeed_channels[channel_id]
                    print(f"Removed non-existent channel {channel_id} from killfeed settings for guild {guild.name}")

                # Update the settings if changes were made
                if to_remove:
                    config.update_settings(guild.id, guild_settings)
                    print(f"Updated settings for guild {guild.name}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChannelEvents(bot))