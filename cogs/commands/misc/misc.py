import discord
from discord.commands import Option, slash_command, message_command, user_command
from discord.ext import commands

import base64
import datetime
import io
import json
import traceback
from discord.object import Object
import pytimeparse
from PIL import Image
from data.services.guild_service import guild_service
from utils.logger import logger
from utils.config import cfg
from utils.context import ChromeyContext
from utils.permissions.checks import PermissionsFailure, always_whisper, whisper
from utils.permissions.permissions import permissions


class PFPView(discord.ui.View):
    def __init__(self, ctx: ChromeyContext):
        super().__init__(timeout=30)
        self.ctx = ctx

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.ctx.respond_or_edit(view=self)


class PFPButton(discord.ui.Button):
    def __init__(self, ctx: ChromeyContext, member: discord.Member):
        super().__init__(label="Show other avatar", style=discord.ButtonStyle.primary)
        self.ctx = ctx
        self.member = member
        self.other = False

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return
        if not self.other:
            avatar = self.member.guild_avatar
            self.other = not self.other
        else:
            avatar = self.member.avatar or self.member.default_avatar
            self.other = not self.other

        embed = interaction.message.embeds[0]
        embed.set_image(url=avatar.replace(size=4096))

        animated = ["gif", "png", "jpeg", "webp"]
        not_animated = ["png", "jpeg", "webp"]

        def fmt(format_):
            return f"[{format_}]({avatar.replace(format=format_, size=4096)})"

        if avatar.is_animated():
            embed.description = f"View As\n {'  '.join([fmt(format_) for format_ in animated])}"
        else:
            embed.description = f"View As\n {'  '.join([fmt(format_) for format_ in not_animated])}"

        await interaction.response.edit_message(embed=embed)


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_cooldown = commands.CooldownMapping.from_cooldown(
            3, 15.0, commands.BucketType.channel)

        self.helpers_cooldown = commands.CooldownMapping.from_cooldown(
            1, 86400, commands.BucketType.member)

        try:
            with open('emojis.json') as f:
                self.emojis = json.loads(f.read())
        except:
            raise Exception(
                "Could not find emojis.json. Make sure to run scrape_emojis.py")

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Send yourself a reminder after a given time gap")
    async def remindme(self, ctx: ChromeyContext, reminder: Option(str, description="What do you want to be reminded?"), duration: Option(str, description="When do we remind you? (i.e 1m, 1h, 1d)")):
        """Sends you a reminder after a given time gap
        
        Example usage
        -------------
        /remindme 1h bake the cake
        
        Parameters
        ----------
        dur : str
            "After when to send the reminder"
        reminder : str
            "What to remind you of"
            
        """
        now = datetime.datetime.now()
        delta = pytimeparse.parse(duration)
        if delta is None:
            raise commands.BadArgument(
                "Please give me a valid time to remind you! (i.e 1h, 30m)")

        time = now + datetime.timedelta(seconds=delta)
        if time < now:
            raise commands.BadArgument("Time has to be in the future >:(")
        reminder = discord.utils.escape_markdown(reminder)

        ctx.tasks.schedule_reminder(ctx.author.id, reminder, time)
        # natural_time = humanize.naturaldelta(
        #     delta, minimum_unit='seconds')
        embed = discord.Embed(title="Reminder set", color=discord.Color.random(
        ), description=f"We'll remind you {discord.utils.format_dt(time, style='R')}")
        await ctx.respond(embed=embed, ephemeral=ctx.whisper, delete_after=5)

    @slash_command(guild_ids=[cfg.guild_id], description="Post large version of a given emoji")
    async def jumbo(self, ctx: ChromeyContext, emoji: str):
        """Posts large version of a given emoji
        
        Example usage
        -------------
        /jumbo <emote>
        
        Parameters
        ----------
        emoji : str
            "Emoji to enlarge"
        
        """
        # non-mod users will be ratelimited
        bot_chan = guild_service.get_guild().channel_offtopic
        if not permissions.has(ctx.guild, ctx.author, 2) and ctx.channel.id != bot_chan:
            bucket = self.spam_cooldown.get_bucket(ctx.interaction)
            if bucket.update_rate_limit():
                raise commands.BadArgument("This command is on cooldown.")

        # is this a regular Unicode emoji?
        try:
            em = await commands.PartialEmojiConverter().convert(ctx, emoji)
        except commands.PartialEmojiConversionFailure:
            em = emoji
        if isinstance(em, str):
            async with ctx.typing():
                emoji_url_file = self.emojis.get(em)
                if emoji_url_file is None:
                    raise commands.BadArgument(
                        "Couldn't find a suitable emoji.")

            im = Image.open(io.BytesIO(base64.b64decode(emoji_url_file)))
            image_conatiner = io.BytesIO()
            im.save(image_conatiner, 'png')
            image_conatiner.seek(0)
            _file = discord.File(image_conatiner, filename='image.png')
            await ctx.respond(file=_file)
        else:
            await ctx.respond(em.url)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Get avatar of another user or yourself.")
    async def avatar(self, ctx: ChromeyContext, member: Option(discord.Member, description="User to get avatar of", required=False)) -> None:
        """Posts large version of a given emoji
        
        Example usage
        -------------
        /avatar member:<member>
        
        Parameters
        ----------
        member : discord.Member, optional
            "Member to get avatar of"
        
        """
        if member is None:
            member = ctx.author

        await self.handle_avatar(ctx, member)
    
    @whisper()
    @user_command(guild_ids=[cfg.guild_id], name="View avatar")
    async def avatar_rc(self, ctx: ChromeyContext, member: discord.Member):
        await self.handle_avatar(ctx, member)
    
    @whisper()
    @message_command(guild_ids=[cfg.guild_id], name="View avatar")
    async def avatar_msg(self, ctx: ChromeyContext, message: discord.Message):
        await self.handle_avatar(ctx, message.author)
    
    async def handle_avatar(self, ctx, member: discord.Member):
        embed = discord.Embed(title=f"{member}'s avatar")
        animated = ["gif", "png", "jpeg", "webp"]
        not_animated = ["png", "jpeg", "webp"]

        avatar = member.avatar or member.default_avatar
        def fmt(format_):
            return f"[{format_}]({avatar.replace(format=format_, size=4096)})"

        if member.display_avatar.is_animated():
            embed.description = f"View As\n {'  '.join([fmt(format_) for format_ in animated])}"
        else:
            embed.description = f"View As\n {'  '.join([fmt(format_) for format_ in not_animated])}"

        embed.set_image(url=avatar.replace(size=4096))
        embed.color = discord.Color.random()

        view = PFPView(ctx)
        if member.guild_avatar is not None:
            view.add_item(PFPButton(ctx, member))

        view.message = await ctx.respond(embed=embed, ephemeral=ctx.whisper, view=view)

    @always_whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Tag helpers, usable in #support once every 24 hours per user")
    async def helpers(self, ctx: ChromeyContext):
        """Tag helpers, usable in #support once every 24 hours per user"""
        # TODO: this needs to be fixed.
        db_guild = guild_service.get_guild()
        if ctx.channel.id != db_guild.channel_support:
            raise commands.BadArgument(f'This command is only usable in <#{db_guild.channel_support}>!')

        # obj = Object(ctx.interaction.user.id)
        # obj.author = ctx.interaction
        # obj.guild = ctx.interaction.guild

        bucket = self.helpers_cooldown.get_bucket(...)
        current = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc).timestamp()
        if bucket.update_rate_limit(current):
            raise commands.BadArgument("This command is on cooldown.")

        helper_role = ctx.guild.get_role(db_guild.role_helpers)
        await ctx.channel.send(f'{ctx.author.mention} pinged {helper_role.mention}', allowed_mentions=discord.AllowedMentions(roles=True))
        await ctx.send_success("Done!")

    @helpers.error
    @remindme.error
    @jumbo.error
    @avatar.error
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
    bot.add_cog(Misc(bot))
