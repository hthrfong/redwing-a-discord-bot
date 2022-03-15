import discord
import asyncio
from glob import glob
from random import randint
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext.commands import Bot as BotBase

import os

OWNER_IDS = [268862253326008322]
COGS = [path.split("/")[-1][:-3] for path in glob("./lib/cogs/*.py")]


class Ready(object):
    def __init__(self):
        for cog in COGS:
            setattr(self, cog, False)

    def ready_up(self, cog):
        setattr(self, cog, True)
        print(f" {cog} cog ready")

    def all_ready(self):
        return all([getattr(self, cog) for cog in COGS])


class Bot(BotBase):
    def __init__(self):
        self.test = True  # True or False
        self.mod_role_name = ""  # Name of the moderator role

        self.command_prefix = "/"

        self.guild_channels = None
        self.testing_log_channel = None

        self.ready = False
        self.cogs_ready = Ready()

        self.scheduler = AsyncIOScheduler()
        self.persistent_views_added = False

        self.TOKEN = None
        self.MARVEL_PUBLICKEY = None
        self.MARVEL_PRIVATEKEY = None
        self.TINIFY_KEY = None
        self.REDDIT_CLIENTID = None
        self.REDDIT_CLIENTSECRET = None

        super().__init__(command_prefix=self.command_prefix,
                         owner_ids=OWNER_IDS,
                         intents=discord.Intents().all())

    def setup(self):
        for cog in COGS:
            self.load_extension(f"lib.cogs.{cog}")
            print(f" {cog} cog loaded")
        print("setup complete")

    def run(self):
        print("running setup...")
        self.setup()
        if self.test:
            # Read .env to get keys (for testing)
            with open("./lib/bot/.env", "r", encoding="utf-8") as tf:
                keys = tf.readlines()
            self.TOKEN = keys[0].rstrip('\n')
            self.MARVEL_PUBLICKEY = keys[1].rstrip('\n')
            self.MARVEL_PRIVATEKEY = keys[2].rstrip('\n')
            self.TINIFY_KEY = keys[3].rstrip('\n')
            self.REDDIT_CLIENTID = keys[4].rstrip('\n')
            self.REDDIT_CLIENTSECRET = keys[5].rstrip('\n')
        else:
            self.TOKEN = os.environ['TOKEN']
            self.MARVEL_PUBLICKEY = os.environ['MARVEL_PUBLICKEY']
            self.MARVEL_PRIVATEKEY = os.environ['MARVEL_PRIVATEKEY']
            self.TINIFY_KEY = os.environ['TINIFY_KEY']
            self.REDDIT_CLIENTID = os.environ['REDDIT_CLIENTID']
            self.REDDIT_CLIENTSECRET = os.environ['REDDIT_CLIENTSECRET']

        print("running bot...")
        super().run(self.TOKEN, reconnect=True)

    async def on_ready(self):
        if not self.ready:
            # RN: 832899923321552916
            # general: general chat channel, where awws are posted automatically
            # resize: resize image channel
            # marvel: daily marvel channel
            # mod: member DMs Redwing channel
            # games: Wordle channel
            # output: Redwing command usage tracker (RN only)
            self.guild_channels = {832899923321552916: {"general": 832899923321552919, "resize": 834997161027436595,
                                                        "marvel": 833006319388196904,
                                                        "mod": 845317876105347134,
                                                        "games": 832899923321552919,
                                                        "name": self.get_guild(832899923321552916).name,
                                                        "output": 861186911002689537}}

            # Log channel to track who uses aww, yum, marvel, time, resize, joke, etc.
            self.testing_log_channel = self.find_channel(832899923321552916, 'output')

            self.scheduler.add_job(self.change_status, 'interval', minutes=10)  # Keep bot from being disconnect due to inactivity
            self.scheduler.start()  # Start the scheduled jobs

            while not self.cogs_ready.all_ready():
                print("not ready")
                await asyncio.sleep(0.5)

            self.ready = True
            await self.change_status()
            print("bot logged in as {0.user}".format(self))

            if self.test:
                print("in test mode")

            # Post an image immediately if elapsed time duration reached (otherwise, CronTrigger will wait until next
            # time to fire)
            await self.get_cog("Aww").check_elapsed_time()

        else:
            print("bot reconnected")

    async def change_status(self):
        # Change to a random status
        x = randint(1, 5)
        if x == 1:
            activity = discord.Activity(type=discord.ActivityType.listening, name="Bucky Barnes be broody")
        elif x == 2:
            activity = discord.Game('mind games with Baron Zemo')
        elif x == 3:
            activity = discord.Activity(type=discord.ActivityType.watching, name="Sam Wilson do a barrel roll")
        elif x == 4:
            activity = discord.Game(f"type '{self.command_prefix}marvel' for fun")
        else:
            activity = discord.Game(f"type '{self.command_prefix}redwing' for help")

        print(f"bot status set: {x}")
        await self.change_presence(activity=activity)

    def find_channel(self, guild, name):
        if name != "name":
            return self.get_guild(guild).get_channel_or_thread(self.guild_channels[guild][name])
        else:
            return self.guild_channels[guild]["name"]

    async def on_message(self, message):
        if not message.author.bot:
            await self.process_commands(message)


bot = Bot()
