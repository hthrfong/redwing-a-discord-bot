from discord.ext.commands import Cog
from discord.commands import slash_command, Option, SlashCommandGroup
import re
from datetime import datetime
import collections
import pytz
from dateutil import parser


with open('./data/guild_ids.txt', 'r') as f:
    guild_ids = [int(guild_id) for guild_id in f.read().strip().split(',')]


class Conversion(Cog):
    def __init__(self, bot):
        self.bot = bot

        # Temperature
        self.keywords = {"F": ['degrees f', 'deg f', 'deg. f', 'fahrenheit', '°f', 'f\\b'],
                         "C": ['degrees c', 'deg c', 'deg. c', 'celsius', '°c', 'c\\b']}
        self.regular_expression = r"([-+]?[.\d]+)\s*(%s)" % ('|'.join(sum(self.keywords.values(), [])))

        # Timezone
        self.timezones = ['Asia/Tokyo', 'Australia/Sydney', 'Europe/London',
                          'Europe/Stockholm', 'US/Eastern', 'US/Mountain', 'US/Pacific', 'PST8PDT',
                          'MST7MDT', 'EST5EDT', 'UTC']
        self.timezones_pretty = ['Asia/Tokyo', 'Australia/Sydney', 'Europe/London', 'Europe/Stockholm', 'US/Eastern',
                                 'US/Central']
        self.timezones_pretty.sort()
        self.timezones_marvel = {"wakanda": "Africa/Nairobi", "genosha": "Asia/Baku",
                                 "atlantis": "America/Sao_Paulo", "asgard": "Europe/Oslo", "sokovia": "Europe/Prague",
                                 "madripoor": "Asia/Singapore", "latveria": "Europe/Belgrade"}

        self.tzones = collections.defaultdict(set)
        self.abbrevs = collections.defaultdict(set)
        for name in pytz.common_timezones:
            tzone = pytz.timezone(name)
            for utcoffset, dstoffset, tzabbrev in getattr(tzone, '_transition_info',
                                                          [[None, None, datetime.now(tzone).tzname()]]):
                self.tzones[tzabbrev].add(name)
                self.abbrevs[name].add(tzabbrev)

    time = SlashCommandGroup("time", "Time in various timezones.")

    @time.command(guild_ids=guild_ids, description="Convert date/time.", name="convert")
    async def convert_time(self, ctx,
                           date_time: Option(str, "The date/time to be converted (e.g. Jan 1 2021 3pm). Required.", required=True, default=None),
                           timezone: Option(str, "Timezone of original date/time (e.g. EST, Wakanda). Default is UTC.", required=False, default='UTC')):
        timezone.replace(" ", "_")
        try:
            datetime_obj = parser.parse(date_time)
            fmt = "%Y-%m-%d %H:%M %Z%z"
            if datetime_obj.tzinfo:
                regions = self.tzones[datetime_obj.tzinfo.tzname(datetime_obj)]
                local = None
                for region in regions:
                    if region in self.timezones_pretty:
                        local = pytz.timezone(region)
                if not local:
                    local = pytz.timezone(list(regions)[0])
            else:
                local = self.find_locale(timezone)
                datetime_obj = local.localize(datetime_obj)
        except parser.ParserError:
            await ctx.respond(f"I don't understand this time: '{timezone}'.")
            raise ValueError(f"User inputted invalid time format: {datetime}")
        time_converted = [self.convert_timezone(datetime_obj, t, fmt) for t in self.timezones_pretty]
        await ctx.respond(f"**{datetime_obj.astimezone(local).strftime(fmt)}**\n" + '\n'.join(time_converted))
        await self.bot.testing_log_channel.send(
            f"{self.bot.command_prefix}time convert: {ctx.author} converted '{date_time}' in channel '{ctx.channel}' in guild '{ctx.guild}'")

    @time.command(guild_ids=guild_ids, description="Get the current time of various locations.", name="now")
    async def get_time_now(self, ctx,
                           timezone: Option(str, "Desired timezone (e.g. EST, Madripoor). If omitted, multiple timezones are given.", required=False, default=None)):
        fmt = "%Y-%m-%d %H:%M %Z%z"
        now_utc = datetime.now(pytz.timezone('UTC'))
        if timezone is None:
            time_converted = [self.convert_timezone(now_utc, t, fmt) for t in self.timezones_pretty]
            await ctx.respond('\n'.join(time_converted))
            await self.bot.testing_log_channel.send(
                f"{self.bot.command_prefix}time now: {ctx.author} converted current time in channel '{ctx.channel}' in guild '{ctx.guild}'")
        else:
            local = self.find_locale(timezone)
            if local:
                await ctx.respond(f"**{str(local).replace('_', ' ')}**: {now_utc.astimezone(local).strftime(fmt)}")
                await self.bot.testing_log_channel.send(
                    f"{self.bot.command_prefix}time now: {ctx.author} converted current time to {timezone} in channel '{ctx.channel}' in guild '{ctx.guild}'")
            else:
                await ctx.respond(f"Sorry, I don't know where '{timezone}' is. 😕")

    def find_locale(self, tz):
        # Takes a string and parses it to find the timezone location or acronym. Returns a pytz timezone object.
        tz = "_".join(tz.split()).lower()
        send = False
        if tz.lower() in self.timezones_marvel.keys():
            tz = self.timezones_marvel[tz].lower()

        try:
            regions = self.tzones[tz.upper()]  # Search by timezone acronym
            intersect = list(set(regions) & set(self.timezones))
            if len(intersect) > 0:
                tz = intersect[0]
            else:
                tz = list(regions)[0]
            return pytz.timezone(tz)
        except IndexError:
            for abbrev in self.abbrevs.keys():  # Search by timezone location
                if tz in abbrev.lower():
                    tz = abbrev
                    return pytz.timezone(tz)
        if not send:
            return None

    def convert_temp(self, value, unit):
        if unit == 'F':
            return round((value - 32) * (5 / 9), 1)
        if unit == 'C':
            return round(value * (9 / 5) + 32, 1)

    def convert_timezone(self, time, tz, fmt):
        return f"**{tz}**: {time.astimezone(pytz.timezone(tz)).strftime(fmt)}"

    @Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
            if message.guild:
                msg = message.content.lower()
                if not any([m in msg for m in ['http://', 'https://', '.jpg', '.gif', '.png']]):  # Don't search for links or images
                    matches = re.findall(self.regular_expression, message.content.lower())
                    if matches:
                        msgs = []
                        for match in matches:
                            temperature = float(match[0])
                            for key, value in self.keywords.items():
                                for val in value:
                                    if match[1] in val:
                                        converted_temperature = self.convert_temp(temperature, key)
                                        converted_unit = 'F' if key == 'C' else 'C'
                                        msgs.append(f"{temperature}°{key} = {converted_temperature}°{converted_unit}")
                                        break
                        await message.channel.send('\n'.join(msgs))

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up('conversion')


def setup(bot):
    bot.add_cog(Conversion(bot))
