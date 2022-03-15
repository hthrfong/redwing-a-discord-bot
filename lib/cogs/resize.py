import discord
import tinify

from discord.ext.commands import Cog, command, has_permissions
from discord import Embed, Colour
from discord.commands import slash_command, Option

import subprocess

with open('./data/guild_ids.txt', 'r') as f:
    guild_ids = [int(guild_id) for guild_id in f.read().strip().split(',')]

resize_choices = ['app (400x250)', 'avatar (250x400)', 'custom (WIDTHxHEIGHT)']


class Resize(Cog):
    # Tinify policy: First 500 images uploaded per month are free
    def __init__(self, bot):
        self.bot = bot

    @slash_command(guild_ids=guild_ids, description="Resize a given image to app, avatar, or custom dimensions.", name="resize")
    async def resize_image(self, ctx,
                           type: Option(str, "Resized image dimensions. Required.", choices=resize_choices, required=True, default=None),
                           image_url: Option(str, "URL of image (JPG or PNG). Required", required=True, default=None),
                           width: Option(int, "Width in pixels. Omit unless type: custom.", required=False, default=None),
                           height: Option(int, "Height in pixels. Omit unless type: custom.", required=False, default=None)):
        resize_image_channel = self.bot.find_channel(ctx.guild.id, "resize")
        if ctx.channel == resize_image_channel:
            await ctx.defer()
            resized = None
            try:
                source = tinify.from_url(image_url)
            except tinify.ClientError:
                await ctx.respond("Invalid image URL.")
                raise ValueError(f"Could not read image URL: {image_url}")
            if "custom" not in type:
                if width or height:
                    await ctx.respond(f"Resizing to preset {type} dimensions. To resize to the width/height you specified, choose type: custom.", ephemeral=True)
                if "avatar" in type:
                    resized = source.resize(method="cover", width=250, height=400)
                elif "app" in type:
                    resized = source.resize(method="cover", width=400, height=250)
            else:
                if width and height:
                    resized = source.resize(method="cover", width=int(width), height=int(height))
                else:
                    await ctx.respond("Make sure to specify a width and height.")
                    raise ValueError("Did not specify width and/or height")
            if resized is None:
                await ctx.respond("Sorry, something went wrong. Try again?")
            else:
                filename = f"User_{ctx.author.id}_resized_{type}.png"
                resized.to_file(filename)
                with open(filename, 'rb') as f:
                    await ctx.respond(f"Looking good!", file=discord.File(f, filename=filename))

                await self.bot.testing_log_channel.send(f"{self.bot.command_prefix}resize: {ctx.author} resized <{image_url}> in guild '{ctx.guild}'")

        else:
            await ctx.respond(f"Use me in {resize_image_channel.mention}!", ephemeral=True)

    @command(name='compressioncount', aliases=['cc'], brief="Admin only")
    @has_permissions(manage_guild=True)
    async def get_compression_count(self, ctx):
        # count = tinify.compression_count  # This is how you're supposed to get the compression count, but it doesn't work
        # Beware: the below method works, but calling it does add on an additional compression
        p = subprocess.check_output(
            ['curl', 'https://api.tinify.com/shrink', '--user', f'api:{self.bot.TINIFY_KEY}', '--data-binary',
             '@redwing_avatar.png', '--dump-header', '/dev/stdout'])
        count = int(p.split()[18])
        await self.bot.find_channel(ctx.guild.id, "admin").send(f"Number of images resized this month: {count}/500.")

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up('resize')
            tinify.key = self.bot.TINIFY_KEY


def setup(bot):
    bot.add_cog(Resize(bot))
