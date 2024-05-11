import discord, aiohttp, json, random, asyncio, html
from discord import ButtonStyle, Interaction, ui
from discord.ext import commands
from economy.levels import Levels
from _requestplayview import RequestToPlayView

class BoardIsFullError(Exception):
    pass

class Board:
    def __init__(self):
        self.board = [[0 for _ in range(7)] for _ in range(6)]

    def place_counter(self, column, player):
        if self.board[0][column - 1] == 0:
            self.board[0][column - 1] = player
            self.compress()
        else:
            return BoardIsFullError
    
    def compress(self):
        state = self.board

        for c, line in enumerate(state):
            for count, item in enumerate(line):
                if item != 0:
                    if c + 1 <= len(state) - 1:
                        if state[c + 1][count] == 0:
                            state[c + 1][count] = item
                            state[c][count] = 0
        
        self.board = state

    def read_lines(self, state):
        for board_line in state:
            repeats = 1
            item = None
            for iterable in board_line:
                if iterable != 0:
                    if iterable == item:
                        repeats += 1
                    elif not item:
                        pass
                    else:
                        repeats = 1
                    
                    item = iterable

                    if repeats == 4:
                        if item == 1:
                            return 1
                        if item == 2:
                            return 2
                else:
                    repeats = 1
                        
    def rotate_90(self, matrix): # rotate 90 degrees clockwize
        return [[matrix[-1-i][x] for i, _ in enumerate(matrix)] for x, _ in enumerate(matrix)]
    
    def horizontalflip(self, matrix): # flips along x axis
        return [line[::-1] for line in matrix]

    def get_new(self, x, y): # needed for rotate_45()
        if x + 1 > -1 and y - 1 > -1:
            return (x + 1, y - 1)

    def rotate_45(self, matrix): # rotate 45 degrees clockwise
        matrix_coords = [[(x, y) for x, _ in enumerate(line)] for y, line in enumerate(matrix)]

        last_row = matrix_coords[-1]
        first_col = [matrix_coords[i][0] for i, _ in enumerate(matrix_coords)]

        diag_starts = first_col + last_row[1:]
        diagonals = []
        
        for diagonal in diag_starts:
            x, y = diagonal
            D = []

            while self.get_new(x, y):
                try:
                    f = matrix_coords[y][x]
                except IndexError:
                    break
                else:
                    D.append((x, y))
                    x, y = self.get_new(x, y)

            D.append((x, y))
            
            diagonals.append(D)

        for d in diagonals:
            for c, v in enumerate(d):
                if v[0] == len(last_row):
                    del d[c]
                else:
                    x, y = v
                    d[c] = matrix[y][x]
        
        for i, d in enumerate(diagonals):
            if not d:
                del diagonals[i]
        
        return diagonals
    
    def check(self):
        wins = [
            self.read_lines(self.board),
            self.read_lines(self.rotate_90(self.board)),
            self.read_lines(self.rotate_45(self.board)),
            self.read_lines(self.rotate_45(self.horizontalflip(self.board)))
        ]

        if 1 in wins:
            return 1
        if 2 in wins:
            return 2
        
        zeroes = 0
        for line in self.board:
            zeroes += line.count(0)
        
        if zeroes == 0:
            return False

