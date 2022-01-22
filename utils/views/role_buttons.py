import discord

class ReactionRoleButton(discord.ui.Button):
    def __init__(self, role: discord.Role, emoji: discord.Emoji):
        super().__init__(label=role.name, style=discord.ButtonStyle.primary, emoji=emoji, custom_id=str(role.id))

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        role = interaction.guild.get_role(int(self.custom_id))
        if role is None:
            return
        await interaction.response.defer(ephemeral=True)
        if role not in user.roles:
            await user.add_roles(role)
            await interaction.followup.send(f"{self.emoji} You have been given the {role.mention} role")
        else:
            await user.remove_roles(role)
            await interaction.followup.send(f"{self.emoji} You have removed the {role.mention} role")
