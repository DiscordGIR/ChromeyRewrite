import json
import traceback

import discord
from discord import Color, Embed
from discord.commands import slash_command
from discord.commands import Option
from discord.ext import commands
from utils.autocompleters import (board_autocompleter, device_autocompleter,
                                  get_skylar_api)
from utils.config import cfg
from utils.context import ChromeyContext
from utils.logger import logger
from utils.menu import Menu
from utils.permissions.checks import PermissionsFailure


async def format_devices_page(ctx, entries, current_page, all_pages):
    embed = Embed(
        title=f'Search results', color=Color.blurple())
    for v in entries:
        embed.add_field(name=v[0], value=(
            v[1][:250] + '...') if len(v[1]) > 250 else v[1], inline=False)
    embed.set_footer(text=f"Page {current_page} of {len(all_pages)}")
    return embed


class Devices(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(guild_ids=[cfg.guild_id], description="Retreive the brand name for a given Chromebook board name")
    async def board2device(self, ctx: ChromeyContext, board: Option(str, autocomplete=board_autocompleter)):
        """(alias !b2d) Retreive the brand name for a given Chromebook board name

        Example usage
        --------------
        !b2d edgar


        Parameters
        ----------
        board : str
            "Board name to convert"
        """

        # case insensitivity
        board = board.lower()

        # fetch data from skylar's API
        response = await get_skylar_api()
        if response is None:
            raise commands.BadArgument(
                "An error occurred communicating with the API.")

        devices = [device for device in response if device.get(
            "Codename").lower() == board.lower()]
        if not devices:
            raise commands.BadArgument("A board with that name was not found!")

        device_match = devices[0]

        await ctx.respond(embed=Embed(title=f'{device_match["Codename"]} belongs to...', color=Color(value=0x37b83b), description=device_match["Brand names"]).set_footer(text=f"Powered by https://cros.tech/ (by Skylar), requested by {ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.display_avatar))

    @slash_command(guild_ids=[cfg.guild_id], description="Retrieve the board name from a specified brand name as a search term")
    async def device2board(self, ctx: ChromeyContext, *, search_term: Option(str, autocomplete=device_autocompleter)):
        """(alias !d2b) Retrieve the board name from a specified brand name as a search term

        Example usage
        --------------
        !d2b acer chromebook 11

        Parameters
        ----------
        search_term : str
            "Model name to search for"

        """

        if search_term == "":
            raise commands.BadArgument(
                "You need to supply a boardname! Example: `!d2b acer chromebook`")

        search_term = search_term.lower()

        # fetch data from skylar's API
        response = await get_skylar_api()
        if response is None:
            raise commands.BadArgument(
                "An error occurred communicating with the API.")

        search_results = [(device["Codename"], device["Brand names"])
                          for device in response if 'Brand names' in device and search_term in device['Brand names'].lower()]

        if not search_results:
            raise commands.BadArgument("A board with that name was not found!")

        menu = Menu(ctx, search_results, per_page=8, page_formatter=format_devices_page, whisper=ctx.whisper)
        await menu.start()

    @slash_command(guild_ids=[cfg.guild_id], description="Get ChromeOS version data for a specified Chromebook board name")
    async def updates(self, ctx: ChromeyContext, *, board: Option(str, autocomplete=board_autocompleter)):
        """(alias !updates) Get ChromeOS version data for a specified Chromebook board name

        Example usage
        --------------
        !updates edgar

        Parameters
        ----------
        board : str
            "name of board to get updates for"
        """

        # ensure the board arg is only alphabetical chars
        if (not board.isalpha()):
            raise commands.BadArgument(
                "The board should only be alphabetical characters!")

        # case insensitivity
        board = board.lower()

        # fetch data from skylar's API
        data = await get_skylar_api()

        # loop through response to find board
        devices = [d for d in data if d['Codename'] == board]
        if not devices:
             raise commands.BadArgument("Couldn't find a result with that boardname!")

        data_board = devices[0]

        embed = Embed(
            title=f"ChromeOS update status for {board}", color=Color(value=0x37b83b))
        version = data_board["Stable"].split("<br>")
        embed.add_field(
            name=f'Stable Channel', value=f'**Version**: {version[1]}\n**Platform**: {version[0]}')

        version = data_board["Beta"].split("<br>")
        if len(version) == 2:
            embed.add_field(
                name=f'Beta Channel', value=f'**Version**: {version[1]}\n**Platform**: {version[0]}')
        else:
            embed.add_field(name=f'Beta Channel',
                            value=f'**Version**: {data_board["Beta"]}')

        version = data_board["Dev"].split("<br>")
        if len(version) == 2:
            embed.add_field(
                name=f'Dev Channel', value=f'**Version**: {version[1]}\n**Platform**: {version[0]}')
        else:
            embed.add_field(name=f'Dev Channel',
                            value=f'**Version**: {data["Dev"]}')

        if (data_board["Canary"] is not None):
            version = data_board["Canary"].split("<br>")
            if len(version) == 2:
                embed.add_field(
                    name=f'Canary Channel', value=f'**Version**: {version[1]}\n**Platform**: {version[0]}')

        embed.set_footer(
            text=f"Powered by https://cros.tech/ (by Skylar), requested by {ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.display_avatar)
        await ctx.respond(embed=embed)

    @updates.error
    @board2device.error
    @device2board.error
    async def info_error(self,  ctx: ChromeyContext, error):
        if isinstance(error, discord.ApplicationCommandInvokeError):
            error = error.original

        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, PermissionsFailure)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MaxConcurrencyReached)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(error)
        else:
            await ctx.send_error("A fatal error occured. Tell <@109705860275539968> about this.")
            logger.error(traceback.format_exc())


def setup(bot):
    bot.add_cog(Devices(bot))
