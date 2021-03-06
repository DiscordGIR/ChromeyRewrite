import traceback

import discord
from data.model.filterword import FilterWord
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from discord.commands import Option, slash_command
from discord.ext import commands
from utils.autocompleters import filterwords_autocomplete
from utils.config import cfg
from utils.context import ChromeyContext
from utils.views.menu import Menu
from utils.logger import logger
from utils.permissions.checks import (PermissionsFailure, admin_and_up, always_whisper,
                                      mod_and_up)
from utils.permissions.permissions import permissions
from utils.permissions.slash_perms import slash_perms


def format_filter_page(_, entries, current_page, all_pages):
    """Formats the page for the filtered words embed
    
    Parameters
    ----------
    entry : dict
        "The dictionary for the entry"
    all_pages : list
        "All entries that we will eventually iterate through"
    current_page : number
        "The number of the page that we are currently on"
        
    Returns
    -------
    discord.Embed
        "The embed that we will send"
        
    """
    embed = discord.Embed(
        title=f'Filtered words', color=discord.Color.blurple())
    for word in entries:
        notify_flag = ""
        if word.notify:
            notify_flag = "🔔"
        embed.add_field(name=word.word, value=f"Bypassed by: {permissions.level_info(word.bypass)}\nFlags: {notify_flag}")
    embed.set_footer(
        text=f"Page {current_page} of {len(all_pages)}")
    return embed


