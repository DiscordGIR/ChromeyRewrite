import discord
from discord import Embed
from discord.ext import commands, tasks
from data.services.guild_service import guild_service
from utils.config import cfg

class RoleCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rolecount.start()

    def cog_unload(self):
        self.rolecount.cancel()

    @tasks.loop(seconds=30)
    async def rolecount(self):
        """Track number of users with a given role"""
        guild_id = cfg.guild_id
        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(guild_service.get_guild().channel_reaction_roles)
        messages = await channel.history(limit=10).flatten()

        roles_to_track = [
            "Acer",
            "HP",
            "Samsung",
            "MadeByGoogle",
            "Asus",
            "Lenovo",
            "Toshiba",
            "Dell",
            "LG",
            "CTL",
            "Intel",
            "AMD",
            "ARM",
            "Stable Channel",
            "Beta Channel",
            "Dev Channel",
            "Canary Channel",
            "Developer Mode",
            "Helpers",
            "Announcements",
            "Deals",
            "Chromium",
            "Pronouns: he/him",
            "Pronouns: she/her",
            "Pronouns: they/them",
            "Pronouns: other (see profile)"
        ]
        response = "These statistics reload every 30 seconds.\n"
        for role in roles_to_track:
            role_obj = discord.utils.get(guild.roles, name=role)
            if (role_obj is not None):
                response += f'{role_obj.mention} has {len(role_obj.members)} members\n'
        embed = Embed(title="Role statistics", description=response)
        for message in messages:
            if (message.author == self.bot.user) and len(message.embeds) > 0 and message.embeds[0].title == "Role statistics":
                await message.edit(embed=embed)
                return

        await channel.send(embed=embed)

    @rolecount.before_loop
    async def before_rolecount(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(RoleCount(bot))
