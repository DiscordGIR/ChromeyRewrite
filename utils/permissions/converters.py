import discord
from discord.errors import NotFound
from discord.ext.commands.errors import BadArgument

from utils.permissions.checks import PermissionsFailure
from utils.context import ChromeyContext

async def mods_and_above_member_resolver(ctx: ChromeyContext, argument):
    if not isinstance(argument, discord.Member):
        raise BadArgument("User must be in the guild.")
    await check_invokee(ctx, argument)
    return argument


async def mods_and_above_external_resolver(ctx: ChromeyContext, argument):
    if isinstance(argument, discord.Member):
        user = argument
    elif isinstance(argument, discord.User):
        user = argument
    else:
        try:
            argument = int(argument)
            user = await ctx.bot.fetch_user(argument)
        except NotFound:
            raise PermissionsFailure(
                f"Couldn't find user with ID {argument}")
        except Exception as e:
            print(e)
            raise PermissionsFailure("Could not parse argument \"user\".")
            
    await check_invokee(ctx, user)
    return user 


async def user_resolver(ctx: ChromeyContext, argument):
    if isinstance(argument, discord.User):
        user = argument
    else:
        try:
            argument = int(argument)
            user = await ctx.bot.fetch_user(argument)
        except NotFound:
            raise PermissionsFailure(
                f"Couldn't find user with ID {argument}")
        except Exception:
            raise PermissionsFailure("Could not parse argument \"user\".")
        
    return user 


async def check_invokee(ctx, user):
    if isinstance(user, discord.Member):
        if user.id == ctx.author.id:
            raise PermissionsFailure("You can't call that on yourself.")
        
        if user.id == ctx.bot.user.id:
            raise PermissionsFailure("You can't call that on me :(")
        
        if user:
            if user.top_role >= ctx.author.top_role:
                raise PermissionsFailure(
                    message=f"{user.mention}'s top role is the same or higher than yours!")