class Filters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @always_whisper()
    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Toggles bot pinging for reports when offline.", permissions=slash_perms.mod_and_up())
    async def offlineping(self, ctx: ChromeyContext, should_ping: Option(bool, description="Do you want to get pinged?", required=False) = None):
        """Toggles bot pinging for reports when offline

        Example usage
        --------------
        /offlineping val:<value>

        Parameters
        ----------
        val : bool
            "True or False, if you want pings or not"

        """

        cur = user_service.get_user(ctx.author.id)
        
        if should_ping is None:
            should_ping = not cur.offline_report_ping 

        cur.offline_report_ping = should_ping
        cur.save()

        if should_ping:
            await ctx.send_success("You will now be pinged for reports when offline")
        else:
            await ctx.send_warning("You will no longer be pinged for reports when offline")

    _filter = discord.SlashCommandGroup("filter", "Interact with filter", guild_ids=[cfg.guild_id], permissions=slash_perms.mod_and_up())

    @mod_and_up()
    @_filter.command(description="Add a word to filter")
    async def add(self, ctx: ChromeyContext, notify: Option(bool, description="Whether to generate a report or not when this word is filtered"), bypass: Option(int, description="Level that bypasses this filter"), *, phrase: str) -> None:
        """Adds a word to filter (admin only)

        Example usage
        -------------
        /filter add notify:<shouldnotify> bypass:<bypasslevel> <phrase>

        Parameters
        ----------
        notify : bool
            "Whether to generate a report or not when this word is filtered"
        bypass : int
            "Level that can bypass this word"
        phrase : str
            "Phrase to filter"
        """

        fw = FilterWord()
        fw.bypass = bypass
        fw.notify = notify
        fw.word = phrase

        if not guild_service.add_filtered_word(fw):
            raise commands.BadArgument("That word is already filtered!")

        phrase = discord.utils.escape_markdown(phrase)
        phrase = discord.utils.escape_mentions(phrase)

        await ctx.send_success(title="Added new word to filter!", description=f"This filter {'will' if notify else 'will not'} ping for reports, level {bypass} can bypass it, and the phrase is `{phrase}`")

    @mod_and_up()
    @_filter.command(description="List filtered words", name="list")
    async def _list(self, ctx: ChromeyContext):
        """Lists filtered words (admin only)
        
        Example usage
        -------------
        /filter list
        
        """

        filters = guild_service.get_guild().filter_words
        if len(filters) == 0:
            raise commands.BadArgument("The filterlist is currently empty. Please add a word using `/filter`.")
        
        filters = sorted(filters, key=lambda word: word.word.lower())

        menu = Menu(ctx, filters, per_page=12, page_formatter=format_filter_page, whisper=False)
        await menu.start()

    @mod_and_up()
    @_filter.command(description="Remove word from filter")
    async def remove(self, ctx: ChromeyContext, *, word: Option(str, autocomplete=filterwords_autocomplete)):
        """Removes a word from filter (admin only)

        Example usage
        --------------
        /filter remove <word>

        Parameters
        ----------
        word : str
            "Word to remove"

        """

        word = word.lower()

        words = guild_service.get_guild().filter_words
        words = list(filter(lambda w: w.word.lower() == word.lower(), words))
        
        if len(words) > 0:
            guild_service.remove_filtered_word(words[0].word)
            await ctx.send_success("Deleted!")
        else:
            await ctx.send_warning("That word is not filtered.", delete_after=5)            

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Whitelist a guild from invite filter", permissions=slash_perms.admin_and_up())
    async def whitelist(self, ctx: ChromeyContext, id: Option(str, description="Guild ID to whitelist")):
        """Whitelists a guild from invite filter (admin only)

        Example usage
        --------------
        /whitelist <guildid>

        Parameters
        ----------
        id : int
            "ID of guild to whitelist"

        """

        try:
            id = int(id)
        except ValueError:
            raise commands.BadArgument("Invalid ID!")

        if guild_service.add_whitelisted_guild(id):
            await ctx.send_success("Whitelisted.")
        else:
            await ctx.send_warning("That server is already whitelisted.", delete_after=5)

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Blacklist a guild from invite filter ", permissions=slash_perms.admin_and_up())
    async def blacklist(self, ctx: ChromeyContext, id: Option(str, description="Guild ID to blacklist")):
        """Blacklists a guild from invite filter (admin only)

        Example usage
        --------------
        /blacklist <guildid>

        Parameters
        ----------
        id : int
            "ID of guild to blacklist"

        """

        try:
            id = int(id)
        except ValueError:
            raise commands.BadArgument("Invalid ID!")

        if guild_service.remove_whitelisted_guild(id):
            await ctx.send_success("Blacklisted.")
        else:
            await ctx.send_warning("That server is already blacklisted.", delete_after=5)

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Ignore channel in filter", permissions=slash_perms.admin_and_up())
    async def ignorechannel(self, ctx: ChromeyContext, channel: discord.TextChannel) -> None:
        """Ignores channel in filter (admin only)

        Example usage
        -------------
        /ignorechannel <channel>

        Parameters
        ----------
        channel : discord.Channel
            "Channel to ignore"

        """

        if guild_service.add_ignored_channel(channel.id):
            await ctx.send_success(f"The filter will no longer run in {channel.mention}.")
        else:
            await ctx.send_warning("That channel is already ignored.", delete_after=5)

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Unignore channel in filter", permissions=slash_perms.admin_and_up())
    async def unignorechannel(self, ctx: ChromeyContext, channel: discord.TextChannel) -> None:
        """Unignores channel in filter (admin only)

        Example usage
        -------------
        /unignorechannel <channel>

        Parameters
        ----------
        channel : discord.Channel
            "Channel to unignore"
            
        """

        if guild_service.remove_ignored_channel(channel.id):
            await ctx.send_success(f"Resumed filtering in {channel.mention}.")
        else:
            await ctx.send_warning("That channel is not already ignored.", delete_after=5)

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Disabling enhanced filter checks on a word", permissions=slash_perms.mod_and_up())
    async def falsepositive(self, ctx: ChromeyContext, *, word: Option(str, autocomplete=filterwords_autocomplete)):
        """Disabling enhanced filter checks on a word (admin only)

        Example usage
        --------------
        /falsepositive <word>

        Parameters
        ----------
        word : str
            "Word to mark as false positive"

        """

        word = word.lower()

        words = guild_service.get_guild().filter_words
        words = list(filter(lambda w: w.word.lower() == word.lower(), words))
        
        if len(words) > 0:
            words[0].false_positive = not words[0].false_positive
            if guild_service.update_filtered_word(words[0]):
                await ctx.send_success("Marked as potential false positive, we won't perform the enhanced checks on it!" if words[0].false_positive else "Removed as potential false positive.")
            else:
                raise commands.BadArgument("Unexpected error occured trying to mark as false positive!")
        else:
            await ctx.send_warning("That word is not filtered.", delete_after=5)  
            
    @falsepositive.error
    @whitelist.error
    @blacklist.error
    @remove.error
    @add.error
    @_list.error
    @offlineping.error
    @ignorechannel.error
    @unignorechannel.error
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
    bot.add_cog(Filters(bot))
