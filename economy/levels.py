import discord
from discord.ext import commands

class Levels(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.pool = bot.pool

    def calc_xp(self, level):
        return int(5*level**2 / 3.7) + 1

    def calc_level(self, xp: int):
        x = 1
        while xp > self.calc_xp(x):
            x += 1
        
        level = x - 1

        return (level, int(xp - self.calc_xp(level)), self.calc_xp(x))
    

    async def on_level_up(self, ctx, old, new):
        old_level, _, _ = self.calc_level(old)
        new_level, _, _ = self.calc_level(new)
        
        arrowup = "<:greenarrowup:1206939568759373854>"
        xp_icon = "<a:xp:1206668715710742568>"
        addlevel = "<:1_xp:1206668555916148847>"

        if new_level > old_level:
            embed = discord.Embed(
                title = f"Level up!  {addlevel}",
                description = f"You leveled up from **Level {old_level}** to **Level {new_level}!**  {arrowup} {xp_icon}",
                color = 0x88e595
            )
            await ctx.reply(embed = embed)


    @commands.command(name = "level", aliases = ['xp', 'viewlevel'])
    async def level(self, ctx, user: discord.Member = None):
        if user:
            person = user
        else:
            person = ctx.author

        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT xp FROM discord WHERE user_id = ?", (person.id,))
            row = await req.fetchone()
            xp = row['xp']
        
        level, xp, xp_max = self.calc_level(xp)
        xp = 0 if xp == -1 else xp

        await ctx.reply(embed = discord.Embed(
            title = "Levels  <a:xp:1206668715710742568>",
            description = f"""{person.mention} is at **Level {level}**\nTheir XP is **{xp}/{xp_max}**\n\nJust **{xp_max - xp}** more XP to go before they can <:1_xp:1206668555916148847>""",
            color = discord.Color.brand_green()
        ))

    @commands.command(name = 'leveltop', aliases = ['lvltop', 'lt'])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def leveltop(self, ctx):
        async with self.pool.acquire() as conn:
            req = await conn.execute("""SELECT * FROM discord
                                            ORDER BY xp DESC
                                            LIMIT 10""")
            
            rows = await req.fetchall()

            embed = discord.Embed(
                title = 'Highest Levels',
                description = "\n".join(
                    [f"**#{i+1}** - <@{row['user_id']}> (`Level {self.calc_level(row['xp'])[0]}`)" \
                     for i, row in enumerate(rows)] + [f"**#{i+1}** - None" for i in range(len(rows), 10)]
                ), color = discord.Color.green()
            )
            await ctx.reply(embed = embed)


async def setup(bot):
    await bot.add_cog(Levels(bot))