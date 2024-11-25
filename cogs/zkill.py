from typing import Any, Coroutine
import discord
from discord import app_commands
import asyncio
import json
import websockets
from collections import defaultdict

from discord.ext import commands
import config

class zKill(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot=bot
        self.websocket_url = config.websocket_url
        # self.guild_configs = {}
        self.subscription_counts = defaultdict(int) # tracks subscription usage counts
        self.subscription_channels = defaultdict(list) # maps subscriptions to channels
        self.killmail_queue = asyncio.Queue()
        # start tasks for websocket listener and queue processor
        self.websocket = None
        self.payload = {"action":"sub", "channel":"killstream"}

        # start tasks
        # self.loop = asyncio.get_event_loop()
        # self.loop.create_task(self.websocket_listener())
        # self.loop.create_task(self.queue_processor())
        self.websocket_task = None # websocket task
        self.queue_task = None # queue processing task

    async def start_tasks(self):
        """Start the WebSocket and queue tasks after bot is ready"""
        if not self.websocket_task:
            print("Starting WebSocket task...")
            self.websocket_task = self.bot.loop.create_task(self.websocket_listener())

        if not self.queue_task:
            print("Starting Queue Processor task...")
            self.queue_task = self.bot.loop.create_task(self.queue_processor())

    @commands.Cog.listener()
    async def on_ready(self):
        """Ensure tasks are started after the bot is fully ready."""
        # TODO: when you stop debugging autocompletion uncomment this.
        await self.start_tasks()

    def cog_unload(self):
        """Clean up tasks when the cog is unloaded."""
        if self.websocket_task:
            self.websocket_task.cancel()
        if self.queue_task:
            self.queue_task.cancel()

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    # async def cog_before_invoke(self, ctx: commands.Context):

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send('An error occurred: {}'.format(str(error)))

    
    async def websocket_listener(self):
        """Connect to the WebSocket and listen for data."""
        while True:
                try:
                    async with websockets.connect(self.websocket_url) as websocket:
                        self.websocket = websocket
                        print("Connected to WebSocket")
                        # subscribe with filters
                        # await self.update_subscriptions()
                        # TODO: update channels???
                        #Test payload
                        await self.websocket.send(json.dumps(self.payload))
                        while True:
                            try:
                                # Receive data from WebSocket
                                message = await websocket.recv()
                                data = json.loads(message)
                                # add to queue
                                await self.killmail_queue.put(data)
                            except websockets.ConnectionClosed as e:
                                print(f"Websocket closed: {e}")
                                break
                            except Exception as e:
                                print(f"Error receiving data: {e}")
                                break
                except Exception as e:
                    print(f"WebSocket connection error: {e}")

                #  Delay before reconnecting
                print("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    async def queue_processor(self):
        """Process killmails from the queue."""

        while True:
            # get a killmail
            killmail = await self.killmail_queue.get()

            # route the killmail to approprate channels
            await self.route_killmail(killmail)

            self.killmail_queue.task_done()

    # async def update_subscriptions(self):
    #     """Subscribe to new filters and manage reference counts."""
    #     # Extract all unique filters from guild configs
    #     current_filters = {
    #         (filters["websocket_channel"], filters["group_id"])
    #         for guild_id, guild_config in config.GUILD_SETTINGS.items()
    #         for filters in guild_config.get("killfeed_channels", {}).values()
    #     }

    #     # Unsubscribe from unused filters
    #     for subscription in list(self.subscription_counts.keys()):
    #         if subscription not in current_filters:
    #             await self.unsubscribe(subscription)

    #     # Subscribe to new filters
    #     for subscription in current_filters:
    #         if subscription not in self.subscription_counts:
    #             await self.subscribe(subscription)

    # async def subscribe(self, filters):
    #     """Send a subscription payload to the WebSocket and increment reference count."""
    #     if self.websocket:
    #         payload = {
    #             "action":"sub",
    #             "channel":f"{filters[0]}"
    #         }
    #         await self.websocket.send(json.dumps(payload))
    #         self.subscription_counts[filters] += 1
    #         print(f"Subscribed: {payload}")

    # async def unsubscribe(self, filters):
    #     """Send an unsubscribe payload to the WebSocket and decrement reference count."""
    #     if self.websocket and self.subscription_counts[filters] > 0:
    #         self.subscription_counts[filters] -= 1
    #         if self.subscription_counts[filters] == 0:
    #             payload = {
    #                 "action": "unsub",
    #                 "channel": f"{filters[0]}"
    #             }
    #             await self.websocket.send(json.dumps(payload))
    #             del self.subscription_counts[filters]
    #             print(f"Unsubscribed: {payload}")

    # async def update_channel_filters(self):
    #     """Updates adds/remove channel with filters and manage reference counts."""
    #     # Extract all unique filters from guild configs
    #     current_filters = {
    #         (filters["alliance_id"], filters['character_id'], filters['ship_type_id'], filters["group_id"], filters["is_npc"], filters["is_attacker"])
    #         for guild_id, guild_config in config.GUILD_SETTINGS.items()
    #         for filters in guild_config.get("killfeed_channels", {}).values()
    #     }

    #     # Unsubscribe from unused filters
    #     for subscription in list(self.subscription_counts.keys()):
    #         if subscription not in current_filters:
    #             await self.unsubscribe(subscription)

    #     # Subscribe to new filters
    #     for subscription in current_filters:
    #         if subscription not in self.subscription_counts:
    #             await self.subscribe(subscription)

    async def route_killmail(self, killmail):
        """Route received killmail to appropriate Discord channels."""

        victim = [killmail.get("victim", {})]
        attackers = killmail.get("attackers",[])
        solar_system_id = killmail.get("solar_system_id")

        location_data = config.location_lookup_dict.get(solar_system_id, {})
        region_id = location_data.get("regionID")
        constellation_id = location_data.get("constellationID")

        matching_channels = []
        for guild_id, guild_config in config.GUILD_SETTINGS.items():
            for channel_id, filters in guild_config.get("killfeed_channels", {}).items():
                # Determine the target for filtering (attacker or victim)
                filter_region_id = filters.get("region_id")
                filter_constellation_id = filters.get("constellation_id")
                filter_system_id = filters.get("solar_system_id")
                attackers_group_id_filter = filters.get("attacker_group_id", None)
                attackers_type_id_filter = filters.get("attacker_type_id", None)
                victim_group_id_filter = filters.get("victim_group_id", None)
                victim_type_id_filter = filters.get("victim_type_id", None)
                attacker_npc_filter = filters.get("attacker_npc", 0)

                # Match region_id if present in filters
                if filter_region_id and filter_region_id != region_id:
                    continue # Skip if region doesn't match

                # Match constellation_id if present in filters
                if filter_constellation_id and filter_constellation_id != constellation_id:
                    continue # Skip if constellation doesn't match

                # Match system_id if present in filters
                if filter_system_id and filter_system_id != solar_system_id:
                    continue # Skip if system doesn't match
                
                # Match victim_group_id using lookup_dict if specified
                victim_matched = True
                if victim_group_id_filter:
                    victim_matched = any(
                        config.entity_lookup_dict.get(entity.get("ship_type_id"), {}).get("groupID") == victim_group_id_filter 
                        for entity in victim
                    )
                
                # Match victim_type_id filter directly against ship_type_id
                if victim_type_id_filter and not any(entity.get("ship_type_id") == victim_type_id_filter for entity in victim):
                    victim_matched = False
                

                # Match attacker_group_id using lookup_dict if specified
                attacker_matched = True
                if attackers_group_id_filter:
                    attacker_matched = any(
                        config.entity_lookup_dict.get(entity.get("ship_type_id"), {}).get("groupID") == attackers_group_id_filter
                        for entity in attackers
                    )
                
                # Match attacker_type_id filter directly against ship_type_id
                if attackers_type_id_filter and not any(
                    entity.get("shipy_type_id") == attackers_type_id_filter for entity in attackers
                ):
                    attacker_matched = False

                # If apply_to_attacker is and is_npc is set, check attackers for NPCs
                if attacker_npc_filter == 1 and not any(
                        attacker.get("faction_id") 
                        for attacker in attackers
                    ):
                        attacker_matched = False
                
                # Check if either victim or attacker matches
                if victim_matched or attacker_matched:
                    matching_channels.append(channel_id)


        for channel_id in matching_channels:
            await self.send_to_channel(channel_id, killmail)

        # killmail_filters = (
        #     killmail.get("channel"),
        #     killmail.get("group_id"),
        # )

        # # Find channels associated with this filter
        # channels = [
        #     channel_id
        #     for guild_id, guild_config in config.GUILD_SETTINGS.items()
        #     for channel_id, channel_filters in guild_config.get("killfeed_channels", {}).items()
        #     if (
        #         (channel_filters['group_id'] == 0 and channel_filters["websocket_channel"] == killmail_filters[0]) or
        #         (channel_filters["group_id"] == killmail_filters[1] and channel_filters["websocket_channel"] == killmail_filters[0])
        #     )
        # ]

        # for channel_id in channels:
        #     await self.send_to_channel(channel_id, killmail)

    async def send_to_channel(self, channel_id, killmail):
        """Send the killmail to a specific Discord channel."""
        channel = await self.bot.fetch_channel(channel_id)
        message = killmail['zkb']['url']
        if channel:
            # print(f"killmail url: {killmail['url']} was sent to channel: {channel_id}")
            # await channel.send(killmail["url"])
            print(f"killmail url: {message} was sent to channel: {channel_id}")
            await channel.send(message)
        else:
            print(f"Channel ID {channel_id} not found or bot has no access.")

    async def location_filter_autocompletion(
            self,
            interaction: discord.Interaction,
            current: str
        ):
        """Generate filter type suggestions."""
        return [
            app_commands.Choice(name=k, value=k) 
            for k, v in config.filter_location_type_dict.items() if current.lower() in k.lower()
        ][:25]
    
    async def location_type_autocompletion(
            self,
            interaction: discord.Interaction,
            current: str
        ):
        # access the selected location filter from interaction.namespace
        selected_location_filter = interaction.namespace.location_filter

        # get lookup dict for selected location filter
        options = config.filter_location_type_dict.get(selected_location_filter)

        return [
            app_commands.Choice(name=k, value=k)
            for k, v in options.items() if current.lower() in k.lower()
        ][:25]

    async def victim_filter_autocompletion(
            self,
            interaction: discord.Interaction,
            current: str    
        ):
        return [
            app_commands.Choice(name=k, value=k)
            for k, v in config.filter_entity_type_dict.items() if current.lower() in k.lower()
        ][:25]

    async def victim_type_autocompletion(
            self,
            interaction: discord.Interaction,
            current: str
        ):
        # access the selected entity filter from interaction.namespace
        selected_entity_filter = interaction.namespace.victim_filter

        # get lookup dict for selected entity filter
        options = config.filter_entity_type_dict.get(selected_entity_filter)

        return [
            app_commands.Choice(name=k, value=k)
            for k, v in options.items() if current.lower() in k.lower()
        ][:25]

    async def attacker_filter_autocompletion(
            self,
            interaction: discord.Interaction,
            current: str      
        ):
        return [
            app_commands.Choice(name=k, value=k)
            for k, v in config.filter_entity_type_dict.items() if current.lower() in k.lower()
        ][:25]
    
    async def attacker_type_autocompletion(
            self,
            interaction: discord.Interaction,
            current: str
        ):
        # access the selected entity filter from interaction.namespace
        selected_entity_filter = interaction.namespace.attacker_filter

        # get lookup dict for selected entity filter
        options = config.filter_entity_type_dict.get(selected_entity_filter)

        return [
            app_commands.Choice(name=k, value=k)
            for k, v in options.items() if current.lower() in k.lower()
        ][:25]

    async def attacker_npc_autocompletion(
            self,
            interaction: discord.Interaction,
            current: str
        ):
        return [
            app_commands.Choice(name=k, value=k)
            for k,v in config.filter_attacker_npc_dict.items() if current.lower() in k.lower()
        ]

    # previously it wasnt showing autocomplete results for type_id due to wrong type (str changed to int)
    @app_commands.command(name='killfeed')
    @app_commands.autocomplete(
        location_filter=location_filter_autocompletion,
        location_name=location_type_autocompletion,
        victim_filter=victim_filter_autocompletion,
        victim_entity_name=victim_type_autocompletion,
        attacker_filter=attacker_filter_autocompletion,
        attacker_entity_name=attacker_type_autocompletion,
        attacker_npc=attacker_npc_autocompletion
    )
    @commands.has_permissions(manage_guild=True)
    async def broadcast_killfeed_to_channel(
            self, 
            interaction: discord.Interaction, 
            location_filter: str,
            location_name: str,
            victim_filter: str,
            victim_entity_name: str,
            attacker_filter: str,
            attacker_entity_name: str,
            attacker_npc: str,
        ) -> None:
        """adds killfeed broadcasting to text channel"""
        guild_id = interaction.guild.id
        channel = interaction.channel

        current_location_filter = config.filter_location_type_dict.get(location_filter)
        current_location_id = current_location_filter.get(location_name)
        current_victim_filter = config.filter_entity_type_dict.get(victim_filter)
        current_victim_entity_id = current_victim_filter.get(victim_entity_name)
        current_attacker_filter = config.filter_entity_type_dict.get(attacker_filter)
        current_attacker_entity_id = current_attacker_filter.get(attacker_entity_name)
        current_attacker_npc = config.filter_attacker_npc_dict.get(attacker_npc)

        current_settings = config.get_settings(guild_id)

        if str(channel.id) not in current_settings["killfeed_channels"]:
            current_settings["killfeed_channels"][str(channel.id)] = {
                    f"{location_filter.lower()}_id":current_location_id,
                    "attacker_npc": current_attacker_npc
                }
            
            if current_victim_entity_id != 0:
                current_settings["killfeed_channels"][str(channel.id)][f"{victim_filter.lower()}_id"]=current_victim_entity_id

            if current_attacker_entity_id != 0:
                current_settings["killfeed_channels"][str(channel.id)][f"{attacker_filter.lower()}_id"]=current_attacker_entity_id

            config.update_settings(guild_id, current_settings)
            # await self.update_subscriptions()
            await interaction.response.send_message(f"Text channel {channel.mention} has been assigned for killfeed broadcasting with parameters:\n```location_filter: {location_filter}\nlocation_type: {location_name}\nvictim_filter: {victim_filter}\nvictim_name: {victim_entity_name}\nattacker_filter: {attacker_filter}\nattacker_name: {attacker_entity_name}\nattacker_npc: {attacker_npc}```")
        else:
            await interaction.response.send_message(f'Text channel {channel.mention} has already been assigned for killfeed broadcasting.')


        # if str(channel.id) not in current_settings["killfeed_channels"]:
        #     current_settings["killfeed_channels"][str(channel.id)] = {
        #             "websocket_channel": f"{filter_type}:{type_id}",
        #             "group_id": group_id
        #         }

        #     config.update_settings(guild_id, current_settings)
        #     # await self.update_subscriptions()
        #     await interaction.response.send_message(f"```Text channel {channel.mention} has been assigned for killfeed broadcasting with parameters:\nfilter_type: {filter_type}\ntype_name:{current_filter_type}\ngroup_name:{config.id_group_dict.get(group_id)}```")
        # else:
        #     await interaction.response.send_message(f'Text channel {channel.mention} has already been assigned for killfeed broadcasting with parameters: ...')

    @app_commands.command(name='reset')
    @commands.has_permissions(manage_guild=True)
    async def reset(self, interaction: discord.Interaction):
        """removes killfeed broadcasting from text channel"""
        guild = interaction.guild
        channel = interaction.channel
        current_settings = config.get_settings(guild.id)
        if str(channel.id) in current_settings["killfeed_channels"]:
            del current_settings["killfeed_channels"][str(channel.id)]
            config.update_settings(guild.id, current_settings)
            # await self.update_subscriptions()
            await interaction.response.send_message(f"Channel {channel.mention} has been removed from killfeed.")
        else:
            await interaction.response.send_message(f"Channel {channel.mention} is not configured as a killfeed channel.")

    # @commands.command(name='', aliases=[''])
    # @commands.has_guild_permissions(manage_guild=True)
    # async def watchlist(self, ctx: commands.Context) -> None:
    #     """Pick text channel where watchlisted characters killfeed will be pushed"""
    #     pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(zKill(bot))