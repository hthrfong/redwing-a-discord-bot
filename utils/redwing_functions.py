import aiohttp
from bs4 import BeautifulSoup
import re


async def parse_webpage(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status == 200:
                return BeautifulSoup(await r.read(), 'html.parser')


def find_word(msg, keywords):
    return any([len(re.findall(f"\\b{word}\\b", msg)) > 0 for word in keywords])