class TicTacToeButton(ui.Button):
    def __init__(self, _id):
        super().__init__(label = "\u200b", style = ButtonStyle.blurple,
                         row = _id // 3 - 1 if _id % 3 == 0 else _id // 3)
        self._id = _id
        
    async def callback(self, interaction: Interaction):
        await self.view.input_move(interaction, self, self._id)

class TicTacToeView(ui.View):
    def __init__(self, players, ctx = None, bet: int = 0, pool = None):
        super().__init__(timeout = 20)

        for i in range(9):
            self.add_item(TicTacToeButton(i + 1))
        
        self.pieces = {1: 'X', 2: 'O'}
        self.board = [[0 for _ in range(3)] for _ in range(3)]
        self.players = [None] + players # buffer to use L[x] instead of L[x - 1]
        self.turn = random.randint(1, 2)

        self.bet = bet
        self.pool = pool
        self.ctx = ctx

    async def on_callback(self):
        for child in self.children:
            child.disabled = True

    async def on_timeout(self):
        winner = [p for p in self.players if p and p != self.players[self.turn]][0]

        async with self.pool.acquire() as conn:
            await conn.execute(f"""UPDATE discord SET wallet = wallet + ?
                                   WHERE user_id = ?""", (self.bet * 2, winner.id))
        
        await self.on_callback()

        await self.message.edit(
            content = None,
            embed = discord.Embed(
                title = "⏰  **Timed out!**",
                description = f"""Looks like {self.players[self.turn].mention} ran from the game!
                                  
                                  _And oh? What's this? They also left behind `☾ {self.bet}` for {winner.mention}_""",
                color = 0xff9691
            ), view = self
        )

    def rotate_90(self, matrix): # rotate 90 degrees clockwize
        return [[matrix[-1-i][x] for i, _ in enumerate(matrix)] for x, _ in enumerate(matrix)]
    
    def check_for_wins(self):
        horizontal = [sum(line) for line in self.board]
        vertical = [sum(line) for line in self.rotate_90(self.board)]
        diagonals = [sum(self.board[x][x] for x in range(3)),
                    sum(self.board[2-x][x] for x in range(3))]

        lines = [horizontal, vertical, diagonals]

        for line in lines:
            if 3 in line:
                return 1
            elif -3 in line:
                return 2
            else:
                if sum([line.count(0) for line in self.board]) == 1:
                    return 0
    
    async def game_end_embed(self, result = None):
        if result or result == 0:
            rewardxp = random.randint(1, 15)

            if result == 0:
                header = "<:woeisme:1202950900604211220> Draw!"
                desc = "To be fair, it is just a 3x3 grid."
                colour = 0xc3b1e1
                
            elif result in [1, 2]:
                header = "🏆 Winner!"
                desc = f"""{self.players[result].mention} won as :{self.pieces[result].lower()}:
                            Looks like someone needs to step up their game.
                            
                            _And it looks like someone's XP level has stepped up! <a:xp:1206668715710742568>
                            (Check your level with `as xp`)""",
                colour = 0xfdfd96

                async with self.pool.acquire() as conn:
                    async with self.pool.acquire() as conn:
                        req = await conn.execute("SELECT xp FROM discord WHERE user_id = ?", (self.ctx.author.id,))
                        row = await req.fetchone()
                        old_xp = row[0]

                    from economy.levels import Levels
                    
                    rewardxp = random.randint(1, 15)
                    levels = Levels(bot = self.bot)
                    await levels.on_level_up(self.ctx, old_xp, old_xp + rewardxp)

                    await conn.execute(f"""UPDATE discord SET wallet = wallet + ?, xp = xp + ? WHERE user_id = ?""",
                                           (self.bet * 2, rewardxp, self.players[result].id))
            
            embed = discord.Embed(
                title = header,
                description = desc[0],
                color = colour
            )

            return embed
        
    async def input_move(self, interaction: Interaction, button: discord.Button, position: int):
        piece_display = {
            'X': '❌',
            'O': '⭕'
        }
        
        if interaction.user == self.players[self.turn]:
            button.label = piece_display[self.pieces[self.turn]]
            button.disabled = True

            if self.pieces[self.turn] == 'X':
                piece_to_place = 1
            if self.pieces[self.turn] == 'O':
                piece_to_place = -1

            x, y = divmod(position, 3)
            
            cells = [
                (0, 0), (0, 1), (0, 2),
                (1, 0), (1, 1), (1, 2),
                (2, 0), (2, 1), (2, 2)
            ]

            x, y = cells[position - 1]
            self.board[x][y] = piece_to_place
            
            if self.turn == 1:
                self.turn = 2
            else:
                self.turn = 1

            E = await self.game_end_embed(self.check_for_wins())
            if E:
                await self.on_callback()
                await interaction.response.edit_message(
                    content = None,
                    embed = E, view = self
                )
                self.stop()
            else:
                await interaction.response.edit_message(
                    content = self.players[self.turn].mention,
                    embed = None, view = self
                )

class ColumnsButton(ui.Button):
    def __init__(self, _id, row):
        super().__init__(label = _id, style = ButtonStyle.blurple, row = _id // 5)
        self._id = _id
    
    async def callback(self, interaction: Interaction):
        if interaction.user == self.view.players[self.view.player]:
            A = self.view.play_move(self._id)
            await self.view.play(A, interaction, self)
        else:
            await interaction.response.send_message(content = "it's not your turn.", ephemeral = True)

class Columns(ui.View):
    def __init__(self, players: list, bet: int = 0):
        super().__init__()
        self.board = Board()

        cancel_button = self.children[0]
        self.remove_item(cancel_button)

        for i in range(7):
            self.add_item(ColumnsButton(i + 1, row = i % 5))
        
        self.add_item(cancel_button)

        random.shuffle(players)
        self.users = players
        self.player = random.choice([1, 2])
        self.coin = ['🔴', '🟡'][self.player - 1]
        self.players = {n + 1: players[n] for n, _ in enumerate(players)}

        self.bet = bet
        self.timeout = 30
        self.cancelled = True
        self.cancel_user = self.players[self.player]

    async def on_callback(self):
        for item in self.children:
            item.disabled = True

    async def on_timeout(self):
        self.cancelled = True
        self.cancel_user = self.players[self.player]
        await self.on_callback()
        self.stop()

    def play_move(self, column):
        C = self.board.place_counter(column, self.player)

        if C is BoardIsFullError:
            return -1
        else:
            if self.board.check():
                return self.board.check()
            elif self.board.check() is False:
                return 0
            else:
                if self.player == 1:
                    self.player = 2
                else:
                    self.player =  1

    def retrieve_board(self):
        board_str = f":one::two::three::four::five::six::seven:\n" + \
                     "\n".join(["".join([str(i) for i in self.board.board[x]]) \
                                for x, _ in enumerate(self.board.board)])
        
        board_str = board_str.replace('0', '⬛').replace('1', '🔴').replace('2', '🟡')
        return board_str
    
    async def play(self, A, interaction, button):
        if A == -1:
            button.disabled = True
            await interaction.response.edit_message(content = self.players[self.player].mention, view = self)
        elif A == 0:
            await interaction.response.edit_message(embed = self.draw_embed, view = None)
            self.stop()
        elif A in [1, 2]:
            self.cancelled = False
            await self.on_callback()
            self.stop()
        else:
            if self.player == 1:
                self.coin = "🔴"
                embedcolour = discord.Color.red()
            else:
                self.coin = "🟡"
                embedcolour = 0xfdfd96

            await interaction.response.edit_message(
                content = self.players[self.player].mention,
                embed = discord.Embed(
                    title = f"{self.coin} Connect 4",
                    description = self.retrieve_board(),
                    color = embedcolour
                ), view = self)
    
    @ui.button(label = "❌", style = ButtonStyle.red, row = 1)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        if interaction.user in self.players.values():
            self.cancel = True

            if self.player == 1:
                self.coin = "🔴"
            else:
                self.coin = "🟡"

            await self.on_timeout()
            self.stop()
        else:
            await interaction.response.send_message(content = "you're not involved, lil bro", ephemeral = True)

class RockPaperScissorsView(ui.View):
    def __init__(self, player: discord.Member, timeout: int = 20):
        super().__init__()
        self.player = player
        self.timeout = timeout

        self.choice = None

    async def on_callback(self):
        for child in self.children:
            child.disabled = True

    async def on_timeout(self):
        await self.on_callback()
        await self.message.edit(
            content = None,
            embed = discord.Embed(
                title = "⏰  **Timed out!**",
                description = f"How hard is it to press a few buttons, {self.player.mention}?",
                color = 0xff9691
            ), view = self
        )
    
    @ui.button(style = ButtonStyle.blurple, emoji = "✊")
    async def rock(self, interaction: Interaction, button: discord.Button):
        if interaction.user == self.player and not self.choice:
            self.choice = "rock"
            await interaction.response.send_message(f"you played **{self.choice}**", ephemeral = True)
            self.stop()  
    
    @ui.button(style = ButtonStyle.blurple, emoji = "🖐️")
    async def paper(self, interaction: Interaction, button: discord.Button):
        if interaction.user == self.player and not self.choice:
            self.choice = "paper"
            await interaction.response.send_message(f"you played **{self.choice}**", ephemeral = True)
            self.stop()

    @ui.button(style = ButtonStyle.blurple, emoji = "✌️")
    async def scissors(self, interaction: Interaction, button: discord.Button):
        if interaction.user == self.player and not self.choice:
            self.choice = "scissors"
            await interaction.response.send_message(f"you played **{self.choice}**", ephemeral = True)
            self.stop()

def generate_loot(file_name: str, location: str) -> str | None:
    loot_tables = json.loads(open(f'./loot tables/{file_name}.json').read())

    try:
        loot_table = loot_tables[location] | {None: 100 - sum(list(loot_tables[location].values()))}
    except KeyError:
        return

    return random.choices(list(loot_table.keys()), weights = list(loot_table.values()), k = 1)[0]

def readable_time(time_in_seconds: int):
    days, hours = divmod(time_in_seconds, 24*60**2)
    hours, mins = divmod(hours, 60**2)
    mins, secs = divmod(mins, 60)

    time_units = ['d', 'h', 'm', 's']

    converted_time = " ".join([f"{int(unit)}{time_units[i]}" for i, unit in enumerate([days, hours, mins, secs]) if unit])
    return converted_time

class SearchButton(ui.Button):
    def __init__(self, ctx, user: discord.Member = None, bot = None, label: str = None, **kwargs):
        super().__init__(label = label, style = ButtonStyle.blurple, **kwargs)
        self.user = user
        self.bot = bot
        self.pool = bot.pool
        self.ctx = ctx

    async def searchforcoins(self, place):
        if random.randint(1, 100) / 100 > 1/3: # 66% chance of succeeding
            reward = random.randint(40, 400)
            embed = discord.Embed(
                title = "You found something!",
                description = f"You searched {place} and found a hefty sum of `☾ {reward}`. Nice work!",
                color = discord.Color.green()
            )
            rewarditem = generate_loot('search', place)
            sep = '<:separator:1206287822558986281>'

            if rewarditem:
                async with self.pool.acquire() as conn:
                    req = await conn.execute("SELECT item_id, emoji FROM shop WHERE name = ?", (rewarditem,))
                    row = await req.fetchone()
                    emoji = row['emoji']
                    rewarditem_id = row['item_id']

                embed.description += f"\n{sep} And lucky you, you found a **{rewarditem}**! {emoji}"

                async with self.pool.acquire() as conn:
                    await conn.execute(f"""INSERT INTO inventory (item_id, user_id, quantity) VALUES (?, ?, ?)
                                        ON CONFLICT(item_id, user_id) DO UPDATE
                                        SET quantity = quantity + excluded.quantity WHERE user_id = ?
                                        """, (rewarditem_id, self.user.id, 1, self.user.id))

            if random.random() < 0.2:
                rewardxp = random.randint(12, 20)
                embed.description += f"\n{sep} And oh? What's this? They also got **{rewardxp}** <a:xp:1206668715710742568>!"

                async with self.pool.acquire() as conn:
                    req = await conn.execute("SELECT xp FROM discord WHERE user_id = ?", (self.user.id,))
                    row = await req.fetchone()
                    old_xp = row['xp']
                    
                    await Levels(bot = self.bot).on_level_up(self.ctx, old_xp, old_xp + rewardxp)

                    await conn.execute("UPDATE discord SET xp = xp + ? WHERE user_id = ?", (rewardxp, self.user.id))
            
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (reward, self.user.id))
        else:
            embed = discord.Embed(
                title = "You found nothing!",
                description = f"You searched {place} and come up with nothing. Better luck next time!",
                color = discord.Color.red()
            )
        
        return embed

    async def callback(self, interaction: Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("do your own search lmao. go away :joy_cat: :-1:", ephemeral = True)
            return
        
        embed = await self.searchforcoins(self.label)

        for item in self.view.children:
            item.disabled = True

            if item.label == self.label:
                if "nothing" in embed.title:
                    item.style = discord.ButtonStyle.red
                else:
                    item.style = discord.ButtonStyle.green
            else:
                item.style = discord.ButtonStyle.grey
        
        await interaction.response.edit_message(embed = embed, view = self.view)
        self.view.stop()

class PlaceholderView(ui.View):
    def __init__(self, timeout = 20):
        super().__init__(timeout = timeout)
        self.selected = None
        self.value = None

    async def on_callback(self):
        for child in self.children:
            child.disabled = True
        
        await self.message.edit(view = self)

    async def on_timeout(self):
        await self.on_callback()
        await self.message.edit(
            content = None,
            embed = discord.Embed(
                title = "⏰  **Timed out!**",
                description = f"I ran out of ideas... what do I even put here?",
                color = discord.Color.red()
            ), view = self
        )

crimes = {
    "carjacking": [
        "You commit carjacking and earn yourself a nice new car. Congrats! Not many people get this far :tada:\n\nAnd the glove compartment even had _!",
        "The owner of the car sees you breaking the window with a rock and runs after you with a machete. As you run, you drop your prized wallet full of `☾ 500` and he grabs it off the floor. Next time, bring better tools :grimacing:"
    ],
    "steal a purse": [
        "You run past an elderly lady and yank the purse off her arm. She broke her dentures but the _ in her wallet was worth it!",
        "Someone sees you mugging a purse and they promptly trip you over, meaning you spill out what's in the purse and `☾ 500`. Wasn't worth it.",
    ],
    "punch an old lady": [
        "You punch an old lady and break her jaw. Did you get anything out of it? Just _. But was it fun? Yes. Yes it was.",
        "You punch an old lady and get your ass whooped by her purse. Next time, don't mess with Grandma."
    ],
    "burglary": [
        "Through an open window, you managed to grab a TV, a laptop, some cookies and _. That's a pretty nice haul if you ask me.",
        "In the dark of the night, you fling a heavy rock at someone's window. The sound wakes up everybody in the neighbourhood and sets off their alarms. "
    ],
    "cyberbullying": [
        "You destroy an 8-year-old in a Hypixel Duel and he starts crying in his mic. His mum offers you _ to leave him alone and you take it. feelsgoodman.jpg",
        "You thoroughly roast every part of an 8-year-old's mother and get banned from proximity chat for 2 weeks. For fu- \*banned\*"
    ],
    "arson": [
        "You launch a molotov at the Town Hall and successfully set it on fire. The campaign of arsonists rewards you with a collective _ for your leadership. Well done.",
        "You launch a molotov for your friends as a joke and the children's hospital goes up in flames. I'm deeply disappointed in you. You should be ashamed of yourself."
    ],
    "sell drugs": [
        "The drug addicts in your area completely devour the kilogram of cocaine you had on you, and in return, you made a whopping _. Good job.",
        "You get curious and end up getting high on your own supply. Now you have nothing but a bill from the hospital saying to pay `☾ 500`."
    ],
    "speeding": [
        "180mph on the dashboard as you're cruising down the motorway. You hit an animal and your car does a backflip. Insurance gives you _ but your head still hurts and your leg is broken. Was it worth it?",
        "Police in the area get reported to your car and while trying to get away, you collide head-on with the back of a lorry emergency braking to save a rabbit. Womp womp!"
    ],
    "hacking": [
        "You successfully hack into a bank but steal a measly _. TOR browser hid your IP but the FBI are still actively hunting you down.",
        "The YouTube tutorial doesn't work and you end up downloading a virus. Looks like hacking isn't a viable career option after all."
    ],
    "create ransomware": [
        "Your Bitcoin wallet fills up with _. That's a pretty good hustle in malware standards... at the expense of all the hospitals, companies, e- I don't think you care that much, do you?",
        "\"he really thought he could remake wannacry lmao\" \n - most of twitter after your awful ransomware attempt"
    ],
    "murder": [
        "You plunge a rusty knife in and out of a senior manager's chest as he leaves work in the middle of the night. In his classy suit, you see _ and take it for yourself. All the street hears is a few cries for help and the skidding of tyres. Mission successful.",
        "You murder a stranger in broad daylight and get arrested. Fucking idiot."
    ],
    "prank call": [
        "You prank someone posing as an insurance company and their dumbass actually gave you _. What an idiot!",
        "You call up someone and ask them if their refridgerator is running. They promptly respond with a yes and you tell them to go and catch it. Nobody but you is laughing. You weren't funny."
    ],
    "scam call": [
        "You scam call Microsoft and somehow get passwords to their accounts? Even I don't know what happened, but you managed to get _ so I won't judge - fair game.",
        "You pose as an electrician but fumble your opening line and they hang up on you. That was your only call of the day. Sorry, bud."
    ],
    "shoplifting": [
        "I guess they didn't question your pregnancy, even after the clothes fell out on the floor and were hastily picked up and stuffed under your T-shirt. It is 2024 after all: anyone can be pregnant™.\n\nThe clothes got you _ at a pawn shop.",
        "They saw you trying to take a handful of lollipops from the front desk. Like they _wouldn't_ have seen you stuffing them in your pockets 🙄"
    ],
    "touching grass": [
        "You open your door, take a deep breath in, exhale slowly and sit down on the front lawn, feeling the grass in your fingertips. You are free from all your worries- oh, you got a Discord ping. \"Oh hey! Look! _\"",
        "As a user of this discord bot, you are obligated to not go outside and touch grass. Don't do it again, or you will be banned!1!!11!"
    ]
}

class CrimeButton(ui.Button):
    def __init__(self, user: discord.Member, pool, label: str, **kwargs):
        super().__init__(label = label, style = ButtonStyle.blurple, **kwargs)
        self.user = user
        self.pool = pool

    async def commitcrime(self, place, user_id, interaction: Interaction):
        outcome = crimes[place]
        crime_payout = random.randint(750, 7500)

        if random.random() < 0.3: # 30% chance
            crime_embed = discord.Embed(
                title = "Crime Commited!",
                description = outcome[0].replace('_', f'`☾ {crime_payout:,}`'),
                color = discord.Color.green()
            )

            rewarditem = generate_loot('crime', place)
            
            if rewarditem:
                async with self.pool.acquire() as conn:
                    req = await conn.execute("SELECT item_id, emoji FROM shop WHERE name = ?", (rewarditem,))
                    row = await req.fetchone()

                sep = '<:separator:1206287822558986281>'
                crime_embed.description += f"\n{sep} And lucky you, you found a  {row['emoji']}  **{rewarditem}!**"

                async with self.pool.acquire() as conn:
                    await conn.execute(f"""INSERT INTO inventory (item_id, user_id, quantity) VALUES (?, ?, ?)
                                        ON CONFLICT(item_id, user_id) DO UPDATE
                                        SET quantity = quantity + excluded.quantity WHERE user_id = ?
                                        """, (row['item_id'], self.user.id, 1, self.user.id))

            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (crime_payout, user_id))

            color = discord.ButtonStyle.green
        else:
            crime_embed = discord.Embed(
                title = "Crime Failed",
                description = outcome[1],
                color = discord.Color.red()
            )
            crime_embed.set_footer(text = "You got fined for your stupidity. Say goodbye to your ☾ 500.")

            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = wallet - 500 WHERE user_id = ?", (user_id,))
            
            color = discord.ButtonStyle.red
        
        for child in self.view.children:
            if child.label == self.label:
                child.style = color
            else:
                child.style = discord.ButtonStyle.grey

        await interaction.response.edit_message(embed = crime_embed, view = self.view)
    
    async def callback(self, interaction: Interaction):
        if not interaction.user == self.user:
            await interaction.response.send_message("do your own crimes lmao. teaming up hasn't been added so go away :joy_cat: :-1:", ephemeral = True)
            return
        
        for item in self.view.children:
            item.disabled = True
        
        await self.commitcrime(self.label, interaction.user.id, interaction)
        self.view.stop()

class CryptoAskView(ui.View):
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
                description = "\"_BitConneeeeeeeeeeecct!_\"",
                color = discord.Color.brand_red()
            )
        )

    @ui.button(label = "Yes, I want to start trading crypto.", style = ButtonStyle.green)
    async def confirm(self, interaction: Interaction, button: discord.Button):
        if not interaction.user == self.user:
            await interaction.response.send_message("Not everything revolves around you.")
            return
        
        self.value = True

        await self.on_callback()
        await interaction.response.defer()
        self.stop()
    
    @ui.button(label = "No, I want to keep my money.", style = ButtonStyle.red)
    async def cancel(self, interaction: Interaction, button: discord.Button):
        if not interaction.user == self.user:
            await interaction.response.send_message("Not everything revolves around you.")
            return
        
        await self.message.edit(
            embed = discord.Embed(
                title = "Cancelled Crypto Trading",
                description = ":x: _You close the laptop lid and put it back on your bed, putting your legs up and watching TV instead._",
                color = discord.Color.brand_red()
            )
        )

        await self.on_callback()
        await interaction.response.defer()
        self.stop()

