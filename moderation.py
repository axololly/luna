import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingPermissions):
            if ctx.command.name == 'clear':
                await ctx.reply("You are missing the `Manage Messages` permission.")
            else:
                await ctx.reply("You are missing either `Kick Members` or `Ban Members` permissions.")
        

    @commands.command(name = 'clear', aliases = ['purge'])
    @commands.has_permissions(manage_messages = True)
    async def clear(self, ctx, total: int = 0):
        if not total:
            await ctx.reply("how many messages am i clearing, boss?")
            return
        
        total = int(total)
        total = 1000 if total > 1000 else total
        await ctx.channel.purge(limit = total + 1)
        await ctx.send(f"Cleared {total} messages from {ctx.channel.mention}!", delete_after = 2)

    @commands.command(name = 'kick')
    async def kick(self, ctx, user: discord.Member, reason: str = None):
        await ctx.reply(embed = discord.Embed(
            title = f"Kicked {user.name}",
            description = f"The reason for {ctx.author.mention} kicking {user.name} was:\n{reason}",
            color = discord.Color.red()
        ))
        user_dm = await user.create_dm()
        await user_dm.send(embed = discord.Embed(
            title = f"You got kicked from {ctx.guild.name}!",
            description = f"The reason for {ctx.author.name} kicking you was:\n{reason}",
            color = discord.Color.red()
        ))
        await user.kick(reason = reason)

    @commands.command(name = 'ban')
    async def ban(self, ctx, user: discord.Member = None, reason: str = None):
        if not user:
            await ctx.reply("you haven't told me anyone to ban, schizo")

        await ctx.reply(embed = discord.Embed(
            title = f"Banned {user.name}",
            description = f"The reason for {ctx.author.mention} kicking {user.name} was:\n{reason}",
            color = discord.Color.red()
        ))

        user_dm = await user.create_dm()
        await user_dm.send(embed = discord.Embed(
            title = f"You got banned from {ctx.guild.name}!",
            description = f"The reason for {ctx.author.name} banning you was:\n{reason}",
            color = discord.Color.red()
        ))
        
        await ctx.guild.ban(user, reason = reason)
    
    @commands.command(name = 'unban')
    async def unban(self, ctx, userid: int = None, reason: str = None):
        if not userid:
            await ctx.reply("""Specify a user by their user ID to unban.
                               For example, my user ID is 797215104763691109. Use this ID to unban someone.""")

        try:
            user_to_unban = await self.bot.fetch_user(userid)
        except discord.NotFound:
            await ctx.reply("User cannot be found.")
            return

        user_dm = await user_to_unban.create_dm()

        await user_dm.send(embed = discord.Embed(
            title = f"You got unbanned from {ctx.guild.name}!",
            description = f"The reason for {ctx.author.name} unbanning you was:\n{reason}",
            color = discord.Color.red()
        ))

async def setup(bot):
    await bot.add_cog(Moderation(bot))