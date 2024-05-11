import asyncio, discord, random, string
from discord.ext import commands
from economy.minigames import Minigames

def readable_time(time_in_seconds: int):
    days, hours = divmod(time_in_seconds, 24*60**2)
    hours, mins = divmod(hours, 60**2)
    mins, secs = divmod(mins, 60)

    time_units = ['d', 'h', 'm', 's']

    converted_time = " ".join([f"{int(unit)}{time_units[i]}" for i, unit in enumerate([days, hours, mins, secs]) if unit])
    return converted_time

class RequestView(discord.ui.View):
    def __init__(self, user: discord.Member):
        super().__init__()
        self.user = user
        self.value = None
        self.timeout = 15

    async def on_callback(self):
        for child in self.children:
            child.disabled = True

    async def on_timeout(self):
        await self.on_callback()
        await self.message.edit(
            content = None,
            embed = discord.Embed(
                title = "⏰  **Timed out!**",
                description = f"You finally realised gambling isn't good for you. <:explodingboar:1205232579024781362>",
                color = 0xff9691
            ), view = self
        )
    
    @discord.ui.button(label = "Accept", style = discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("not you, dummy")
            return
        
        self.value = True
        await self.on_callback()
        await interaction.response.edit_message(view = self)
        self.stop()
    
    @discord.ui.button(label = "Deny", style = discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("not you, dummy")
            return

        await self.message.edit(
            embed = discord.Embed(
                title = "Don't want to gamble? <:sadsponge:1205232363659853904>",
                description = "Are you _sure_ though?\nGambling's pretty fun, you know...",
                color = discord.Color.red()
            )
        )
        await self.on_callback()
        await interaction.response.edit_message(view = self)
        self.stop()

rouletteHelp = "In roulette, you have to pick the colour of the pocket the ball will land in. You can pick either red or black, both equally likely.\n_Or green if you're feeling lucky..._\n\nIf you guess red  (\🟥)  or black  (\⬛)  and you get the correct pocket, you win **twice** your original bet. Sounds nice, right?\n\nWell, if you guess green and it's the right pocket, you win **five times** your bet.\n\nFor all pockets, if you don't get the correct one, you lose the money you bet. No extra fees!\n\n**Minimum bet of 100, can bet 'all' or '5k', '10k', etc**"

slotsHelp = "With a new scrolling effect, you just run slots with a bet of your choice and wait for the payouts to roll in. We're obviously going to gatekeep the chances of each item appearing so good luck and have fun!\n\n**Minimum bet of 100, can bet 'all' or '5k', '10k', etc**"

class Gamble(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.pool

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandOnCooldown):
            await ctx.reply(f"you can play {ctx.command.name} again in **{readable_time(int(error.retry_after))}**")
        else:
            raise error

    @commands.command(name = "roulette", help = rouletteHelp)
    @commands.cooldown(1, 45, commands.BucketType.user)
    async def roulette(self, ctx, bet: str = None, colour: str = None):
        if not await Minigames(self.bot).check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            ctx.command.reset_cooldown(ctx)
            return
        
        if not colour or not bet:
            await ctx.reply("Try `as help roulette` instead!")
            ctx.command.reset_cooldown(ctx)
            return
        
        if ',' in bet:
            bet = bet.translate(string.maketrans(",", ""))
                    
        elif bet[-1] == 'k':
            bet = float(bet[:-1]) * 10**3
                    
        elif bet[-1] == 'm':
            bet = float(bet[:-1]) * 10**6
                    
        elif bet == "all":
            async with self.pool.acquire() as conn:
                req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (ctx.author.id,))
                row = await req.fetchone()
                bet = row['wallet']
        else:
            await ctx.reply("its `all` or nothing buddy")
                
        try:
            bet = int(bet)
        except ValueError:
            await ctx.reply("Something went wrong with your `bet` argument! Check `as help roulette` for syntax info!")
            return

        if bet < 100:
            await ctx.reply("Don't cheap out on your gambling addiction. Put ☾ 100 or more into slots.")
            ctx.command.reset_cooldown(ctx)
            return
        
        if bet > 20000:
            await ctx.reply("Can't play with more than 20k. If you want to know why, ask William.\nAnd William, if you want to know why, Jaden paid me off. £2.37 and a sweet.")
            ctx.command.reset_cooldown(ctx)
            return
        
        view = RequestView(ctx.author)
        view.message = await ctx.reply(embed = discord.Embed(
            title = "Are you sure you want to play Roulette?",
            description = f"""If you're not familiar, run `as roulette` to get an explanation of how to play Roulette. If you are, ignore this.\n\nAre you sure you want to bet `☾ {bet}` and continue playing?""",
            color = 0xeed202
        ), view = view)

        await view.wait()

        if view.value:
            async with self.pool.acquire() as conn:
                req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (ctx.author.id,))
                row = await req.fetchone()
                
                if row['wallet'] < bet:
                    await ctx.reply("not enough money bozo. :joy_cat: :-1:")
                    return
                
                await conn.execute("UPDATE discord SET wallet = wallet - ? WHERE user_id = ?", (bet, ctx.author.id))
            
            rouletteEmbed = discord.Embed(
                title = "Roulette Wheel",
                description = None,
                color = discord.Color.dark_embed()
            )
            rouletteEmbed.set_image(url = """https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExOGdvNGUxeHB3cTA5c2xsZTJ5d3FsczdjOXhyejl6amRibzNqaG5xMiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/nXeB6Jy7vHUVIsbN9d/giphy.gif""")
                                    
            message = await ctx.reply(embed = rouletteEmbed)
            
            await asyncio.sleep(3)
            
            squares = {'green': '🟩', 'black': '⬛', 'red': '🟥'}
            invsquares = {'🟩': 'green', '⬛': 'black', '🟥': 'red'}

            board = {0: '🟩'} | {n+1: list(squares.values())[(n+1) % 2] for n in range(36)}

            from random import randint as rand
            pocket = board[rand(0, 36)]

            if colour == invsquares[pocket]:
                state = "won"
                embedcolour = discord.Color.green()

                if pocket == board[0]:
                    money_after = 5 * bet
                else:
                    money_after = 2 * bet
            else:
                money_after = 0
                state = "lost"
                embedcolour = discord.Color.red()

            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (money_after, ctx.author.id))

            if money_after == 0:
                money_after = bet

            await message.edit(
                embed = discord.Embed(
                    title = "Roulette Wheel",
                    description = f"""The ball has landed in **{invsquares[pocket]}**.\nYou chose **{colour}**...\n\nSo that means...\n\nYou {state} `☾ {money_after}`!""",
                    color = embedcolour
                )
            )
        
    @commands.command(name = 'slots', help = slotsHelp)
    @commands.cooldown(1, 45, commands.BucketType.user)
    async def slots(self, ctx, bet: str = None):
        if not bet:
            await ctx.reply("gotta be more than that lmao. bet something")
            return
        
        if not await Minigames(self.bot).check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            return

        bet = str(bet)

        if type(bet) is str:
            if ',' in bet:
                bet = bet.translate(string.maketrans(",", ""))
            
            if bet[-1] == 'k':
                bet = float(bet[:-1]) * 10**3
            
            if bet[-1] == 'm':
                bet = float(bet[:-1]) * 10**6
                
            elif str(bet).lower() == 'all':
                async with self.pool.acquire() as conn:
                    req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (ctx.author.id,))
                    row = await req.fetchone()
                    
                    bet = row['wallet']
            else:
                await ctx.reply("it's `all` or nothing buddy")
                ctx.command.reset_cooldown(ctx)
                return
        
        bet = int(bet)

        if bet < 1000:
            await ctx.reply("Don't cheap out on your gambling addiction.")
            ctx.command.reset_cooldown(ctx)
            return
    
        view = RequestView(ctx.author)
        view.message = await ctx.reply(embed = discord.Embed(
            title = "Are you sure you want to play Slots?",
            description = f"""Thanks to my awful programming, I screwed up the odds so you might rage after losing a few times.\n\nAre you sure you want to bet `☾ {bet}` and continue playing?""",
            color = 0xeed202
        ), view = view)

        await view.wait()

        if view.value:
            slots = view.message
            
            async with self.pool.acquire() as conn:
                req = await conn.execute("SELECT user_id FROM discord")
                accounts = [x[0] for x in await req.fetchall()]

                if ctx.author.id not in accounts:
                    await ctx.reply("no account, broke boy. make one with `as bal`")
                    return
                
                req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (ctx.author.id,))
                wallet = list(await req.fetchone())[0]

                if wallet < bet:
                    await ctx.reply("you don't have that much money. stop abusing glitches like max")
                    return

                await conn.execute("UPDATE discord SET wallet = wallet - ? where user_id = ?", (bet, ctx.author.id))

                req = await conn.execute("SELECT * FROM slots")
                rows = await req.fetchall()
                names = [f":{x[0]}:" for x in rows]
                chances = [int(x[1][:-1]) for x in rows]
            
            display = [random.choices(names, k = 3) for _ in range(3)]
            await slots.edit(content = "\n".join([" ".join(line) if display.index(line) != 1 else \
                                        " ".join(line) + "\u200b" * 4 + ":arrow_left:" for line in display]), embed = None, view = None)

            for _ in range(9):
                await asyncio.sleep(0.3)
                display.pop()
                display.insert(0, random.choices(names, weights = chances, k = 3))
                await slots.edit(content = "\n".join([" ".join(line) if display.index(line) != 1 else \
                                            " ".join(line) + "\t\t:arrow_left:" for line in display]))

            payout = 0

            display = display[1]

            if len(set(display)) == 1:
                item = display[0]
                payout = int(rows[names.index(display[0])][2][:-1])
                res = f"**3**  {item}, meaning you won `☾ {int(payout) * bet}`!"
            elif len(set(display)) == 2:
                item = [x for x in display if display.count(x) == 2][0]
                payout = int(rows[names.index(item)][3][:-1])
                res = f"**2** {item}, meaning you won `☾ {int(payout) * bet}`!"
            else:
                res = f"1 of each fruit, meaning you got nothing! <:pointandlaugh:1205232587736485888>"
            
            think = "\n\nI'll give you half a minute to think about if you want to do slots again."
        
            if payout > 0:
                result = discord.Embed(
                    title = "Slots Result",
                    description = res + think,
                    color = discord.Color.green()
                )
            else:
                result = discord.Embed(
                    title = "Slots Result",
                    description = res + think,
                    color = discord.Color.red()
                )

            async with self.pool.acquire() as conn:
                if len(set(display)) != 3:
                    req = await conn.execute("SELECT xp FROM discord WHERE user_id = ?", (ctx.author.id,))
                    row = await req.fetchone()
                    old_xp = row[0]

                    from economy.levels import Levels
                    
                    rewardxp = random.randint(1, 15)
                    levels = Levels(bot = self.bot)
                    await levels.on_level_up(ctx, old_xp, old_xp + rewardxp)

                await conn.execute("UPDATE discord SET wallet = wallet + ? where user_id = ?", (int(payout) * bet, ctx.author.id))

            await slots.reply(embed = result)

    @commands.command(name = 'coinflip', aliases = ['cf'])
    @commands.cooldown(1, 45, commands.BucketType.user)
    async def coinflip(self, ctx, bet: str = None, side: str = None):
        if not bet or type(bet) is not str:
            await ctx.reply("you put your bet in wrong. has to be a number. type `as help coinflip` for help with syntax.")            
            ctx.command.reset_cooldown(ctx)
            return
        
        bet = str(bet)

        if ',' in bet:
            bet = bet.translate(string.maketrans(",", ""))
                    
        elif bet[-1] == 'k':
            bet = float(bet[:-1]) * 10**3
                                
        elif bet[-1] == 'm':
            bet = float(bet[:-1]) * 10**6
                                
        elif bet == "all":
            async with self.pool.acquire() as conn:
                req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (ctx.author.id,))
                row = await req.fetchone()
                bet = row['wallet']
        else:
            await ctx.reply("it's `all` or nothing buddy")
            ctx.command.reset_cooldown(ctx)
            return
        
        bet = int(bet)

        if bet > 20000:
            await ctx.reply("You can't bet more than 20k. If you want to know why, blame Jaden.")
            return
        
        if not side or type(side) is not str or side not in ['heads', 'h', 'tails', 't']:
            await ctx.reply("you can't bet that side of the coin. has to be either \"heads\" (can be \"h\") or \"tails\" (can be \"t\")\n\ntype `as help coinflip` for help with syntax.")
            ctx.command.reset_cooldown(ctx)
            return
        
        if not await Minigames(self.bot).check_for_account(ctx.author.id):
            await ctx.reply("Looks like you don't have an account! Make one with `as bal` before playing any games!")
            ctx.command.reset_cooldown(ctx)
            return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (ctx.author.id,))
            row = await req.fetchone()

            if row['wallet'] < bet:
                await ctx.reply("Can't bet what you don't have. We might be a casino but we still have to follow the rules!")
                ctx.command.reset_cooldown(ctx)
                return

            await conn.execute("UPDATE discord SET wallet = wallet - ? WHERE user_id = ?", (bet, ctx.author.id))
        
        embed = discord.Embed(title = "Coinflip :coin:")
        embed.set_image(url = "https://cdn.dribbble.com/users/1493264/screenshots/5573460/coin-flip-dribbble.gif")

        message = await ctx.reply(embed = embed)
        await asyncio.sleep(3)

        correct_side = random.choice(['heads', 'tails'])
        side = 'heads' if side == 'h' else side
        side = 'tails' if side == 't' else side

        if side == correct_side:
            await message.edit(
                embed = discord.Embed(
                    title = "Coinflip :coin:",
                    description = f"You guessed **{side}** and you were correct!\n\nYou won `☾ {bet * 2}`, spend it responsibly!",
                    color = discord.Color.green()
                )
            )

            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (bet * 2, ctx.author.id))
        else:
            await message.edit(
                embed = discord.Embed(
                    title = "Coinflip :coin:",
                    description = f"You guessed **{side}** and you were wrong! <:pointandlaugh:1205232587736485888>\n\nYou lost `☾ {bet}`, womp womp!",
                    color = discord.Color.red()
                )
            )

async def setup(bot):
    await bot.add_cog(Gamble(bot))