class CryptoGameView(ui.View):
    def __init__(self, OGI: int = None, pool = None):
        super().__init__()
        self.pool = pool

        self.iter_before_crash = random.randint(5, 15)
        self.original_investment = OGI
        self.percentage = random.randint(-10, 15)

        self.cashout = False

    async def on_callback(self):
        for child in self.children:
            child.disabled = True

        await self.message.edit(view = self)

    @ui.button(label = "Cash Out", style = ButtonStyle.green)
    async def cash_out(self, interaction: Interaction, button: discord.Button):
        self.cashout = True
        self.payout = int(self.original_investment * (1 + self.percentage/100))
        await self.on_callback()
        await interaction.response.defer()
        self.stop()

class PostMemesButton(ui.Button):
    def __init__(self, pool, user, device_id, label: str = None, **kwargs):
        super().__init__(label = label, style = ButtonStyle.blurple, **kwargs)
        self.pool = pool
        self.user = user
        self.device_id = device_id
        self.clicked_on = False

    async def on_timeout(self):
        for item in self.view.children:
            item.disabled = True
            item.style = ButtonStyle.grey

        self.view.message.edit(
            embed = discord.Embed(
                title = "⏰  Timed out!",
                description = "Looks like you weren't quick enough to post your memes and someone else stole all your Reddit karma. Sucks to suck!",
                color = discord.Color.red()
            ),
            view = self.view
        )

    async def callback(self, interaction: Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("go post your own memes  :joy_cat: :-1:", ephemeral = True)
            return

        if random.random() < 0.6:
            for item in self.view.children:
                item.disabled = True
                    
                if item.label != self.label:
                    item.style = ButtonStyle.grey
                else:
                    item.style = ButtonStyle.green
            
            await self.view.message.edit(view = self.view)

            reward = random.randint(400, 4000)
            message = f"Everyone **loves** your memes and you even scored yourself a nice `☾ {reward}`. Spend it wisely. Reddit isn't often this nice to newbies!"

            rewarditem = generate_loot('postmemes', 'meme_chances')

            if rewarditem:
                async with self.pool.acquire() as conn:
                    req = await conn.execute("SELECT item_id, emoji FROM shop WHERE name = ?", (rewarditem,))
                    row = await req.fetchone()
                    rewardemoji = row['emoji']
                    await conn.execute("""INSERT INTO inventory (item_id, user_id, quantity) VALUES (?, ?, ?)
                                            ON CONFLICT(item_id, user_id) DO UPDATE
                                            SET quantity = quantity + excluded.quantity WHERE user_id = ?""",
                                            (row['item_id'], interaction.user.id, 1, interaction.user.id))

                message += f"\nAnd would you look at that? The wonderful posters on r/memes decided to gift you a  {rewardemoji}  **{rewarditem}!**"

            await interaction.response.send_message(message, ephemeral = True)

            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (reward, interaction.user.id))
        
        else:
            for item in self.view.children:
                item.disabled = True

                if item.label != self.label:
                    item.style = ButtonStyle.grey
                else:
                    item.style = ButtonStyle.red
            
            await self.view.message.edit(view = self.view)
            
            if random.random() < 1/12:                
                async with self.pool.acquire() as conn:
                    if self.device_id == 25:
                        await interaction.response.send_message("Everybody **despises** your memes and your home network gets DDOSed. But it's alright - your killer gaming PC held up somehow.  <:thepcitself:1213109767803764776> :white_check_mark:")
                        return

                    await interaction.response.send_message("Everybody **despises** your memes and your home network gets DDOSed until the router and your device's motherboard gets fried. Looks like you'll have to get a new one!  <:laptop:1207641456215457802> :x:")

                    req = await conn.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (interaction.user.id, self.device_id))
                    row = await req.fetchone()
                    if row['quantity'] <= 1:
                        await conn.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ?", (interaction.user.id, self.device_id))
                    else:
                        await conn.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?", (interaction.user.id, self.device_id))
            else:
                await interaction.response.send_message(f"Everybody hates your memes and you got banned off of r/memes because you scored an abyssmal **{random.randint(-1000, -500)}** karma. Be ashamed of yourself, {interaction.user.mention}.")
        
        self.view.stop()

