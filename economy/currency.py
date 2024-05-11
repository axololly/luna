import asyncio, random, discord, string
from discord import ui, ButtonStyle, Button, Interaction
from discord.ext import commands, tasks
from economy.levels import Levels
from economy.minigames import Minigames
from paginators import calc_page_num, BasicPaginator

def readable_time(time_in_seconds: int):
    days, hours = divmod(time_in_seconds, 24*60**2)
    hours, mins = divmod(hours, 60**2)
    mins, secs = divmod(mins, 60)

    time_units = ['d', 'h', 'm', 's']

    converted_time = " ".join([f"{int(unit)}{time_units[i]}" for i, unit in enumerate([days, hours, mins, secs]) if unit])
    
    if len(converted_time) == 0:
        return "0s"
    
    return converted_time

class SendView(ui.View):
    def __init__(self, sender: discord.Member, receiver: discord.Member, amount: int, timeout: int = 30):
        super().__init__()
        self.timeout = timeout
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.value = None
    
    async def on_callback(self):
        for child in self.children:
            child.disabled = True

    async def on_timeout(self):
        await self.on_callback()
        await self.message.edit(
            content = None,
            embed = discord.Embed(
                title = "⏰  **Timed out!**",
                description = f"Trade request expired. Make another request with `as trade`!",
                color = 0xff9691
            ), view = self
        )
    
    @ui.button(label = "Accept", style = ButtonStyle.green)
    async def accept(self, interaction: Interaction, button: ui.Button):
        if interaction.user == self.sender:
            await interaction.response.send_message(content = "You can't accept for them.\n(Press Deny to cancel the trade)", ephemeral = True)
        elif interaction.user == self.receiver:
            await self.on_callback()
            completeTransactionEmbed = discord.Embed(
                title = "**Coins have been sent! 💸**",
                description = f":white_check_mark:  {self.sender.mention} has shared `☾ {self.amount:,}` with {self.receiver.mention}",
                color = discord.Color.green()
            )
            completeTransactionEmbed.set_footer(text = "Hope you enjoy your new coins!")

            await interaction.response.edit_message(
                embed = completeTransactionEmbed, view = self
            )
            self.value = True
            self.stop()
        else:
            await interaction.response.send_message("This trade is not about you.", ephemeral = True)
    
    @ui.button(label = "Deny", style = ButtonStyle.red)
    async def deny(self, interaction: Interaction, button: ui.Button):
        if interaction.user == self.sender:
            await interaction.response.edit_message(
                content = self.receiver.mention,
                embed = discord.Embed(
                    title = f"Someone doesn't want to send some coins! 💳",
                    description = f":x:  {self.receiver.mention}, {self.sender.name} cancelled the trade.",
                    color = discord.Color.red()
                ), view = None
            )
        elif interaction.user in [self.sender, self.receiver]:
            await self.on_callback()
            await interaction.response.edit_message(
                embed = discord.Embed(
                    title = "**Offer declined!**",
                    description = f":x:  {self.receiver.mention} has declined the transaction. Sorry bro, not my fault.",
                    color = discord.Color.red()
                ), view = None
            )
            self.stop()
        else:
            await interaction.response.send_message("This trade is not about you.", ephemeral = True)

class BuyView(ui.View):
    def __init__(self, user: discord.Member):
        super().__init__()
        self.value = None
        self.user = user
        self.timeout = 15

    async def on_callback(self):
        for child in self.children:
            child.disabled = True

        await self.message.edit(view = self)

    async def on_timeout(self):
        await self.on_callback()
        await self.message.edit(
            embed = discord.Embed(
                title = "⏰  Timed out!",
                description = "You were too slow to press a few buttons.\nSeriously?",
                color = discord.Color.red()
            )
        )

    @ui.button(label = "Yes", style = ButtonStyle.green)
    async def accept(self, interaction: Interaction, button: Button):
        if not interaction.user == self.user:
            await interaction.response.send_message("Not everything revolves around you.")
            return
        
        self.value = True

        await self.on_callback()
        await interaction.response.defer()
        self.stop()
    
    @ui.button(label = "No", style = ButtonStyle.red)
    async def deny(self, interaction: Interaction, button: Button):
        if not interaction.user == self.user:
            await interaction.response.send_message("Not everything revolves around you.")
            return
        
        await self.message.edit(
            embed = discord.Embed(
                title = "Cancelled Purchase",
                description = ":x: _You leave the checkout and put the items back on the shelf, then walk out._",
                color = discord.Color.red()
            )
        )

        await self.on_callback()
        await interaction.response.defer()
        self.stop()

class SellView(ui.View):
    def __init__(self, user: discord.Member):
        super().__init__(timeout = 15)
        self.value = None
        self.user = user

    async def on_callback(self):
        for child in self.children:
            child.disabled = True

        await self.message.edit(view = self)

    async def on_timeout(self):
        await self.on_callback()
        await self.message.edit(
            embed = discord.Embed(
                title = "⏰  Timed out!",
                description = "You were too slow to press a few buttons.\nSeriously?",
                color = discord.Color.red()
            )
        )

    @ui.button(label = "Yes", style = ButtonStyle.green)
    async def accept(self, interaction: Interaction, button: Button):
        if not interaction.user == self.user:
            await interaction.response.send_message("This is not your transaction.")
            return
        
        self.value = True

        await self.on_callback()
        await interaction.response.defer()
        self.stop()
    
    @ui.button(label = "No", style = ButtonStyle.red)
    async def deny(self, interaction: Interaction, button: Button):
        if not interaction.user == self.user:
            await interaction.response.send_message("This is not your transaction.")
            return
        
        await self.message.edit(
            embed = discord.Embed(
                title = "Cancelled Purchase",
                description = ":x: _You leave the pawn shop and carry the items back to your house._",
                color = discord.Color.red()
            )
        )

        await self.on_callback()
        await interaction.response.defer()
        self.stop()

class RobView(ui.View):
    def __init__(self, user: discord.Member):
        super().__init__()
        self.value = None
        self.user = user
        self.timeout = 15

    async def on_callback(self):
        for child in self.children:
            child.disabled = True

        await self.message.edit(view = self)

    async def on_timeout(self):
        await self.on_callback()
        await self.message.edit(
            embed = discord.Embed(
                title = "⏰  Timed out!",
                description = "You finally realised stealing from people isn't a good idea <:explodingboar:1205232579024781362>",
                color = discord.Color.red()
            )
        )

    @ui.button(label = "Yes", style = ButtonStyle.green)
    async def accept(self, interaction: Interaction, button: Button):
        if not interaction.user == self.user:
            await interaction.response.send_message("don't get involved :-1:", ephemeral = True)
            return
        
        self.value = True

        await self.message.edit(
            embed = discord.Embed(
                title = "Let's get on with it then!",
                description = f"You have decided to pickpocket someone. Good luck!",
                color = discord.Color.green()
            ), view = None
        )

        await interaction.response.defer()
        self.stop()
    
    @ui.button(label = "No", style = ButtonStyle.red)
    async def deny(self, interaction: Interaction, button: Button):
        if not interaction.user == self.user:
            await interaction.response.send_message("don't get involved :-1:", ephemeral = True)
            return
        
        await self.message.edit(
            embed = discord.Embed(
                title = f"{self.user.name} has chosen a better path in life",
                description = ":x: _You look at the wallet with curiosity, then turn your gaze back forward and keep walking._",
                color = discord.Color.red()
            ), view = None
        )
        await interaction.response.defer()
        self.stop()

