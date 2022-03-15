from discord import Forbidden
from discord.ext.commands import Cog
from random import choice


class Welcome(Cog):
    def __init__(self, bot):
        self.bot = bot

    def random_message(self, member):
        messages = [f"Avengers, assemble! {member.mention} has just joined the team!",
                    f"By Odin's beard, tis the worthy {member.mention}!",
                    f"They are inevitable. They are {member.mention}. Welcome.",
                    f"Coming in higher, further, faster, it's {member.mention}!",
                    f"By the Hoary Hosts of Hoggoth, it's {member.mention}!",
                    f"Excelsior! Welcome, {member.mention}!",
                    f"Sweet Christmas! Welcome aboard, {member.mention}!",
                    f"Oh, my stars and garters, it's {member.mention}!",
                    f"My spider-sense is tingling--it's {member.mention}!",
                    f"It's clobberin' time! Welcome, {member.mention}!",
                    f"{member.mention} is here to kick names and take ass!",
                    f"Coming from your friendly neighbourhood... {member.mention}!",
                    f"Flame on! It's {member.mention}, coming in hot!",
                    f"With great power, comes the great {member.mention}!",
                    f"Face front, true believers, {member.mention} has just arrived!",
                    f"{member.mention} still believes in heroes. Welcome!"]
        return choice(messages)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("welcome")

    @Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel is not None:
            await channel.send(self.random_message(member))

        try:
            await member.send(f"Welcome to **{member.guild.name}**! All messages here are automatically forwarded to the admins, so feel free to ask me any questions.")
        except Forbidden:
            pass

        # await member.add_roles(member.guild.get_role(626609604813651979), member.guild.get_role(626609649294114857))


def setup(bot):
    bot.add_cog(Welcome(bot))
