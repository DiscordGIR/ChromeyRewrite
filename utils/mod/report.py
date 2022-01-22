from typing import Union
import discord
from data.services import user_service
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from discord.utils import format_dt
from utils.config import cfg
from utils.context import ChromeyOldContext
from utils.views.report import (RaidPhraseReportActions, ReportActions,
                                SpamReportActions)


async def report(bot: discord.Client, message: discord.Message, word: str, invite=None):
    """Deals with a report

    Parameters
    ----------
    bot : discord.Client
        "Bot object"
    message : discord.Message
        "Filtered message"
    word : str
        "Filtered word"
    invite : bool
        "Was the filtered word an invite?"

    """
    db_guild = guild_service.get_guild()
    channel = message.guild.get_channel(db_guild.channel_reports)

    ping_string = prepare_ping_string(db_guild, message)
    view = ReportActions(message.author)

    if invite:
        embed = prepare_embed(message, word, title="Invite filter")
        report_msg = await channel.send(f"{ping_string}\nMessage contained invite: {invite}", embed=embed, view=view)
    else:
        embed = prepare_embed(message, word)
        report_msg = await channel.send(ping_string, embed=embed, view=view)

    ctx = await bot.get_context(report_msg)
    await view.start(ctx)

async def manual_report(bot: discord.Client, mod: discord.Member, target: Union[discord.Message, discord.Member] = None):
    """Deals with a report

    Parameters
    ----------
    bot : discord.Client
        "Bot object"
    message : discord.Message
        "Filtered message"
    mod : discord.Member
        "The moderator that started this report

    """
    db_guild = guild_service.get_guild()
    channel = target.guild.get_channel(db_guild.channel_reports)

    ping_string = f"{mod.mention} reported a member"
    if isinstance(target, discord.Message):
        view = ReportActions(target.author)
    else:
        view = ReportActions(target)

    embed = prepare_embed(target, title="A moderator reported a member")
    report_msg = await channel.send(ping_string, embed=embed, view=view)

    ctx = await bot.get_context(report_msg)
    await view.start(ctx)


async def report_raid_phrase(bot: discord.Client, message: discord.Message, domain: str):
    """Deals with a report

    Parameters
    ----------
    bot : discord.Client
        "Bot object"
    message : discord.Message
        "Filtered message"
    word : str
        "Filtered word"
    invite : bool
        "Was the filtered word an invite?"

    """
    db_guild = guild_service.get_guild()
    channel = message.guild.get_channel(db_guild.channel_reports)

    ping_string = prepare_ping_string(db_guild, message)
    view = RaidPhraseReportActions(message.author, domain)

    embed = prepare_embed(
        message, domain, title=f"Possible new raid phrase detected\n{domain}")
    report_msg = await channel.send(ping_string, embed=embed, view=view)

    ctx = await bot.get_context(report_msg, cls=ChromeyOldContext)
    await view.start(ctx)


async def report_spam(bot, msg, user, title):
    db_guild = guild_service.get_guild()
    channel = msg.guild.get_channel(db_guild.channel_reports)
    ping_string = prepare_ping_string(db_guild, msg)

    view = SpamReportActions(user)
    embed = prepare_embed(msg, title=title)

    report_msg = await channel.send(ping_string, embed=embed, view=view)

    ctx = await bot.get_context(report_msg, cls=ChromeyOldContext)
    await view.start(ctx)


async def report_raid(user, msg=None):
    embed = discord.Embed()
    embed.title = "Possible raid occurring"
    embed.description = "The raid filter has been triggered 5 or more times in the past 10 seconds. I am automatically locking all the channels. Use `/unfreeze` when you're done."
    embed.color = discord.Color.red()
    embed.set_thumbnail(url=user.display_avatar)
    embed.add_field(name="Member", value=f"{user} ({user.mention})")
    if msg is not None:
        embed.add_field(name="Message", value=msg.content, inline=False)

    db_guild = guild_service.get_guild()
    reports_channel = user.guild.get_channel(db_guild.channel_reports)
    await reports_channel.send(f"<@&{db_guild.role_moderator}>", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))


def prepare_ping_string(db_guild, message):
    """Prepares modping string

    Parameters
    ----------
    db_guild
        "Guild DB"
    message : discord.Message
        "Message object"

    """
    ping_string = ""
    if cfg.dev:
        return ping_string
    
    role = message.guild.get_role(db_guild.role_moderator)
    for member in role.members:
        offline_ping = (user_service.get_user(member.id)).offline_report_ping
        if member.status == discord.Status.online or offline_ping:
            ping_string += f"{member.mention} "

    return ping_string


def prepare_embed(target: Union[discord.Message, discord.Member], word: str = None, title="Word filter"):
    """Prepares embed

    Parameters
    ----------
    message : discord.Message
        "Message object"
    word : str
        "Filtered word"
    title : str
        "Embed title"

    """
    if isinstance(target, discord.Message):
        member = target.author
    else:
        member = target

    user_info = user_service.get_user(member.id)
    rd = user_service.rundown(member.id)
    rd_text = ""
    for r in rd:
        rd_text += f"**{r._type}** - {r.punishment} - {r.reason} - {format_dt(r.date, style='R')}\n"

    embed = discord.Embed(title=title)
    embed.color = discord.Color.red()

    embed.set_thumbnail(url=member.display_avatar)
    embed.add_field(name="Member", value=f"{member} ({member.mention})")
    if isinstance(target, discord.Message):
        embed.add_field(name="Channel", value=target.channel.mention)

        if len(target.content) > 400:
            target.content = target.content[0:400] + "..."

    if word is not None:
        embed.add_field(name="Message", value=discord.utils.escape_markdown(
            target.content) + f"\n\n[Link to message]({target.jump_url}) | Filtered word: **{word}**", inline=False)
    else:
        if isinstance(target, discord.Message):
            embed.add_field(name="Message", value=discord.utils.escape_markdown(
                target.content) + f"\n\n[Link to message]({target.jump_url})", inline=False)
    embed.add_field(
        name="Join date", value=f"{format_dt(member.joined_at, style='F')} ({format_dt(member.joined_at, style='R')})", inline=True)
    embed.add_field(name="Created",
                    value=f"{format_dt(member.created_at, style='F')} ({format_dt(member.created_at, style='R')})", inline=True)

    reversed_roles = member.roles
    reversed_roles.reverse()

    roles = ""
    for role in reversed_roles[0:4]:
        if role != member.guild.default_role:
            roles += role.mention + " "
    roles = roles.strip() + "..."

    embed.add_field(
        name="Roles", value=roles if roles else "None", inline=False)

    if len(rd) > 0:
        embed.add_field(name=f"{len(rd)} most recent cases",
                        value=rd_text, inline=True)
    else:
        embed.add_field(name=f"Recent cases",
                        value="This user has no cases.", inline=True)
    return embed
