import aiohttp
import io
import json
from random import choice
import re

import discord
from discord.commands import slash_command, Option
from discord.ext.commands import Cog

import sys
sys.path.append('./utils')
import redwing_functions

with open('./data/aww_api_urls.json', 'r') as f:
    api_urls_json = json.load(f)
    aww_choices = sorted(list(api_urls_json.keys()))

with open('./data/guild_ids.txt', 'r') as f:
    guild_ids = [int(guild_id) for guild_id in f.read().strip().split(',')]


class Aww(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sad_channel = []
        self.sad_words = ["sad", "angry", "upset", "depressed", "miserable", "unhappy"]
        self.auto_messages = ["Sending you awws!", "Floof alert!", "Floof attack!", "Incoming awws!", "Incoming floof!",
                              "Cuteness comin' your way!", "Hope this makes your day a little brighter. ♥",
                              "You're as awesome as this ball of floof right here.", "We love you 3000! ♥",
                              "Here's a well-deserved dose of aww.", "An aww-pple a day keeps the doctor away. 🍎",
                              "Take a break and have some cuteness.", "Cute as a button, just like you. 😘",
                              "You are absolutely aww-some!", "Pet Avengers, assemble!",
                              "Higher, further, faster, cuter! ✨", "And now, for your moment of aww."]
        self.reply_to_sad = ["Hope this makes you feel better. ♥",
                             "Sorry to hear you're having a rough day. Hope this helps.",
                             "Sounds like you could use some love and awws. ♥",
                             "We're here for you. And so's this little guy. 🥰",
                             "It sounds like you need a hug. Can we give you one?",
                             "Sending you love and support! You'll get through this."]

        self.api_urls = api_urls_json

        bot.scheduler.add_job(self.check_elapsed_time, 'interval', minutes=30)

    async def check_elapsed_time(self, threshold=7.8 * 3600):
        # Send awws if the last message sent has exceeded threshold time
        for guildid in self.bot.guild_channels.keys():
            channel = self.bot.find_channel(guildid, "general")
            last_msg = await channel.history(limit=1).flatten()
            timestamp = last_msg[0].created_at  # datetime object of last message timestamp in UTC
            now = discord.utils.utcnow()  # datetime object of current time in UTC
            print(f"Seconds since last message ({self.bot.find_channel(guildid, 'name')}): {(now - timestamp).total_seconds()}")
            if (now - timestamp).total_seconds() > threshold:
                await self.post_image(ctx=None, channel=channel)

    async def get_image_url(self, aww_type):
        # Retrieves image URL from the API
        # If the URL is not a static image file, then retrieve another one
        image = None
        while image is None:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_urls[aww_type]['url']) as r:
                    if r.status == 200:
                        data = await r.text()
                        url = json.loads(data)[self.api_urls[aww_type]['key']]
                        if any([x in url for x in ['.jpg', '.png', '.jpeg']]):
                            image = url
                    else:
                        image = f"Cannot find {self.api_urls[aww_type]['url']}."
        return image

    async def post_image(self, ctx, channel=None, aww_type=None, sad=False):
        auto_message = choice(self.reply_to_sad if sad else self.auto_messages)
        if ctx:
            await ctx.respond(auto_message)  # Output auto_message first before slash command times out

        if aww_type not in list(self.api_urls.keys()):
            aww_type = choice(list(self.api_urls.keys()))  # Choose randomly from list of APIs
        image = await self.get_image_url(aww_type)  # Retrieve image url from API

        sent = False

        if ctx:  # When a user calls the command, a ctx object will be associated with it
            while not sent:
                try:
                    await ctx.send(image)
                    sent = True
                except discord.HTTPException:
                    print(f"Failed to post {image}, trying again...")
                    await self.bot.testing_log_channel.send(
                        f"{self.bot.command_prefix}aww: Failed to post {image}, trying again...")
                    image = await self.get_image_url(aww_type)

            await self.bot.testing_log_channel.send(
                f"{self.bot.command_prefix}aww: {ctx.author} posted <{image}> to channel '{ctx.channel}' in guild '{ctx.guild}'")
        else:  # this method is slower, but for auto aww it's okay. Looks nicer and less spammy when auto message and image are combined in one.
            while not sent:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image) as resp:
                            data = io.BytesIO(await resp.read())
                            await channel.send(auto_message, file=discord.File(data, filename='aww.jpg'))
                            print(f"Posted {image} to channel '{channel}' in guild '{channel.guild}'")
                            sent = True
                except discord.HTTPException:
                    await self.bot.testing_log_channel.send(
                        f"{self.bot.command_prefix}auto aww: Failed to post {image}, trying again...")
                    print(f"Failed to post {image}, trying again...")
                    image = await self.get_image_url(aww_type)

    @slash_command(guild_ids=guild_ids, name="aww", description="Get a cute animal picture.")
    async def aww_on_command(self, ctx,
                             type: Option(str, "Specify an animal or omit for a random result.",
                                          choices=aww_choices, required=False, default=None)):
        # Post cute image when commanded to
        await self.post_image(ctx=ctx, aww_type=type)

    @Cog.listener()
    async def on_message(self, message):
        # If someone expresses sadness in the general channel, send them awws
        if not message.author.bot and message.guild:
            if message.channel in self.sad_channel:
                msg = message.content.lower()
                find_sad = [re.search(f"\\b{word}\\b", msg) for word in self.sad_words]
                if any(find_sad):
                    max_index = min([find_sad[i].start() for i in range(len(find_sad)) if find_sad[i] != None])  # Find index of sad word
                    find_me = [re.search(f"\\b{word}\\b", msg) for word in ["i", "im", "me", "we"]]
                    if any(find_me):
                        min_index = min([find_me[i].start() for i in range(len(find_me)) if find_me[i] != None])  # Find index of a 'me' word
                        if min_index < max_index and max_index-min_index < 30:  # If the message has some combination of 'I'm sad', 'makes me sad', etc.
                            if not redwing_functions.find_word(msg, ["gif", "png", "jpg", "jpeg"]):
                                await self.post_image(ctx=None, channel=message.channel, sad=True)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up('aww')
            for guildid in self.bot.guild_channels.keys():
                self.sad_channel.append(self.bot.find_channel(guildid, "general"))


def setup(bot):
    bot.add_cog(Aww(bot))
