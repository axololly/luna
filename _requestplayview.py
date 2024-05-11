import discord

class RequestToPlayView(discord.ui.View):
    def __init__(self, player: discord.Member, opponent: discord.Member, bet: int = None, game: str = None, timeout: int = 20):
        super().__init__()
        self.player = player
        self.opponent = opponent
        self.value = None
        self.timeout = timeout
        self.game = game
        self.bet = bet
    
    async def on_callback(self):
        for item in self.children:
            item.disabled = True

    async def on_timeout(self):
        await self.on_callback()
        await self.message.edit(
            content = None,
            embed = discord.Embed(
                title = "⏰  **Timed out!**",
                description = f"Probably a good idea to find new friends.",
                color = 0xff9691
            ), view = self
        )
    
    @discord.ui.button(label = "Accept", style = discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.player:
            await interaction.response.send_message(content = "not you, dingus", ephemeral = True)
        elif interaction.user == self.opponent:
            await self.on_callback()
            await interaction.response.edit_message(
                embed = discord.Embed(
                    title = "**Match found!**",
                    description = f":white_check_mark:  {self.opponent.mention} has accepted the challenge.\n Game will begin shortly.",
                    color = discord.Color.green()
                ), view = self
            )

            if self.bet:
                async with interaction.client.pool.acquire() as conn:
                    await conn.execute(f"UPDATE discord SET wallet = wallet - ? WHERE user_id = ?", (self.bet, self.player.id))
                    await conn.execute(f"UPDATE discord SET wallet = wallet - ? WHERE user_id = ?", (self.bet, self.opponent.id))

            self.value = True
            self.stop()
        else:
            await interaction.response.send_message("not you, dingus", ephemeral = True)
    
    @discord.ui.button(label = "Deny", style = discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.player:
            await interaction.response.edit_message(
                content = self.opponent.mention,
                embed = discord.Embed(
                    title = f":mag: Someone wants to play a game of {self.game}!",
                    description = f":x:  {self.opponent.mention}, {self.player.name} cancelled the challenge.",
                    color = discord.Color.red()
                ), view = None
            )
            self.stop()
        elif interaction.user in [self.player, self.opponent]:
            await self.on_callback()
            await interaction.response.edit_message(
                embed = discord.Embed(
                    title = "**Match declined!**",
                    description = f":x:  {self.opponent.mention} has declined the challenge. Sorry bro, not my fault.",
                    color = discord.Color.red()
                ), view = None
            )
            self.stop()
        else:
            await interaction.response.send_message("not you, dingus", ephemeral = True)