from random import choice, randint
from glob import glob
import requests
import json
import os
import re

import discord
from discord.ext import commands
from discord.commands import slash_command, Option
from discord.ext.commands import Cog
from discord.ext.commands import has_permissions
from discord import Embed, Colour
from discord import Forbidden

import sys
sys.path.append('./utils')
import redwing_functions
import buttons

with open('./data/guild_ids.txt', 'r') as f:
    guild_ids = [int(guild_id) for guild_id in f.read().strip().split(',')]


class Misc(Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('./data/reaction_redwingmention.json', 'r') as f:
            self.keywords = json.load(f)
        with open('./data/reaction_greetings.json', 'r') as f:
            self.greetings = json.load(f)
        with open('./data/reaction_emoji.json', 'r') as f:
            self.reactions = json.load(f)

        self.joke_words = ['love puns', 'more puns', 'tell me a joke', "hear a joke", "more jokes", "love jokes",
                           "like jokes", "enjoy puns", "like puns", "dad jokes", "dad joke", "hate puns",
                           "another joke", "another pun"]

        self.emoji_choices = sorted([os.path.basename(x) for x in glob("./img/emoji/*")])

        self.general_channel = []

    async def post_joke(self, ctx, channel=None, keyword=None):
        if keyword:
            request_string = f"https://icanhazdadjoke.com/search?term={keyword}"
        else:
            request_string = f"https://icanhazdadjoke.com/"

        result = json.loads(requests.get(request_string,
                                         headers={'User-Agent': 'https://github.com/hthrfong/redwing-a-discord-bot',
                                                  'Accept': "application/json"}).text)
        try:
            joke = result['joke']
        except KeyError:
            joke = choice(result['results'])['joke']

        if ctx:
            await ctx.respond(joke)
            await self.bot.testing_log_channel.send(
                f"{self.bot.command_prefix}joke: {ctx.author} posted '{joke}' to channel '{ctx.channel}' in guild '{ctx.guild}'")
        else:
            await channel.send(joke)

    @slash_command(guild_ids=guild_ids, description="Get a random dad joke.", name="joke")
    async def joke_on_command(self, ctx,
                              keyword: Option(str, "Search for a joke by keyword.", required=False, default=None)):
        await self.post_joke(ctx, keyword=keyword)

    @slash_command(guild_ids=guild_ids, description="Roll dice.", name="roll")
    async def roll_dice(self, ctx,
                        dice: Option(str, "Specify roll type via ?d? (default is 1d6) or a list of choices (e.g. red, blue, green).", default="1d6", required=False),
                        question: Option(str, "Specify the question. Optional.", default="", required=False)):
        if question != "":
            question = f"**{question}**\n"
        if ',' not in dice:
            try:
                num, side = [int(i) for i in dice.lower().split("d")]
                roll_result = [str(randint(1, side)) for i in range(num)]
                await ctx.respond(f"{question}🎲 Roll results ({dice}): {', '.join(roll_result)}.")
                await self.bot.testing_log_channel.send(
                    f"{self.bot.command_prefix}roll: {ctx.author} rolled '{dice}' to channel '{ctx.channel}' in guild '{ctx.guild}'")
            except ValueError:
                await ctx.respond("Sorry, I don't understand. 🤔")
        else:
            options = [d.strip() for d in dice.split(",")]
            await ctx.respond(f"{question}🎲 Roll results ({dice}): {choice(options)}.")
            await self.bot.testing_log_channel.send(
                f"{self.bot.command_prefix}roll: {ctx.author} rolled '{dice}' to channel '{ctx.channel}' in guild '{ctx.guild}'")

    @slash_command(guild_ids=guild_ids, description="Slap someone.", name="slap")
    async def slap(self, ctx,
                   member: Option(discord.Member, "Name of member", required=True, default=None)):
        # Slap someone with a large trout
        view = buttons.Slap(ctx)  # Create a view for a slap back button
        if ctx.author == member:
            interaction = await ctx.respond(f"{ctx.author.display_name} slaps themselves around a bit with a large trout. Um, why?", view=view)
        else:
            interaction = await ctx.respond(f"{ctx.author.display_name} slaps {member.mention} around a bit with a large trout.", view=view)
        if member.bot:
            # Redwing reacts if a fellow bot or itself is slapped
            message = await interaction.original_message()
            await message.add_reaction(choice(self.reactions['shock']))
        await view.wait()
        if view.value:
            if view.user == ctx.author:
                await ctx.send(f"{ctx.author.display_name} slaps themselves around a bit with a large trout. Kind of masochistic, but you do you.")
            else:
                await ctx.send(f"{view.user.display_name} slaps {ctx.author.mention} around a bit with a large trout.")

    async def emoji_characters(self, ctx: discord.AutocompleteContext):
        # Autocompletes all available emoji characters
        return [name for name in self.emoji_choices if name.startswith(ctx.value.lower())]

    @slash_command(guild_ids=guild_ids, description="Send a Marvel emoji.", name="emoji")
    @commands.cooldown(3, 15, commands.BucketType.user)
    async def get_emoji(self, ctx: discord.ApplicationContext,
                        character: Option(str, "Character name.",
                                          autocomplete=emoji_characters, required=False, default=None)):

        async def send_emoji(character):
            emoji_path = choice(glob(f"./img/emoji/{character}/*.png"))
            await ctx.respond(file=discord.File(emoji_path, filename=f"{character}.png"))

        if character:
            sent = False
            for character_name in self.emoji_choices:
                if character.lower() in character_name:
                    sent = True
                    await send_emoji(character_name)
                    break
            if not sent:
                embed = Embed(title=f"Unknown: {character}", description="", colour=Colour.red())
                embed.add_field(name="Available characters", value=f"{', '.join(self.emoji_choices)}")
                await ctx.respond(embed=embed, ephemeral=True)
            else:
                await self.bot.testing_log_channel.send(
                    f"{self.bot.command_prefix}emoji: {ctx.author} sent '{character}' to channel '{ctx.channel}' in guild '{ctx.guild}'")
        else:
            character = choice(self.emoji_choices)
            await send_emoji(character)
            await self.bot.testing_log_channel.send(
                f"{self.bot.command_prefix}emoji: {ctx.author} sent '{character}' to channel '{ctx.channel}' in guild '{ctx.guild}'")

    @Cog.listener()
    async def on_application_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.respond(f"Currently on cooldown, try again in {error.retry_after:.1f} seconds.")
        else:
            raise error  # raise other errors so they aren't ignored

    @Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
            if message.guild:  # Handle messages posted in guild server
                keep_listening = True
                msg = message.content.lower()
                # Tag people who say 'don't @ me'
                if redwing_functions.find_word(msg, ["don't @ me", "dont @ me", "don't @me", "dont @me", "do not @ me", "do not @me"]):
                    await message.reply(f"{message.author.mention} {choice(self.reactions['happy'])}")
                    keep_listening = False
                # If player asks a question for an admin
                elif redwing_functions.find_word(msg, ["admin", "admins", "staff", "mod", "mods", "moderator", "moderators"]):
                    if redwing_functions.find_word(msg, ["question", "questions"]) or "?" in msg:
                        staff = []
                        for member in message.guild.members:
                            for role in member.roles:
                                if role.name == self.bot.mod_role_name:
                                    staff.append(member)
                        # Automatic reply if all admins are offline and tag admins
                        if all([s.status == discord.Status.offline for s in staff]):
                            await message.reply(f"Sorry, all moderators are offline right now, but I've tagged them so they can get back to you ASAP. {' '.join([s.mention for s in staff])}")
                            keep_listening = False
                if keep_listening:
                    # Redwing reacts to messages that mention him
                    if "redwing" in msg or f'<@!{self.bot.user.id}>' in msg or "レッドウィング" in msg:
                        for key in self.keywords.keys():
                            if redwing_functions.find_word(msg, self.keywords[key]):
                                await message.add_reaction(choice(self.reactions[key]))
                                break
                    if message.channel in self.general_channel:
                        # Redwing reacts to standard greetings in general channel
                        for key in self.greetings.keys():
                            if redwing_functions.find_word(msg, self.greetings[key]):
                                await message.add_reaction(choice(self.reactions[key]))
                        # Exception to handle short greetings and have Redwing still react to them
                        if any([len(re.findall(f"\\b{word}\\b", msg[:len(word)+1])) > 0 for word in ["morning", "afternoon", "evening", "night", "welcome"]]) and len(msg) < 20:
                            await message.add_reaction(choice(self.reactions['greet']))
                        # Redwing listens for jokes
                        elif redwing_functions.find_word(msg, self.joke_words):
                            await self.post_joke(ctx=None, channel=message.channel)
            else:  # Handle messages posted in DM channel
                for guildid in self.bot.guild_channels.keys():
                    guild = self.bot.get_guild(guildid)
                    if guild.get_member(message.author.id) is not None:
                        # DM-ing Redwing will forward the message to the admin channel
                        embed = Embed(title=f"Direct message from {message.author}", description=f"{message.content}",
                                      colour=Colour.blue())
                        embed.set_footer(text=f"Sent: {message.created_at} UTC")
                        await self.bot.find_channel(guildid, "mod").send(embed=embed)
                        try:
                            await message.channel.send(
                                f"Thanks for your message! I've forwarded it to the {self.bot.find_channel(guildid, 'name')} moderators and they'll get back to you ASAP.")
                        except Forbidden:
                            pass
                        print(f"Received DM from {message.author} at {message.created_at}.")
                        break

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up('misc')
            for guildid in self.bot.guild_channels.keys():
                self.general_channel.append(self.bot.find_channel(guildid, "general"))


def setup(bot):
    bot.add_cog(Misc(bot))
