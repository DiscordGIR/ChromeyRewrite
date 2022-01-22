import discord
from discord import ui
from utils.context import ChromeyContext


class Confirm(ui.View):
    def __init__(self, ctx: ChromeyContext, true_response = None, false_response = None):
        super().__init__()
        self.ctx = ctx
        self.value = None
        self.true_response = true_response
        self.false_response = false_response

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @ui.button(label='Yes', style=discord.ButtonStyle.success)
    async def confirm(self, button: ui.Button, interaction: discord.Interaction):
        if interaction.user == self.ctx.author:
            self.value = True
            self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @ui.button(label='No', style=discord.ButtonStyle.grey)
    async def cancel(self, button: ui.Button, interaction: discord.Interaction):
        if interaction.user == self.ctx.author:
            if self.false_response is not None:
                await self.ctx.send_warning(description=self.false_response)
            self.value = False
            self.stop()
