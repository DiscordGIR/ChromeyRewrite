from discord.ext import commands

from data.services.guild_service import guild_service
from utils.context import ChromeyContext
from utils.permissions.permissions import permissions


class PermissionsFailure(commands.BadArgument):
    def __init__(self, message):
        super().__init__(message)


def always_whisper():
    """Always respond ephemerally"""
    async def predicate(ctx: ChromeyContext):
        ctx.whisper = True
        return True
    return commands.check(predicate)


def whisper():
    """If the user is not a moderator and the invoked channel is not #bot-commands, send the response to the command ephemerally"""
    async def predicate(ctx: ChromeyContext):
        if not permissions.has(ctx.guild, ctx.author, 1) and ctx.channel.id != guild_service.get_guild().channel_offtopic:
            ctx.whisper = True
        else:
            ctx.whisper = False
        return True
    return commands.check(predicate)

####################
# Staff Roles
####################


def mod_and_up():
    """If the user is not at least a Moderator, deny command access"""
    async def predicate(ctx: ChromeyContext):
        if not permissions.has(ctx.guild, ctx.author, 2):
            raise PermissionsFailure(
                "You do not have permission to use this command.")

        return True
    return commands.check(predicate)


def admin_and_up():
    """If the user is not at least an Administrator, deny command access"""
    async def predicate(ctx: ChromeyContext):
        if not permissions.has(ctx.guild, ctx.author, 3):
            raise PermissionsFailure(
                "You do not have permission to use this command.")

        return True
    return commands.check(predicate)

####################
# Other
####################


def guild_owner_and_up():
    """If the user is not the guild owner, deny command access"""
    async def predicate(ctx: ChromeyContext):
        if not permissions.has(ctx.guild, ctx.author, 4):
            raise PermissionsFailure(
                "You do not have permission to use this command.")

        return True
    return commands.check(predicate)


def bot_owner_and_up():
    """If the user is not the bot owner, deny command access"""
    async def predicate(ctx: ChromeyContext):
        if not permissions.has(ctx.guild, ctx.author, 5):
            raise PermissionsFailure(
                "You do not have permission to use this command.")

        return True
    return commands.check(predicate)


def ensure_invokee_role_lower_than_bot():
    """If the invokee's role is higher than the bot's, deny command access"""
    async def predicate(ctx: ChromeyContext):
        if ctx.me.top_role < ctx.author.top_role:
            raise PermissionsFailure(
                f"Your top role is higher than mine. I can't change your nickname :(")

        return True
    return commands.check(predicate)
