from datetime import datetime, timedelta

import asyncio

import discord.errors
from discord import Embed, Colour
from discord.ext.commands import Cog, command, has_permissions
from discord.commands import slash_command, Option, SlashCommandGroup
from random import choice, choices, sample, randint
import random
import json

# from discord_slash import cog_ext, SlashContext
# from discord_slash.utils.manage_commands import create_option, create_choice


with open('./data/guild_ids.txt', 'r') as f:
    guild_ids = [int(guild_id) for guild_id in f.read().strip().split(',')]

with open('./data/randompoll_options.json', 'r') as f:
    randompoll_json = json.load(f)
    randompoll_choices = sorted(list(randompoll_json.keys()))


class Reactions(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.polls = []
        with open('./data/wouldyouratherpoll_options.json', 'r') as f:
            self.available_options_wyr = json.load(f)
        self.available_options_random = randompoll_json
        self.wyr_weights = tuple([len(self.available_options_wyr[m]) / sum(
            [len(self.available_options_wyr[n]) for n in self.available_options_wyr.keys()]) for m in
                                  self.available_options_wyr.keys()])

        with open("./text_generator/myimmortal.txt", "r") as f:
            self.original = f.read().split('.')
        with open("./text_generator/myimmortal_redwing.txt", "r") as f:
            self.machine = f.read().split('.')

    @slash_command(guild_ids=guild_ids, description="Create a poll and let others vote!", name="poll")
    async def make_poll(self, ctx,
                        question: Option(str, "Poll question, required.", required=True, default=None),
                        options: Option(str, "Poll options (text), required. Separate by comma.", required=True,
                                        default=""),
                        emojis: Option(str, "Poll options (emojis), required. Separate by comma.", required=True,
                                       default=""),
                        description: Option(str, "Description of the poll, optional.", required=False, default=""),
                        time: Option(int,
                                     "Time in minutes until votes are tallied. Omit or set to 0 to leave poll open.",
                                     required=False, default=0)):
        options = options.split(',')
        emojis = emojis.split(',')
        if len(options) == len(emojis):
            options_dictionary = {emojis[i].strip(): options[i].strip() for i in range(len(options))}
            await self.create_poll(ctx, time=time, question=question, description=description,
                                   options_dictionary=options_dictionary)
        else:
            await ctx.respond(f"Oops, number of options ({len(options)}) and emojis ({len(emojis)}) are different.")

    game = SlashCommandGroup("game", "Play some games!")

    @game.command(guild_ids=guild_ids, description="Given two scenarios, which would you choose?",
                  name="wouldyourather")
    async def create_wouldyourather_poll(self, ctx):
        # Asks you to choose between two scenarios, announces results in 5 minutes.
        poll_options = self.available_options_wyr[
            choices(list(self.available_options_wyr.keys()), weights=self.wyr_weights)[0]]
        if poll_options == self.available_options_wyr['character']:
            poll_question = choice(poll_options)
            choose_options = list(sample(list(self.bot.characters.keys()), 2))
            options_dictionary = {"1️⃣": poll_question.replace('[character]', choose_options[0]),
                                  "2⃣": poll_question.replace('[character]', choose_options[1])}
        else:
            choose_options = list(sample(poll_options, 2))
            options_dictionary = {"1️⃣": choose_options[0],
                                  "2⃣": choose_options[1]}

        await self.create_poll(ctx, time=5, question="Would you rather...", description="5 minutes to vote!",
                               options_dictionary=options_dictionary)

    @game.command(guild_ids=guild_ids, description="Choose your favourite!", name="vote")
    async def create_random_poll(self, ctx,
                                 type: Option(str, "Type of poll", choices=randompoll_choices, required=False,
                                              default=None)):
        # Creates a random poll with 2-5 choices, announces results in 5 minutes.
        poll_type = type

        if poll_type not in list(self.available_options_random.keys()):
            p = random.random()
            poll_type = choice(list(self.available_options_random.keys()))
            while poll_type in ['beaman'] and p > 0.5:
                p = random.random()
                poll_type = choice(list(self.available_options_random.keys()))

        poll_options = self.available_options_random[poll_type]
        if poll_type == 'beaman':  # Always post all options for 'Be A Man' poll
            options = poll_options
        else:
            options = sample(poll_options, randint(2, 5))

        options_dictionary = {options[i].split('=')[0].strip(): options[i].split('=')[1].strip() for i in
                              range(len(options))}

        # Change poll title for certain types
        if poll_type == 'death':
            question = "How would you rather go out? Death by..."
        elif poll_type == 'beaman':
            question = "What's most important?"
        else:
            question = f"Which {poll_type} is best?"
        await self.create_poll(ctx, time=5, question=question, description="5 minutes to vote!",
                               options_dictionary=options_dictionary)

    async def create_poll(self, ctx, question=None, description=None, options_dictionary=None, time=None):
        time = float(time)  # Number of minutes before poll results are posted

        embed = Embed(title=question, description=description, colour=ctx.author.colour)
        fields = [
            ("Options", "\n".join([f"{key} {options_dictionary[key]}" for key in options_dictionary.keys()]), False)]
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        interaction = await ctx.respond(embed=embed)
        message = await interaction.original_message()

        for emoji in options_dictionary.keys():
            await message.add_reaction(emoji)

        self.polls.append((message.channel.id, message.id))

        if time > 0:
            self.bot.scheduler.add_job(self.complete_poll, "date", run_date=datetime.now() + timedelta(minutes=time),
                                       args=[timedelta(minutes=time).total_seconds(), message.channel.id, message.id])

    @command(name='globalpoll', brief="Admin only")
    @has_permissions(manage_guild=True)
    async def create_global_poll(self, ctx, question=None, description=None, options=None, time=0):
        try:
            time = float(time)  # Number of minutes before poll results are posted
            options = options.split('|')
            options_dictionary = {options[n].split('=')[0].strip(): options[n].split('=')[1] for n in
                                  range(len(options))}

            options_string = "\n".join([f"{key} {options_dictionary[key]}" for key in options_dictionary.keys()])
            description = f"{description}\n\n{options_string}"

            embed = Embed(title=question, description=description)
            message = await ctx.channel.send(embed=embed)

            for emoji in options_dictionary.keys():
                await message.add_reaction(emoji)

            self.polls.append((message.channel.id, message.id))

            if time > 0:
                self.bot.scheduler.add_job(self.complete_poll, "date",
                                           run_date=datetime.now() + timedelta(minutes=time),
                                           args=[timedelta(minutes=time).total_seconds(), message.channel.id,
                                                 message.id])
        except (ValueError, IndexError, discord.HTTPException) as e:
            await ctx.channel.send(f"Something went wrong. Check the **options** formatting and try again.")

    async def complete_poll(self, runtime, channel_id, message_id):
        # For time-limited polls, post results
        message = await self.bot.get_channel(channel_id).fetch_message(message_id)

        if runtime < 60:
            runtime_string = f"{round(runtime)} seconds"
        elif 60 <= runtime < 3600:
            runtime_string = f"{round(runtime / 60)} minutes"
        elif 3600 <= runtime <= 24 * 3600:
            runtime_string = f"{round(runtime / 3600)} hours"
        else:
            runtime_string = f"{round(runtime / (3600 * 24))} days"

        for i, m in enumerate(message.reactions):
            if type(m.emoji) != str:
                message.reactions[i].emoji = f"<:{m.emoji.name}:{m.emoji.id}>"

        max_votes = max(message.reactions, key=lambda r: r.count).count
        most_voted = [m for m in message.reactions if m.count == max_votes]

        vote_count = '\t'.join([f"{m.emoji}: {m.count - 1}" for m in message.reactions])

        if len(most_voted) < 2:
            final_results = f"{most_voted[0].emoji} wins!"
        else:
            final_results = f"It's a tie between {', '.join([most_voted[n].emoji for n in range(len(most_voted))])}!"

        results_message = f"After {runtime_string} of polling, here are the results:\n\n{vote_count}\n\n{final_results}"
        await message.reply(results_message, mention_author=False)
        self.polls.remove((message.channel.id, message.id))

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("reactions")

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id in (poll[1] for poll in self.polls):
            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            for reaction in message.reactions:
                if not payload.member.bot and payload.member in await reaction.users().flatten():
                    try:
                        if reaction.emoji.name != payload.emoji.name:
                            await message.remove_reaction(reaction.emoji, payload.member)
                    except AttributeError:
                        if reaction.emoji != payload.emoji.name:
                            await message.remove_reaction(reaction.emoji, payload.member)


def setup(bot):
    bot.add_cog(Reactions(bot))