class BankrobLobby(ui.View):
    def __init__(self, orchestrator, being_robbed, pool):
        super().__init__()
        self.robbers = [orchestrator]
        self.being_robbed = being_robbed
        self.pool = pool
        self.is_robbery_commencing = False
    
    async def on_callback(self):
        for item in self.children:
            item.disabled = True
            item.style = ButtonStyle.grey

        await self.message.edit(view = self)

    async def on_timeout(self):
        await self.on_callback()

        if len(self.robbers) < 2:
            await self.message.edit(
                embed = discord.Embed(
                    title = "⏰  Timed out!",
                    description = "Good work. You couldn't find anyone for the bank robbery, you dingus. You have 15 minutes to recruit people and come back to me with the list. Otherwise, you're fired.",
                    color = discord.Color.red()
                )
            )
        else:
            self.is_robbery_commencing = True

class ShowPlayersButton(ui.Button):
    def __init__(self, robbers_involved):
        super().__init__(label = "Show Players", style = ButtonStyle.red)
        self.robbers_involved = robbers_involved
    
    async def callback(self, interaction: Interaction):
        await interaction.response.send_message(
            embed = discord.Embed(
                title = "Players Involved",
                description = "\n".join([p.mention for p in self.robbers_involved]),
                color = 0xFF5F1F
            ), ephemeral = True
        )
        self.disabled = True

class ChooseAJobButton(ui.Button):
    def __init__(self, label, **kwargs):
        super().__init__(label = label, style = ButtonStyle.green, **kwargs)
    
    async def callback(self, interaction: Interaction):
        if interaction.user != self.view.user:
            await interaction.response.send_message("This isn't your window. Get your own with `as jobs`", ephemeral = True)
            return
        
        async with self.view.pool.acquire() as conn:
            await conn.execute("UPDATE discord SET occupation = ? WHERE user_id = ?", (self.label, interaction.user.id))

            req = await conn.execute("SELECT salary FROM jobs WHERE job = ?", (self.label,))
            row = await req.fetchone()

        for child in self.view.children[:4]:
            self.view.remove_item(child)

        for child in self.view.children:
            child.disabled = True

            if child.label != self.label:
                child.style = ButtonStyle.grey
        
        n = 'n' if self.label[0].lower() in ['a', 'e', 'i', 'o', 'u'] else ''
        
        await interaction.response.edit_message(
            view = self.view,
            embed = discord.Embed(
                title = f"You now work as a{n} **{self.label}**",
                description = f"Your salary is `☾ {row['salary']}` and you can start work... well... now? I guess? I dunno, go ahead and start making some money.",
                color = discord.Color.green()
            )
        )
        self.view.job_chosen = self.label
        self.view.stop()

class ChooseAJobView(BasicPaginator):
    def __init__(self, user: discord.Member, page_size: int, page_numbers: int, pool):
        super().__init__(user, page_size, page_numbers)
        self.pool = pool

    def calc_level(self, xp: int):
        level = 1

        while not 5 / 3.7 * level**2 > xp:
            level += 1
        
        return level - 1

    async def display_page(self) -> None:
        async with self.pool.acquire() as conn:
            req = await conn.execute(f"""SELECT job, description, salary, level FROM jobs
                                         ORDER BY level ASC
                                         LIMIT {self.page_size}
                                         OFFSET {(self.page - 1) * self.page_size}""")
            rows = await req.fetchall()

            embed = discord.Embed(
                title = "Jobs Hiring",
                description = None,
                color = discord.Color.blue()
            )

            sep = '<:separator:1206287822558986281>'

            if len(self.children) > 4:
                for child in self.children[4:]:
                    self.remove_item(child)
            
            req = await conn.execute("SELECT xp FROM discord WHERE user_id = ?", (self.user.id,))
            user_row = await req.fetchone()
            user_level = self.calc_level(user_row['xp'])

            for i, row in enumerate(rows):
                embed.add_field(
                    name = f"{row['job']}",
                    value = f"_{row['description']}_\n{sep} Salary: `☾ {row['salary']:,}`\n{sep} \
                              Level required: `{row['level']}`" + ("\n\u200b" if i != len(rows) - 1 else ''), inline = i % 2 == 1)

                self.add_item(ChooseAJobButton(label = row['job'], row = 1, disabled = user_level < row['level']))
                
            await self.message.edit(embed = embed, view = self)

class BotBreakerView(ui.View):
    def __init__(self, user: discord.Member):
        super().__init__()
        self.value = None
        self.user = user
        self.timeout = 15

    async def on_callback(self):
        for child in self.children:
            child.disabled = True

        await self.message.edit(view = self)

    async def on_timeout(self):
        await self.on_callback()
        await self.message.edit(
            embed = discord.Embed(
                title = "⏰  Timed out!",
                description = "I guess they're not getting their _Bot Breaker_ item then. Sucks to suck!",
                color = discord.Color.red()
            )
        )

    @ui.button(label = "Yes", style = ButtonStyle.green)
    async def accept(self, interaction: Interaction, button: Button):
        if not interaction.user == self.user:
            await interaction.response.send_message("You're not getting anything.")
            return
        
        self.value = True

        await self.on_callback()
        await interaction.response.defer()
        self.stop()
    
    @ui.button(label = "No", style = ButtonStyle.red)
    async def deny(self, interaction: Interaction, button: Button):
        if not interaction.user == self.user:
            await interaction.response.send_message("You're not getting anything.")
            return
        
        await self.message.edit(
            embed = discord.Embed(
                title = "Cancelled Purchase",
                description = ":x: Looks like someone isn't getting their special _Bot Breaker_ item",
                color = discord.Color.red()
            )
        )

        await self.on_callback()
        await interaction.response.defer()
        self.stop()

