import datetime
import traceback

import discord
import pytz
from data.model.case import Case
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from discord.commands import Option, slash_command
from discord.errors import ApplicationCommandInvokeError
from discord.ext import commands
from discord.utils import format_dt
from utils.config import cfg
from utils.context import ChromeyContext
from utils.logger import logger
from utils.permissions.checks import (PermissionsFailure, admin_and_up,
                                      guild_owner_and_up, mod_and_up, whisper)
from utils.permissions.slash_perms import slash_perms


class ModUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Get information about a user (join/creation date, xp, etc.)", permissions=slash_perms.mod_and_up())
    async def rundown(self, ctx: ChromeyContext, user: discord.Member):
        await ctx.respond(embed = await self.prepare_rundown_embed(ctx, user))

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Transfer all data in the database between users", permissions=slash_perms.admin_and_up())
    async def transferprofile(self, ctx: ChromeyContext, oldmember: discord.Member, newmember: discord.Member):
        if isinstance(oldmember, int):
            try:
                oldmember = await self.bot.fetch_user(oldmember)
            except discord.NotFound:
                raise commands.BadArgument(
                    f"Couldn't find user with ID {oldmember}")

        if isinstance(newmember, int):
            try:
                newmember = await self.bot.fetch_user(newmember)
            except discord.NotFound:
                raise commands.BadArgument(
                    f"Couldn't find user with ID {newmember}")

        u, case_count = user_service.transfer_profile(oldmember.id, newmember.id)

        embed = discord.Embed(title="Transferred profile")
        embed.description = f"We transferred {oldmember.mention}'s profile to {newmember.mention}"
        embed.color = discord.Color.blurple()
        embed.add_field(name="Cases", value=f"We tranferred {case_count} cases")

        await ctx.respond(embed=embed)

        try:
            await newmember.send(f"{ctx.author} has transferred your profile from {oldmember}", embed=embed)
        except Exception:
            pass

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Sayyyy", permissions=slash_perms.mod_and_up())
    async def say(self, ctx: ChromeyContext, message: str, channel: Option(discord.TextChannel, required=False, description="Where to post the message") = None):
        if channel is None:
            channel = ctx.channel

        await channel.send(message)
        ctx.whisper = True
        await ctx.send_success("Done!")
        logging_channel = ctx.guild.get_channel(guild_service.get_guild().channel_private)
        embed = discord.Embed(color=discord.Color.gold(), title="Someone abused me :(", description=f"In {ctx.channel.mention} {ctx.author.mention} said:\n\n{message}" )
        await logging_channel.send(embed=embed)

    async def prepare_rundown_embed(self, ctx: ChromeyContext, user):
        user_info = user_service.get_user(user.id)
        rd = user_service.rundown(user.id)
        rd_text = ""
        for r in rd:
            rd_text += f"**{r._type}** - {r.punishment} - {r.reason} - {format_dt(r.date, style='R')}\n"

        reversed_roles = user.roles
        reversed_roles.reverse()

        roles = ""
        for role in reversed_roles[0:4]:
            if role != user.guild.default_role:
                roles += role.mention + " "
        roles = roles.strip() + "..."

        embed = discord.Embed(title="Rundown")
        embed.color = user.color
        embed.set_thumbnail(url=user.display_avatar)

        embed.add_field(name="Member", value=f"{user} ({user.mention}, {user.id})")
        embed.add_field(name="Join date", 
                        value=f"{format_dt(user.joined_at, style='F')} ({format_dt(user.joined_at, style='R')})")
        embed.add_field(name="Account creation date",
                        value=f"{format_dt(user.created_at, style='F')} ({format_dt(user.created_at, style='R')})")

        embed.add_field(
            name="Roles", value=roles if roles else "None", inline=False)

        if len(rd) > 0:
            embed.add_field(name=f"{len(rd)} most recent cases",
                            value=rd_text, inline=False)
        else:
            embed.add_field(name=f"Recent cases",
                            value="This user has no cases.", inline=False)

        return embed

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Give a user the birthday role!", permissions=slash_perms.mod_and_up())
    async def birthday(self, ctx: ChromeyContext, user: discord.Member):
        if user.id == self.bot.user.id:
            await ctx.message.add_reaction("🤔")
            raise commands.BadArgument("You can't call that on me :(")

        eastern = pytz.timezone('US/Eastern')
        birthday_role = ctx.guild.get_role(guild_service.get_guild().role_birthday)
        if birthday_role is None:
            return
        if birthday_role in user.roles:
            return
        now = datetime.datetime.now(eastern)

        try:
            time = now + datetime.timedelta(days=1)
            ctx.tasks.schedule_remove_bday(user.id, time)
        except:
            raise commands.BadArgument("An error occured scheduling the job in the database.")

        await user.add_roles(birthday_role)
        await ctx.send_success(f"{user.mention}'s birthday was set.")
        await user.send(f"According to my calculations, today is your birthday! We've given you the {birthday_role} role for 24 hours.")

    @say.error
    @rundown.error
    @transferprofile.error
    @birthday.error
    async def info_error(self,  ctx: ChromeyContext, error):
        if isinstance(error, ApplicationCommandInvokeError):
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
    bot.add_cog(ModUtils(bot))
