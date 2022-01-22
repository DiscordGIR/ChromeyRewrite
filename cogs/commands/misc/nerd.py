import asyncio
import datetime

import traceback

import discord
from discord.ext import commands
from data.services.guild_service import guild_service
from utils.logger import logger

from utils.context import ChromeyContext, PromptData
from utils.permissions.slash_perms import slash_perms
from utils.permissions.checks import PermissionsFailure, always_whisper, nerds_and_up
from utils.config import cfg

class Nerd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot        

    @nerds_and_up()
    @discord.slash_command(guild_ids=[cfg.guild_id], description="Post an embed", permissions=slash_perms.nerds_and_up())
    async def postembed(self, ctx: ChromeyContext, *, title: str):
        """Post an embed in the current channel (Geniuses only)

        Example usage
        ------------
        /postembed This is a title (you will be prompted for a description)

        Parameters
        ----------
        title : str
            "Title for the embed"
        
        """

        # get #common-issues channel
        channel = ctx.channel

        # prompt the user for common issue body
        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="description",
            description="Please enter a description of this embed (optionally attach an image)",
            convertor=str,
            raw=True)

        res = await ctx.prompt(prompt)
        if res is None:
            await ctx.send_warning("Cancelled new embed.")
            return

        description, response = res

        embed, f = await self.prepare_issues_embed(title, description, response)
        await channel.send(embed=embed, file=f)

    async def prepare_issues_embed(self, title, description, message):
        embed = discord.Embed(title=title)
        embed.color = discord.Color.random()
        embed.description = description
        f = None
        if len(message.attachments) > 0:
            f = await message.attachments[0].to_file()
            embed.set_image(url=f"attachment://{f.filename}")
        embed.set_footer(text=f"Submitted by {message.author}")
        embed.timestamp = datetime.datetime.now()
        return embed, f

    @nerds_and_up()
    @discord.slash_command(guild_ids=[cfg.guild_id], description="Put user on timeout to read rules", permissions=slash_perms.nerds_and_up())
    async def rules(self, ctx: ChromeyContext, member: discord.Member):
        """Put user on timeout to read rules (nerds and up)
        
        Example usage
        --------------
        !rules @SlimShadyIAm#9999

        Parameters
        ----------
        member : discord.Member
            "user to time out"
        """

        if member.id == ctx.author.id:
            await ctx.message.add_reaction("🤔")
            raise commands.BadArgument("You can't call that on yourself.")
        if member.id == self.bot.user.id:
            await ctx.message.add_reaction("🤔")
            raise commands.BadArgument("You can't call that on me :(")

        role = ctx.guild.get_role(guild_service.get_guild().role_rules)
        
        if (role is None):
            raise commands.BadArgument('rules role not found!')

        try:
            ctx.tasks.schedule_unrules(member.id, datetime.datetime.now() + datetime.timedelta(minutes=15))
        except Exception:
            raise commands.BadArgument("This user is probably already on timeout.")
        
        embed = discord.Embed(title="You have been put in timeout.", color=discord.Color(value=0xebde34), description=f'{ctx.author.name} thinks you need to review the rules. You\'ve been placed on timeout for 15 minutes. During this time, you won\'t be able to interact with the server').set_footer(text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.display_avatar)
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            channel = ctx.guild.get_channel(guild_service.get_guild().channel_offtopic)
            await channel.send(f'{member.mention} I tried to DM this to you, but your DMs are closed! You\'ll be timed out in 10 seconds.', embed=embed)
            await ctx.defer()
            await asyncio.sleep(10)
        
        await member.add_roles(role)
        
        await ctx.respond(embed=discord.Embed(title="Done!", color=discord.Color(value=0x37b83b), description=f'Gave {member.mention} the rules role. We\'ll let them know and remove it in 15 minutes.').set_footer(text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.display_avatar))

    @nerds_and_up()
    @discord.slash_command(guild_ids=[cfg.guild_id], description="Put user on timeout", permissions=slash_perms.nerds_and_up())
    async def timeout(self, ctx: ChromeyContext, member: discord.Member):
        """Put user on timeout (nerds and up)
        
        Example usage
        --------------
        !timeout @SlimShadyIAm#9999

        Parameters
        ----------
        member : discord.Member
            "user to time out"
        """
        
        if member.id == ctx.author.id:
            await ctx.message.add_reaction("🤔")
            raise commands.BadArgument("You can't call that on yourself.")
        if member.id == self.bot.user.id:
            await ctx.message.add_reaction("🤔")
            raise commands.BadArgument("You can't call that on me :(")

        role = ctx.guild.get_role(guild_service.get_guild().role_timeout)
        
        if (role is None):
            raise commands.BadArgument('timeout role not found!')

        try:
            ctx.tasks.schedule_untimeout(member.id, datetime.datetime.now() + datetime.timedelta(minutes=15))
        except Exception as e:
            print(e)
            raise commands.BadArgument("This user is probably already on timeout.")
        
        embed = discord.Embed(title="You have been put in timeout.", color=discord.Color(value=0xebde34), description=f'{ctx.author.name} gave you the timeout role. We\'ll remove it in 15 minutes. Please read the message in the timeout channel and review the rules.').set_footer(text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.display_avatar)
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            channel = ctx.guild.get_channel(guild_service.get_guild().channel_offtopic)
            await channel.send(f'{member.mention} I tried to DM this to you, but your DMs are closed! You\'ll be timed out in 10 seconds.', embed=embed)
            await ctx.defer()
            await asyncio.sleep(10)
        
        await member.add_roles(role)
        
        await ctx.respond(embed=discord.Embed(title="Done!", color=discord.Color(value=0x37b83b), description=f'Gave {member.mention} the timeout role. We\'ll let them know and remove it in 15 minutes.').set_footer(text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.display_avatar))

    @always_whisper()
    @nerds_and_up()
    @discord.slash_command(guild_ids=[cfg.guild_id], description="Create a poll", permissions=slash_perms.nerds_and_up())
    async def poll(self, ctx: ChromeyContext, *, content: str):
        """Create a poll (Nerds and up)
        
        Example usage
        --------------
        !poll are u good?

        Parameters
        ----------
        content : str
            "Description"
        """

        embed = discord.Embed(title="New poll!", description=content, color=discord.Color.blurple())
        msg = await ctx.channel.send(embed=embed)
        await msg.add_reaction('👍')
        await msg.add_reaction('👎')

        await ctx.send_success("Done!")

    @rules.error
    @poll.error
    @timeout.error
    @postembed.error
    async def info_error(self, ctx: ChromeyContext, error):
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
    bot.add_cog(Nerd(bot))
