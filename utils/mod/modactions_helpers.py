import discord

from typing import Union
from data.model.case import Case
from data.model.guild import Guild
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from utils.context import ChromeyContext
from utils.mod.mod_logs import prepare_ban_log, prepare_kick_log

from utils.config import cfg


async def add_kick_case(ctx: ChromeyContext, user, reason, db_guild):
    """Adds kick case to user

    Parameters
    ----------
    ctx : ChromeyContext
        "Bot context"
    user : discord.Member
        "Member who was kicked"
    reason : str
        "Reason member was kicked"
    db_guild
        "Guild DB"

    """
    # prepare case for DB
    case = Case(
        _id=db_guild.case_id,
        _type="KICK",
        mod_id=ctx.author.id,
        mod_tag=str(ctx.author),
        reason=reason,
    )

    # increment max case ID for next case
    guild_service.inc_caseid()
    # add new case to DB
    user_service.add_case(user.id, case)

    return prepare_kick_log(ctx.author, user, case)


async def notify_user(user, text, log):
    """Notifies a specified user about something

    Parameters
    ----------
    user : discord.Member
        "User to notify"
    text : str
        "Text to send"
    log : discord.Embed
        "Embed to send"
    """
    try:
        await user.send(text, embed=log)
    except Exception:
        return False
    return True


async def notify_user_warn(ctx: ChromeyContext, user: discord.User, log):
    """Notifies a specified user about a warn

    Parameters
    ----------
    ctx : ChromeyContext
        "Bot context"
    user : discord.Member
        "User to notify"
    log : discord.Embed
        "Embed to send"
    """

    if isinstance(user, discord.Member):
        await notify_user(user, f"You were warned in {ctx.guild.name}.", log)


async def submit_mod_log(ctx: ChromeyContext, db_guild: Guild, user: Union[discord.Member, discord.User], log):
    """Submits a public log

    Parameters
    ----------
    ctx : ChromeyContext
        "Bot context"
    user : discord.Member
        "User to notify"
    db_user
        "User DB"
    db_guild
        "Guild DB"
    log : discord.Embed
        "Embed to send"
    """
    modlogs_chan = ctx.guild.get_channel(
        db_guild.channel_modlogs)
    if modlogs_chan:
        log.remove_author()
        log.set_thumbnail(url=user.display_avatar)
        await modlogs_chan.send(embed=log)


async def add_ban_case(ctx: ChromeyContext, user: discord.User, reason, db_guild: Guild = None):
    """Adds ban case to user

    Parameters
    ----------
    ctx : ChromeyContext
        "Bot context"
    user : discord.Member
        "Member who was banned"
    reason : str
        "Reason member was banned"
    db_guild
        "Guild DB"

    """
    # prepare the case to store in DB
    case = Case(
        _id=db_guild.case_id,
        _type="BAN",
        mod_id=ctx.author.id,
        mod_tag=str(ctx.author),
        punishment="PERMANENT",
        reason=reason,
    )

    # increment DB's max case ID for next case
    guild_service.inc_caseid()
    # add case to db
    user_service.add_case(user.id, case)
    # prepare log embed to send to #public-mod-logs, user and context
    return prepare_ban_log(ctx.author, user, case)
