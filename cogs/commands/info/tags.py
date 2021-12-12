import random
import re
import traceback
from datetime import datetime
from io import BytesIO

import discord
from data.model.tag import Tag
from data.services.guild_service import guild_service
from discord.commands import Option, slash_command
from discord.commands.commands import message_command, user_command
from discord.ext import commands
from discord.ext.commands.cooldowns import CooldownMapping
from utils.autocompleters import tags_autocomplete
from utils.config import cfg
from utils.context import ChromeyContext, PromptData
from utils.logger import logger
from utils.menu import Menu
from utils.message_cooldown import MessageTextBucket
from utils.permissions.checks import (PermissionsFailure,
                                      nerds_and_up, whisper)
from utils.permissions.permissions import permissions
from utils.permissions.slash_perms import slash_perms


async def format_tag_page(entries, all_pages, current_page, ctx):
    embed = discord.Embed(title=f'Tags', color=discord.Color.blurple())
    for tag in entries:
        res = tag.content[:50] + "..." if len(tag.content) > 50 else tag.content
        argo = " [args]" if tag.args else ""
        if (argo != ""):
            res += argo
        embed.add_field(name=f'!t {tag.name}{argo}', value=f'**ID**: {tag._id}\n**Supports arguments**: {tag.args}\n**Creator**: {tag.added_by_tag}\n**Number of uses**: {tag.use_count}')

    embed.set_footer(
        text=f"Page {current_page} of {len(all_pages)}")
    return embed