class TriviaView(ui.View):
    def __init__(self):
        super().__init__(timeout = 20)

    async def on_timeout(self):
        self.correct_answer = self.children[0].correct_answer

        for child in self.children:
            child.disabled = True

            if child.label == self.correct_answer:
                child.style = ButtonStyle.green
            else:
                child.style = ButtonStyle.grey

        await self.message.edit(
            view = self,
            embed = discord.Embed(
                title = "⏰  You ran out of time!",
                description = f"20 seconds and you still couldn't figure out the answer?\n\nOh well. The correct answer was {self.correct_answer} and you got **absolutely nothing** for your efforts!",
                color = discord.Color.red()
            )
        )

class TriviaButton(ui.Button):
    def __init__(self, user, pool, label, correctAnswer):
        super().__init__(label = label, style = ButtonStyle.blurple)
        self.user = user
        self.pool = pool
        self.correct_answer = correctAnswer

    async def callback(self, interaction: Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("hey! no helping! that's cheating!", ephemeral = True)
            return

        if self.label == self.correct_answer:           
            for child in self.view.children:
                child.style = ButtonStyle.grey
                child.disabled = True
            
            self.style = ButtonStyle.green

            reward = random.randint(1000, 3000)

            await self.view.message.edit(
                view = self.view,
                embed = discord.Embed(
                    title = "You got the correct answer!",
                    description = f"Well done on you for guessing **{html.unescape(self.correct_answer)}** and getting it right! Here's a treat: `☾ {reward}`",
                    color = discord.Color.green()
                )
            )

            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (reward, self.user.id))
        else:
            for child in self.view.children:
                if child.label == self.label:
                    self.style = ButtonStyle.red
                elif child.label == self.correct_answer:
                    child.style = ButtonStyle.green
                else:
                    child.style = ButtonStyle.grey
                
                child.disabled = True

            await self.view.message.edit(
                view = self.view,
                embed = discord.Embed(
                    title = "You got the wrong answer!",
                    description = f"Well done on you for guessing **{html.unescape(self.label)}** and getting it wrong. If you had gotten it right by clicking **{html.unescape(self.correct_answer)}**, I would've given you `☾ {random.randint(1000, 3000)}` but since you got it wrong, say goodbye to it. LOSER!",
                    color = discord.Color.red()
                )
            )
        
        await interaction.response.defer()
        self.view.stop()

class HigherOrLowerButton(ui.Button):
    def __init__(self, user, label, answer):
        super().__init__(label = label, style = ButtonStyle.blurple)
        self.user = user
        self.answer = answer
        self.selected = None
    
    async def on_timeout(self):
        for item in self.view.children:
            item.disabled = True

            if self.label == self.answer:
                item.style = ButtonStyle.green
            else:
                item.style = ButtonStyle.grey
        
        await self.view.message.edit(
            view = self.view,
            embed = discord.Embed(
                title = "⏰  Ran out of time!",
                description = f"Looks like you ran out of time to decide. You could've gotten `☾ {random.randint(300, 3000)}` but instead, you decided to do something less important. Kiss your winnings goodbye!",
                color = discord.Color.red()
            )
        )
    
    async def callback(self, interaction: Interaction):
        for item in self.view.children:
            item.disabled = True

            if item.label == self.answer:
                if item.label == self.label:
                    item.style = ButtonStyle.green
                else:
                    item.style = ButtonStyle.red
            else:
                item.style = ButtonStyle.grey
        
        self.selected = self.label
        await interaction.response.edit_message(view = self.view)
        self.view.stop()

