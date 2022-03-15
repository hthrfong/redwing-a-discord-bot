from discord.ext.commands import Cog
from discord.ext.commands import command
from discord import Embed, Colour
from discord.ext.commands import has_permissions
from discord.commands import slash_command, Option

from apscheduler.triggers.cron import CronTrigger
from random import choices


total_guesses = {4: 5, 5: 6, 6: 6, 7: 7}  # {number of letters: number of guesses}
with open('./data/guild_ids.txt', 'r') as f:
    guild_ids = [int(guild_id) for guild_id in f.read().strip().split(',')]


class Wordle(Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("./data/wordle.txt", "r") as f:
            self.words = f.readlines()
        self.words = [word.strip() for word in self.words]
        self.wordle = None
        self.wordle_alphaonly = None
        self.word_string = []
        self.total_guesses = None
        self.players = {}
        self.good_luck_message = ["Good luck!", "You've got this!", ":nerd:", ":partying_face:", "Have fun!", "Let's go!"]

        bot.scheduler.add_job(self.daily_wordle, CronTrigger(hour=0, minute=0, second=0))

    @has_permissions(manage_guild=True)
    @command(name="resetword", brief="Reset puzzle. Admin only.")
    async def reset_wordle(self, ctx, word=None):
        # Manually change the word
        await self.daily_wordle(word=word, print_message=False)

    async def daily_wordle(self, word=None, print_message=False):
        # Sets the daily word to be guessed
        if word:
            self.wordle = word
        else:
            self.wordle = choices(self.words)[0].lower()
        self.wordle_alphaonly = ''.join(filter(str.isalpha, self.wordle))  # Word with letters only
        self.total_guesses = total_guesses[len(self.wordle_alphaonly)]  # Total guesses allowed
        self.players = {}
        for guildid in self.bot.guild_channels.keys():
            channel = self.bot.find_channel(guildid, "games")
            self.word_string = []
            for letter in self.wordle:
                if str.isalpha(letter):
                    self.word_string.append(f"🟦")
                else:
                    self.word_string.append(f"🔹")
            if print_message:
                # Prints the message if it's called by the scheduler
                await channel.send(f"Today's word:\n{' '.join(self.word_string)}\nType /word to play. {choices(self.good_luck_message)[0]}")
            if self.bot.test:
                break

    @slash_command(guild_ids=guild_ids, name="word", description="Play Wordle, Marvel-style! Daily word updates at midnight UTC")
    async def play_wordle(self, ctx,
                          guess: Option(str, "Guess a word.", required=False, default=None)):
        if guess is None:
            await ctx.respond(f"Today's word:\n{' '.join(self.word_string)}\n\nHow to play:\nGuess the Marvel-themed word, using the following clues.\n🟩 Right letter, right place\n🟨 Right letter, wrong place\n⬛ Wrong letter\n🔹 Space/hyphen/apostrophe", ephemeral=True)
            await self.bot.testing_log_channel.send(f"{self.bot.command_prefix}word: {ctx.author}")
        else:
            guess = ''.join(filter(str.isalpha, guess.lower()))
            # Make sure guess length matches word length
            if len(guess) == len(self.wordle_alphaonly):
                print_embed = False
                win = False
                result_string = []
                guess_string = []

                try:
                    guess_num = max(list(self.players[ctx.author.id].keys()))
                    if self.players[ctx.author.id][guess_num]["result"].count("🟩") == len(self.wordle_alphaonly):
                        print_embed = True
                        win = True
                except (KeyError, ValueError):
                    guess_num = 0
                    self.players[ctx.author.id] = {guess_num+1: {"result": [], "guess": []}}

                if not print_embed:
                    for ind, letter in enumerate(guess):
                        guess_string.append(f":regional_indicator_{letter}:")
                        if letter in self.wordle_alphaonly:
                            if letter == self.wordle_alphaonly[ind]:
                                result_string.append("🟩")  # Green square
                            else:
                                result_string.append("🟨")  # Yellow square
                        else:
                            result_string.append("⬛")  # Black square

                    for i in range(len(self.wordle)):
                        if not str.isalpha(self.wordle[i]):
                            guess_string.insert(i, "🔹")
                            result_string.insert(i, "🔹")

                    if guess_num + 1 == self.total_guesses:
                        print_embed = True
                    if guess_num + 1 <= self.total_guesses:
                        self.players[ctx.author.id][guess_num+1] = {"result": result_string, "guess": guess_string}

                    if self.players[ctx.author.id][guess_num+1]["result"].count("🟩") == len(self.wordle_alphaonly):
                        print_embed = True
                        win = True

                if print_embed:
                    word_string = []
                    for letter in self.wordle:
                        if str.isalpha(letter):
                            word_string.append(f":regional_indicator_{letter}:")
                        else:
                            word_string.append(f"🔹")
                    answer = f"\nAnswer: {' '.join(word_string)}."
                else:
                    answer = ""
                output = ''.join([f"{' '.join(self.players[ctx.author.id][key]['guess'])}\n{' '.join(self.players[ctx.author.id][key]['result'])}\n" for key in self.players[ctx.author.id].keys()])
                await ctx.respond(f"Guess {max(list(self.players[ctx.author.id]))} of {self.total_guesses}:\n{output}{answer}", ephemeral=True)

                if print_embed:
                    full_result = '\n'.join([' '.join([r for r in self.players[ctx.author.id][num]['result']]) for num in
                                             self.players[ctx.author.id].keys()])
                    if win:
                        title = choices(["Great job!", "Nice work!", "🥳", "You did it!", "Woo hoo!"])[0]
                    else:
                        title = "You'll get it next time!"
                    embed = Embed(title=f"{ctx.author.display_name}'s Wordle results!", description=full_result,
                                  colour=ctx.author.colour)
                    embed.set_footer(
                        text=f"Guesses: {max(list(self.players[ctx.author.id]))}/{self.total_guesses}. {title}")
                    await ctx.channel.send(embed=embed)

            else:
                await ctx.respond(f"Invalid guess, try again! Today's word has {len(self.wordle_alphaonly)} letters.", ephemeral=True)

            await self.bot.testing_log_channel.send(f"{self.bot.command_prefix}word: {ctx.author} is guessing.")

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up('wordle')
            await self.daily_wordle(print_message=False)


def setup(bot):
    bot.add_cog(Wordle(bot))
