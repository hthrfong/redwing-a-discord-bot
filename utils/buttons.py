import discord


class Slap(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=3600)
        self.value = None
        self.user = None
        self.ctx = ctx

    @discord.ui.button(label="Slap Back!", style=discord.ButtonStyle.blurple)
    async def slap(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True
        self.user = interaction.user
        button.label = "Slapped!"
        button.disabled = True
        self.stop()
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        print("Slap button timeout")
        await self.ctx.interaction.edit_original_message(view=None)