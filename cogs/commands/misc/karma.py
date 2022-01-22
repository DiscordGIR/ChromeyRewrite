import datetime
import traceback
import typing

import discord
import humanize
from data.services.user_service import user_service
from discord.ext import commands
from utils.logger import logger
from utils.config import cfg
from utils.context import ChromeyContext
from utils.permissions.permissions import permissions
from utils.permissions.checks import PermissionsFailure, mod_and_up, nerds_and_up
from utils.permissions.slash_perms import slash_perms
from utils.views.menu import Menu

def format_history_page(ctx, entries, current_page, all_pages):
    embed = discord.Embed(
        title='History', color=discord.Color(value=0xfcba03))
    for v in entries:
        invoker_text = f"<@{v['from']}>"

        if v["amount"] < 0:
            embed.add_field(
                name=f'{humanize.naturaltime(v["date"])}', value=f'{invoker_text} took {v["amount"]} karma from {ctx.invokee.mention}\n**Reason**: {v["reason"]}', inline=False)
        else:
            embed.add_field(
                name=f'{humanize.naturaltime(v["date"])}', value=f'{invoker_text} gave {v["amount"]} karma to {ctx.invokee.mention}\n**Reason**: {v["reason"]}', inline=False)
    
    embed.set_footer(text=f'Page {current_page}/{len(all_pages)}')
    return embed

def format_modhistory_page(ctx, entries, current_page, all_pages):
    embed = discord.Embed(
        title='History', color=discord.Color(value=0xfcba03))
    for v in entries:
        target = f"<@{v['to']}>"

        if v["amount"] < 0:
            embed.add_field(
                name=f'{humanize.naturaltime(v["date"])}', value=f'{ctx.invoker} took {v["amount"]} karma from {target}\n**Reason**: {v["reason"]}', inline=False)
        else:
            embed.add_field(
                name=f'{humanize.naturaltime(v["date"])}', value=f'{ctx.invoker} gave {v["amount"]} karma to {target}\n**Reason**: {v["reason"]}', inline=False)
    
    embed.set_footer(text=f'Page {current_page}/{len(all_pages)}')
    return embed

def format_leaderboard_page(ctx, entries, current_page, all_pages):
    embed = discord.Embed(
        title=f'Leaderboard: Page {current_page}/{len(all_pages)}', color=discord.Color(value=0xfcba03))
    embed.set_footer(icon_url=ctx.author.display_avatar,
                        text="Note: Nerds and Moderators were excluded from these results.")
    embed.description = ""

    for i, data in enumerate(entries):
        user, member = data
        embed.add_field(
            name=f"Rank {i+1}", value=f"<@{member.id}> ({member})\n{user.karma} karma", inline=False)
    return embed

