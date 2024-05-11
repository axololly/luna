import asqlite, logging, discord
from discord.ext import commands
from utility import Utility

token = open('token.txt').read()

class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix = 'as ',
            intents = discord.Intents.all(),
            status = discord.Status.idle,
            activity = discord.Game("with spaceships")
        )

    async def setup_hook(self):
        self.pool = await asqlite.create_pool('playerdata.sql', size = 20)

        for cog in Utility(bot = self).cogs.keys():
            await self.load_extension(cog)

bot = DiscordBot()

handler = logging.FileHandler(filename = 'discord.log', encoding = 'utf-8', mode = 'w')

bot.run(token, log_handler = handler, root_logger = True)