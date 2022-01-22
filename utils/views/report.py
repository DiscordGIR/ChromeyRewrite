import discord
from discord import ui
from discord.ext.commands import Context
import pytimeparse
from data.services.guild_service import guild_service
from utils.context import ChromeyOldContext, PromptData
from utils.mod.global_modactions import ban, mute, unmute, warn
from utils.permissions.permissions import permissions
from utils.views.modactions import ModViewReport

class ReportActions(ui.View):
    def __init__(self, target_member: discord.Member):
        super().__init__(timeout=None)
        self.target_member = target_member

    async def start(self, ctx: Context):
        self.ctx = ctx
        # await self.wait()
        
    def check(self, interaction: discord.Interaction):
        if not permissions.has(self.target_member.guild, interaction.user, 2):
            return False
        return True

    @ui.button(emoji="✅", label="Dismiss", style=discord.ButtonStyle.primary)
    async def dismiss(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        await self.ctx.message.delete()

    @ui.button(emoji="⚠️", label="Warn", style=discord.ButtonStyle.primary)
    async def warn(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        # view = ModViewReport(self.target_member, interaction.user, self.ctx.message, mod_action=ModViewReport.ModAction.WARN)
        # await (await self.ctx.bot.get_application_context(interaction)).defer()
        # msg = await self.ctx.channel.send(embed=discord.Embed(description=f"{interaction.user.mention}, choose a warn reason for {self.target_member.mention}.", color=discord.Color.blurple()), view=view)
        # new_ctx = await self.ctx.bot.get_context(msg, cls=ChromeyOldContext)
        # await view.start(new_ctx)
        prompt_data = PromptData(value_name="Reason", 
                                        description=f"Reason for warn?",
                                        convertor=str,
                                        timeout=30
                                        )
        if not interaction.response.is_done():
            await interaction.response.defer()

        self.ctx.author = interaction.user
        reason = await self.ctx.prompt(prompt_data)
        if reason is not None:
            await warn(self.ctx, self.target_member, reason)

        await self.ctx.message.delete()

    @ui.button(emoji="❌", label="Ban", style=discord.ButtonStyle.primary)
    async def ban(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        # view = ModViewReport(self.target_member, interaction.user, self.ctx.message, mod_action=ModViewReport.ModAction.BAN)
        # await (await self.ctx.bot.get_application_context(interaction)).defer()
        # msg = await self.ctx.channel.send(embed=discord.Embed(description=f"{interaction.user.mention}, choose a ban reason for {self.target_member.mention}.", color=discord.Color.blurple()), view=view)
        # new_ctx = await self.ctx.bot.get_context(msg, cls=ChromeyOldContext)
        # await view.start(new_ctx)
        prompt_data = PromptData(value_name="Reason", 
                                        description=f"Reason for ban?",
                                        convertor=str,
                                        timeout=30
                                        )
        if not interaction.response.is_done():
            await interaction.response.defer()

        self.ctx.author = interaction.user
        reason = await self.ctx.prompt(prompt_data)
        if reason is not None:
            await ban(self.ctx, self.target_member, reason)

        await self.ctx.message.delete()

    @ui.button(emoji="🆔", label="Post ID", style=discord.ButtonStyle.primary)
    async def id(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        await self.ctx.channel.send(self.target_member.id)

    @ui.button(emoji="🧹", label="Clean up", style=discord.ButtonStyle.primary)
    async def purge(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        await self.ctx.channel.purge(limit=100)

    @ui.button(emoji="🔎", label="Claim report", style=discord.ButtonStyle.primary)
    async def claim(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        embed = discord.Embed(color=discord.Color.blurple())
        embed.description = f"{interaction.user.mention} is looking into {self.target_member.mention}'s report!"
        await self.ctx.send(embed=embed, delete_after=5)

        report_embed = self.ctx.message.embeds[0]
        report_embed.color = discord.Color.orange()
        report_embed.title = f"{report_embed.title} (claimed)"
        await self.ctx.message.edit(embed=report_embed)

class RaidPhraseReportActions(ui.View):
    def __init__(self, author: discord.Member, domain: str):
        super().__init__(timeout=None)
        self.target_member = author
        self.domain = domain

    async def start(self, ctx: Context):
        self.ctx = ctx
        await self.wait()
        
    def check(self, interaction: discord.Interaction):
        if not permissions.has(self.target_member.guild, interaction.user, 2):
            return False
        return True

    @ui.button(emoji="✅", label="Dismiss", style=discord.ButtonStyle.primary)
    async def dismiss(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        self.ctx.author = self.ctx.message.author = interaction.user
        try:
            await unmute(self.ctx, self.target_member, reason="Reviewed by a moderator.")
        except Exception:
            await self.ctx.send_warning("I wasn't able to unmute them.", delete_after=5)
        finally:
            await self.ctx.message.delete()
        
    @ui.button(emoji="💀", label="Ban, unban, and add raidphrase", style=discord.ButtonStyle.primary)
    async def ban(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        self.ctx.author = self.ctx.message.author = interaction.user
        try:
            await self.target_member.remove_timeout()
            await ban(self.ctx, self.target_member, reason="Raid phrase detected", extra_text="We detected that your account was hacked as it posted a scam text in our server. We have banned and unbanned you to delete all of your scam messages. Please secure your account, then you can rejon using https://discord.gg/chromeos.")
            await self.ctx.guild.unban(discord.Object(id=self.target_member.id))
            self.ctx.bot.ban_cache.unban(self.target_member.id)
        except Exception:
            await self.ctx.send_warning("I wasn't able to ban them.", delete_after=5)

        done = guild_service.add_raid_phrase(self.domain)
        if done:
            await self.ctx.send_success(f"{self.domain} was added to the raid phrase list.", delete_after=5)
        else:
            await self.ctx.send_warning(f"{self.domain} was already in the raid phrase list.", delete_after=5)

        await self.ctx.message.delete()

class SpamReportActions(ui.View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=None)
        self.target_member = author

    async def start(self, ctx: Context):
        self.ctx = ctx
        await self.wait()
        
    def check(self, interaction: discord.Interaction):
        if not permissions.has(self.target_member.guild, interaction.user, 2):
            return False
        return True

    @ui.button(emoji="✅", label="Dismiss", style=discord.ButtonStyle.primary)
    async def dismiss(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        self.ctx.author = self.ctx.message.author = interaction.user
        try:
            await unmute(self.ctx, self.target_member, reason="Reviewed by a moderator.")
        except:
            await self.ctx.send_warning("I wasn't able to unmute them.", delete_after=5)
        finally:
            await self.ctx.message.delete()
        
    @ui.button(emoji="💀", label="Ban", style=discord.ButtonStyle.primary)
    async def ban(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        self.ctx.author = self.ctx.message.author = interaction.user
        try:
            await ban(self.ctx, self.target_member, reason="Spam detected")
        except Exception:
            await self.ctx.send_warning("I wasn't able to ban them.")
        finally:
            await self.ctx.message.delete()
        
    @ui.button(emoji="⚠️", label="Temporary mute", style=discord.ButtonStyle.primary)
    async def mute(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        
        prompt_data = PromptData(value_name="duration", 
                                        description="Please enter a duration for the mute (i.e 15m).",
                                        convertor=pytimeparse.parse,
                                        )
        await interaction.response.defer()
        self.ctx.author = interaction.user
        duration = await self.ctx.prompt(prompt_data)
        await self.target_member.remove_timeout()
        self.ctx.bot.tasks.cancel_unmute(self.target_member.id)
        await mute(self.ctx, self.target_member, duration, reason="A moderator has reviewed your spam report.")
        await self.ctx.message.delete()
