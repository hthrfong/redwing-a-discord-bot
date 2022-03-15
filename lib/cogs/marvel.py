import json
from datetime import datetime
import dateutil.relativedelta

from random import choices, choice, sample
import aiohttp
import hashlib

from discord.ext.commands import Cog
from discord import Embed, Colour
from discord.commands import slash_command, Option

from bs4 import BeautifulSoup

import sys
sys.path.append('./utils')
import redwing_functions


marvel_choices = ['characters', 'creators', 'events', 'series']
with open('./data/guild_ids.txt', 'r') as f:
    guild_ids = [int(guild_id) for guild_id in f.read().strip().split(',')]


class Marvel(Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('./data/marvel_random.json', 'r') as f:
            self.random_query = json.load(f)
        self.options = ['characters', 'events', 'creators', 'series']
        self.weights = tuple([0.35, 0.15, 0.35, 0.15])  # Make it more even
        self.title_category = {"characters": "Character", "events": "Event", "series": "Series", "creators": "Creator"}
        self.query_type = {'startswith': {'series': 'titleStartsWith',
                                          'characters': 'nameStartsWith',
                                          'events': 'nameStartsWith',
                                          'creators': 'nameStartsWith'},
                           'exact': {'series': 'title',
                                     'creators': 'nameStartsWith',
                                     'characters': 'name',
                                     'events': 'name'}}
        self.authentication = None
        bot.scheduler.add_job(self.daily_marvel, 'cron', day_of_week='tue,thu,sat,sun', hour=14, minute=0, second=0, jitter=120)  # 14:00 GMT/10:00 EST, except Mon, Wed, Fri

    # @has_permissions(manage_guild=True)
    # @command(name="queryall")
    # async def get_query_all(self, ctx):
    #     # names = self.random_query['characters']
    #     names = self.random_query['series'].keys()
    #     for name in list(names):
    #         if name not in self.random_query['description'].keys():
    #             # await self.get_marvel(ctx, category='characters', query=name)
    #             await self.get_marvel(ctx, category='series', query=name, query_type=self.random_query['series'][name])

    async def post_marvel(self, ctx, channel=None, category=None, query=None, query_type='startswith',
                          offset='0', show_time=True):
        is_random = False
        time_start = datetime.utcnow()

        if not query:  # If query argument is None
            if not category:  # If category argument is None, choose one randomly
                category = choices(self.options, weights=self.weights)[0]
            if category == 'series':
                find_new = choice([True, False])
                last_month = time_start + dateutil.relativedelta.relativedelta(months=-1)
                if find_new:  # Get a series, new as of last month
                    print("New series")
                    async with aiohttp.ClientSession() as session:
                        json_data = {}
                        while len(json_data) < 1:
                            async with session.get(
                                    f"https://gateway.marvel.com:443/v1/public/series?modifiedSince={last_month.strftime('%Y-%m-%d')}T00%3A00%3A00&orderBy=modified&{self.authentication}") as r:
                                if r.status == 200:
                                    json_data = await r.json()
                                    if isinstance(json_data, int):
                                        json_data = {}
                    series = choice(json_data["data"]["results"])
                    while "image_not_available" in series["thumbnail"]["path"]:
                        # Only choose series with a thumbnail image
                        series = choice(json_data["data"]["results"])
                    query = series["title"][:series["title"].index('(')].strip() + f" {series['startYear']}"
                    query_type = 'exact'
                else:
                    query = choice(list(self.random_query[category].keys()))
                    query_type = self.random_query[category][query]
            else:
                query = choice(self.random_query[category])
                query_type = 'exact'
            is_random = True
            show_time = False
            print(category, query)

        query_type = self.query_type[query_type][category]

        if category == 'series':
            split_query = query.split(' ')
            try:
                start_year = int(split_query[-1])
                if 1930 <= start_year <= time_start.year:
                    query = f"{' '.join(split_query[:-1])}&startYear={start_year}"
            except ValueError:
                pass

        search_parameters = f"{category}?{query_type}={query}&offset={offset}"
        if category == 'series':
            search_parameters += '&orderBy=startYear&'
            print(query)
        async with aiohttp.ClientSession() as session:
            json_data = {}
            while len(json_data) < 1:
                async with session.get(f"https://gateway.marvel.com:443/v1/public/{search_parameters}{self.authentication}") as r:
                    if r.status == 200:
                        json_data = await r.json()
                        if isinstance(json_data, int):
                            json_data = {}
                print("Queried:", json_data)

        if len(json_data['data']['results']) == 0:
            print(f"Failed query: {query}")
            await ctx.respond(f"No results found for '{query}'. Try a different search?")
            show_time = False
        elif len(json_data['data']['results']) <= 5:
            if not is_random:
                await ctx.respond(f"{len(json_data['data']['results'])} result(s) found.")

            description = None
            for i in range(len(json_data['data']['results'])):
                result = json_data['data']['results'][i]

                if category == "events":
                    title = result['title']
                    try:
                        url = result['urls'][1]['url']
                    except IndexError:
                        url = result['urls'][0]['url']

                    description = result['description']
                    character_count = result['characters']['available']
                    # Create list of featured characters
                    if character_count >= 20:
                        choose_characters = sorted(sample(range(20), 10))
                    elif 10 < character_count < 20:
                        choose_characters = sorted(sample(range(character_count), 10))
                    else:
                        choose_characters = range(character_count)
                    description += f"\n\n**Featured characters:** {', '.join([result['characters']['items'][i]['name'] for i in choose_characters])}\n"
                    series_result, series_url = self.get_series(result, category)
                    description += series_result

                elif category == "characters":
                    title = result["name"]
                    description = BeautifulSoup(result['description'], 'lxml').text
                    url = result['urls'][1]['url']
                    print(title, description, url)
                    if result['description'] in ["", "&nbsp;", " "]:
                        try:
                            description = self.random_query['description'][title]
                            print("Description found in JSON database.")
                        except KeyError:
                            print('Description not in JSON database, scraping from URL...')
                            description = await self.get_website_description(url, divclasses=['text', 'masthead__copy'])
                            if description:
                                if "Get hooked" in description or "Dive into" in description:
                                    print("Got default site text.")
                                    description = None
                            else:
                                print("URL1 didn't work")
                                url = result['urls'][0]['url']
                                description = await self.get_website_description(url, divclasses=['masthead__copy', 'text'])
                                if description:
                                    if "Get hooked" in description or "Dive into" in description:
                                        print("Got default site text.")
                                        description = None
                                else:
                                    print("URL2 didn't work")
                    if title == "Redwing":
                        await ctx.send("Hey, that's me! 🥰")
                    works, series_uri = self.get_series(result, category)
                    if 'image_not_available' in result['thumbnail']['path'] and len(series_uri) > 0:
                        while 'image_not_available' in result['thumbnail']['path']:
                            for s in series_uri:
                                async with aiohttp.ClientSession() as session:
                                    js = {}
                                    while len(js) < 1:
                                        async with session.get(f"{s}?{self.authentication}") as r:
                                            if r.status == 200:
                                                js = await r.json()
                                                if isinstance(js, int):
                                                    js = {}
                                        print(js)

                                series_json = js['data']['results'][0]

                                # If character doesn't have thumbnail image, obtain one from series
                                result['thumbnail']['path'] = self.get_thumbnail_path(result, series_json)

                elif category == 'creators':
                    title = result["fullName"]
                    print(title)
                    works, series_uri = self.get_series(result, category)
                    roles = []
                    # For the highlighted series, get the creator's role
                    for s in series_uri:
                        async with aiohttp.ClientSession() as session:
                            js = {}
                            while len(js) < 1:
                                async with session.get(f"{s}?{self.authentication}") as r:
                                    if r.status == 200:
                                        js = await r.json()
                                        if isinstance(js, int):
                                            js = {}
                                print(js)

                        series_json = js['data']['results'][0]

                        # If creator doesn't have thumbnail image, obtain one from series
                        result['thumbnail']['path'] = self.get_thumbnail_path(result, series_json)

                        series_creators = series_json['creators']
                        for i in range(len(series_creators['items'])):
                            if series_creators['items'][i]['name'] == title:  # Find creator in series creator list
                                # Keep spelling consistent
                                if series_creators['items'][i]['role'] == 'penciler':
                                    role = 'penciller'
                                elif series_creators['items'][i]['role'] == 'penciler (cover)':
                                    role = 'penciller (cover)'
                                else:
                                    role = series_creators['items'][i]['role'].lower()
                                roles.append(role)
                                continue
                    # Turn list of roles into string (get rid of duplicates, sort in alphabetical order)
                    if len(roles) > 0:
                        works += f"\n**Role(s):** {', '.join(sorted(list(set(roles))))}"

                    url = result['urls'][0]['url']

                elif category == 'series':
                    title = result["title"]
                    if not result["description"]:  # If no description in series, search for description in comics
                        if result['comics']['available'] > 0:
                            async with aiohttp.ClientSession() as session:
                                js = {}
                                while len(js) < 1:
                                    async with session.get(f"{result['comics']['items'][0]['resourceURI']}?{self.authentication}") as r:
                                        if r.status == 200:
                                            js = await r.json()
                                            if isinstance(js, int):
                                                js = {}
                                    print("Search comics for description:", js)

                            comics_json = js['data']['results'][0]

                            # If series doesn't have thumbnail image, obtain one from series
                            result['thumbnail']['path'] = self.get_thumbnail_path(result, comics_json)
                            print("thumbnail", result['thumbnail']['path'])
                            # Obtain description by querying the first available comic
                            if comics_json['description']:
                                description = self.replace_html_tags(comics_json['description']) + '\n'
                            else:  # If no description in comics, search for description in URL
                                print("Scraping comics description from URL...")
                                description = await self.get_website_description(comics_json['urls'][0]['url'],
                                                                                 ['featured-item-desc'])
                                if description is None:
                                    description = ''
                                    print(f"No description found from {comics_json['urls'][0]['url']}")
                                else:
                                    description += '\n'
                            print("Pulled description taken from comic")
                        else:
                            description = ''
                    else:
                        description = self.replace_html_tags(result["description"]) + '\n'
                    character_count = result['characters']['available']
                    if character_count == 0 and is_random:
                        continue
                    elif character_count >= 20:
                        choose_characters = sorted(sample(range(20), 10))
                    elif 10 < character_count < 20:
                        choose_characters = sorted(sample(range(character_count), 10))
                    else:
                        choose_characters = range(character_count)
                    creator_count = result['creators']['available']
                    if creator_count >= 20:
                        choose_creators = sorted(sample(range(20), 5))
                    elif 5 < creator_count < 20:
                        choose_creators = sorted(sample(range(creator_count), 5))
                    else:
                        choose_creators = range(creator_count)

                    description += f"\n**Featured characters:** {', '.join([result['characters']['items'][i]['name'] for i in choose_characters])}"
                    description += f"\n**Featured creators:**  {', '.join([result['creators']['items'][i]['name'] + ' (' + result['creators']['items'][i]['role'] + ')' for i in choose_creators])}"
                    url = result['urls'][0]['url']

                if category in ["characters", "creators"]:
                    if description:
                        embed = Embed(title=f"{self.title_category[category]}: {title}",
                                      description=description + "\n\n" + works, url=url)
                    else:
                        # if "Couldn't find" in works:
                        #    await self.bot.get_channel(834997161027436595).send(title)
                        embed = Embed(title=f"{self.title_category[category]}: {title}", description=works, url=url)
                else:
                    embed = Embed(title=f"{self.title_category[category]}: {title}", description=description, url=url)

                embed_image = result['thumbnail']['path'] + "/standard_fantastic." + result['thumbnail']['extension']
                embed.set_image(url=embed_image)
                embed.set_footer(text=json_data['attributionText'])

                if ctx:
                    await ctx.send(embed=embed)
                    await self.bot.testing_log_channel.send(
                        f"{self.bot.command_prefix}marvel: {ctx.author} queried '{category}, {query}' in guild '{ctx.guild}'")
                else:
                    embed.set_author(name=f"Today's daily Marvel feature!")
                    await channel.send(embed=embed)

        else:
            results = json_data['data']['results']
            if category == 'creators':
                header = 'fullName'
            elif category == 'series':
                header = 'title'
            else:
                header = 'name'
            results_string = '\n'.join(
                [results[i][header] for i in range(len(results))])
            embed = Embed(
                title=f"{1 + int(offset)} - {len(results) + int(offset)} of {json_data['data']['total']} total matches",
                description=results_string)
            embed.add_field(name="Note", value="To print individual results, make sure your query is specific enough that it returns at most "
                                               "5 matches. Only 20 results are returned per query; to view more, set the <offset> value.",
                            inline=False)
            embed.set_footer(text=json_data['attributionText'])

            await ctx.respond(embed=embed)
            await self.bot.testing_log_channel.send(
                f"{self.bot.command_prefix}marvel: {ctx.author} queried '{category}, {query}' in guild '{ctx.guild}'")

        if show_time:
            time_end = datetime.utcnow()
            time_elapsed = (time_end - time_start).total_seconds()
            if ctx.guild:
                await ctx.channel.send(f"Time taken to query: {time_elapsed} seconds")
            else:
                await ctx.send(f"Time taken to query: {time_elapsed} seconds")

    # @command(name="marvel", brief="Query from Marvel API.")
    # @cog_ext.cog_subcommand(base="marvel", name="search", description="Query from the Marvel Comics API.",
    #                         options=[
    #                             create_option(name="category",
    #                                           description="Category of your query. Omit for a random result.",
    #                                           option_type=3, required=False,
    #                                           choices=[create_choice(name=name, value=name) for name in
    #                                                    marvel_choices]),
    #                             create_option(name="query",
    #                                           description="Name of character, creator, or event, or title of series. Omit for a random result.",
    #                                           option_type=3, required=False),
    #                             create_option(name="query_type",
    #                                           description="Search type of query. Default is 'starts with'.",
    #                                           option_type=3, required=False,
    #                                           choices=[create_choice(name='starts with', value='startswith'),
    #                                                    create_choice(name='exact match', value='exact')]),
    #                             create_option(name="offset", description="For search with more than 20 results, choose number to skip. Default is 0.",
    #                                           option_type=3,
    #                                           required=False)])
    @slash_command(guild_ids=guild_ids, description="Query from the Marvel Comics API.", name="marvel")
    async def get_marvel(self, ctx,
                         category: Option(str, "Category of your query. Omit for a random result.", choices=marvel_choices, required=False, default=None),
                         query: Option(str, "Name of character, creator, event, or series. Omit for a random result.", required=False, default=None),
                         query_type: Option(str, "Query search time. Default is 'starts with'.", choices=['startswith', 'exact'], required=False, default='startswith'),
                         offset: Option(str, "For query with 20+ results, choose number of results to skip. Default is 0.", required=False, default='0'),
                         show_time=True):
        await ctx.defer()
        await self.post_marvel(ctx, category=category, query=query, query_type=query_type, offset=offset, show_time=show_time)

    # @cog_ext.cog_subcommand(base="marvel", name="examples",
    #                         description="Examples of how to query the Marvel Comics API.")
    # async def get_examples(self, ctx: SlashContext):
    #     embed = Embed(title="Examples", description="Examples for using **/marvel search**.", colour=Colour.red())
    #     embed.add_field(name="1) Get a random Marvel character",
    #                     value=f"{self.bot.command_prefix}marvel category: characters", inline=False)
    #     embed.add_field(name="2) Get a random Marvel event", value=f"{self.bot.command_prefix}marvel category: events",
    #                     inline=False)
    #     embed.add_field(name='3) Find all characters whose name starts with "Captain"',
    #                     value=f'{self.bot.command_prefix}marvel category: characters query: captain', inline=False)
    #     embed.add_field(name='4) Find creator named "Stan Lee"',
    #                     value=f'{self.bot.command_prefix}marvel category: creators query: Stan Lee', inline=False)
    #     embed.add_field(name='5) Find series called "Captain Marvel", published in 2019',
    #                     value=f'{self.bot.command_prefix}marvel category: series query: captain marvel 2019 query_type: exact',
    #                     inline=False)
    #     embed.add_field(name='6) Find all series that start with "Captain America"',
    #                     value=f'{self.bot.command_prefix}marvel category: series query: captain america', inline=False)
    #     embed.add_field(name='7) Find all series that start with "Captain America" and show next 20 results',
    #                     value=f'{self.bot.command_prefix}marvel category: series query: captain america query_type: startswith offset: 20',
    #                     inline=False)
    #
    #     await ctx.send(embed=embed, hidden=True)

    async def get_website_content(self, url, divclass, id='page-wrapper'):
        website_content = None
        while website_content is None:
            website_content = await redwing_functions.parse_webpage(url)
        results = website_content.find(id=id)
        if results is None:
            return results
        else:
            return results.find('div', class_=divclass)

    def replace_html_tags(self, text):
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text().strip()

    def get_thumbnail_path(self, original, new):
        if 'image_not_available' in original['thumbnail']['path']:
            print("Finding new thumbnail...")
            original['thumbnail']['path'] = new['thumbnail']['path']
        return original['thumbnail']['path']

    def get_series(self, result, category):
        num = result['series']['available']
        series_uri = []
        if num == 0:
            return "No featured works available.", series_uri
        choose_series = None
        if 0 < num <= 5:
            choose_series = range(num)
        elif 5 < num < 20:
            choose_series = sorted(sample(range(num), 5))
        elif num >= 20:
            choose_series = sorted(
                sample(range(20), 5))  # API only retrieves 20 most recent series, so sample from that
        highlights = ', '.join([result['series']['items'][i]['name'] for i in choose_series])
        series_uri = [result['series']['items'][i]['resourceURI'] for i in choose_series]
        if category == 'characters':
            return "Featured in %i comics and %i series. \n**Series highlights:** %s" % (
                result['comics']['available'], result['series']['available'], highlights), series_uri
        elif category == 'events':
            if result['comics']['available'] > 0:
                return "**Series highlights:** %s" % highlights, series_uri
            else:
                return ''
        elif category == "creators":
            return "Created %i comics and %i series.\n**Series highlights:** %s" % (
                result['comics']['available'], result['series']['available'], highlights), series_uri

    def write_to_json(self, filename, name, description):
        print('Writing to JSON...')
        with open(filename, 'r') as f:
            data = json.load(f)
            data['description'][name] = description
        with open(filename, 'w') as f:
            json.dump(data, f)
        print('Writing to JSON complete.')
        return json.load(open(filename, 'r'))

    async def get_website_description(self, url, divclasses=None):
        if divclasses is None:
            divclasses = ['text', 'masthead__copy']
        description = None
        if len(divclasses) > 1:
            for d in divclasses:
                biography = await self.get_website_content(url, d)
                if d == 'text':
                    try:
                        if biography.find('p') == None:
                            description = '. '.join(biography.text.strip().split('. ')[:3]) + '.'
                            break
                        else:
                            description = '. '.join(biography.find('p').text.strip().split('. ')[:3]) + '.'
                            break
                    except AttributeError:
                        pass
                if d == 'masthead__copy':
                    try:
                        description = biography.text
                        break
                    except AttributeError:
                        pass
        else:
            print(url)
            comic_blurb = await self.get_website_content(url, divclasses, id='')
            if comic_blurb:
                description = comic_blurb.find('p').text.strip()
            else:
                description = ''
        return description

    async def daily_marvel(self):
        for guildid in self.bot.guild_channels.keys():
            channel = self.bot.find_channel(guildid, "marvel")
            await self.post_marvel(ctx=None, channel=channel, show_time=False)
            print(f"Posted daily Marvel feature to channel {channel}")

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up('marvel')
            ts = str(
                int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()))  # Unique timestamp, approximately GPS
            unique_hash = hashlib.md5(
                (ts + self.bot.MARVEL_PRIVATEKEY + self.bot.MARVEL_PUBLICKEY).encode('utf-8')).hexdigest()
            self.authentication = f"&ts={ts}&apikey={self.bot.MARVEL_PUBLICKEY}&hash={unique_hash}"


def setup(bot):
    bot.add_cog(Marvel(bot))
