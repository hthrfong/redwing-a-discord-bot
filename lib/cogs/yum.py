from random import choice
import praw
from discord.ext.commands import Cog
from discord import Embed, Colour
from discord.commands import slash_command, Option

yum_choices = ['dessert', 'food', 'vegan', 'shit']
with open('./data/guild_ids.txt', 'r') as f:
    guild_ids = [int(guild_id) for guild_id in f.read().strip().split(',')]


class Yum(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.subreddits = {'food': ['FoodPorn', 'food', 'recipes', 'foodphotography', 'tonightsdinner'],
                           'vegan': ['VeganFoodPorn', 'veganrecipes'],
                           'dessert': ['DessertPorn', 'baking', 'dessert', 'CAKEWIN']}
        self.reddit = None

    @slash_command(guild_ids=guild_ids, description="Get a yummy post.", name="yum")
    async def get_yum(self, ctx,
                      type: Option(str, "Specify food type, or omit for a random result.", choices=yum_choices, required=False, default=None)):
        await ctx.defer()
        if type == 'shit':
            subreddit_name = 'ShittyFoodPorn'
        elif type not in self.subreddits.keys():
            type = choice(list(self.subreddits.keys()))
            subreddit_name = choice(self.subreddits[type])
        else:
            subreddit_name = choice(self.subreddits[type])
        submissions = list(self.reddit.subreddit(subreddit_name).top(time_filter='week', limit=30))

        submission = choice(submissions)
        while submission.stickied or not submission.url.endswith(('jpg', 'png', 'jpeg')):
            submission = choice(submissions)

        embed = Embed(title=f"{type.capitalize()} yums", description="",
                      url=f'https://www.reddit.com/r/{subreddit_name}/comments/{submission.id}', colour=ctx.author.colour)
        embed.add_field(name="Description", value=submission.title)
        embed.set_image(url=submission.url)
        embed.set_footer(text=f"Source: Reddit (r/{subreddit_name}).")

        if ctx:
            await ctx.respond(embed=embed)
            await self.bot.testing_log_channel.send(f"{self.bot.command_prefix}yum: {ctx.author} posted <{submission.url}> to channel '{ctx.channel}' in guild '{ctx.guild}'")

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up('yum')
            self.reddit = praw.Reddit(client_id=self.bot.REDDIT_CLIENTID,
                                      client_secret=self.bot.REDDIT_CLIENTSECRET,
                                      user_agent="redwing", check_for_async=False)


def setup(bot):
    bot.add_cog(Yum(bot))