class Karma(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_cache = {}

    karma = discord.SlashCommandGroup("karma", "Interact with karma", guild_ids=[
                                      cfg.guild_id], permissions=slash_perms.nerds_and_up())

    @karma.command()
    @nerds_and_up()
    async def get(self, ctx: ChromeyContext, member: discord.Option(discord.Member, description="Member to get karma of")) -> None:
        """Get a user's karma 

        Example usage
        ---------------
        !karma get @member
        !karma get 2342492304928

        Parameters
        ----------
        member : typing.Union[discord.Member, int]
            "Member whose karma to get"
        """

        if isinstance(member, int):
            try:
                member = await self.bot.fetch_user(member)
            except discord.NotFound:
                raise commands.BadArgument(
                    f"Couldn't find user with ID {member}")

        karma, rank, overall = user_service.karma_rank(member.id)

        embed = discord.Embed(
            title=f"Karma results", color=discord.Color(value=0x37b83b))
        embed.add_field(
            name="Karma", value=f'{member.mention} has {karma} karma')
        embed.add_field(
            name="Leaderboard rank", value=f'{member.mention} is rank {rank}/{overall}')
        embed.set_footer(
            text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar)

        await ctx.respond(embed=embed)

    @mod_and_up()
    @discord.slash_command(guild_ids=[cfg.guild_id], description="Whitelist a guild from invite filter", permissions=slash_perms.mod_and_up())
    async def karmaset(self, ctx: ChromeyContext, member: discord.Member, val: int):
        """Force set a user's karma (mod only)

        Example usage
        --------------
        !karma set @user 100

        Parameters
        ----------
        member : discord.Member
            "Member whose karma to set"
        val : int
            "Karma value"
        """

        m = user_service.get_user(member.id)
        m.karma = val
        m.save()

        embed = discord.Embed(title=f"Updated {member}'s karma!",
                              color=discord.Color(value=0x37b83b))
        embed.description = ""
        embed.description += f'**Current karma**: {m.karma}\n'
        embed.set_footer(
            text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar)
        await ctx.respond(member.mention, embed=embed)

    @nerds_and_up()
    @karma.command()
    async def give(self, ctx: ChromeyContext, member: discord.Member, val: int, *, reason: str = "No reason."):
        """ Give up to 3 karma to a user. Optionally, you can include a reason as an argument.

        Example usage
        --------------
        !karma give @member 3 reason blah blah blah


        Parameters
        ----------
        member : discord.Member
            "User to give karma to "
        val : int
            "Amount of karma"
        reason : str, optional
            "Reason, by default 'No reason.'"
        """

        if val < 1 or val > 3:
            raise commands.BadArgument(
                "You can give 1-3 karma in a command!\nExample usage `!karma give @member 3 reason blah blah blah`")

        if member.bot:
            raise commands.BadArgument(
                "You can't give a bot karma")

        if member.id == ctx.author.id and member.id != cfg.guild_owner_id:
            raise commands.BadArgument(
                "You can't give yourself karma")

        receiver = user_service.get_user(member.id)
        receive_action = {
            "amount": val,
            "from": ctx.author.id,
            "date": datetime.datetime.now(),
            "reason": reason
        }
        receiver.karma += val
        receiver.karma_received_history.append(receive_action)
        receiver.save()

        giver = user_service.get_user(ctx.author.id)
        give_action = {
            "amount": val,
            "to": member.id,
            "date": datetime.datetime.now(),
            "reason": reason
        }
        giver.karma_given_history.append(give_action)
        giver.save()

        embed = discord.Embed(title=f"Updated {member.name}#{member.discriminator}'s karma!",
                              color=discord.Color(value=0x37b83b))
        embed.description = ""

        embed.description += f'**Karma given**: {val}\n'
        embed.description += f'**Current karma**: {receiver.karma}\n'
        embed.description += f'**Reason**: {reason}'
        embed.set_footer(
            text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar)
        await ctx.respond(member.mention, embed=embed)

    @nerds_and_up()
    @karma.command()
    async def take(self, ctx: ChromeyContext, member: discord.Member, val: int, *, reason: str = "No reason."):
        """ Take up to 3 karma from a user. Optionally, you can include a reason as an argument.

        Example usage
        --------------
        !karma take @member 3 reason blah blah blah


        Parameters
        ----------
        member : discord.Member
            "User take karma from "
        val : int
            "Amount of karma"
        reason : str, optional
            "Reason, by default 'No reason."
        """

        if val < 1 or val > 3:
            raise commands.BadArgument(
                "You can give 1-3 karma in a command!\nExample usage `!karma give @member 3 reason blah blah blah`")

        if member.bot:
            raise commands.BadArgument(
                "You can't give a bot karma")

        if member.id == ctx.author.id and member.id != cfg.guild_owner_id:
            raise commands.BadArgument(
                "You can't give yourself karma")

        val = (-1) * val

        receiver = user_service.get_user(member.id)
        receive_action = {
            "amount": val,
            "from": ctx.author.id,
            "date": datetime.datetime.now(),
            "reason": reason
        }
        receiver.karma += val
        receiver.karma_received_history.append(receive_action)
        receiver.save()

        giver = user_service.get_user(ctx.author.id)
        give_action = {
            "amount": val,
            "to": member.id,
            "date": datetime.datetime.now(),
            "reason": reason
        }
        giver.karma_given_history.append(give_action)
        giver.save()

        embed = discord.Embed(title=f"Updated {member.name}#{member.discriminator}'s karma!",
                              color=discord.Color(value=0x37b83b))
        embed.description = ""

        embed.description += f'**Karma taken**: {(-1) * val}\n'
        embed.description += f'**Current karma**: {receiver.karma}\n'
        embed.description += f'**Reason**: {reason}'
        embed.set_footer(
            text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar)
        await ctx.respond(member.mention, embed=embed)

    @nerds_and_up()
    @karma.command()
    async def history(self, ctx: ChromeyContext, member: discord.Member):
        """History of a specific user's karma

        Example usage
        --------------
        !karma history @member

        Parameters
        ----------
        member : discord.Member
            "Member whose karma history to get"
        """

        data = sorted(user_service.get_user(member.id).karma_received_history, key=lambda d: d['date'], reverse=True)

        if (len(data) == 0):
            raise commands.BadArgument("This user had no history.")
        
        ctx.invokee = member
        menu = Menu(ctx, data, per_page=10, page_formatter=format_history_page, whisper=False)
        await menu.start()

    @nerds_and_up()
    @karma.command()
    async def modhistory(self, ctx: ChromeyContext, mod: discord.Option(discord.Member, description="Mod to see action history of")):
        """History of a karma given by a user

        Example usage
        --------------
        `!karma modhistory @member`

        Parameters
        ----------
        member : discord.Member
            Member whose karma history to get
        """

        data = sorted(user_service.get_user(mod.id).karma_given_history, key=lambda d: d['date'], reverse=True)

        if (len(data) == 0):
            raise commands.BadArgument("This user had no history.")

        ctx.invoker = mod
        menu = Menu(ctx, data, per_page=10, page_formatter=format_modhistory_page, whisper=False)
        await menu.start()

    @discord.slash_command(guild_ids=[cfg.guild_id], description="View karma leaderboard")
    async def leaderboard(self, ctx: ChromeyContext):
        """Get karma leaderboard for the server
        """

        data = user_service.leaderboard()

        if (len(data) == 0):
            raise commands.BadArgument("No history in this guild!")
        else:
            data_final = []
            for leaderboard_user in data:
                member = ctx.guild.get_member(leaderboard_user._id)
                if member is None:
                    try:
                        member = await self.bot.fetch_user(leaderboard_user._id)
                    except:
                        continue
                data_final.append((leaderboard_user, member))

        menu = Menu(ctx, data_final, per_page=10, page_formatter=format_leaderboard_page, whisper=False)
        await menu.start()

    @karma.error
    @get.error
    @karmaset.error
    @give.error
    @take.error
    @leaderboard.error
    @history.error
    @modhistory.error
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
    bot.add_cog(Karma(bot))
