import random, discord, asyncio, aiohttp, json, time
from discord.ext import commands
from paginators import BasicPaginator, calc_page_num
from discord import ui
from typing import Any

class InvalidInput(Exception):
    pass

def time_reader(time):
    time = time.split(' ')
    accepted_time_formats = {
        's': 1,
        'm': 60,
        'h': 60**2,
        'd': 24*60**2
    }

    try:
        final_time_in_sec = sum([float(amount[:-1]) * accepted_time_formats[amount[-1]] for amount in time])
    except ValueError:
        return InvalidInput
    
    return final_time_in_sec

def readable_time(time_in_seconds: int):
    days, hours = divmod(time_in_seconds, 24*60**2)
    hours, mins = divmod(hours, 60**2)
    mins, secs = divmod(mins, 60)

    time_units = ['d', 'h', 'm', 's']

    converted_time = " ".join([f"{int(unit)}{time_units[i]}" for i, unit in enumerate([days, hours, mins, secs]) if unit])
    
    if len(converted_time) == 0:
        return "0s"
    
    return converted_time

class VoteView(ui.View):
    def __init__(self, question: str, timeout: int):
        super().__init__(timeout = timeout)
        self.question = question
        self.voted_for = []
        self.voted_against = []

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title = "⏰  **Vote Closed!**",
            description = f"The vote has closed! Let's take a look at the vote results.",
            color = discord.Color.red()
        )
        embed.add_field(name = "Question", value = self.question)
        embed.add_field(name = "Voted For", value = f"**{len(self.voted_for)}** people voted in favour of the original question.", inline = False)
        embed.add_field(name = "Voted Against", value = f"**{len(self.voted_against)}** people voted against the original question.", inline = True)

        await self.message.edit(
            view = self,
            embed = embed
        )
    
    @ui.button(label = "Yes! (Votes: 0)", style = discord.ButtonStyle.green)
    async def vote_in_favour(self, interaction: discord.Interaction, button: discord.Button):
        if interaction.user.id in self.voted_for:
            await interaction.response.send_message("You already voted for this!", ephemeral = True)
            return

        elif interaction.user.id in self.voted_against:
            self.voted_against.remove(interaction.user)
            await interaction.response.send_message("Changing your vote to **in favour**.", ephemeral = True)

            L = list(button.label)
            L[-2] = str(int(L[-2]) + 1)

            button.label = "".join(L)

            L = list(self.children[0].label)
            L[-2] = str(int(L[-2]) - 1)

            self.children[1].label = "".join(L)

        else:
            self.voted_for.append(interaction.user.id)

            L = list(button.label)
            L[-2] = str(int(L[-2]) + 1)

            button.label = "".join(L)
        
        await self.message.edit(view = self)
        await interaction.response.defer()
    
    @ui.button(label = "No! (Votes: 0)", style = discord.ButtonStyle.red)
    async def vote_against(self, interaction: discord.Interaction, button: discord.Button):
        if interaction.user.id in self.voted_against:
            await interaction.response.send_message("You already voted for this!", ephemeral = True)
            return
        
        elif interaction.user.id in self.voted_for:
            self.voted_against.remove(interaction.user)
            await interaction.response.send_message("Changing your vote to **in favour**.", ephemeral = True)

            L = list(self.label)
            L[-2] = str(int(L[-2]) + 1)

            self.label = "".join(L)

            L = list(self.children[0].label)
            L[-2] = str(int(L[-2]) - 1)

            self.children[0].label = "".join(L)

        else:
            self.voted_for.append(interaction.user.id)

            L = list(button.label)
            L[-2] = str(int(L[-2]) + 1)

            button.label = "".join(L)
        
        await self.message.edit(view = self)
        await interaction.response.defer()


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.pool
        self.cogs = {
            'economy.minigames': ['m'],
            'economy.currency': ['c'],
            'economy.gamble': ['gamble', 'g'],
            'economy.levels': ['levels', 'l'],
            'economy.use_items': ['use', 'useitems'],
            'moderation': ['mod'],
            'utility': ['utils', 'u'],
            'help': []
        }
    
    @commands.Cog.listener('on_message')
    async def watch_out_for_spam(message: discord.Message):
        from thefuzz import fuzz

        if message.channel.id not in [1221873373106147328, 1221874267524829244]:
            return

        data = open('horrible_context.txt').read().split('|')
        
        for piece in data:
            if fuzz.partial_ratio(message.content, piece) > 30:
                await message.delete()
                await message.channel.send("Don't put those things in here.")


    @commands.command(name = 'dadjoke', aliases = ['dad'])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def dadjoke(self, ctx):
        msg = await ctx.reply("Hold on just a moment  <a:loading:1209630119157825606>")
        key = 'SQK2POXVPkZcgkOY8uWVyg==g0O3xnnMWOJZIW0r'

        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://api.api-ninjas.com/v1/dadjokes?limit=1') as request:
                response = request.json()

        await msg.edit(content = response['joke'])

    @commands.command(name = 'rizzquote', aliases = ['rizz', 'rq'], help = "Get a helpful hand at rizzing up some baddies.")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def rizzquote(self, ctx):
        msg = await ctx.reply("Hold on just a moment  <a:loading:1209630119157825606>")
        await asyncio.sleep(1)

        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT line FROM rizz")
            rows = [row['line'] for row in await req.fetchall()]
        
        await msg.edit(content = random.choice(rows))

    @commands.command(name = 'emoji', help = "Get the ID of an emoji in your server. It also shows you how to structure it in code.")   
    async def emoji(self, ctx, *, emoji_name):
        try:
            emoji = [emoji for emoji in await ctx.guild.fetch_emojis() if emoji.name == emoji_name][0]
        except discord.HTTPException:
            await ctx.reply("Error with fetching emojis.")
        else:
            await ctx.reply(f"ID: {emoji.id}\nStructure: \<a:{emoji_name}:{emoji.id}>")

    @commands.command(name = 'loadcog', aliases = ['unfreeze', 'load'], help = "Load a cog.")
    async def loadcog(self, ctx, *, cog_to_load = None):
        if ctx.author.id not in [672530816529596417, 566653183774949395]:
            await ctx.reply("you are not sigma owner.")
            return

        if cog_to_load:
            loaded = False
            for cog, aliases in list(self.cogs.items()):
                if cog_to_load in aliases or cog_to_load == cog.split('.')[len(cog.split('.')) - 1]:
                    try:
                        await self.bot.load_extension(cog)
                    except commands.errors.ExtensionAlreadyLoaded:
                        await ctx.reply(f"Extension `{cog}` is already loaded.")
                        return

                    await ctx.reply(f"Unfrozen all `{cog}` commands :ice_cube: :white_check_mark:")
                    loaded = True
            
            if not loaded:
                await ctx.reply("Not a valid cog :-1:")                
        else:
            await ctx.reply("No cog specified :x:")

    @commands.command(name = 'reloadcog', aliases = ['reload', 'rlc'], help = "Reload a cog.")
    async def reloadcog(self, ctx, *, cog_to_load = None):
        if ctx.author.id not in [672530816529596417, 566653183774949395]:
            await ctx.reply("you are not sigma owner.")
            return
        
        if cog_to_load:
            loaded = False
            for cog, aliases in list(self.cogs.items()):
                if cog_to_load in aliases or cog_to_load == cog.split('.')[len(cog.split('.')) - 1]:
                    try:
                        await self.bot.reload_extension(cog)
                    except commands.errors.ExtensionNotLoaded:
                        await ctx.reply("Extension isn't loaded.")
                        return

                    await ctx.reply(f"Refreshed all `{cog}` commands 🔄")
                    loaded = True
            
            if not loaded:
                await ctx.reply("Not a valid cog :-1:")                
        else:
            await ctx.reply("No cog specified :x:")

    @commands.command(name = 'unloadcog', aliases = ['freeze', 'unload'], help = "Unload a cog.")
    async def unloadcog(self, ctx, *, cog_to_load = None):
        if ctx.author.id not in [672530816529596417, 566653183774949395]:
            await ctx.reply("you are not sigma owner.")
            return
        
        if cog_to_load:
            loaded = False
            for cog, aliases in list(self.cogs.items()):
                if cog_to_load in aliases or cog_to_load == cog.split('.')[len(cog.split('.')) - 1]:
                    try:
                        await self.bot.unload_extension(cog)
                    except commands.errors.ExtensionNotLoaded:
                        await ctx.reply("Extension isn't loaded.")
                        return
                    
                    await ctx.reply(f"Frozen all `{cog}` commands :ice_cube: :white_check_mark:")
                    loaded = True
            
            if not loaded:
                await ctx.reply("Not a valid cog :-1:")                
        else:
            await ctx.reply("No cog specified :x:")

    @commands.command(name = 'say')
    async def say(self, ctx, *, message: str = None):
        if not message:
            await ctx.reply("write smth bro. what am i supposed to say :joy:")
            return
        
        await ctx.send(message)

    @commands.command(name = 'poll', aliases = ['vote'], help = "Create a poll with a desired question.\n\nTime inputs are \"_d _h _m _s\" and can be optional (ie. this is an accepted value: '1d 2s', this is not an accepted value: 'asdwas'). Weeks are not accepted.")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def poll(self, ctx, time: str = None, *, question: str = None):
        if ctx.author.id in [672530816529596417, 566653183774949395]:
            ctx.command.reset_cooldown(ctx)

        if not time or type(time) is not str:
            await ctx.reply("You have to specify a time for how long the poll runs.")
            ctx.command.reset_cooldown(ctx)
            return

        if not question or type(question) is not str:
            await ctx.reply("You need a question for the poll so people know what they're voting for.")
            ctx.command.reset_cooldown(ctx)
            return

        from datetime import datetime, timedelta

        read_time = time_reader(time)

        if read_time is InvalidInput:
            await ctx.reply("Invalid time input.")
            ctx.command.reset_cooldown(ctx)
            return

        future = int(datetime.timestamp(datetime.now() + timedelta(seconds = read_time)))

        embed = discord.Embed(
            title = f"{ctx.author.name}'s poll",
            description = f"Ending <t:{future}:R>",
            color = discord.Color.purple()
        )
        embed.add_field(name = "Question", value = question)

        view = VoteView(question = question, timeout = read_time)
        view.message = await ctx.send(embed = embed, view = view)
        
        await discord.utils.sleep_until(future)

        view.stop()
        await view.on_timeout()

    @poll.error
    async def poll_EH(self, ctx, error):
        if isinstance(error, commands.errors.CommandOnCooldown):
            await ctx.reply(f"You already ran a poll. Try again in {int(error.retry_after)}s")
            return
    
    @commands.command(name = 'colour', aliases = ['color', 'cl'], help = "Select a name colour from a dropdown menu of available colours. More to be added soon.")
    async def select_role_colour(self, ctx):
        view = RoleSelectView(ctx, self.bot)
        
        view.message = await ctx.reply(
            view = view,
            embed = discord.Embed(
                title = "Choose a Role",
                description = "Pick a colour below, and this will change the colour of your name in messages.",
                color = discord.Color.blue()
            )
        )
        await view.wait()

        selected = view.children[0].selected

        if not selected:
            await ctx.reply("You didn't select anything.")
            return

        try:
            role = discord.utils.get(ctx.guild.roles, name = selected)
        except Exception as e:
            embed = discord.Embed(
                title = "Woops, we've had an error!",
                description = f"Looks like there's been an error fetching the role name `{selected}`.\n\nTry making a role with that name and running the command again, or you can run `as create` to create all the roles for you.",
                color = discord.Color.red()
            )
            embed.set_footer(text = f"Exception: {e}")

            await ctx.reply(embed = embed)
            return

        try:
            await ctx.author.add_roles(role)
        except Exception as e:
            if ctx.author == ctx.guild.owner:
                await ctx.reply("I don't think I can do that for you, chief. Just the way Discord designed me.")
            
            elif ctx.me.top_role <= ctx.author.top_role:
                await ctx.reply("Your role is higher than mine, so I have to submit to you. I don't want to, but I have to.")

            elif isinstance(e, commands.BotMissingPermissions):
                await ctx.reply("Looks like I'm missing the `Manage Roles` permission. Can I please have it back?")
            
            else:
                await ctx.reply(f"```py\nException: {e}\n```")
            
            return

        await view.message.edit(
            embed = discord.Embed(
                title = "Added Roles",
                description = f"You have been given the role {role.mention}",
                color = discord.Color.green()
            )
        )
    
    @commands.command(name = 'create', help = "Create roles used for `as select` and is more helpful if you put me higher up in the role hierarchy. (That's the list of roles you see in the Roles tab on your Server settings)")
    @commands.has_permissions(manage_roles = True)
    async def create(self, ctx):
        from colours import Colours as C

        roles = [x[1] for x in RoleSelect(ctx.author).colours]
        status = dict.fromkeys(roles)
        loading = "<a:loading:1209630119157825606>"
        
        embed = discord.Embed(
            title = "Adding Roles...",
            description = None,
            color = discord.Color.red()
        )
        embed.add_field(
            name = "Role Colours",
            value = "\n".join([f"{name} {loading if not status[name] else '✅'}" for name in status.keys()])
        )
        message = await ctx.reply(embed = embed)

        for i, name in enumerate(roles):
            if not discord.utils.get(ctx.guild.roles, name = name):
                role = await ctx.guild.create_role(
                    name = name,
                    hoist = False,
                    colour = C().retrieve(name)
                )
                await asyncio.sleep(0.5)
                await role.edit(position = ctx.guild.me.top_role.position - 1)
            
            status[name] = True

            message_embed = message.embeds[0]

            if i == len(roles) - 1:
                message_embed.color = discord.Color.green()

            message_embed.clear_fields()
            message_embed.add_field(
                name = "Role Colours",
                value = "\n".join([f"{name} {loading if not status[name] else '✅'}" for name in status.keys()])
            )

            await message.edit(embed = message_embed)

            await asyncio.sleep(1)

    @commands.command(name = 'suggest', help = "Suggest an idea to make the bot even better! All suggestions accepted.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def suggest(self, ctx):
        view = SuggestionsView(ctx.author)
        
        view.message = await ctx.reply(
            view = view,
            embed = discord.Embed(
                title = "Suggestion",
                description = "Make a suggestion to improve the bot. All help would be appreciated!",
                color = discord.Color.green()
            )
        )

    @suggest.error
    async def suggest_EH(self, ctx, error):
        if isinstance(error, commands.errors.CommandOnCooldown):
            await ctx.reply(f"You can run this command again in {readable_time(int(error.retry_after))}")
        else:
            raise error
        
    @commands.command(name = 'suggestions', help = "Useful for viewing all suggestions made by users. Paginated as well!")
    async def suggestions(self, ctx):
        if ctx.author.id != 672530816529596417:
            await ctx.reply("nuh uh, you no do that")
            return
                  
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT * FROM suggestions")
            rows = await req.fetchall()

        view = DeleteSuggestionsView(user = ctx.author, page_size = 4, page_numbers = calc_page_num(len(rows), 4), bot = self.bot)
        view.add_item(DeleteSuggestionsButton(ctx.author))

        view.message = await ctx.reply(
            view = view,
            embed = discord.Embed(
                title = "Hold on...",
                description = "Give us a moment.",
                color = discord.Color.red()
            )
        )
        await view.display_page()
    
    @commands.command(name = 'user', aliases = ['lookup'], help = "Get info about a user.")
    async def user(self, ctx, user: discord.Member | int  = None):
        if not user:
            await ctx.reply("You didn't specify a user ID.")
            return
        
        if type(user) == int:
            user = self.bot.get_user(user)
        
            if not user:
                await ctx.message.add_reaction('‼️')
                return
        
        embed = discord.Embed(color = discord.Color.dark_embed())

        if type(user) == discord.Member:
            embed.set_author(name = f"{user.name}'s Information", icon_url = user.avatar)
            embed.add_field(
                name = "User Data",
                value = f"Nickname: {user.nick}\nID: {user.id}\nJoined: {discord.utils.format_dt(user.joined_at)}",
                inline = False
            )
        else:
            embed.set_author(name = f"{user.name}'s Information")

        embed.add_field(
            name = "Public Flags",
            value = "\n".join([f"{key}: {value}" for key, value in dict(user.public_flags).items()]),
            inline = False
        )
        
        await ctx.reply(embed = embed)
    
    @commands.command(name = 'avatar', aliases = ['av'], help = "See another user's avatar.")
    async def avatar(self, ctx, user: discord.Member = None):
        if not user:
            await ctx.reply("You need to specify a user.")
            return
        
        embed = discord.Embed(title = f"{user.name}'s Information", color = discord.Color.dark_embed())
        embed.set_image(url = user.avatar)

        await ctx.reply(embed = embed)


class DeleteSuggestionsView(BasicPaginator):
    def __init__(self, user: discord.Member, page_size: int, page_numbers: int, bot):
        super().__init__(user, page_size, page_numbers)
        self.timeout = None
        self.bot = bot
        self.pool = bot.pool
    
    async def display_page(self):
        async with self.pool.acquire() as conn:
            req = await conn.execute(f"SELECT * FROM suggestions LIMIT {self.page_size} OFFSET {(self.page - 1) * self.page_size}")
            rows = await req.fetchall()

        embed = discord.Embed(title = "Suggestions", color = discord.Color.blue())

        from datetime import datetime

        if len(rows) == 0:
            embed.description = "Hmm, weird, there's nothing here."
        else:
            for row in rows:
                embed.add_field(
                    name = row['name'],
                    value = f"{self.bot.get_user(row['author']).mention} suggested: \"{row['suggestion']}\"\nCreated at: {discord.utils.format_dt(datetime.fromtimestamp(row['time_made']))}\nID: {row['id']}"
                )
        
        await self.message.edit(view = self, embed = embed)

class DeleteSuggestionsButton(ui.Button):
    def __init__(self, user: discord.Member):
        super().__init__(label = "Delete All Suggestions", style = discord.ButtonStyle.red, row = 1)
        self.user = user

    async def on_callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("no permissions??", ephemeral = True)
            return

        await interaction.response.defer()

        async with interaction.client.pool.acquire() as conn:
            await conn.execute("DELETE FROM suggestions")
        
        await interaction.followup.send("Deleted the requested suggestion!", ephemeral = True)

class SuggestionsModal(ui.Modal):
    def __init__(self):
        super().__init__(title = "Suggestion", custom_id = "1")

    name = ui.TextInput(label = "Idea", style = discord.TextStyle.short)
    suggestion = ui.TextInput(label = "How it works", style = discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        with open('blacklisted_words.txt') as f:
            bad_words = f.read().split('\n')
            name_check = set([word in bad_words for word in str(self.name).split(' ')])
            sugg_check = set([word in bad_words for word in str(self.suggestion).split(' ')])

            if any(name_check) or any(sugg_check):
                await interaction.response.send_message(
                    embed = discord.Embed(
                        title = "Woops, something went wrong!",
                        description = "Looks like your submission contains blacklisted words. Please try again!",
                        color = discord.Color.red()
                    ), ephemeral = True, view = None
                )
                return
        
            async with interaction.client.pool.acquire() as conn:
                while True:
                    unique_id = random.randint(1, 10**5)
                    
                    req = await conn.execute("SELECT * FROM suggestions WHERE id = ?", (unique_id,))
                    row = await req.fetchone()

                    if not row:
                        break

                await conn.execute("INSERT INTO suggestions VALUES (?, ?, ?, ?, ?)",
                (unique_id, interaction.user.id, str(self.name), str(self.suggestion), int(time.time())))
        
            await interaction.response.send_message(
                embed = discord.Embed(
                    title = "Your suggestion went through! Thanks!",
                    description = f"**Name:** {str(self.name)}\n**Description:** {str(self.suggestion)}",
                    color = discord.Color.green()
                )
            )

class SuggestionsView(ui.View):
    def __init__(self, user):
        super().__init__(timeout = 20)
        self.suggestion_modal = SuggestionsModal()
        self.user = user

    @ui.button(label = "Make a Suggestion", style = discord.ButtonStyle.green)
    async def make_a_suggestion(self, interaction: discord.Interaction, button: discord.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("This is not your suggestion menu.", ephemeral = True)
            return

        button.disabled = True
        await self.message.edit(view = self)

        await interaction.response.send_modal(self.suggestion_modal)

class RoleSelectView(ui.View):
    def __init__(self, ctx, bot):
        super().__init__()
        self.add_item(RoleSelect(ctx))
        self.bot = bot

class RoleSelect(ui.Select):
    def __init__(self, ctx):
        self.ctx = ctx
        self.user = ctx.author
        self.selected = None
        self.colours = [['❤️', 'Light Red'], ['🧡', 'Light Orange'], ['💛', 'Light Yellow'], ['💚', 'Light Green'],
                        ['💙', 'Light Blue'], ['💜', 'Light Purple'], ['🖤', 'Black']]
        options = [discord.SelectOption(label = colour, description = f"Your name colour will be {colour.lower()}", emoji = emoji) for emoji, colour in self.colours]
        super().__init__(options = options, placeholder = "Select a role colour.")

    async def callback(self, interaction: discord.Interaction) -> Any:
        self.selected = self.values[0]

        if interaction.user != self.user:
            await interaction.response.send_message("This is not your menu.", ephemeral = True)
            return

        if discord.utils.get(self.ctx.author.roles, name = self.selected):
            await interaction.response.send_message("You already have that role.")
            return

        await interaction.response.send_message("Selected your role. Give us a second.", ephemeral = True)
        self.disabled = True
        await self.view.message.edit(view = self.view)
        self.view.stop()
    
async def setup(bot):
    await bot.add_cog(Utility(bot))