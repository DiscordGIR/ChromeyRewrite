import json
from typing import List

import aiohttp
from aiocache import cached
from discord import OptionChoice
from data.model.case import Case
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from discord.commands.context import AutocompleteContext

from utils.mod.give_birthday_role import MONTH_MAPPING


@cached(ttl=3600)
async def get_skylar_api():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://raw.githubusercontent.com/skylartaylor/cros-updates/master/src/data/cros-updates.json') as response:
            if response.status == 200:
                text = await response.text()
                return json.loads(text)
            else:
                return None


async def board_autocompleter(ctx: AutocompleteContext):
    boards = await get_skylar_api()
    if boards is None:
        return []

    boards = [device.get("Codename") for device in boards if device.get("Codename") is not None and len(device.get("Codename")) < 60 and ctx.value.lower() in device.get("Codename").lower()]
    boards.sort()
    return boards[:25]


async def device_autocompleter(ctx: AutocompleteContext):
    boards = await get_skylar_api()
    if boards is None:
        return []

    # boards = [device.get("Codename") for device in boards if device.get("Codename") is not None and len(device.get("Codename")) < 60 and ctx.value.lower() in device.get("Codename").lower()]
    # boards.sort()
    # return boards[:25]
    
    #     search_results = [(device["Codename"], device["Brand names"])
    #                       for device in devices if 'Brand names' in device and search_term in device['Brand names'].lower()]
    devices = [device.get("Brand names")[:100] for device in boards if device.get("Brand names") is not None and ctx.value.lower() in device.get("Brand names").lower()]
    devices.sort()
    return devices[:25]


async def date_autocompleter(ctx: AutocompleteContext) -> list:
    """Autocompletes the date parameter for !mybirthday"""
    month = MONTH_MAPPING.get(ctx.options.get("month"))
    if month is None:
        return []

    return [i for i in range(1, month["max_days"]+1) if str(i).startswith(str(ctx.value))][:25]


async def tags_autocomplete(ctx: AutocompleteContext):
    tags = [tag.name.lower() for tag in guild_service.get_guild().tags]
    tags = list(set(tags))
    tags.sort()
    return [tag for tag in tags if tag.lower().startswith(ctx.value.lower())][:25]


async def memes_autocomplete(ctx: AutocompleteContext):
    memes = [meme.name.lower() for meme in guild_service.get_guild().memes]
    memes.sort()
    return [meme for meme in memes if meme.lower().startswith(ctx.value.lower())][:25]


async def liftwarn_autocomplete(ctx: AutocompleteContext):
    cases: List[Case] = [case for case in user_service.get_cases(
        int(ctx.options["user"])).cases if case._type == "WARN" and not case.lifted]
    cases.sort(key=lambda x: x._id, reverse=True)

    return [OptionChoice(f"{case._id} - {case.reason}", str(case._id)) for case in cases if (not ctx.value or str(case._id).startswith(str(ctx.value)))][:25]


async def filterwords_autocomplete(ctx: AutocompleteContext):
    words = [word.word for word in guild_service.get_guild().filter_words]
    words.sort()

    return [word for word in words if str(word).startswith(str(ctx.value))][:25]
