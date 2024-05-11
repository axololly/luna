import discord
from discord.ext import commands

"""
            per_page = 10,
            accent_color = discord.Color.blue(),
            error_color = discord.Color.red(),
            pagination_buttons = {
                "start_button": discord.ui.Button(label = '<<', style = discord.ButtonStyle.grey),
                "previous_button": discord.ui.Button(label = '<', style = discord.ButtonStyle.blurple),
                "stop_button": None,
                "next_button": discord.ui.Button(label = '>', style = discord.ButtonStyle.blurple),
                "end_button": discord.ui.Button(label = '>>', style = discord.ButtonStyle.grey),
            }
"""

class HelpCommand(commands.MinimalHelpCommand):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def send_command_help(self, command: commands.Command):
        embed = discord.Embed(title = f"{command.name}", color = discord.Color.blue())
        embed.add_field(name = "Explanation", value = command.help, inline = False)
        embed.add_field(name = "Syntax", value = self.get_command_signature(command), inline = False)
        aliases = command.aliases

        if aliases:
            embed.add_field(name = "Aliases", value = ", ".join(aliases), inline = False)        

        channel = self.get_destination()
        await channel.send(embed = embed)
    
    async def send_cog_help(self, cog: commands.Cog):
        embed = discord.Embed(title = cog.name)
        
        for command in cog.walk_commands():
            embed.add_field(name = command, value = command.help)
        
        channel = self.get_destination()
        await channel.send(embed = embed)

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title = "Help", color = discord.Color.blue())
        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort = True)
            command_signatures = [self.get_command_signature(command) for command in filtered]

            if command_signatures:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(name = cog_name, value = "\n".join(command_signatures), inline = False)
        
        channel = self.get_destination()
        await channel.send(embed = embed)
    
class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = HelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help_command
        

async def setup(bot):
    await bot.add_cog(Help(bot = bot))