class ShopView(BasicPaginator):
        def __init__(self, user: discord.Member, page_size: int, page_numbers: int, pool):
            super().__init__(user, page_size, page_numbers)
            self.pool = pool
            self.tag = "All"
        
        async def display_page(self):
            async with self.pool.acquire() as conn:
                if self.tag == "All":
                    req = await conn.execute(f"""SELECT * FROM shop
                                                WHERE price IS NOT NULL AND sell_price IS NOT NULL
                                                ORDER BY price ASC
                                                LIMIT ? OFFSET ?""", (self.page_size, (self.page - 1) * self.page_size))
                else:
                    req = await conn.execute(f"""SELECT * FROM shop WHERE tags LIKE '%{self.tag}%'
                                                AND price IS NOT NULL AND sell_price IS NOT NULL
                                                ORDER BY price ASC
                                                LIMIT ? OFFSET ?""", (self.page_size, (self.page - 1) * self.page_size))

                rows = await req.fetchall()

                embed = discord.Embed(
                    title = "Items in the Shop",
                    description = None,
                    color = discord.Color.blue()
                )

                sep = '<:separator:1206287822558986281>'

                for row in rows:
                    price = f"{row['price']:,}" if row['price'] else "None"
                    sell_price = f"{row['sell_price']:,}" if row['sell_price'] else "None"

                    embed.add_field(
                        name = f"{row['name']}  {row['emoji']}",
                        value = f"{row['description']}\n{sep} Price: `☾ {price}`\n {sep} Sell Price: `☾ {sell_price}`\n\
                                {sep} Tags: `{row['tags']}`\n{sep} Keywords: {', '.join([f'`{kw}`' for kw in row['keywords'].split(', ')])}\nㅤ",
                        inline = False
                    )
                    
                await self.message.edit(embed = embed, view = self)

class ShopSelect(ui.Select):
    def __init__(self):
        options_data = [
            ("All", "Show all of the items you can buy in the shop."),
            ("Consumable", "Show all items that can be consumed."),
            ("Item", "Show items with no distinct purpose that only serve as collectables."),
            ("Openable", "Show all of the items that can be opened."),
            ("Usable", "Show items that can be used with the \"use\" command."),
            ("Powerup", "Show items that give special effects when used with the \"use\" command.")
        ]
        self.reverse_options = {desc: name for name, desc in options_data}
        options = [discord.SelectOption(label = name, value = desc) for name, desc in options_data]

        super().__init__(options = options, min_values = 1, max_values = 1, placeholder = "Search for items by their tag.")
    
    async def callback(self, interaction: Interaction):
        self.view.page = 1
        self.view.tag = self.reverse_options[self.values[0]]

        async with self.view.pool.acquire() as conn:
            req = await conn.execute("SELECT * FROM shop WHERE tags = ?", (self.view.tag,))
            self.view.page_count = calc_page_num(len(await req.fetchall()), self.view.page_size)

        await self.view.display_page()
        await interaction.response.defer()

class InventoryView(BasicPaginator):
    def __init__(self, user: discord.Member, page_size: int, page_numbers: int, pool, target_user):
        super().__init__(user, page_size, page_numbers)
        self.pool = pool
        self.target_user = target_user

    async def display_page(self) -> None:
        async with self.pool.acquire() as conn:
            req = await conn.execute("""SELECT shop.name, inventory.quantity, shop.emoji FROM inventory 
                                        INNER JOIN shop USING (item_id) WHERE inventory.user_id = ?
                                        LIMIT ? OFFSET ?""", (self.target_user.id, self.page_size, (self.page - 1) * self.page_size))
            
            inv = "\n".join([f"{emoji} — {quantity}x {item}" for item, quantity, emoji in await req.fetchall()])

            await self.message.edit(view = self, embed = discord.Embed(title = f"{self.target_user.name}'s Inventory", description = inv, color = discord.Color.dark_embed()))

# coin symbol is ☾

