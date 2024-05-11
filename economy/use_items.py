import discord, sqlite3, datetime, asyncio, random, json
from discord import ui, Interaction, Button
from discord import ButtonStyle as BS
from discord.ext import commands, tasks

def readable_time(time_in_seconds: int):
    days, hours = divmod(time_in_seconds, 24*60**2)
    hours, mins = divmod(hours, 60**2)
    mins, secs = divmod(mins, 60)

    time_units = ['d', 'h', 'm', 's']

    converted_time = " ".join([f"{int(unit)}{time_units[i]}" for i, unit in enumerate([days, hours, mins, secs]) if unit])
    return converted_time

def time_reader(time):
    time = time.split(' ')
    accepted_time_formats = {
        's': 1,
        'm': 60,
        'h': 60**2,
        'd': 24*60**2
    }

    final_time_in_sec = sum([float(amount[:-1]) * accepted_time_formats[amount[-1]] for amount in time])
    
    return final_time_in_sec

def generate_loot(file_name: str, location: str) -> str | None:
    loot_tables = json.loads(open(f'./loot tables/{file_name}.json').read())

    try:
        loot_table = loot_tables[location] | {None: 100 - sum(list(loot_tables[location].values()))}
    except KeyError:
        return

    return random.choices(list(loot_table.keys()), weights = list(loot_table.values()), k = 1)[0]

def open_chest_loot(loot: str) -> str:
    try:
        quantity, item = loot.split('x ')
    except:
        return None
    else:
        quantity = quantity.split('-')
        return int(random.choice(quantity)), item

def get_loot_counts(loot_items: list[str], loot_emojis: list[str]):
    if loot_items == []:
        return ''
    
    loot_emojis = list(dict.fromkeys(loot_emojis))

    from collections import Counter
    counts = dict(sum(map(Counter, loot_items), start = Counter())).items()
    data = []
    
    data = "\n".join([f"{emoji}  {quantity}x {item}" for emoji, (item, quantity) in list(zip(loot_emojis, counts))])
    
    return data

