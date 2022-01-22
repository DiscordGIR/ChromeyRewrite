from apscheduler.jobstores.base import ConflictingIdError
import discord
from discord.commands import Option, slash_command, message_command, user_command
from discord.errors import HTTPException
from discord.ext import commands
from discord.utils import escape_markdown, escape_mentions

import traceback
import humanize
import pytimeparse
from datetime import datetime, timedelta, timezone
from data.model.case import Case
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from utils.autocompleters import liftwarn_autocomplete
from utils.config import cfg
from utils.logger import logger
from utils.context import ChromeyContext
from utils.mod.mod_logs import (prepare_editreason_log, prepare_liftwarn_log, prepare_mute_log,
                                prepare_unban_log, prepare_unmute_log)
from utils.mod.modactions_helpers import (
    add_ban_case, add_kick_case, notify_user, submit_mod_log)
from utils.mod.global_modactions import ban, warn
from utils.permissions.checks import PermissionsFailure, always_whisper, mod_and_up
from utils.permissions.converters import (
    mods_and_above_external_resolver, mods_and_above_member_resolver, user_resolver)
from utils.permissions.slash_perms import slash_perms
from utils.views.modactions import WarnView


class ModActions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Warn a user", permissions=slash_perms.mod_and_up())
    async def warn(self, ctx: ChromeyContext, user: Option(discord.Member, description="User to warn"), reason: Option(str, description="Reason for warn")):
        """Warns a user (mod only)

        Example usage
        --------------
        /warn user:<user> reason:<reason>

        Parameters
        ----------
        user : discord.Member
            "The member to warn"
        reason : str, optional
            "Reason for warning, by default 'No reason.'"

        """
        user = await mods_and_above_external_resolver(ctx, user)

        await warn(ctx, user, reason)

    @mod_and_up()
    @always_whisper()
    @user_command(guild_ids=[cfg.guild_id], name="Warn user")
    async def warn_rc(self, ctx: ChromeyContext, member: discord.Member) -> None:
        member = await mods_and_above_external_resolver(ctx, member)
        view = WarnView(ctx, member)
        await ctx.respond(embed=discord.Embed(description=f"Choose a warn reason for {member.mention}.", color=discord.Color.blurple()), view=view, ephemeral=True)

    @mod_and_up()
    @always_whisper()
    @message_command(guild_ids=[cfg.guild_id], name="Warn user")
    async def warn_msg(self, ctx: ChromeyContext, message: discord.Message) -> None:
        member = await mods_and_above_external_resolver(ctx, message.author)
        view = WarnView(ctx, message.author)
        await ctx.respond(embed=discord.Embed(description=f"Choose a warn reason for {member.mention}.", color=discord.Color.blurple()), view=view, ephemeral=True)

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Kick a user", permissions=slash_perms.mod_and_up())
    async def kick(self, ctx: ChromeyContext, member: Option(discord.Member, description="User to kick"), *, reason: Option(str, description="Reason for kick")) -> None:
        """Kicks a user (mod only)

        Example usage
        --------------
        /kick member:<member> reason:<reason>

        Parameters
        ----------
        user : discord.Member
            "User to kick"
        reason : str, optional
            "Reason for kick, by default 'No reason.'"

        """

        member = await mods_and_above_member_resolver(ctx, member)

        reason = escape_markdown(reason)
        reason = escape_mentions(reason)

        db_guild = guild_service.get_guild()

        log = await add_kick_case(ctx, member, reason, db_guild)
        await notify_user(member, f"You were kicked from {ctx.guild.name}", log)

        await member.kick(reason=reason)

        await ctx.respond(embed=log)
        await submit_mod_log(ctx, db_guild, member, log)

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Mute a user", permissions=slash_perms.mod_and_up())
    async def mute(self, ctx: ChromeyContext, member: Option(discord.Member, description="User to mute"), duration: Option(str, description="Duration for mute") = "", reason: Option(str, description="Reason for mute") = "No reason.") -> None:
        """Mutes a user (mod only)

        Example usage
        --------------
        /mute member:<member> dur:<duration> reason:<reason>

        Parameters
        ----------
        user : discord.Member
            "Member to mute"
        dur : str
            "Duration of mute (i.e 1h, 10m, 1d)"
        reason : str, optional
            "Reason for mute, by default 'No reason.'"

        """
        await ctx.defer()
        member: discord.Member = await mods_and_above_member_resolver(ctx, member)

        reason = escape_markdown(reason)
        reason = escape_mentions(reason)

        now = datetime.now(tz=timezone.utc)
        delta = pytimeparse.parse(duration)

        if delta is None:
            raise commands.BadArgument("Please input a valid duration!")

        if member.timed_out:
            raise commands.BadArgument("This user is already muted.")

        time = now + timedelta(seconds=delta)
        if time > now + timedelta(days=14):
            raise commands.BadArgument("Mutes can't be longer than 14 days!")

        db_guild = guild_service.get_guild()
        case = Case(
            _id=db_guild.case_id,
            _type="MUTE",
            date=now,
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            reason=reason,
        )

        case.until = time
        case.punishment = humanize.naturaldelta(
            time - now, minimum_unit="seconds")

        try:
            await member.timeout(until=time, reason=reason)
            ctx.tasks.schedule_untimeout(member.id, time)
        except ConflictingIdError:
            raise commands.BadArgument(
                "The database thinks this user is already muted.")

        guild_service.inc_caseid()
        user_service.add_case(member.id, case)

        log = prepare_mute_log(ctx.author, member, case)
        await ctx.respond(embed=log)

        log.remove_author()
        log.set_thumbnail(url=member.display_avatar)

        await notify_user(member, f"You have been muted in {ctx.guild.name}", log)
        await submit_mod_log(ctx, db_guild, member, log)

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Unmute a user", permissions=slash_perms.mod_and_up())
    async def unmute(self, ctx: ChromeyContext, member: Option(discord.Member, description="User to mute"), reason: Option(str, description="Reason for mute")) -> None:
        """Unmutes a user (mod only)

        Example usage
        --------------
        /unmute member:<member> reason:<reason>

        Parameters
        ----------
        user : discord.Member
            "Member to unmute"
        reason : str, optional
            "Reason for unmute, by default 'No reason.'"

        """

        member = await mods_and_above_member_resolver(ctx, member)

        db_guild = guild_service.get_guild()

        if not member.timed_out:
            raise commands.BadArgument("This user is not muted.")

        await member.remove_timeout()

        try:
            ctx.tasks.cancel_unmute(member.id)
        except Exception:
            pass

        case = Case(
            _id=db_guild.case_id,
            _type="UNMUTE",
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            reason=reason,
        )
        guild_service.inc_caseid()
        user_service.add_case(member.id, case)

        log = prepare_unmute_log(ctx.author, member, case)

        await ctx.respond(embed=log)

        await notify_user(member, f"You have been unmuted in {ctx.guild.name}", log)
        await submit_mod_log(ctx, db_guild, member, log)

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Soft ban a user", permissions=slash_perms.mod_and_up())
    async def scam(self, ctx: ChromeyContext, user: Option(discord.Member, description="User to ban")):
        user = await mods_and_above_external_resolver(ctx, user)

        await ban(ctx, user, reason="Account hacked", extra_text="We detected that your account was hacked as it posted a scam text in our server. We have banned and unbanned you to delete all of your scam messages. Please secure your account, then you can rejon using https://discord.gg/chromeos.")
        await ctx.guild.unban(discord.Object(id=user.id))
        ctx.bot.ban_cache.unban(user.id)
        await ctx.send_success("User has been banned and unbanned.")

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Ban a user", permissions=slash_perms.mod_and_up())
    async def ban(self, ctx: ChromeyContext, user: Option(discord.Member, description="User to ban"), reason: Option(str, description="Reason for ban")):
        """Bans a user (mod only)

        Example usage
        --------------
        /ban user:<user> reason:<reason>

        Parameters
        ----------
        user : discord.Member
            "The user to be banned, doesn't have to be part of the guild"
        reason : str, optional
            "Reason for ban, by default 'No reason.'"

        """

        user = await mods_and_above_external_resolver(ctx, user)

        reason = escape_markdown(reason)
        reason = escape_mentions(reason)
        db_guild = guild_service.get_guild()

        member_is_external = isinstance(user, discord.User)

        # if the ID given is of a user who isn't in the guild, try to fetch the profile
        if member_is_external:
            async with ctx.typing():
                if self.bot.ban_cache.is_banned(user.id):
                    raise commands.BadArgument("That user is already banned!")

        self.bot.ban_cache.ban(user.id)
        log = await add_ban_case(ctx, user, reason, db_guild)

        if not member_is_external:
            # if cfg.ban_appeal_url is None:
            await notify_user(user, f"You have been banned from {ctx.guild.name}", log)
            # else:
                # await notify_user(user, f"You have been banned from {ctx.guild.name}\n\nIf you would like to appeal your ban, please fill out this form: <{cfg.ban_appeal_url}>", log)

            await user.ban(reason=reason)
        else:
            # hackban for user not currently in guild
            await ctx.guild.ban(discord.Object(id=user.id))

        await ctx.respond(embed=log)
        await submit_mod_log(ctx, db_guild, user, log)

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Unban a user", permissions=slash_perms.mod_and_up())
    async def unban(self, ctx: ChromeyContext, user: Option(discord.Member, description="User to unban"), reason: Option(str, description="Reason for unban")) -> None:
        """Unbans a user (must use ID) (mod only)

        Example usage
        --------------
        /unban user:<userid> reason:<reason>

        Parameters
        ----------
        user : discord.Member
            "ID of the user to unban"
        reason : str, optional
            "Reason for unban, by default 'No reason.'"

        """

        user = await user_resolver(ctx, user)
        if ctx.guild.get_member(user.id) is not None:
            raise commands.BadArgument(
                "You can't unban someone already in the server!")

        reason = escape_markdown(reason)
        reason = escape_mentions(reason)

        if not self.bot.ban_cache.is_banned(user.id):
            raise commands.BadArgument("That user isn't banned!")

        try:
            await ctx.guild.unban(discord.Object(id=user.id), reason=reason)
        except discord.NotFound:
            raise commands.BadArgument(f"{user} is not banned.")

        self.bot.ban_cache.unban(user.id)

        db_guild = guild_service.get_guild()
        case = Case(
            _id=db_guild.case_id,
            _type="UNBAN",
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            reason=reason,
        )
        guild_service.inc_caseid()
        user_service.add_case(user.id, case)

        log = prepare_unban_log(ctx.author, user, case)
        await ctx.respond(embed=log)

        await submit_mod_log(ctx, db_guild, user, log)

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Purge channel messages", permissions=slash_perms.mod_and_up())
    async def purge(self, ctx: ChromeyContext, limit: Option(int, description="Number of messages to remove", min_value=1, max_value=100)) -> None:
        """Purges messages from current channel (mod only)

        Example usage
        --------------
        /purge limit:<number of messages>

        Parameters
        ----------
        limit : int, optional
            "Number of messages to purge, must be > 0, by default 0 for error handling"

        """

        if limit <= 0:
            raise commands.BadArgument(
                "Number of messages to purge must be greater than 0")
        elif limit >= 100:
            limit = 100

        msgs = await ctx.channel.history(limit=limit).flatten()

        await ctx.channel.purge(limit=limit)
        await ctx.respond(f'Purged {len(msgs)} messages.', delete_after=10)

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Lift a warn", permissions=slash_perms.mod_and_up())
    async def liftwarn(self, ctx: ChromeyContext, user: Option(discord.Member, description="User to lift warn of"), case_id: Option(str, autocomplete=liftwarn_autocomplete), reason: Option(str)) -> None:
        """Marks a warn as lifted. (mod only)

        Example usage
        --------------
        /liftwarn user:<user> case_id:<case ID> reason:<reason>

        Parameters
        ----------
        user : discord.Member
            "User to remove warn from"
        case_id : int
            "The ID of the case for which we want to remove points"
        reason : str, optional
            "Reason for lifting warn, by default 'No reason.'"

        """

        user = await mods_and_above_external_resolver(ctx, user)

        # retrieve user's case with given ID
        cases = user_service.get_cases(user.id)
        case = cases.cases.filter(_id=case_id).first()

        reason = escape_markdown(reason)
        reason = escape_mentions(reason)

        # sanity checks
        if case is None:
            raise commands.BadArgument(
                message=f"{user} has no case with ID {case_id}")
        elif case._type != "WARN":
            raise commands.BadArgument(
                message=f"{user}'s case with ID {case_id} is not a warn case.")
        elif case.lifted:
            raise commands.BadArgument(
                message=f"Case with ID {case_id} already lifted.")

        # passed sanity checks, so update the case in DB
        case.lifted = True
        case.lifted_reason = reason
        case.lifted_by_tag = str(ctx.author)
        case.lifted_by_id = ctx.author.id
        case.lifted_date = datetime.now()
        cases.save()

        # prepare log embed, send to #public-mod-logs, user, channel where invoked
        log = prepare_liftwarn_log(ctx.author, user, case)
        await notify_user(user, f"Your warn has been lifted in {ctx.guild}.", log)

        await ctx.respond(embed=log)
        await submit_mod_log(ctx, guild_service.get_guild(), user, log)

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Edit case reason", permissions=slash_perms.mod_and_up())
    async def editreason(self, ctx: ChromeyContext, user: Option(discord.Member), case_id: Option(str, autocomplete=liftwarn_autocomplete), new_reason: Option(str)) -> None:
        """Edits a case's reason and the embed in #public-mod-logs. (mod only)

        Example usage
        --------------
        /editreason user:<user> case_id:<case ID> reason:<reason>

        Parameters
        ----------
        user : discord.Member
            "User to edit case of"
        case_id : int
            "The ID of the case for which we want to edit reason"
        new_reason : str
            "New reason"

        """

        user = await mods_and_above_external_resolver(ctx, user)

        # retrieve user's case with given ID
        cases = user_service.get_cases(user.id)
        case = cases.cases.filter(_id=case_id).first()

        new_reason = escape_markdown(new_reason)
        new_reason = escape_mentions(new_reason)

        # sanity checks
        if case is None:
            raise commands.BadArgument(
                message=f"{user} has no case with ID {case_id}")

        old_reason = case.reason
        case.reason = new_reason
        case.date = datetime.now()
        cases.save()

        log = prepare_editreason_log(ctx.author, user, case, old_reason)

        await notify_user(user, f"Your case was updated in {ctx.guild.name}.", log)

        modlogs_chan = ctx.guild.get_channel(
            guild_service.get_guild().channel_modlogs)

        found = False
        async with ctx.typing():
            async for message in modlogs_chan.history(limit=200):
                if message.author.id != ctx.me.id:
                    continue
                if len(message.embeds) == 0:
                    continue
                embed = message.embeds[0]

                if embed.footer.text == discord.Embed.Empty:
                    continue
                if len(embed.footer.text.split(" ")) < 2:
                    continue

                if f"#{case_id}" == embed.footer.text.split(" ")[1]:
                    for i, field in enumerate(embed.fields):
                        if field.name == "Reason":
                            embed.set_field_at(
                                i, name="Reason", value=new_reason)
                            await message.edit(embed=embed)
                            found = True
        if found:
            await ctx.respond(f"We updated the case and edited the embed in {modlogs_chan.mention}.", embed=log, delete_after=10)
        else:
            await ctx.respond(f"We updated the case but weren't able to find a corresponding message in {modlogs_chan.mention}!", embed=log, delete_after=10)
            log.remove_author()
            log.set_thumbnail(url=user.display_avatar)
            await modlogs_chan.send(embed=log)

    @unmute.error
    @mute.error
    @liftwarn.error
    @unban.error
    @scam.error
    @ban.error
    @warn.error
    @warn_rc.error
    @warn_msg.error
    @purge.error
    @kick.error
    @editreason.error
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
            or isinstance(error, HTTPException)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(error)
        else:
            await ctx.send_error("A fatal error occured. Tell <@109705860275539968> about this.")
            logger.error(traceback.format_exc())


def setup(bot):
    bot.add_cog(ModActions(bot))