class SimonSaysButton(ui.Button):
    def __init__(self, user, label, **kwargs):
        super().__init__(label = label, style = ButtonStyle.blurple, **kwargs)
        self.user = user
        self.selected_board_size = None

    async def callback(self, interaction: Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("Play your own game of Simon Says with `as simonsays`!")
            return
        
        self.selected_board_size = int(self.label[0])

        for item in self.view.children:
            item.disabled = True
            if item.label == self.label:
                item.style = ButtonStyle.green
            else:
                item.style = ButtonStyle.grey

        await self.view.message.edit(view = self.view)
        await interaction.response.defer()
        self.view.stop()

class SimonSaysIntroView(ui.View):
    def __init__(self, user):
        super().__init__(timeout = 15)
        self.user = user

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        await self.message.edit(
            view = self,
            embed = discord.Embed(
                title = "⏰  Timed out!",
                description = "\"You don't wanna play with Mommy~?\" - me, probably",
                color = discord.Color.red()
            )
        )

class SimonSaysView(ui.View):
    def __init__(self, user, correct_order, selected_board_size):
        super().__init__(timeout = 15)
        self.user = user
        self.correct_order = correct_order
        self.failed = False
        self.index = 0

        for i in range(selected_board_size**2):
            self.add_item(SimonSaysGameButton(i + 1, selected_board_size, disabled = True))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        await self.message.edit(
            view = self,
            embed = discord.Embed(
                title = "⏰  Timed out!",
                description = "It's one thing if you tried and even if you failed, I would've given you money, but since you didn't even try, you get nothing. You deserve it.",
                color = discord.Color.red()
            )
        )

class SimonSaysGameButton(ui.Button):
    def __init__(self, _id, board_size, disabled):
        super().__init__(label = "\u200b", style = ButtonStyle.blurple,  disabled = disabled,
                         row = _id // board_size - 1 if _id % board_size == 0 else _id // board_size)
        self.id = _id
        self.board_size = board_size

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        correct_button = self.view.correct_order[self.view.index]

        if correct_button == self.id:
            self.view.index += 1

            if self.view.index == len(self.view.correct_order):
                for child in self.view.children:
                    child.disabled = True

                rounds_completed = len(self.view.correct_order) - self.board_size + 1

                await self.view.message.edit(
                    view = self.view,
                    embed = discord.Embed(
                        title = "Simon Says",
                        description = f"Well done! You got them all right. Prepare for the next round!\n\nRounds completed: `{rounds_completed}`\nReward so far: `☾ {rounds_completed * 100}`",
                        color = discord.Color.green()
                    )
                )

                await asyncio.sleep(1.5)
                self.view.index = 0
                self.view.correct_order.append(random.randint(1, self.board_size**2))

                await self.view.message.edit(
                    view = self.view,
                    embed = discord.Embed(
                        title = "Simon Says",
                        description = "Watch closely, a pattern is going to flash on the screen!",
                        color = discord.Color.dark_embed()
                    )
                )

                for _id in self.view.correct_order:
                    self.view.children[_id - 1].style = ButtonStyle.green
                    await self.view.message.edit(view = self.view)

                    await asyncio.sleep(0.5)

                    self.view.children[_id - 1].style = ButtonStyle.blurple
                    await self.view.message.edit(view = self.view)

                for child in self.view.children:
                    child.disabled = False
                
                await self.view.message.edit(view = self.view)
        else:
            for child in self.view.children:
                child.disabled = True
                if child.id == self.id:
                    child.style = ButtonStyle.red
                elif child.id == correct_button:
                    child.style = ButtonStyle.green
                else:
                    child.style = ButtonStyle.grey

            winnings = (len(self.view.correct_order) - self.board_size) * self.board_size * 100
            if winnings == 0:
                winnings = 50

            await self.view.message.edit(
                view = self.view,
                embed = discord.Embed(
                    title = "Simon Says",
                    description = f"You were supposed to click **button {correct_button}** but you clicked **button {self.id}** instead!\n\nBut it's okay. Looks like you ended up taking home `☾ {winnings}` as a treat. Well done, play again in 3 and a half minutes, and thank you so much for playing with my bot! :heart:",
                    color = discord.Color.purple()
                )
            )
            self.view.stop()

class ChooseDeviceButton(ui.Button):
    def __init__(self, label, **kwargs):
        super().__init__(label = label, style = ButtonStyle.blurple, **kwargs)
        
    async def callback(self, interaction: Interaction):
        if interaction.user != self.view.user:
            await interaction.response.send_message("This isn't your menu.")
            return

        self.view.selected = self.label
        await interaction.response.defer()
        await self.view.on_timeout()
        self.view.stop()

class ChooseDeviceView(ui.View):
    def __init__(self, user):
        super().__init__(timeout = 20)
        self.user = user
        self.selected = None
        
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
            item.style = ButtonStyle.grey
        
        await self.message.edit(view = self)


class Minigames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.pool
        self.draw_embed = discord.Embed(
            title = "Draw! <:woeisme:1202950900604211220>",
            description = f"Looks like both of you suck. Damn.",
            color = 0xfdfd96
        )

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandOnCooldown):
            await ctx.reply(f"You used **{ctx.command.name}** already. Take a break and go outside, then come back in `{readable_time(int(error.retry_after))}`! :park:")
        else:
            raise error
    
    async def check_for_account(self, id):
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (id,))
            row = await req.fetchone()

            if row:
                return True
            
            return False

    async def check_for_wins(self, p, o):
        if p == o:
            return 0
        else:
            if p == "rock" and o == "scissors" or p == "paper" and o == "rock" or p == "scissors" and o == "paper":
                return 1
            if p == "rock" and o == "paper" or p == "paper" and o == "scissors" or p == "scissors" and o == "rock":
                return 2

    @commands.command(name = 'tweet', help = "Tweet your opinion and get tomatoes thrown at you by the Twitter userbase. However, there's a pretty cool reward if you tread lightly and get to the other side.\n\nThe users on Twitter are ruthless. Make sure you don't get your router DDOSed!")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def tweet(self, ctx):
        if not await self.check_for_account(ctx.author.id):
            await ctx.reply("You need a bank account for this. How else are you gonna pay for Twitter Blue?")
            ctx.command.reset_cooldown(ctx)
            return

        if ctx.author.id in [672530816529596417]:
            ctx.command.reset_cooldown(ctx)

        view = ChooseDeviceView(ctx.author)

        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ? AND item_id IN (8, 23, 25, 26)", (ctx.author.id,))

            devices_dict = {8: 'laptop', 23: 'mobile phone', 25: 'desktop', 26: 'monitor'}
            devices = [devices_dict[row['item_id']] for row in await req.fetchall()]

            if not ("laptop" in devices or "mobile phone" in devices or 'desktop' in devices and 'monitor' in devices):
                await ctx.reply("You don't even have a laptop, a phone or a proper setup! What are you supposed to post memes on?")
                ctx.command.reset_cooldown(ctx)
                return

            req = await conn.execute("SELECT * FROM using_items WHERE item_id = 24 AND user_id = ?", (ctx.author.id,))
            row = await req.fetchone()

            if row:
                outcome = generate_loot('tweet', 'twitter blue')
            else:
                outcome = generate_loot('tweet', 'normal')
        
        if not(len(devices) == 1 or devices == ['desktop', 'monitor']):
            view.selected = "Desktop PC"

            added_desktop = False

            for i, device in enumerate(devices):
                if ('desktop' in devices and 'monitor' in devices):
                    if device == 'desktop' and devices[i + 1] == 'monitor' and not added_desktop:
                        view.add_item(ChooseDeviceButton(label = "Desktop PC"))
                        added_desktop = True
                        continue
                else:
                    view.add_item(ChooseDeviceButton(label = device.capitalize()))

            view.message = await ctx.reply(
                view = view,
                embed = discord.Embed(
                    title = "Choose a device to tweet on",
                    description = "Pick a device below. Be warned: the device you choose might get fried if someone tries to fry your router.",
                    color = discord.Color.blue()
                )
            )
            await view.wait()

            if not view.selected:
                ctx.command.reset_cooldown(ctx)
                return
        
            await view.message.delete()

        if '_' in outcome:
            reward = random.randint(5000, 10000)
            outcome = outcome.replace('_', f"`☾ {str(reward)}`")

            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (reward, ctx.author.id))
            
            await ctx.reply(
                embed = discord.Embed(
                    title = "Success!",
                    description = f"Your tweet actually did something! {outcome}",
                    color = discord.Color.green()
                )
            )
            return
        
        elif 'stole' in outcome:
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = 0 WHERE user_id = ?", (ctx.author.id,))

            await ctx.reply(
                embed = discord.Embed(
                    title = "Where did my money go?",
                    description = outcome,
                    color = discord.Color.red()
                )
            )
        
        elif 'DDOS' in outcome:
            async with self.pool.acquire() as conn:
                if view.selected == "Desktop PC":
                    device = ('25', '26')
                else:
                    req = await conn.execute("SELECT item_id FROM shop WHERE name = ?", (view.value,))
                    row = await req.fetchone()
                    device = (row['item_id'],)

                req = await conn.execute(f"SELECT item_id, quantity FROM inventory WHERE user_id = ? AND item_id IN ({', '.join(device)})", (ctx.author.id, device))
                rows = [(row['item_id'], row['quantity']) for row in await req.fetchall()]

                for item_id, quantity in rows:
                    if quantity - 1 > 0:
                        await conn.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?", (ctx.author.id, item_id))
                    else:
                        await conn.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ?", (ctx.author.id, item_id))
                
                await ctx.reply(
                    embed = discord.Embed(
                        title = "What happened to my device?",
                        description = outcome + f"\n\nYour {view.value} got destroyed and you had to throw it out in the garbage.",
                        color = discord.Color.red()
                    )
                )

        else:
            await ctx.reply(
                embed = discord.Embed(
                    title = "The usual.",
                    description = outcome,
                    color = discord.Color.yellow()
                )
            )

    @commands.command(name = "rock paper scissors", aliases = ['rps'], help = "Play Rock Paper Scissors with another user.\n\nBets are optional. You cannot bet what you don't have.")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def rps(self, ctx, opponent: discord.Member = None, amount: int = None):
        if amount < 0:
            await ctx.reply("can't use negative numbers. im not stupid lmao")
            return
        
        if not opponent or opponent == ctx.author:
            await ctx.reply("can't play with yourself. go touch grass and find some new friends! :park:")
            return
        
        if opponent == self.bot:
            await ctx.reply("my maker didn't give me arms to play  :x:")
            return
        
        if not await self.check_for_account(ctx.author.id):
            await ctx.reply("Looks like you don't have an account. Make one with `as bal` today!")
            ctx.command.reset_cooldown(ctx)
            return
        
        if not await self.check_for_account(opponent.id):
            await ctx.reply(f"Looks like {opponent.mention} don't have an account. Make one with `as bal` today!")
            ctx.command.reset_cooldown(ctx)
            return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT game FROM in_games WHERE user_id = ?", (ctx.author.id,))
            row = await req.fetchone()

            if row:
                embed = discord.Embed(
                    title = "Opponent in a Game",
                    description = f"Looks like {opponent.mention} is already playing a game. Wait until they're done and you can ask to play them again!",
                    color = discord.Color.brand_red()
                )
                embed.set_footer(text = f"Opponent is playing {row['game']} at the moment.")

            
                await ctx.reply(embed = embed)
                return

            for player in [ctx.author, opponent]:
                req = await conn.execute(f"SELECT wallet FROM discord WHERE user_id = ?", (player.id,))
                row = await req.fetchone()

                if row['wallet'] < amount:
                    await ctx.reply(f"Looks like {player.mention} doesn't have enough money to play.")
                    ctx.command.reset_cooldown(ctx)
                    return
        
        view = RequestToPlayView(ctx.author, opponent, game = "Rock Paper Scissors", bet = amount)
        requestToPlay = discord.Embed(
            title = ":mag: Someone wants to play a game of Rock Paper Scissors!",
            description = f"{opponent.mention}, do you want to take up the challenge?",
            color = 0xbffcc6
        )
        view.message = await ctx.reply(
            content = opponent.mention, embed = requestToPlay, view = view
        )
        await view.wait()

        if view.value:
            async with self.pool.acquire() as conn:
                await conn.execute("INSERT INTO in_games VALUES (?, ?)", (ctx.author.id, "Rock Paper Scissors"))

            await view.message.delete()

            rpsview1 = RockPaperScissorsView(ctx.author)
            rpsview1.message = await ctx.reply(
                embed = discord.Embed(
                    title = "Rock Paper Scissors",
                    description = f"""{ctx.author.mention}  \❌
                                      {opponent.mention}  \❌

                                      {ctx.author.mention}, make your move!""",
                    color = 0xc3b1e1
                ), view = rpsview1
            )
            await rpsview1.wait()
            p = rpsview1.choice

            rpsview2 = RockPaperScissorsView(opponent)

            await rpsview1.message.edit(
                embed = discord.Embed(
                    title = "Rock Paper Scissors",
                    description = f"""{ctx.author.mention}  \✅
                                      {opponent.mention}  \❌

                                      {opponent.mention}, make your move!""",
                    color = 0xc3b1e1
                ), view = rpsview2
            )
            
            await rpsview2.wait()
            o = rpsview2.choice

            win = await self.check_for_wins(p, o)
            await rpsview1.on_callback()

            if win == 0:
                async with self.pool.acquire() as conn:
                    await conn.execute(f"UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (amount, ctx.author.id))
                    await conn.execute(f"UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (amount, opponent.id))

                await rpsview1.message.edit(
                    embed = discord.Embed(
                        title = "Draw! <:pain:1203002986331242536>",
                        description = f"""{ctx.author.mention}:  \✅
                                          {opponent.mention}:  \✅
                                          
                                          Looks like a draw! {ctx.author.mention} :handshake: {opponent.mention}""",
                        color = discord.Color.green()
                    ), view = rpsview2
                )
                return

            if win == 1:
                async with self.pool.acquire() as conn:
                    req = await conn.execute("SELECT xp FROM discord WHERE user_id = ?", (ctx.author.id,))
                    row = await req.fetchone()
                    old_xp = row[0]

                    rewardxp = random.randint(1, 15)
                    levels = Levels(bot = self.bot)
                    levels.on_level_up(ctx, old_xp, old_xp + rewardxp)

                    await conn.execute(f"UPDATE discord SET wallet = wallet + ?, xp = xp + ? WHERE user_id = ?", (amount, rewardxp, ctx.author.id))

                await rpsview1.message.edit(
                    embed = discord.Embed(
                        title = "Winner! :trophy:",
                        description = f"""{ctx.author.mention}  \✅
                                          {opponent.mention}  \✅

                                          {ctx.author.mention} won with **{p}** and got some XP! <a:xp:1206668715710742568>""",
                        color = 0xfffaa0
                    ), view = rpsview2
                )
            
            if win == 2:
                async with self.pool.acquire() as conn:
                    req = await conn.execute("SELECT xp FROM discord WHERE user_id = ?", (ctx.author.id,))
                    row = await req.fetchone()
                    old_xp = row[0]

                    rewardxp = random.randint(1, 15)
                    levels = Levels(bot = self.bot)
                    await levels.on_level_up(ctx, old_xp, old_xp + rewardxp)
                    
                    await conn.execute(f"UPDATE discord SET wallet = wallet + ?, xp = xp + ? WHERE user_id = ?", (2 * amount, rewardxp, opponent.id))

                await rpsview1.message.edit(
                    embed = discord.Embed(
                        title = "Winner! <:holymoly:1205945639435903106>",
                        description = f"""{ctx.author.mention}  \✅
                                          {opponent.mention}  \✅
                                  
                                          {opponent.mention} won with **{o}** and got some XP! <a:xp:1206668715710742568>""",
                        color = 0xfffaa0
                    ), view = rpsview2
                )
    
    @commands.command(name = "connect4", aliases = ['c4'], help = "Play Connect 4 with another user. You cannot play with someone in a game.\n\nBets are optional. You cannot bet what you don't have.")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def connect4(self, ctx, opponent: discord.Member = None, amount: int = 0):
        if amount < 0:
            await ctx.reply("can't use negative numbers. im not stupid lmao")
            return
        
        if not opponent or opponent == ctx.author:
            await ctx.reply("can't play with yourself. go touch grass and find some new friends! :park:")
            return
        
        if opponent == self.bot:
            await ctx.reply("my maker didn't give me arms to play  :x:")
            return
        
        if not await self.check_for_account(ctx.author.id):
            await ctx.reply("Looks like you don't have an account. Make one with `as bal` today!")
            ctx.command.reset_cooldown(ctx)
            return
        
        if not await self.check_for_account(opponent.id):
            await ctx.reply(f"Looks like {opponent.mention} don't have an account. Make one with `as bal` today!")
            ctx.command.reset_cooldown(ctx)
            return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT game FROM in_games WHERE user_id = ?", (ctx.author.id,))
            row = await req.fetchone()

            if row:
                embed = discord.Embed(
                    title = "Opponent in a Game",
                    description = f"Looks like {opponent.mention} is already playing a game. Wait until they're done and you can ask to play them again!",
                    color = discord.Color.brand_red()
                )
                embed.set_footer(text = f"Opponent is playing {row['game']} at the moment.")

                await ctx.reply(embed = embed)
                return
            
            for player in [ctx.author, opponent]:
                req = await conn.execute(f"SELECT wallet FROM discord WHERE user_id = ?", (player.id,))
                row = await req.fetchone()

                if row['wallet'] < amount:
                    await ctx.reply(f"Looks like {player.mention} doesn't have enough money to play.")
                    ctx.command.reset_cooldown(ctx)
                    return
        
        if opponent and opponent not in [ctx.author, self.bot]:
            view = RequestToPlayView(ctx.author, opponent, game = "Connect 4", bet = amount)
            requestToPlay = discord.Embed(
                title = ":mag: Someone wants to play a game of Connect 4!",
                description = f"{opponent.mention}, do you want to bet `☾ {amount}` and play Connect 4?",
                color = 0xbffcc6
            )
            view.message = await ctx.reply(
                content = opponent.mention, embed = requestToPlay, view = view
            )
            await view.wait()

            if view.value:
                await view.message.delete()
                ColView = Columns([ctx.author, opponent], amount)
                board_message = await ctx.send(
                    content = ColView.players[ColView.player].mention,
                    embed = discord.Embed(
                        title = "**Connect 4**",
                        description = ColView.retrieve_board(),
                        color = discord.Color.blurple()
                    ), view = ColView
                )

                await ColView.wait()

                if not ColView.cancelled:
                    async with self.pool.acquire() as conn:
                        req = await conn.execute("SELECT xp FROM discord WHERE user_id = ?", (ColView.players[ColView.player].id,))
                        row = await req.fetchone()
                        old_xp = row[0]

                    from economy.levels import Levels
                    
                    rewardxp = random.randint(1, 15)
                    levels = Levels(bot = self.bot)
                    await levels.on_level_up(ctx, old_xp, old_xp + rewardxp)
                    
                    await board_message.edit(
                        content = None,
                        embed = discord.Embed(
                            title = "🏆 Connect 4",
                            description = f"""{ColView.retrieve_board()}\n
                                        Looks like {ColView.players[ColView.player].mention} won the game! Well done!
                                        
                                        _And oh, what's this? They also won_ `☾ {amount * 2}`_ and some XP!_ <a:xp:1206668715710742568>
                                        (Check your level with `as xp`)""",
                            color = discord.Color.green()
                        ), view = None
                    )

                    await conn.execute(f"""UPDATE discord SET wallet =  wallet + ?, xp = xp + ? WHERE user_id = ?""",
                                           (amount * 2, rewardxp, ColView.players[ColView.player].id))
                else:
                    winner = ColView.players[ColView.users.index([p for p in ColView.users if p != ColView.players[ColView.player]][0]) + 1]

                    from economy.levels import Levels
                    
                    rewardxp = random.randint(1, 15)
                    levels = Levels(bot = self.bot)

                    async with self.pool.acquire() as conn:
                        req = await conn.execute("SELECT xp FROM discord WHERE user_id = ?", (ctx.author.id,))
                        row = await req.fetchone()
                        old_xp = row[0]

                    await levels.on_level_up(ctx, old_xp, old_xp + rewardxp)

                    await board_message.edit(
                        content = ColView.players[ColView.player].mention,
                        embed = discord.Embed(
                            title = f"{ColView.coin} Connect 4",
                            description = f"""{ColView.retrieve_board()}\n
                                            💸 {ColView.cancel_user.mention} ran from the match!
                                            Looks like they left behind `☾ {amount * 2}` for {winner.mention} and some extra XP!
                                            (Check your level with `as xp`)""",
                            color = 0xf8c8dc
                        ), view = None
                    )

                    await conn.execute(f"""UPDATE discord SET wallet = wallet + ?, xp = xp + ? WHERE user_id = ?""",
                                           (amount * 2, rewardxp, winner.id))
        else:
            await ctx.reply("Can't play with me. I'm busy. :x:")
    
    @commands.command(name = "tictactoe", aliases = ['ttt'], help = "Play tic-tac-toe with another user. You cannot play with someone in a game.\n\nBets are optional. You cannot bet what you don't have.")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def tictactoe(self, ctx, opponent: discord.Member = None, amount: int = 0):
        if amount < 0:
            await ctx.reply("can't use negative numbers. im not stupid lmao")
            return
        
        if not opponent or opponent == ctx.author:
            await ctx.reply("can't play with yourself. go touch grass and find some new friends! :park:")
            return
        
        if opponent == self.bot:
            await ctx.reply("my maker didn't give me arms to play  :x:")
            return
        
        if not await self.check_for_account(ctx.author.id):
            await ctx.reply("Looks like you don't have an account. Make one with `as bal` today!")
            ctx.command.reset_cooldown(ctx)
            return
        
        if not await self.check_for_account(opponent.id):
            await ctx.reply(f"Looks like {opponent.mention} don't have an account. Make one with `as bal` today!")
            ctx.command.reset_cooldown(ctx)
            return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT game FROM in_games WHERE user_id = ?", (ctx.author.id,))
            row = await req.fetchone()

            if row:
                embed = discord.Embed(
                    title = "Opponent in a Game",
                    description = f"Looks like {opponent.mention} is already playing a game. Wait until they're done and you can ask to play them again!",
                    color = discord.Color.brand_red()
                )
                embed.set_footer(text = f"Opponent is playing {row['game']} at the moment.")
                
                await ctx.reply(embed = embed)
                return
            
            for player in [ctx.author, opponent]:
                req = await conn.execute(f"SELECT wallet FROM discord WHERE user_id = ?", (player.id,))
                row = await req.fetchone()

                if row['wallet'] < amount:
                    await ctx.reply(f"Looks like {player.mention} doesn't have enough money to play.")
                    ctx.command.reset_cooldown(ctx)
                    return
        
        view = RequestToPlayView(ctx.author, opponent, game = "Tic-Tac-Toe", bet = amount)
        requestToPlay = discord.Embed(
            title = ":mag: Someone wants to play a game of Tic-Tac-Toe!",
            description = f"{opponent.mention}, do you want to bet `☾ {amount}` and take up the challenge?",
            color = 0xbffcc6
        )
        view.message = await ctx.reply(
            embed = requestToPlay, view = view,
            allowed_mentions = discord.AllowedMentions(users = False)
        )
        await view.wait()

        if view.value:
            await view.message.delete()
            tttview = TicTacToeView([ctx.author, opponent], pool = self.pool, ctx = ctx)
            tttview.message = await ctx.reply(
                tttview.players[tttview.turn].mention, view = tttview,
                allowed_mentions = discord.AllowedMentions(users = False)
            )
            await tttview.wait()
        else:
            ctx.command.reset_cooldown(ctx)

    @commands.command(name = 'highlow', aliases = ['hl'])
    @commands.cooldown(1, 180, commands.BucketType.user)
    async def highlow(self, ctx):
        if not await self.check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            return

        view = PlaceholderView()

        hidden = random.randint(1, 100)
        displayed = random.randint(1, 100)

        if hidden < displayed:
            answer = 'Lower'
        elif hidden == displayed:
            answer = 'Jackpot'
        else:
            answer = 'Higher'

        for label in ['Lower', 'Jackpot', 'Higher']:
            view.add_item(HigherOrLowerButton(ctx.author, label, answer))

        embed = discord.Embed(
            title = "Higher Or Lower",
            description = f"I'm thinking of a number, and you have to decide whether the number I give you is higher, lower or _exactly_ the number I'm thinking of. In the case of it being exactly what I'm thinking of, there's a healthy jackpot waiting for you.\n\nYour number: **{displayed}**",
            color = discord.Color.blue()
        )
        embed.set_footer(text = "It's up to you what you decide, and there's a special reward if you get it right.")

        view.message = await ctx.reply(
            view = view,
            embed = embed
        )
        await view.wait()

        try:
            view.selected = [item.selected for item in view.children if item.selected][0]
        except IndexError:
            return
        
        if view.selected == answer:
            if answer == 'Jackpot':
                reward = random.randint(5000, 10000)

                await view.message.edit(
                    embed = discord.Embed(
                        title = "You won the jackpot! :moneybag:",
                        description = f"You won an amazing `☾ {reward}` and one hell of a celebration. Well done! :partying_face: :tada:",
                        color = discord.Color.brand_green()
                    )
                )
            else:
                reward = random.randint(1000, 3000)

                await view.message.edit(
                    embed = discord.Embed(
                        title = "You won some money! :moneybag:",
                        description = f"You won a pretty hefty bag of `☾ {reward}` and deserve one hell of a pat on the back. Well done! :speaking_head: :heart:",
                        color = discord.Color.brand_green()
                    )
                )
            
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (reward, ctx.author.id))
        else:
            await view.message.edit(
                embed = discord.Embed(
                    title = "You won... absolutely NOTHING",
                    description = f"You didn't get it right, so you win NOTHING! Loser! How can you not play a primary school game??",
                    color = discord.Color.brand_red()
                )
            )

    @commands.command(name = 'trivia')
    @commands.cooldown(1, 120, commands.BucketType.user)
    async def trivia(self, ctx):
        if not await self.check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            return

        message = await ctx.reply("Fetching some questions, wait there  <a:loading:1209630119157825606>")
        import urllib3

        view = TriviaView()
        try:
            async with aiohttp.ClientSession() as cs:
                async with cs.get('https://opentdb.com/api.php?amount=1') as response:
                    data = await response.json()

        except urllib3.exceptions.MaxRetryError:
            await ctx.reply(
                embed = discord.Embed(
                    title = "API error",
                    description = "Woops, looks like something went wrong getting your trivia questions. As it's on me, I'll remove the cooldown so you can run it again.",
                    color = discord.Color.red()
                )
            )
            ctx.command.reset_cooldown(ctx)
            return

        try:
            data = data['results'][0]
        except:
            await ctx.reply(
                embed = discord.Embed(
                    title = "API error",
                    description = "Woops, looks like something went wrong converting data for your trivia questions. As it's on me, I'll remove the cooldown so you can run it again.",
                    color = discord.Color.red()
                )
            )
            ctx.command.reset_cooldown(ctx)
            return

        correct_answer = html.unescape(data['correct_answer'])
        options = data['incorrect_answers'].copy()
        options.append(correct_answer)

        random.shuffle(options)
        options = [html.unescape(option) for option in options]

        for option in options:
            view.add_item(TriviaButton(ctx.author, self.pool, option, correct_answer))

        category = " ".join(data['category'].split('_'))

        embed = discord.Embed(
            title = "Trivia Time!",
            description = f"Category: {category}\nDifficulty: {data['difficulty'].capitalize()}",
            color = discord.Color.blue()
        )
        embed.add_field(name = "Question:", value = html.unescape(data['question']))

        view.message = await message.edit(content = None, embed = embed, view = view)
        await view.wait()

    @commands.command(name = 'postmemes', aliases = ['pm', 'postmeme'])
    @commands.cooldown(1, 150, commands.BucketType.user)
    async def postmemes(self, ctx):
        if not await self.check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            ctx.command.reset_cooldown(ctx)
            return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT * FROM inventory WHERE user_id = ? AND item_id in (8, 23, 25, 26)", (ctx.author.id,))
            rows = await req.fetchall()

        view = ChooseDeviceView(ctx.author)
        
        if len(rows) > 0:
            devices_dict = {8: 'laptop', 23: 'phone', 25: 'desktop', 26: 'monitor'}
            raw_devices = [devices_dict[row['item_id']] for row in rows]
            devices = []

            if "laptop" in raw_devices:
                devices.append("Laptop")
            
            if "phone" in raw_devices:
                devices.append("Phone")
            
            if "desktop" in raw_devices and "monitor" in raw_devices:
                devices.append("Desktop")

            for device in devices:
                view.add_item(ChooseDeviceButton(device))

            view.message = await ctx.reply(
                view = view,
                embed = discord.Embed(
                    title = "Choose a device to post memes on",
                    description = "Since you can't post memes on all your devices at the same time, you have to pick one to do this with. Select below the device you want to use.\n\n_Careful, it might get fried!_",
                    color = discord.Color.dark_embed()
                )
            )
            await view.wait()

            if not view.selected:
                ctx.command.reset_cooldown(ctx)
                return
        else:
            await ctx.reply("What are you supposed to post memes on? Your fridge?  :joy:")
            return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT item_id FROM shop WHERE name = ?", (view.selected,))
            row = await req.fetchone()
            device_in_use_id = row['item_id']
        
        meme_choices = ['dead meme', 'repost meme', 'normie meme', 'gen Z meme', 'youtube shorts meme',
                                  'tiktok meme', 'indian lore meme', 'hood irony meme', 'shitpost meme']
        options = random.sample(meme_choices, k = 3)

        await view.message.delete()

        view = PlaceholderView()

        for option in options:
            view.add_item(PostMemesButton(pool = self.pool, user = ctx.author, label = option, device_id = device_in_use_id))

        view.message = await ctx.reply(
            embed = discord.Embed(
                title = "Post Memes",
                description = "What memes do you want to post today?",
                color = discord.Color.blue()
            ), view = view
        )

    @commands.command(name = 'search')
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def search(self, ctx):
        if not await self.check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            return
        
        places_to_search = [
            "the sofa", "the car", "the mailbox", "the bank", "the shop",
            "the washing machine", "the grass", "a tree", "the cupboard", "under your bed",
            "your wardrobe", "the drawers", "your coat", "your pockets",  "the bathroom"
        ]
        search_options = random.sample(places_to_search, k = 3)

        view = PlaceholderView()

        for option in search_options:
            view.add_item(SearchButton(ctx, ctx.author, self.bot, option))
        
        view.message = await ctx.reply(
            view = view,
            embed = discord.Embed(
                title = "Search  :mag:",
                description = "Where do you want to look?",
                color = discord.Color.dark_embed()
            )
        )    

    @commands.command(name = 'crypto', help = "Trade crypto on the stock market.\n\nNeeds a laptop or desktop to perform this. Can be upgraded with Graphics Cards.")
    @commands.cooldown(1, 240, commands.BucketType.user)
    async def crypto(self, ctx, original_investment: int | str = None):
        if not await self.check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            ctx.command.reset_cooldown(ctx)
            return
        
        if not original_investment:
            await ctx.reply("You need to put actual money into crypto. No cheating!")
            ctx.command.reset_cooldown(ctx)
            return
        
        original_investment = str(original_investment)
        
        if ',' in original_investment:
            original_investment = float(original_investment.replace(',', ''))
                    
        elif original_investment[-1] == 'k':
            original_investment = float(original_investment[:-1]) * 10**3
                    
        elif original_investment[-1] == 'm':
            original_investment = float(original_investment[:-1]) * 10**6

        try:
            original_investment = int(original_investment)
        except ValueError:
            await ctx.reply("you need to put actual money into crypto lmao. no stealing.")
            ctx.command.reset_cooldown(ctx)
            return

        if original_investment > 2*10**5:
            await ctx.reply("That's too much! We can't accept that!")
            ctx.command.reset_cooldown(ctx)
            return

        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT user_id FROM inventory WHERE item_id IN (8, 25, 26)")
            row = await req.fetchone()
            
            if not row:
                await ctx.reply("You need a laptop or a desktop and monitor to trade crypto. Buy one from the shop!")
                ctx.command.reset_cooldown(ctx)
                return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (ctx.author.id,))
            row = await req.fetchone()
            wallet = row['wallet']

            req = await conn.execute("SELECT * FROM inventory WHERE item_id = 47 AND user_id = ?", (ctx.author.id,))
            row = await req.fetchone()
            gtx1080 = row['quantity'] if row else 0

            req = await conn.execute("SELECT * FROM inventory WHERE item_id = 48 AND user_id = ?", (ctx.author.id,))
            row = await req.fetchone()
            gtx3090 = row['quantity'] if row else 0

            cap = 5
            gtx1080 = cap if gtx1080 > cap else gtx1080
            gtx3090 = cap if gtx3090 > cap else gtx3090
        
        if wallet < 2000 or original_investment < 2000:
            await ctx.reply("You need at least ☾ 2000 to start trading crypto.")
            ctx.command.reset_cooldown(ctx)
            return

        view = CryptoAskView(ctx.author)
        view.message = await ctx.reply(
            embed = discord.Embed(
                title = "Crypto Trading",
                description = "The stocks could be volatile right now, and you might be at risk of losing all your money. Are you sure you want to start trading crypto?",
                color = discord.Color.dark_embed()
            ), view = view
        )
        await view.wait()

        if not view.value:
            ctx.command.reset_cooldown(ctx)
            return

        await view.message.delete()

        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE discord SET wallet = wallet - ? WHERE user_id = ?", (original_investment, ctx.author.id))

        view = CryptoGameView(pool = self.pool, OGI = original_investment)

        if abs(view.percentage) == view.percentage:
            arrow = "<:greenarrowup:1206939568759373854>"
            percent = f"+{view.percentage}"
        else:
            arrow = "<:redarrowdown:1206939567211421696>"
            percent = view.percentage

        view.message = await ctx.reply(
            content = f"Current percentage: **{percent}** {arrow}", view = view
        )

        for _ in range(random.randint(5, 15)):
            view.percentage += random.randint(-150 - int(7.5*gtx1080) - 15*gtx3090, 150)
            
            if abs(view.percentage) == view.percentage:
                arrow = "<:greenarrowup:1206939568759373854>"
                percent = f"+{view.percentage}"
            else:
                arrow = "<:redarrowdown:1206939567211421696>"
                percent = view.percentage
            
            await view.message.edit(
                content = f"Current percentage: **{percent}%** {arrow}", view = view
            )

            if view.cashout:
                break

            await asyncio.sleep(2)
            
        if view.cashout:
            view.payout += view.payout * (2 * gtx1080 + 5 * gtx3090)
            boost = f"{gtx1080*2}x boost from {gtx1080} GTX 1080 Ti, {gtx3090*5}x boost from {gtx3090} GTX 3090"

            if view.payout > original_investment:
                embed = discord.Embed(
                    title = "Profit!  <:greenarrowup:1206939568759373854> 💰",
                    description = f"Well done! You played the stock market and earned yourself a nice treat of `☾ {view.payout:,}`. To let the markets recover, you have to wait 10 minutes before you can play the markets again. Have to make it fair!",
                    color = discord.Color.brand_green()
                )
                embed.set_footer(text = boost)
                await view.message.edit(embed = embed)
                
                if random.randint(1, 10) <= 3:
                    rewardxp = random.randint(15, 30)
                else:
                    rewardxp = 0

                async with self.pool.acquire() as conn:
                    await conn.execute("UPDATE discord SET wallet = wallet + ?, xp = xp + ? WHERE user_id = ?", (view.payout, rewardxp, ctx.author.id))
                    
            elif view.payout < original_investment and view.payout > 0:
                embed = discord.Embed(
                    title = "Can you call it a loss?  <:redarrowdown:1206939567211421696> 💰",
                    description = f"Congrats! You didn't play the stock market: you played yourself! `☾ {(original_investment - view.payout):,}` has gone down the drain, leaving you with just `☾ {view.payout:,}` to spare. Sit and think about your actions for 10 minutes, then decide if you want to trade crypto again.",
                    color = discord.Color.yellow()
                )
                embed.set_footer(text = boost)
                await view.message.edit(embed = embed)
                
                async with self.pool.acquire() as conn:
                    await conn.execute("UPDATE discord SET wallet = wallet + ? WHERE user_id = ?", (view.payout, ctx.author.id))
                
            else:
                await view.message.edit(
                    embed = discord.Embed(
                        title = "Loss!  <:redarrowdown:1206939567211421696> 💰",
                        description = f"Congrats! You didn't play the stock market: you played yourself! `☾ {view.original_investment:,}` has gone down the drain. Sit and think about your actions for 10 minutes, then decide if you want to trade crypto again.",
                        color = discord.Color.brand_red()
                    )
                )
        else:
            await view.message.edit(
                embed = discord.Embed(
                    title = "Loss!  <:redarrowdown:1206939567211421696> 💰",
                    description = f"Congrats! You didn't play the stock market: you played yourself! `☾ {view.original_investment:,}` has gone down the drain. Sit and think about your actions for 10 minutes, then decide if you want to trade crypto again.",
                    color = discord.Color.brand_red()
                )
            )
    
    @commands.command(name = 'crime')
    @commands.cooldown(1, 150, commands.BucketType.user)
    async def crime(self, ctx):
        if not await self.check_for_account(ctx.author.id):
            await ctx.reply("You don't even have an account. What are you supposed to use to get money?")
            return
        
        async with self.pool.acquire() as conn:
            req = await conn.execute("SELECT wallet FROM discord WHERE user_id = ?", (ctx.author.id,))
            row = await req.fetchone()
            wallet = row['wallet']

        if wallet < 500:
            await ctx.reply("You need at least ☾ 500 to commit a crime. Sorry bud, it's just the way it is.")
            ctx.command.reset_cooldown(ctx)
            return

        view = PlaceholderView()

        crime_options = random.sample(sorted(crimes), k = 3)
        crime_options = {option: crimes[option] for option in crime_options}

        for option in crime_options:
            view.add_item(CrimeButton(ctx.author, self.pool, option))

        view.message = await ctx.reply(
            embed = discord.Embed(
                title = "Are you sure you want to commit a crime?",
                description = "Crimes are kinda bad, yk. It like breaks the law and stuff. Not good.\nAre you sure you want to go with this?",
                color = discord.Color.blue()
            ), view = view
        )

    @commands.command(name = 'simonsays', aliases = ['ss'])
    @commands.cooldown(1, 210, commands.BucketType.user)
    async def simonsays(self, ctx):
        introview = SimonSaysIntroView(ctx.author)
        for label in ['3x3', '4x4', '5x5']:
            introview.add_item(SimonSaysButton(ctx.author, label))

        embed = discord.Embed(
            title = "Simon Says",
            description = "You can choose between a 3x3 board (9 tiles), a 4x4 board (16 tiles) and a 5x5 board. Keep in mind, the bigger the board, the higher pay you can earn, but the tougher it ends up being.\n\n3x3 board payout: `☾ 100 per correct`\n4x4 board payout: `☾ 200 per correct`\n5x5 board payout: `☾ 350 per correct`\n\nGood luck!",
            color = discord.Color.pink()
        )
        embed.set_footer(text = "To make it fair, cooldown is 3 and a half minutes.")

        introview.message = await ctx.reply(
            view = introview,
            embed = embed
        )
        await introview.wait()

        try:
            selected_board_size = [child.selected_board_size for child in introview.children if child.selected_board_size][0]
        except:
            #ctx.command.reset_cooldown(ctx)
            return

        if selected_board_size:
            sequence = random.choices(list(range(selected_board_size**2)), k = selected_board_size)
            introview.clear_items()
            
            view = SimonSaysView(ctx.author, list(map(lambda s: s + 1, sequence)), selected_board_size)
            view.message = introview.message
        
            await view.message.edit(
                view = view,
                embed = discord.Embed(
                    title = "Simon Says",
                    description = "Watch closely, a pattern is going to flash on the screen!",
                    color = discord.Color.dark_embed()
                )
            )
            await asyncio.sleep(1)

            for _id in sequence:
                view.children[_id].style = ButtonStyle.green
                await view.message.edit(view = view)
                await asyncio.sleep(0.5)
                view.children[_id].style = ButtonStyle.blurple
                await view.message.edit(view = view)
            
            for child in view.children:
                child.disabled = False
            
            await view.message.edit(
                view = view,
                embed = discord.Embed(
                    title = "Simon Says",
                    description = "Okay, now it's your turn! Copy the pattern I just showed you onto the buttons down below.",
                    color = discord.Color.blue()
                )
            )

async def setup(bot):
    await bot.add_cog(Minigames(bot))