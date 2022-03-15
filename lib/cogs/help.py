import discord
from discord.ext import pages, commands
from discord.commands import slash_command
from discord.ext.commands import has_permissions
from discord.ext.commands import Cog
from discord import Embed, Colour

import sys

sys.path.append('./utils')
import buttons

with open('./data/guild_ids.txt', 'r') as f:
    guild_ids = [int(guild_id) for guild_id in f.read().strip().split(',')]


class Help(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(guild_ids=guild_ids, description="Get a summary of Redwing's commands.", name="redwing")
    async def say_help(self, ctx: discord.ApplicationContext):

        embed = Embed(title="Redwing to the rescue!", description=f"Hi, I'm Redwing, {ctx.guild}'s trusty sidekick! "
                                                                  f"I'm pretty cool, even if Bucky doesn't think so. "
                                                                  f"Here's what I can do:",
                      colour=Colour.red())
        embed.add_field(name=f"For fun",
                        value=f"**{self.bot.command_prefix}aww:** Get a cute picture\n"
                              f"**{self.bot.command_prefix}emoji:** Send a Marvel emoji\n"
                              f"**{self.bot.command_prefix}joke:** I tell you a hilarious joke\n"
                              f"**{self.bot.command_prefix}marvel:** Query the Marvel Comics database\n"
                              f"**{self.bot.command_prefix}slap:** Slap someone!\n"
                              f"**{self.bot.command_prefix}yum:** Get something delicious",
                        inline=False)
        embed.add_field(name=f"Games",
                        value=f"**{self.bot.command_prefix}game vote:** Everyone picks their favourite!\n"
                              f"**{self.bot.command_prefix}game wouldyourather:** Would you rather this or that?\n"
                              f"**{self.bot.command_prefix}word:** Play Marvel-style Wordle!",
                        inline=False)
        embed.add_field(name=f"Tools",
                        value=f"**{self.bot.command_prefix}poll:** Create a poll with custom question & options\n"
                              f"**{self.bot.command_prefix}roll:** Roll dice\n"
                              f"**{self.bot.command_prefix}time convert:** Convert time to different timezones\n"
                              f"**{self.bot.command_prefix}time now:** Get current time in different timezones",
                        inline=False)

        await ctx.respond(embed=embed)

        await self.bot.testing_log_channel.send(
            f"{self.bot.command_prefix}redwing: {ctx.author} called in channel '{ctx.channel}' in guild '{ctx.guild}'")

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up('help')
            # self.message = await self.bot.find_channel(832288706982707221, "resize").fetch_message()
            # self.message = await self.bot.get_channel(832899923321552919).fetch_message(935155084206145546)
            print(self.message)
            if not self.bot.persistent_views_added:
                # self.bot.add_view(buttons.PersistentPaginator(self.pages, self.message))
                self.bot.persistent_views_added = True
                print("Added persistent views")


def setup(bot):
    bot.add_cog(Help(bot))