class OpenView(ui.View):
    def __init__(self, user: discord.Member):
        super().__init__(timeout = 15)
        self.user = user
        self.value = False
    
    async def on_timeout(self):
        for item in self.children:
            item.style = BS.grey
            item.disabled = True
        
        await self.message.edit(
            view = self,
            embed = discord.Embed(
                title = "⏰  Timed out!",
                description = "Fetch me their souls.",
                color = discord.Color.red()
            )
        )

    @ui.button(label = "Yes", style = BS.green)
    async def confirm(self, interaction: Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("Open your own chests.", ephemeral = True)
            return
        
        for item in self.children:
            item.style = BS.grey
            item.disabled = True
        
        button.style = BS.green
        
        await interaction.response.edit_message(
            view = self,
            embed = discord.Embed(
                title = "Opening your chests!",
                description = "Let's get it. Good luck - you'll need it!",
                color = discord.Color.green()
            )
        )
        self.stop()

    @ui.button(label = "No", style = BS.red)
    async def cancel(self, interaction: Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("Open your own chests.", ephemeral = True)
            return
        
        for item in self.children:
            item.style = BS.grey
            item.disabled = True
        
        button.style = BS.red

        await interaction.response.edit_message(
            view = self,
            embed = discord.Embed(
                title = "Cancelling Opening",
                description = "I'll put the items away for you, so that you can open them later. You're welcome!",
                color = discord.Color.red()
            )
        )
        self.stop()

class CancelOpeningButton(ui.Button):
    def __init__(self, user):
        super().__init__(label = "Cancel", style = BS.red)
        self.value = False
        self.user = user

    async def callback(self, interaction: Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("Open your own crates.")
            return

        self.value = True
        self.disabled = True

        await interaction.response.edit_message(view = self.view)

class ConfirmMarriageView(ui.View):
    def __init__(self, user: discord.Member, other: discord.Member):
        super().__init__(timeout = 20)
        self.user = user
        self.other = other
        self.been_married = False
    
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
            item.style = BS.grey
        
        await self.message.edit(
            view = self,
            embed = discord.Embed(
                title = "⏰  Timed out!",
                description = "I guess they couldn't make their mind up in time. Now everyone's awkwardly exchanging glances as they wonder what happened to the wedding vows.",
                color = discord.Color.red()
            )
        )
    
    @ui.button(label = "Yes", style = BS.green)
    async def confirm(self, interaction: Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("Stop trying to ruin people's marriages. Get a life, loser.  <:pointandlaugh:1205232587736485888>", ephemeral = True)
            return

        for item in self.children:
            item.disabled = True

            if item.label == button.label:
                item.style = BS.green
            else:
                item.style = BS.grey

        await interaction.response.edit_message(
            view = self,
            embed = discord.Embed(
                title = "Confirmed",
                description = f"You now take {self.other.mention} as your beloved partner. Amen.",
                color = discord.Color.green()
            )
        )
        self.been_married = True

    @ui.button(label = "No", style = BS.red)
    async def cancel(self, interaction: Interaction, button: Button):
        for item in self.children:
            item.disabled = True

            if item.label == button.label:
                item.style = BS.red
            else:
                item.style = BS.grey

        if interaction.user not in [self.user, self.other]:
            await interaction.response.send_message("Stop trying to ruin people's marriages. Get a life, loser.  <:pointandlaugh:1205232587736485888>", ephemeral = True)
            return
        
        await interaction.response.edit_message(
            view = self,
            embed = discord.Embed(
                title = "Cancelled",
                description = f"You kinda just stand there awkwardly at the alter, trying not to stare at your horrifically ugly bride.",
                color = discord.Color.red()
            )
        )

class ConfirmDivorceView(ui.View):
    def __init__(self, user: discord.Member, other: discord.Member):
        super().__init__(timeout = 20)
        self.user = user
        self.other = other
        self.been_divorced = False
    
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
            item.style = BS.grey
        
        await self.message.edit(
            view = self,
            embed = discord.Embed(
                title = "⏰  Timed out!",
                description = "I guess they couldn't fill out the divorce papers properly because I didn't hear any answers. What a shame.",
                color = discord.Color.red()
            )
        )
    
    @ui.button(label = "Yes", style = BS.green)
    async def confirm(self, interaction: Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("Stop trying to fix people's marriages. Get a life, loser.  <:pointandlaugh:1205232587736485888>", ephemeral = True)
            return
        
        for item in self.children:
            item.disabled = True

            if item.label == button.label:
                item.style = BS.green
            else:
                item.style = BS.grey

        await interaction.response.edit_message(
            view = self,
            embed = discord.Embed(
                title = "Confirmed",
                description = f"You now divorce {self.other.mention} and take the kids.",
                color = discord.Color.green()
            )
        )
        self.been_divorced = True
        self.stop()

    @ui.button(label = "No", style = BS.red)
    async def cancel(self, interaction: Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("Stop trying to fix people's marriages. Get a life, loser.  <:pointandlaugh:1205232587736485888>", ephemeral = True)
            return
        
        for item in self.children:
            item.disabled = True

            if item.label == button.label:
                item.style = BS.red
            else:
                item.style = BS.grey
        
        await interaction.response.edit_message(
            view = self,
            embed = discord.Embed(
                title = "Cancelled Divorce",
                description = "You just stare awkwardly at the marriage councellor while trying to figure out how to explain your newfound feelings for your partner.",
                color = discord.Color.red()
            )
        )
        
        self.stop()


class UseItems(commands.Cog, name = "Use Items"):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.pool

    @commands.command(name = 'open', help = "Open your chests to see what's inside!")
    async def open(self, ctx, quantity: int = None, *, item: str = None):
        if not item:
            await ctx.reply("Nothing to open?")
            return
        
        if not quantity:
            await ctx.reply("You must've written something wrong. Try it again")
            return

        async with self.pool.acquire() as conn:
            req = await conn.execute(f"SELECT * FROM shop WHERE name LIKE '%{item}%' OR keywords LIKE '%{item}%'")
            row = await req.fetchone()

            if not row:
                await ctx.reply("That's not an item. Check `as shop` to see what you can get.")
                return
            
            if row['tags'] != 'Openable':
                await ctx.reply("That item can't be used with this command. Only items with the tag `Openable` can be used with this command. Hope that helps!")
                return
    
            req = await conn.execute("SELECT * FROM inventory WHERE item_id = ?", (row['item_id'],))
            id_row = await req.fetchone()

            if not row:
                await ctx.reply("You don't have that item.")
                return
            
            if id_row['quantity'] < quantity:
                await ctx.reply(f"You don't have **{quantity}** of **{row['name']}**")
                return
        
            what_to_open = row['name']
            WTO_emoji = row['emoji']
            
            opening_message = await ctx.reply(f"Opening your **{quantity}x {row['name']}**  <a:loading:1209630119157825606>")

            view = ui.View()
            view.add_item(CancelOpeningButton(ctx.author))

            total_loot = []
            loot_emojis = []

            await opening_message.edit(
                content = None,
                view = view,
                embed = discord.Embed(
                    title = f"{WTO_emoji} Loot Haul!",
                    description = get_loot_counts(total_loot, loot_emojis),
                    color = discord.Color.red()
                )
            )

            for _ in range(quantity):
                if view.children[0].value:
                    embed = discord.Embed(
                        title = f"{WTO_emoji} Loot Haul!",
                        description = get_loot_counts(total_loot, loot_emojis),
                        color = discord.Color.red()
                    )
                    embed.set_footer(text = 'Finished opening chests!')
                    opening_message.edit(embed = embed)
                    break

                if id_row['quantity'] == 1:
                    await conn.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ?", (ctx.author.id, id_row['item_id']))
                else:
                    await conn.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?", (ctx.author.id, id_row['item_id']))

                loot = open_chest_loot(generate_loot('openables', what_to_open))

                if not loot:
                    total_loot.append({'You got **nothing!**': 1})
                    loot_counts = get_loot_counts(total_loot, loot_emojis)

                    embed = discord.Embed(
                        title = f"{WTO_emoji} Loot Haul!",
                        description = loot_counts,
                        color = discord.Color.red()
                    )
                    embed.set_footer(text = "You got **nothing!**")
                    await opening_message.edit(embed = embed)

                    await asyncio.sleep(1)
                    continue

                amount, item = loot

                req = await conn.execute("SELECT * FROM shop WHERE name = ?", (item,))
                row = await req.fetchone()
                emoji = row['emoji'] if row else ''
                
                loot_emojis.append(emoji)
                total_loot.append({item: amount})

                embed = discord.Embed(
                    title = f"{WTO_emoji} Loot Haul!",
                    description = get_loot_counts(total_loot, loot_emojis),
                    color = discord.Color.red()
                )
                embed.set_footer(text = f"You got +{amount} {item}")

                await opening_message.edit(embed = embed)
                
                if item == "Kawaii Molotov":
                    uses_left = 3
                else:
                    uses_left = None

                await conn.execute(f"""INSERT INTO inventory VALUES (?, ?, ?, ?)
                                    ON CONFLICT(item_id, user_id) DO
                                    UPDATE SET quantity = quantity + excluded.quantity""",
                                    (row['item_id'], ctx.author.id, amount, uses_left))
                
                await asyncio.sleep(1)

        embed = discord.Embed(
            title = f"{WTO_emoji} Loot Haul!",
            description = get_loot_counts(total_loot, loot_emojis),
            color = discord.Color.green()
        )
        embed.set_footer(text = 'Finished opening chests!')
        await opening_message.edit(view = None, embed = embed)
    
    @commands.command(name = "marriage", help = "Check up on your marriage stats.")
    async def marriage(self, ctx, user: discord.Member = None):
        if not user:
            person = ctx.author
        else:
            person = user

        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT * FROM marriages WHERE user1 = ? OR user2 = ?", (person.id,) * 2)
            row = await req.fetchone()

            if not row:
                await ctx.reply(
                    embed = discord.Embed(
                        title = "You are not married.",
                        color = discord.Color.red()
                    )
                )
                return

            other = self.bot.get_user([_id for _id in list(row) if _id != person.id][0])
            
            await ctx.reply(
                embed = discord.Embed(
                    title = "Marriage",
                    description = f"{person.mention} is married to {other.mention}.",
                    color = discord.Color.green()
                )
            )

    @commands.command(name = 'marry', help = "Get wedded and be together, forever and ever.")
    async def marry(self, ctx, user: discord.Member = None):
        you = ctx.author

        if not user:
            await ctx.reply("Forever alone...")
            return
        
        async with self.pool.acquire() as conn:
            for person in [you, user]:
                req = await conn.execute("SELECT * FROM marriages WHERE user1 = ? OR user2 = ?", (you.id,) * 2)
                row = await req.fetchone()

                if row:
                    await ctx.reply(f"Looks like {person.mention} is already in a marriage. Awkwardddd...  :grimacing:")
                    return

                req = await conn.execute("SELECT * FROM inventory WHERE user_id = ? AND item_id = ?", (you.id, 45))
                row = await req.fetchone()
                
                if not row:
                    await ctx.reply("You need a wedding ring for this special occasion.")
                    return

                req = await conn.execute("SELECT ending_at FROM cooldowns WHERE name = 'marry' AND user_id = ?", (ctx.author.id,))
                row = await req.fetchone()

                if row:
                    await ctx.reply(
                        embed = discord.Embed(
                            title = "You already got married!",
                            description = f"You recently got married so as per the law (for some reason), you are not allowed a new girl for the next 7 days. Just the way it goes, y'know.\n\nYou can marry again <t:{row['ending_at']}:R>",
                            color = discord.Color.red()
                        )
                    )
                    return
            
        view = ConfirmMarriageView(you, user)
        view.message = await ctx.reply(
            view = view,
            embed = discord.Embed(
                title = "Confirm Marriage",
                description = f"{you.mention} says: \"I promise to cherish and support you, through joy and sorrow, for as long as we both shall live.\"\n\n{user.mention} says: \"I vow to stand by your side, to love and honor you, for all the days of my life.\"",
                color = discord.Color.dark_embed()
            )
        )
        await view.wait()

        if view.been_married:
            async with self.pool.acquire() as conn:
                from datetime import datetime, timedelta
                ending_at = datetime.timestamp(int(datetime.now()) + timedelta(days = 7))
                await conn.execute("INSERT INTO cooldowns VALUES (?, ?, ?)", ("marry", ctx.author.id, ending_at))

                await conn.execute("INSERT INTO marriages VALUES (?, ?)", tuple(sorted([you.id, user.id])))

                for person in [you.id, user.id]:
                    await conn.execute("""INSERT INTO inventory VALUES (?, ?, ?, ?)
                                          ON CONFLICT(item_id, user_id) DO
                                          UPDATE SET quantity = quantity + excluded.quantity""", (46, person, 1, "inf"))
    
    @commands.command(name = "divorce", aliases = ['div'], help = "Divorce your lover and get back the kids.")
    async def divorce(self, ctx):
        you = ctx.author
        
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT user1, user2 FROM marriages WHERE user1 = ? OR user2 = ?", (you.id,) * 2)
            row = await req.fetchone()

            other = self.bot.get_user([_id for _id in list(row) if _id != you.id][0])

            if not row:
                await ctx.reply("Fighting demons in your head, huh? You aren't married yet, pal.")
                return
            
            req = await conn.execute("SELECT ending_at FROM cooldowns WHERE name = 'divorce' AND user_id = ?", (ctx.author.id,))
            row = await req.fetchone()

            if row:
                await ctx.reply(
                    embed = discord.Embed(
                        title = "You already divorced.",
                        description = f"You can't divorce twice in 3 days. That's unfortunately the rules, my friend.\n\nYou can divorce again in <t:{row['ending_at']}:R>",
                        color = discord.Color.green()
                    )
                )
            
        view = ConfirmDivorceView(you, other)
        view.message = await ctx.reply(
            view = view,
            embed = discord.Embed(
                title = "Confirm Divorce",
                description = f"Do you want to divorce your wife or husband or whatever??",
                color = discord.Color.dark_embed()
            )
        )
        await view.wait()

        if view.been_divorced:
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM marriages WHERE user1 = ? AND user2 = ?", tuple(sorted([you.id, other.id])))
                from datetime import datetime, timedelta
                ending_at = datetime.timestamp(int(datetime.now()) + timedelta(days = 3))
                await conn.execute("INSERT INTO cooldowns VALUES (?, ?, ?)", ("divorce", ctx.author.id, ending_at))

    @commands.command(name = "use", help = "Use your items! Only works with the tags `Powerup` and `Usable`")
    async def use(self, ctx, quantity: int = None, *, item: str = None):
        if not item or type(quantity) is not int or not item or type(item) is not str:
            await ctx.reply("Something went wrong. Check `as help use` for more info on syntax.")
            return

        async with self.pool.acquire() as conn:
            req = await conn.execute(f"SELECT * FROM shop WHERE (keywords) LIKE '%{item}%' OR (name) LIKE '%{item.capitalize()}%'")
            row = await req.fetchone()

            req = await conn.execute("SELECT * FROM inventory WHERE item_id = ?", (row['item_id'],))
            quanrow = await req.fetchone()
            
        if not row:
            await ctx.reply("That's not an item. Check `as shop` to see what you can look at.")
            ctx.command.reset_cooldown(ctx)
            return
                
        if row['tags'] not in ["Usable", "Powerup"]:
            await ctx.reply("That item can't be used with this command. Pick a different item.")
            return
                
        if row['name'] == "Wad of Cash":
            await ctx.reply(f"Used **{quantity}x Wad of Cash** which has given you `☾ {(quantity * 5*10**4):,}`")

            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (quantity * 5*10**4, ctx.author.id))
                await conn.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ?", (ctx.author.id,))
                await conn.execute("DELETE FROM inventory WHERE quantity = 0")
                
            return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT item_id, quantity, uses_left FROM inventory WHERE item_id = ?", (row['item_id']))
            quanrow = await req.fetchone()

            if quanrow['quantity'] > 1:
                await conn.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ?", (ctx.author.id,))
            else:
                await conn.execute("DELETE FROM inventory WHERE item_id = ? AND user_id = ?", (row['item_id'], ctx.author.id))
        
            try:
                from datetime import datetime, timedelta

                await conn.execute("INSERT INTO using_items VALUES (?, ?, ?)", (row['item_id'], ctx.author.id,
                                    int(datetime.timestamp(datetime.now() + timedelta(seconds = time_reader(row['cooldown']))))))
                
            except sqlite3.IntegrityError:
                await ctx.reply("Looks like you're already using that item!")
                return

            await ctx.reply(f"You are now using **1x {row['name']}**")

            if self.use_up_items.is_running():
                self.use_up_items.restart()
            else:
                self.use_up_items.start()

    @commands.command(name = "in_use", aliases = ["using"], help = "Check what items you're using right now.")
    async def in_use(self, ctx):
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT item_id, ending_at FROM using_items WHERE user_id = ?", (ctx.author.id,))
            beingusedrows = await req.fetchall()

            item_ids = [row['item_id'] for row in beingusedrows]
            shoprows = []

            for item_id in item_ids:
                req = await conn.execute("SELECT * FROM shop WHERE item_id = ?", (item_id,))
                shoprows += await req.fetchall()
            
            from datetime import datetime

            data = [f" - {shoprow['name']}  `({readable_time(time_left['ending_at'] - datetime.timestamp(datetime.now()))})`" \
                        for time_left, shoprow in list(zip(beingusedrows, shoprows))]
            
            await ctx.reply(
                embed = discord.Embed(
                    title = "Items Being Used",
                    description = "\n".join(data) if len(data) > 0 else 'You are not using any items yet.',
                    color = discord.Color.blue()
                )
            )

    @tasks.loop()
    async def use_up_items(self):
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT * FROM using_items ORDER BY ending_at ASC LIMIT 1")
            row = await req.fetchone()
        
        if not row:
            self.use_up_items.cancel()
            return
            
        await discord.utils.sleep_until(datetime.datetime.fromtimestamp(row['ending_at']))
        
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM using_items WHERE ending_at = ?", (row['ending_at']))



async def setup(bot):
    await bot.add_cog(UseItems(bot))