class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tag_cooldown = CooldownMapping.from_cooldown(
            1, 5, MessageTextBucket.custom)

    @slash_command(guild_ids=[cfg.guild_id], description="Display a tag")
    async def tag(self, ctx: ChromeyContext, name: Option(str, description="Tag name", autocomplete=tags_autocomplete), args: Option(str, description="Arguments to pass to command (optional)", required=False), user_to_mention: Option(discord.Member, description="User to mention in the response", required=False)):
        """Displays a tag.

        Example usage
        -------------
        /tag name:<tagname>

        Parameters
        ----------
        name : str
            "Name of tag to display"

        """
        name = name.lower()
        tag = guild_service.get_tag_by_name(name, args != "")
        
        if tag is None:
            raise commands.BadArgument("That tag does not exist.")
        
        file = tag.image.read()
        if file is not None:
            file = discord.File(BytesIO(file), filename="image.gif" if tag.image.content_type == "image/gif" else "image.png")
        response = await self.tag_response(tag, args)
        
        if user_to_mention is not None:
            response = f"Hey {user_to_mention.mention}, have a look at this!\n{response}"
        
        await ctx.respond_or_edit(response, file=file, mention_author=False)

    def tag_response(self, tag, args):
        pattern = re.compile(r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*")
        if (pattern.match(tag.content)):
            response = tag.content + "%20".join(args.split(" "))
        else:
            response = tag.content + " " + args
        return response

    @nerds_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Add a new tag", permissions=slash_perms.nerds_and_up())
    async def addtag(self, ctx: ChromeyContext, name: str, args: Option(bool)) -> None:
        """Add a tag. Optionally attach an image. (Genius only)

        Example usage
        -------------
        /addtag roblox

        Parameters
        ----------
        name : str
            "Name of the tag"

        """

        pattern = re.compile("^[a-zA-Z0-9_-]*$")
        if (not pattern.match(name)):
            raise commands.BadArgument("The command name should only be alphanumeric characters with `_` and `-`!")

        if len(name.split()) > 1:
            raise commands.BadArgument(
                "Tag names can't be longer than 1 word.")

        if (guild_service.get_tag_by_name(name.lower())) is not None:
            raise commands.BadArgument("Tag with that name already exists.")

        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="description",
            description="Please enter the content of this tag, and optionally attach an image.",
            convertor=str,
            raw=True)
        res = await ctx.prompt(prompt)

        if res is None:
            await ctx.send_warning("Cancelled.")
            return

        description, response = res
        # prepare tag data for database
        tag = Tag()
        tag.name = name.lower()
        tag.content = description
        tag.added_by_id = ctx.author.id
        tag.added_by_tag = str(ctx.author)

        # did the user want to attach an image to this tag?
        if len(response.attachments) > 0:
            # ensure the attached file is an image
            image = response.attachments[0]
            _type = image.content_type
            if _type not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                raise commands.BadArgument("Attached file was not an image.")
            else:
                image = await image.read()
            # save image bytes
            tag.image.put(image, content_type=_type)

        # store tag in database
        guild_service.add_tag(tag)

        _file = tag.image.read()
        if _file is not None:
            _file = discord.File(BytesIO(
                _file), filename="image.gif" if tag.image.content_type == "image/gif" else "image.png")

        await ctx.respond(f"Added new tag!", file=_file or discord.utils.MISSING, embed=await self.prepare_tag_embed(tag))

    @nerds_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Delete a tag", permissions=slash_perms.nerds_and_up())
    async def deltag(self, ctx: ChromeyContext, name: Option(str, description="Name of tag to delete", autocomplete=tags_autocomplete)):
        """Delete tag (geniuses only)

        Example usage
        --------------
        /deltag name:<tagname>

        Parameters
        ----------
        name : str
            "Name of tag to delete"

        """

        name = name.lower()

        tag = guild_service.get_tag_by_name(name)
        if tag is None:
            raise commands.BadArgument("That tag does not exist.")

        if tag.image is not None:
            tag.image.delete()

        guild_service.remove_tag(name)
        await ctx.send_warning(f"Deleted tag `{tag.name}`.", delete_after=5)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="List all tags")
    async def taglist(self, ctx: ChromeyContext):
        """List all tags
        """

        tags = sorted(guild_service.get_guild().tags, key=lambda tag: tag.name)

        if len(tags) == 0:
            raise commands.BadArgument("There are no tags defined.")

        menu = Menu(tags, ctx.channel, per_page=12,
                    format_page=format_tag_page, interaction=True, ctx=ctx, whisper=ctx.whisper)

        await menu.start()

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Search for a tag by name")
    async def search(self, ctx: ChromeyContext, command_name:str):
        """Search through commands for matching name by keyword
        
        Example usage
        --------------
        !search cros
        """
        
        # ensure command name doesn't have illegal chars
        pattern = re.compile("^[a-zA-Z0-9_-]*$")
        if (not pattern.match(command_name)):
            raise commands.BadArgument("The command name should only be alphanumeric characters with `_` and `-`!\nExample usage`!search cam-sucks`")
            
        # always store command name as lowercase for case insensitivity
        command_name = command_name.lower()

        res = sorted(ctx.settings.guild().tags, key=lambda tag: tag.name)
        match = [ command for command in res if command_name in command.name ]

        if len(match) == 0:
            raise commands.BadArgument(f'No commands found with that name!')
        #send paginated results
        
        menu = Menu(res, ctx.channel, per_page=6,
                    format_page=format_tag_page, interaction=True, ctx=ctx, whisper=ctx.whisper)


    async def prepare_tag_embed(self, tag):
        """Given a tag object, prepare the appropriate embed for it

        Parameters
        ----------
        tag : Tag
            Tag object from database

        Returns
        -------
        discord.Embed
            The embed we want to send
        """
        embed = discord.Embed(title=tag.name)
        embed.description = tag.content
        embed.timestamp = tag.added_date
        embed.color = discord.Color.blue()

        if tag.image.read() is not None:
            embed.set_image(url="attachment://image.gif" if tag.image.content_type ==
                            "image/gif" else "attachment://image.png")
        embed.set_footer(
            text=f"Added by {tag.added_by_tag} | Used {tag.use_count} times")
        return embed

    @search.error
    @tag.error
    @taglist.error
    @deltag.error
    @addtag.error
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
    bot.add_cog(Tags(bot))