class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.pool
        self.cooldowns.start()

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandOnCooldown):
            command_aliases = {
                'rob': f"To protect the fictional city of I-haven't-come-up-with-a-name-yet, robbing has been limited to once every 5 minutes. You can rob someone again in **{readable_time(error.retry_after)}**",
                'bankrob': f"To protect the fictional city of I-haven't-come-up-with-a-name-yet, bankrobbing has been limited to once every 15 minutes. You can rob someone again in **{readable_time(error.retry_after)}**",
                'balance': f"You can check your balance again in **{readable_time(int(error.retry_after))}**"
            }

            if ctx.command.name in command_aliases.keys():
                await ctx.reply(command_aliases[ctx.command.name])
            else:
                await ctx.reply(f"you can {ctx.command.name} in **{readable_time(int(error.retry_after))}**")

        else:
            ctx.command.reset_cooldown(ctx)
            raise error

    async def getprice(self, item: str):
        async with self.pool.acquire() as conn:
            req = await conn.execute(f"SELECT price, sell_price FROM shop WHERE name = ?", (item,))
            row = await req.fetchone()
            return row['price'] or row['sell_price']
    
    async def getitemsworth(self, user_id):
        async with self.pool.acquire() as conn:
            req = await conn.execute("""SELECT shop.name, inventory.quantity FROM inventory
                                        INNER JOIN shop USING (item_id)
                                        WHERE inventory.user_id = ?""", (user_id,))
            inv = await req.fetchall()

            return sum([await self.getprice(item) * quantity for item, quantity in inv if await self.getprice(item)])

    @commands.command(name = "shop", help = "See what's in the shop.")
    async def shop(self, ctx):
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT * FROM shop WHERE price IS NOT NULL")
            pages = calc_page_num(len(await req.fetchall()), 3)

        view = ShopView(ctx.author, 3, pages, self.pool)
        view.add_item(ShopSelect())

        view.message = await ctx.reply(
            embed = discord.Embed(
                title = "Hold on...",
                description = "We're working on it.",
                color = discord.Color.red()
            )
        )
        await view.display_page()
    
    @commands.command(name = "jobs")
    async def jobs(self, ctx):
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT * FROM discord WHERE user_id = ?", (ctx.author.id,))
            if not await req.fetchone():
                await ctx.reply("You don't have a bank account. Make one with `as bal`  :moneybag: :x:")

            req = await conn.execute("SELECT * FROM jobs")
            page_size = 3

            pages = calc_page_num(len(await req.fetchall()), page_size)

        view = ChooseAJobView(ctx.author, page_size, pages, self.pool)

        view.message = await ctx.reply(
            embed = discord.Embed(
                title = "Hold on...",
                description = "We're working on it.",
                color = discord.Color.red()
            )
        )
        await view.display_page()
    
    @commands.command(name = "work")
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def work(self, ctx, resign: str = None):
        from datetime import datetime, timedelta
        person = ctx.author.id

        async with self.pool.acquire() as conn:
            req = await conn.execute('SELECT ending_at FROM cooldowns WHERE user_id = ? AND name = "work"', (person,))
            row = await req.fetchone()
            
            if row:
                await ctx.reply(f"Woops! Looks like you resigned from your job. Come back in <t:{row['ending_at']}:R> and you can start work again!")

            req = await conn.execute("SELECT occupation FROM discord WHERE user_id = ?", (person,))
            row = await req.fetchone()
            occupation = row['occupation']

            if not occupation:
                await ctx.reply("You need to choose a job. Choose one with `as jobs`")
                ctx.command.reset_cooldown(ctx)
                return

            if resign == "resign":
                req = await conn.execute("SELECT occupation FROM discord WHERE user_id = ?", (person,))
                row = await req.fetchone()

                if row['occupation']:
                    await conn.execute("UPDATE discord SET occupation = NULL WHERE user_id = ?", (person,))

                    await conn.execute("INSERT INTO cooldowns VALUES (?, ?, ?)", 
                                       ("work", person, datetime.timestamp(datetime.now() + timedelta(hours = 3))))

                    await ctx.reply(f"You have now resigned from your job as **{row['occupation']}**. You have to wait 2 hours until you can start work again at a new job.")

                    if self.cooldowns.is_running():
                        self.cooldowns.restart()
                    else:
                        self.cooldowns.start()

            req = await conn.execute("SELECT salary FROM jobs WHERE job = ?", (occupation))
            row = await req.fetchone()
        
        n = 'n' if occupation[0].lower() in ['a', 'e', 'i', 'o', 'u'] else ''
        reward = int(row['salary'] * random.randint(90, 110) / 100)
        await ctx.reply(f"You got `☾ {reward:,}` from working as a{n} {occupation}.")

        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (reward, person))
    
    @tasks.loop()
    async def cooldowns(self):
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT * FROM cooldowns ORDER BY ending_at ASC LIMIT 1")
            row = await req.fetchone()

        if not row:
            self.cooldowns.cancel()
            return

        from datetime import datetime
        await discord.utils.sleep_until(datetime.fromtimestamp(row['ending_at']))
        
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM cooldowns WHERE name = ? AND user_id = ?", (row['name'], row['user_id']))

    @commands.command(name = 'rob', cooldown_after_parsing = True, help = "Rob another user.\n\nThis requires you to have minimum `☾ 500` and there's no teaming. You get prompted with a confirmation screen combined with the percentage of succeeding and from there, you can decide whether you want to do the robbery.\n\nQuitting will not reset the cooldown.")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def rob(self, ctx, user: discord.Member = None):
        if not user:
            await ctx.reply("Shh, you're gonna get us caught!")
            ctx.command.reset_cooldown(ctx)
            return

        if not await Minigames(self.bot).check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT wallet, bank FROM discord WHERE user_id = ?", (ctx.author.id,))
            row = await req.fetchone()
            robber = sum(list(row))

            if row['wallet'] < 500:
                await ctx.reply("You need at least ☾ 500 in your own wallet to rob people.")
                ctx.command.reset_cooldown(ctx)
                return

            req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (user.id,))
            row = await req.fetchone()
            being_robbed = row['wallet']
        
        if being_robbed == 0:
            await ctx.reply("that person has no money in their wallet lol")
            ctx.command.reset_cooldown(ctx)
            return
        
        P_fail = robber / (robber + being_robbed)

        view = RobView(ctx.author)
        view.message = await ctx.send(embed = discord.Embed(
            title = f"Are you sure you want to steal from {user.name}?",
            description = f"You have a **{int((1 - P_fail)*100)}%** of succeeding. Are you sure it's worth it?",
            color = discord.Color.yellow()
        ), view = view)

        await view.wait()

        if not view.value:
            return
        
        await view.message.delete()

        if random.random() > P_fail: # if they succeed
            if random.randint(1, 100) < 6:
                stolen = int(being_robbed)
            else:
                stolen = int(being_robbed * (1 - P_fail))

            embed = discord.Embed(
                title = "Success!",
                description = f"You got away with `☾ {stolen}` from {user.name}'s wallet. Don't let them catch you! <a:flyingmoney:1206668664133255209>",
                color = discord.Color.green()
            )
            embed.set_footer(text = "(I made a deposit feature for a reason)")
            await ctx.send(embed = embed)

            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = wallet - ? WHERE user_id = ?", (stolen, user.id))
                await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (stolen, ctx.author.id))
        
            dm = await user.create_dm()
            await dm.send(f"You _might_ wanna check your bank balance. Quite a bit is missing :grimacing:\n\n{ctx.author.name} stole `☾ {stolen}` from your wallet, so I advise you get them back for it tonight!")
        else:
            embed = discord.Embed(
                title = "You had one job...",
                description = "Welp, looks like you got caught and fined by the police <:woeisme:1202950900604211220>\n\nMaybe `as crime` is a better way to earn money?",
                color = discord.Color.red()
            )
            embed.set_footer(text = "How did you manage to screw this up?")
            await ctx.send(embed = embed)

            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = wallet - 500 WHERE user_id = ?", (user.id))

            dm = await user.create_dm()
            await dm.send("Phew! Looks like someone nearly stole your money. Deposit it with `as dep all` so that doesn't happen again!")
    
    def generate_bankrob_variation(self, N, upper):
        values = [random.randint(0, 10) for _ in range(N)]

        while sum(values) != upper:
            values = [random.randint(0, int(upper/N + 15)) for _ in range(N)]

        return values

    @commands.command(name = "bankrob", help = "Bankrob another user.\n\nKeep in mind, the person will be alerted to your robbery and there's a button for them to cancel it. If they cancel it, everyone involved loses 1k.\n\nYou need 1k to start and join a robbery.")
    @commands.cooldown(1, 900, commands.BucketType.user)
    async def bankrob(self, ctx, user: discord.Member = None):
        if not user:
            await ctx.reply("Shh, this is a serious robbery and you nearly blew it! :shushing_face: :ninja_tone5:")
            ctx.command.reset_cooldown(ctx)
            return
    
        if not await Minigames(self.bot).check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            return

        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (ctx.author.id,))
            row = await req.fetchone()
            if row['wallet'] < 1000:
                await ctx.reply("You need at least ☾ 1000 to start a bank robbery... aaaaand you blew your cover.")
                ctx.command.reset_cooldown(ctx)
                return

            req = await conn.execute("SELECT bank FROM discord WHERE user_id = ?", (user.id,))
            row = await req.fetchone()
            being_robbed = row['bank']

            if being_robbed < 3500:
                await ctx.reply("That person's too poor for a bank robbery. Aim higher!")
                ctx.command.reset_cooldown(ctx)
                return

        embed = discord.Embed(
            title = "Join Heist",
            description = f"Click the green button below to hop into a heist with {ctx.author.mention}. Who knows? Maybe you'll get some quick cash!",
            color = discord.Color.green()
        )

        view = BankrobLobby(ctx.author, being_robbed = user, pool = self.pool)
        view.message = await ctx.reply(view = view, embed = embed)

        dm = await user.create_dm()
        await dm.send(content = f"Someone's trying to rob you: https://discord.com/channels/{view.message.guild.id}/{view.message.channel.id}/{view.message.id}")

        try:
            await asyncio.wait_for(view.wait(), timeout = 30)
        except:
            if not view.is_robbery_commencing:
                ctx.command.reset_cooldown(ctx)
                await view.message.edit(
                    view = view,
                    embed = discord.Embed(
                        title = "Woops!",
                        description = "Looks like the robbery isn't commencing. You didn't have enough people in your lobby to successfully crack open the vault. Better luck next time!",
                        color = discord.Color.red()
                    )
                )
                return
            
            async with self.pool.acquire() as conn:
                holder = ', '.join(['?' for _, _ in enumerate(view.robbers)])
                req = await conn.execute(f"SELECT wallet FROM discord WHERE user_id IN ({holder})", tuple([r.id for r in view.robbers]))
                robbers_wallets = [row['wallet'] for row in await req.fetchall()]
                
            robbery_alert = await ctx.send("The robbery is commencing.")
            await asyncio.sleep(5)

            P_success = (1 - sum(robbers_wallets) / (sum(robbers_wallets) + being_robbed)) * 100
                
            if random.random() < P_success:
                bankrob_variation = self.generate_bankrob_variation(len(view.robbers), random.randint(50, 100))

                for i, variety in enumerate(bankrob_variation):
                    view.robbers[i] = (view.robbers[i], int(being_robbed * variety/100))

                lost_money = sum([x[1] for x in view.robbers])

                async with self.pool.acquire() as conn:
                    await conn.execute("UPDATE discord SET bank = bank - ? WHERE user_id = ?", (lost_money, user.id))
                
                from num2words import num2words
                embed = discord.Embed(
                    title = "Successful Bank Robbery!",
                    description = f"Looks like you {num2words(len(view.robbers))} managed to pull it off! Give yourselves a pat on the back. Not many got as far as you did.\n\nLet's take a look at the earnings: ```" + "".join([f"\n{robber.name} got away with ☾ {payout:,}" for robber, payout in view.robbers]) + f"```\nThat's a collective `☾ {lost_money}` stolen from {user.mention} so well done!",
                    color = discord.Color.green()
                )
                await robbery_alert.reply(embed = embed)

                async with self.pool.acquire() as conn:
                    for robber, payout in view.robbers:
                        await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (payout, robber.id))

                person_robbed_dm = await user.create_dm()
                new_view = ui.View()
                new_view.add_item(ShowPlayersButton([x[0] for x in view.robbers]))

                await person_robbed_dm.send(
                    embed = discord.Embed(
                        title = "You got robbed!",
                        description = f"A gang of players cracked into your vault and got away with `☾ {lost_money}` from your bank account! Me personally...",
                        color = discord.Color.red()
                    ), view = new_view
                )
            else:
                losses = []
                async with self.pool.acquire() as conn:
                    for robber in view.robbers:
                        await conn.execute("UPDATE discord SET wallet = wallet - 1000 WHERE user_id = ?", (robber.id,))
                        loss = random.randint(50, 100)

                        req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (robber.id,))
                        row = await req.fetchone()

                        losses.append((robber, int(row[0] * (1 + loss/100))))

                        await conn.execute("UPDATE discord SET wallet = wallet - ? WHERE user_id = ?", (int(row[0] * (1 + loss/100)), robber.id))
                        
                    fined_money = sum([x[1] for x in losses])
                    await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (fined_money, user.id))

                person_being_robbed_dm = await user.create_dm()
                await person_being_robbed_dm.send(
                    embed = discord.Embed(
                        title = "Woah, looks like you nearly got robbed.",
                        description = f"This is probably a sign to take good care of your earnings, or invest them into some non-robbable items. But hey, at least they got caught and paid you a collective total of `☾ {fined_money}` so every cloud has a silver lining, yk.",
                        color = discord.Color.green()
                    )
                )
                        
                await ctx.send(
                    embed = discord.Embed(
                        title = "You fucked up the robbery!",
                        description = f"How, how, how did you mess this up?? You knew you had a **{P_success}%** chance of success. You know how to do probability, and you STILL chose to bankrob them?\n\nNow you have to pay {user.mention} each all your money. <:pointandlaugh:1205232587736485888>\nI hope this teaches you a lesson. God, I'm surrounded by morons.\n" + "\n".join([f"{robber.mention} got fined `☾ {payout}`" for robber, payout in losses]) + f"\n\nAltogether, you lost `☾ {fined_money}` so I hope you idiots are proud of yourselves.",
                        color = discord.Color.brand_red()
                    )
                )
    
    @commands.command(name = 'inventory', aliases = ['inv', 'items'], help = "See what's in your inventory.")
    async def inventory(self, ctx, user: discord.Member = None):
        if not user:
            req_id = ctx.author.id
            invuser = ctx.author
        else:
            req_id = user.id
            invuser = user

        if not await Minigames(self.bot).check_for_account(req_id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT * FROM inventory WHERE user_id = ?", (ctx.author.id,))

        view = InventoryView(ctx.author, 15, calc_page_num(len(await req.fetchall()), 15), pool = self.pool, target_user = invuser)

        invembed = discord.Embed(color = discord.Color.dark_embed())
        invembed.set_author(name = f"{invuser.name}'s Inventory", icon_url = invuser.avatar)
        
        view.message = await ctx.reply(embed = invembed, view = view)
        await view.display_page()

    @commands.command(name = 'view', help = "View any items in the shop.")
    async def seeitemdetails(self, ctx, *, query):
        if query == "None":
            await ctx.reply("Oh so you think you're smart?")
            return

        async with self.pool.acquire() as conn:
            req = await conn.execute(f"SELECT * FROM shop WHERE (keywords) LIKE '%{query}%' OR (name) LIKE '%{query}%'")
            row = await req.fetchone()
        
            if not row:
                await ctx.reply("That's not an item. Check `as shop` to see what you can look at.")
                return
            
        price = f"{row['price']:,}" if row['price'] else 'None'
        sell_price = f"{row['sell_price']:,}" if row['price'] else 'None'

        embed = discord.Embed(
            title = None,
            description = f"""{row['description']}  {row['emoji']}\n
                            Price: `☾ {price}`\nSell price: `☾ {sell_price}`\nTags: `{row['tags']}`\nKeywords: `{row['keywords']}`""",
            color = discord.Color.green()
        )
        embed.set_author(name = f"{row['name']}")

        await ctx.reply(embed = embed)
                

    @commands.command(name = 'buy', cooldown_after_parsing = True, help = "Buy items from the shop!")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def buy(self, ctx, quantity: int = None, *, item: str = None):  
        if not await Minigames(self.bot).check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            return

        async with self.pool.acquire() as conn:
            req = await conn.execute(f"SELECT * FROM shop WHERE (keywords) LIKE '%{item}%' OR name LIKE '%{item}%'")
            row = await req.fetchone()

            if not row:
                await ctx.reply("That's not an item. Check `as shop` to see what you can look at.")
                ctx.command.reset_cooldown(ctx)
                return
            
            if not row['price']:
                await ctx.reply("That item cannot be bought.")
                return

            price = row['price'] * quantity

            req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (ctx.author.id))
            wallet_row = await req.fetchone()
            wallet = wallet_row['wallet']
            
            if price > wallet:
                await ctx.reply("not enough money bozo")
                ctx.command.reset_cooldown(ctx)
                return
            
            view = BuyView(ctx.author)
            view.message = await ctx.reply(
                embed = discord.Embed(
                    title = "Pending Purchance",
                    description = f"""You have requested to buy `{quantity}x {row['name']}`.
                                      This will cost `☾ {price:,}`, and leave you with `☾ {int(wallet - price):,}`.
                    
                                      Are you sure you want to buy this?""",
                    color = discord.Color.dark_embed()
                ), view = view)
            
            await view.wait()

            if view.value:
                await conn.execute(f"""INSERT INTO inventory VALUES (?, ?, ?, ?)
                                       ON CONFLICT(item_id, user_id) DO UPDATE
                                       SET quantity = quantity + excluded.quantity
                                    """, (row['item_id'], ctx.author.id, quantity, None))
                
                await conn.execute("UPDATE discord SET wallet = wallet - ? WHERE user_id = ?", (price, ctx.author.id))

                await view.message.edit(
                    embed = discord.Embed(
                        title = "Purchase Completed",
                        description = f"Successfully purchased **{quantity}x {row['name']}** for `☾ {price:,}`\n\nEnjoy your new items!",
                        color = discord.Color.green()
                    )
                )

    @commands.command(name = 'sell', aliases = ['s'], help = "Sell your items!")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def sell(self, ctx, quantity: int = None, *, item: str = None):
        if not await Minigames(self.bot).check_for_account(ctx.author.id):
            await ctx.reply("You need an account to sell stuff. Make one with `as bal`")
            return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute(f"SELECT * FROM shop WHERE (keywords) LIKE '%{item}%' OR name LIKE '%{item}%'")
            row = await req.fetchone()

            if not row:
                await ctx.reply("That's not an item. Check `as shop` to see what you can look at.")
                ctx.command.reset_cooldown(ctx)
                return
            
            req = await conn.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (ctx.author.id, row['item_id']))
            quantityrow = await req.fetchone()
            quan = quantityrow['quantity']
            
            if quan < quantity:
                await ctx.reply("You don't have that many of that item!")
                return
            
            if not row['sell_price']:
                await ctx.reply("That item cannot be sold. Looks like you're stuck with it!")
                return

            price = int(row['sell_price'] * quantity)
            
        view = SellView(ctx.author)

        view.message = await ctx.reply(
            view = view,
            embed = discord.Embed(
                title = "Comfirm selling?",
                description = f"Are you sure you want to sell **{quantity}x {row['name']}?**\nYou will get `☾ {price:,}` from selling these items.",
                color = discord.Color.dark_embed()
            )
        )
        await view.wait()

        if not view.value:
            return
        
        async with self.pool.acquire() as conn:
            if quan == quantity:
                await conn.execute("DELETE FROM inventory WHERE item_id = ? AND user_id = ?", (row['item_id'], ctx.author.id))
            else:
                await conn.execute("UPDATE inventory SET quantity = quantity - ? WHERE item_id = ? AND user_id = ?", (quantity, row['item_id'], ctx.author.id))
            
            await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (price, ctx.author.id))

        await view.message.edit(
            view = view,
            embed = discord.Embed(
                title = "Sold your items!",
                description = f"You have sold **{quantity}x {row['name']}** for `☾ {price}`. Enjoy your new money!",
                color = discord.Color.green()
            )
        )
            
        
    @commands.command(name = 'balance', aliases = ['bal'], help = "Check your balance!")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def balance(self, ctx, user: discord.Member = None):
        async with self.pool.acquire() as conn:
            if user:
                request_user = user
                request_name = user.name
            else:
                request_user = ctx.author
                request_name = ctx.author.name

            req = await conn.execute(f"SELECT * FROM discord WHERE user_id = ?", (request_user.id))
            row = await req.fetchone()
            
            if row:
                wallet = row['wallet']
                bank = row['bank']

                moneyEmbed = discord.Embed(
                    title = None,
                    description = None,
                    color = 0x2c2f33,
                )
                moneyEmbed.add_field(
                    name = "Wallet",
                    value = f"☾ {wallet:,}",
                    inline = True
                )
                moneyEmbed.add_field(
                    name = "Bank",
                    value = f"☾ {bank:,}",
                    inline = True
                )
                moneyEmbed.add_field(
                    name = "Net",
                    value = f"☾ {(wallet + bank + await self.getitemsworth(request_user.id)):,}",
                    inline = True   
                )
                moneyEmbed.set_author(name = f"{request_name}'s Balance", icon_url = request_user.avatar)
                await ctx.reply(embed = moneyEmbed)
            else:
                async with self.pool.acquire() as conn:
                    await ctx.reply("no bank account, broke boy. i'll make one for you.  :moneybag: :white_check_mark:")
                    await conn.execute("INSERT INTO discord VALUES (?, ?, ?, ?, ?)",
                                       (request_user.id, 0, 0, 0, None))
    
    @commands.command(name = "deposit", aliases = ['dep'], help = "Deposit your money.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def deposit(self, ctx, amount: int | str):
        if not await Minigames(self.bot).check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            return

        async with self.pool.acquire() as conn:
            request = await conn.execute(f"SELECT * FROM discord WHERE user_id = ?", (ctx.author.id,))
            row = await request.fetchone()
            
            if row:
                new_wallet, new_bank = None, None

                wallet = row['wallet']
                bank = row['bank']

                if type(amount) == str:                    
                    if ',' in amount:
                        amount = amount.translate(string.maketrans(",", ""))
                    
                    elif amount[-1] == 'k':
                        amount = float(amount[:-1]) * 10**3
                    
                    elif amount[-1] == 'm':
                        amount = float(amount[:-1]) * 10**6
                    
                    elif amount == "all":
                        new_wallet = 0
                        new_bank = wallet
                        amount = wallet
                    else:
                        await ctx.reply("its `all` or nothing buddy")
                
                amount = int(amount)
                
                if type(amount) == int:
                    if amount <= wallet:
                        new_wallet = wallet - amount
                        new_bank = bank + amount
                    else:
                        await ctx.reply("you wish you could deposit that much")
                
                if type(new_wallet) is int and type(new_bank) is int:
                    await conn.execute(f"UPDATE discord SET wallet = ?, bank = ? WHERE user_id = ?",
                                       (new_wallet, new_bank, ctx.author.id))
                    await ctx.reply(f"Deposited ☾ {amount:,} into your bank.")

    @commands.command(name = "withdraw", aliases = ['with'], help = "Withdraw your money.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def withdraw(self, ctx, amount: int | str):
        if not await Minigames(self.bot).check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute(f"SELECT * FROM discord WHERE user_id = ?", (ctx.author.id,))
            row = await req.fetchone()
            
            if row:
                wallet = row['wallet']
                bank = row['bank']

                if type(amount) == str:                    
                    if ',' in amount:
                        amount = amount.translate(string.maketrans(",", ""))
                    
                    elif amount[-1] == 'k':
                        amount = float(amount[:-1]) * 10**3
                    
                    elif amount[-1] == 'm':
                        amount = float(amount[:-1]) * 10**6
                    
                    elif amount == "all":
                        new_wallet = bank
                        new_bank = 0
                        amount = bank
                    else:
                        await ctx.reply("it's `all` or nothing buddy")
                
                amount = int(amount)
                
                new_wallet, new_bank = None, None
                
                if type(amount) == int:
                    if amount <= bank:
                        new_wallet = wallet + amount
                        new_bank = bank - amount
                    else:
                        await ctx.reply("can't withdraw what you don't have. that's called **cheating**")
                
                if type(new_wallet) is int and type(new_bank) is int:
                    await conn.execute(f"UPDATE discord SET wallet = ?, bank = ? WHERE user_id = ?",
                                       (new_wallet, new_bank, ctx.author.id))
                    await ctx.reply(f"Withdrawn ☾ {amount:,} from your bank.")

    @commands.command(name = 'beg', help = "Beg for money like the worthless homeless person you are.")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def beg(self, ctx):
        if not await Minigames(self.bot).check_for_account(ctx.author.id):
            await ctx.reply("You don't have a cup for strangers to put money in. Get one with `as bal`")
            ctx.command.reset_cooldown(ctx)
            return

        decisions = [
            "An old man let you have his last _",
            "A few teenagers pelt you with _ You got bruises, but it's still _",
            "Jay-Z passed and gave you _",
            "You feel asleep and woke up to _ in your cup.",
            "Oh hey! Look! _!",
            "A charity found you in need enough to give you _",
            "I don't even know how you got _",
            "Simon Griggs gave you _ worth of cartel money",
            "Simon Griggs gave you a pair of Jordan 4s which you sell online to get _",
            "Your grandmother left you _ in her will.",
            "Epstein took you to his private island and gave you _ in exchange for some saucy activities. Profit!",
            "You found the One Piece and found a treasure chest full of _.",
            "Jin paid you for head and in exchange for him getting his nut off, you got _. Money is money!",
            "Jaden gave you a certain someone's spicy pics and you paid him _ to get your nut off. Was it really worth it?",
            "A pack of pigeons search the streets of London and bring you back a lovely gift of _ in notes. Well done birds!"
        ]
        if random.randint(1, 10) < 9: # 80% chance
            reward = random.randint(50, 500)
            rewardxp = random.randint(1, 15)

            begEmbed = discord.Embed(
                title = "You got something!",
                description = random.choice(decisions).replace('_', f"`☾ {reward}`") + \
                            f"\nLooks like you also got **{rewardxp}** <a:xp:1206668715710742568>",
                color = discord.Color.green()
            )

            async with self.pool.acquire() as conn:
                req = await conn.execute("SELECT xp FROM discord WHERE user_id = ?", (ctx.author.id,))
                row = await req.fetchone()
                old_xp = row['xp']

                levels = Levels(bot = self.bot)
                await levels.on_level_up(ctx, old_xp, old_xp + rewardxp)
                
                request = await conn.execute(f"SELECT * FROM discord WHERE user_id = ?", (ctx.author.id,))
                row = await request.fetchone()

                if row:
                    await conn.execute(f"UPDATE discord SET wallet = wallet + ?, xp = xp + ? WHERE user_id = ?",
                                       (reward, rewardxp, ctx.author.id))
                    await ctx.reply(embed = begEmbed)
        else:
            decisions = [
                "You asked for money and a girl threw a drink in your face. \"Ew, freak!\"",
                "Someone kicked your cup across the street. You carefully get back all the coins and go back to sleep.",
                "You plead with a group of teens and they laugh in your face.",
                "\"Sorry man, I only have card.\"",
                "\"No spare change. Sorry buddy.\"",
                "\"Get a job, junkie!\"",
                "People pass by and insult you. Another day with no tips.",
                "At that point, just rob another player, smh.",
                "Mr Banham confiscated your phone so you earnt nothing.",
                "You tripped and ate shit while asking for money from someone. Embarrassing!",
                "William yelled at you for not cleaning your smegma, but how can you? You're homeless!",
                "You pleaded for money but Jin just kept showing you videos of animals shitting. Useless.",
                "Zane has a piss kink. And he won't stop. Telling. You. No matter how much you ask for money, he keeps talking about piss.",
                "Jaden reported you to the office as a joke and they took what's left in your cup for you to get back at the end of the day."
            ]
            begEmbed = discord.Embed(
                title = "You got nothing!",
                description = random.choice(decisions),
                color = discord.Color.red()
            )
            await ctx.reply(embed = begEmbed)
        
    @commands.command(name = 'send', help = "Send money to other people!\n\nKeep in mind, this is a one-way transaction. Items will be added eventually, I dunno when.")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def send(self, ctx, amount: int | str = None, recipient: discord.Member = None):
        if not amount:
            await ctx.reply('You have to send something. Check `as help send` to see what to type.')
            ctx.command.reset_cooldown(ctx)
            return

        amount = str(amount)

        if type(amount) == str:
            if ',' in amount:
                amount = amount.translate(string.maketrans(",", ""))
                    
            if amount[-1] == 'k':
                amount = float(amount[:-1]) * 10**3
                        
            if amount[-1] == 'm':
                amount = float(amount[:-1]) * 10**6

        amount = int(amount)
            
        if not recipient:
            await ctx.reply("You gotta have someone to send money to. That's how it works. No friends? Shame.\n(Check `as help send` to see what to type)") 
            ctx.command.reset_cooldown(ctx)
            return
        
        async with self.pool.acquire() as conn:
            row1 = await conn.execute(f"SELECT * FROM discord WHERE user_id = ?", (ctx.author.id,))
            sender = await row1.fetchone()
            row2 = await conn.execute(f"SELECT * FROM discord WHERE user_id = ?", (recipient.id,))
            receiver = await row2.fetchone()

            if sender['wallet'] >= amount:
                sendview = SendView(ctx.author, recipient, amount)

                sendviewembed = discord.Embed(
                    title = "➡️ 💳  Someone wants to send some money!",
                    description = f"{recipient.mention}, do you wish to accept {ctx.author.mention}'s request to send you `☾ {amount:,}`?",
                    color = 0xffa500
                )
                sendviewembed.add_field(
                    name = ctx.author.name,
                    value = f"`☾ -{amount:,}`"
                )
                sendviewembed.add_field(
                    name = recipient.name,
                    value = f"`☾ +{amount:,}`"
                )

                sendview.message = await ctx.reply(
                    content = recipient.mention,
                    embed = sendviewembed,
                    view = sendview
                )
                await sendview.wait()
                    
                if not sendview.value:
                    await ctx.reply("Not enough money in wallet to send.")
                    ctx.command.reset_cooldown(ctx)
                    return


                await conn.execute(f"""UPDATE discord SET wallet = ? WHERE user_id = ?""",
                                       (sender['wallet'] - amount, ctx.author.id))
                        
                await conn.execute(f"""UPDATE discord SET wallet = ? WHERE user_id = ?""",
                                       (receiver['wallet'] + amount, recipient.id))

    @commands.command(name = 'baltop', aliases = ['top10', 'rich'], help = "Check the top 10 net worths in your server.\n\nIf no accounts are opened, you will be prompted with a message.")
    async def baltop(self, ctx):
        async with self.pool.acquire() as conn:
            req = await conn.execute("""SELECT user_id, wallet, bank FROM discord
                                        ORDER BY wallet + bank DESC LIMIT 10""")
            
            rows = await req.fetchall()

            if not rows:
                await ctx.reply("Looks like nobody here has an account. Shame.")
                return

            embed = discord.Embed(
                title = 'Highest Net Worth',
                description = "\n".join([f"**#{i+1}**  - <@{row['user_id']}> (`☾ {sum([row['wallet'], row['bank']]):,}`)" \
                                         for i, row in enumerate(rows)] + [f"**#{i+1}** - None" for i in range(len(rows), 10)]),
                color = discord.Color.green()
            )
            await ctx.reply(embed = embed)

    @commands.command(name = 'botbreaker', aliases = ['bb'], help = 'If you find a bug and report it to the owner, they will patch it and give you a limited-edition item called a Bot Breaker to thank you for your service.')  
    async def give_bot_breaker(self, ctx, user: discord.Member = None, quantity: int = 1):
        if ctx.author.id not in [672530816529596417, 566653183774949395]:
            await ctx.reply("you are not sigma owner.")
            return

        if not user:
            await ctx.reply("You're missing a user to give the _Bot Breaker_ to.")
            return
        
        if quantity < 1:
            await ctx.reply("Can only give at least 1 Bot Breaker. Can be more, no less though.")
            return
        
        view = BotBreakerView(ctx.author)
        view.message = await ctx.reply(
            view = view,
            embed = discord.Embed(
                title = "Are yous ure you want to run this?",
                description = f"Running this command will give {user.mention} a total of **{quantity}x Bot Breaker**. Are you sure you want to do this?",
                color = discord.Color.blue()
            )
        )
        await view.wait()

        if not view.value:
            return

        async with self.pool.acquire() as conn:
            await conn.execute("""INSERT INTO inventory VALUES (?, ?, ?, ?)
                                  ON CONFLICT(item_id, user_id) DO
                                  UPDATE SET quantity = quantity + excluded.quantity""", (21, user.id, quantity, None))
        
        await view.message.edit(
            view = view,
            embed = discord.Embed(
                title = "Confirmed Transfer",
                description = f"Check your inventory, {user.mention} - there's a special item waiting for you.",
                color = discord.Color.green()
            )
        )

    @commands.command(name = 'give')
    async def give(self, ctx, amount: str = 0, recipient: discord.Member = None):
        if ctx.author.id not in [672530816529596417, 566653183774949395]:
            await ctx.reply("you are not sigma owner.")
            return

        async with self.pool.acquire() as conn:
            if amount:
                if ',' in amount:
                    amount = amount.translate(string.maketrans(",", ""))
                    
                elif amount[-1] == 'k':
                    amount = float(amount[:-1]) * 10**3
                    
                elif amount[-1] == 'm':
                    amount = float(amount[:-1]) * 10**6
                
                try:
                    amount = int(amount)
                except ValueError:
                    await ctx.reply("Error with `amount`")
                    return
                
                if recipient:
                    req = await conn.execute(f"SELECT * FROM discord WHERE user_id = ?", (recipient.id,))
                    row = await req.fetchone()
                    if row:
                        new_bal = row['wallet'] + amount

                        await conn.execute(f"""UPDATE discord SET wallet = ? WHERE user_id = ?""",
                                           (new_bal, recipient.id))
                        await ctx.reply(f"Added ☾ {amount} to {recipient.mention}'s account.")
                    else:
                        await ctx.reply("Looks like they don't have an account :man_shrugging:")
                        await conn.execute("INSERT INTO discord VALUES (?, ?, ?, ?)", (recipient.id, 0, 0, 0))
                        await ctx.send(f"Now they do. {recipient.mention}, you're now a brokie!  :x: :moneybag:\nRun `as bal` to see your balance!")
                else:
                    req = await conn.execute(f"SELECT * FROM discord WHERE user_id = ?", (ctx.author.id,))
                    row = await req.fetchone()
                    if row:
                        new_bal = row['wallet'] + amount
                        await conn.execute(f"""UPDATE discord SET wallet = ? WHERE user_id = ?""",
                                           (new_bal, ctx.author.id))
                        
                        if '-' not in str(amount):
                            await ctx.reply(f"Added ☾ {int(amount):,} to your account.")
                        else:
                            await ctx.reply(f"Removed ☾ {int(abs(amount)):,} from your account.")
            else:
                await ctx.reply("what am i supposed to give :skull:")

    @commands.command(name = 'set')
    async def setbal(self, ctx, balance: str, recipient: discord.Member = None):
        if ctx.author.id not in [672530816529596417, 566653183774949395]:
            await ctx.reply("you are not sigma owner.")
            return

        if ',' in balance:
            balance = balance.translate(string.maketrans(",", ""))
                    
        elif balance[-1] == 'k':
            balance = float(balance[:-1]) * 10**3
                    
        elif balance[-1] == 'm':
            balance = float(balance[:-1]) * 10**6

        if not balance and balance != 0:
            await ctx.reply("what am i supposed to set the balance as :skull:")
            return
        
        try:
            balance = int(balance)
        except:
            await ctx.reply("Looks like there was an error with the `balance`")
            return

        if balance < 0:
            await ctx.reply(f"Cannot set balance to ☾ {balance}. Negatives are not allowed.")
            return
        
        async with self.pool.acquire() as conn:
            if recipient:
                requser = recipient
            else:
                requser = ctx.author
            
            await conn.execute(f"UPDATE discord SET wallet = ? WHERE user_id = ?", (balance, requser.id))
            await ctx.reply(f"Updated {requser.mention}'s balance to ☾ {balance}")

async def setup(bot):
    await bot.add_cog(Currency(bot = bot))