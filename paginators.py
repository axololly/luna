import discord
from discord import ButtonStyle, Interaction, Button, ui
from discord.ext.commands import Bot
from typing import Callable

class BasicPaginator(ui.View):
    """
    Display something in a paginator format with a customisable display function.

    Parameters:
    - user: discord.Member (The user who invoked the paginator)
    - page_size: int (The size of the page)
    - page_count: int (The number of pages - use calc_page_size to get the page numbers)
    """
    def __init__(self, user: discord.Member, page_size: int, page_count: int, timeout: int = 20):
        super().__init__(timeout = timeout)
        self.user = user
        self.page = 1
        self.page_size = page_size
        self.page_count = page_count

    async def on_timeout(self):
        await self.message.edit(
            view = None,
            embed = discord.Embed(
                title = "Closed Window",
                description = "We have decided to close this view so it doesn't block most of the screen for other users or just yourself if you have no friends. Apologies for any inconvenience — it's just the way it is unfortunately.",
                color = discord.Color.red()
            )
        )

    async def display_page(self) -> None:
        """
        Display the data using your given method. Must be overrided with subclassing.
        """
        pass

    @ui.button(label = '<<', style = ButtonStyle.grey, disabled = True)
    async def fastfwdleft(self, interaction: Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("This isn't your interaction. Get your own.", ephemeral = True)
            return
        
        self.page = 1

        for i, child in enumerate(self.children):
            child.disabled = True if i < 2 else False

        await self.display_page()
        await interaction.response.defer()

    @ui.button(label = '<', style = ButtonStyle.blurple, disabled = True)
    async def left(self, interaction: Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("This isn't your interaction. Get your own.", ephemeral = True)
            return

        if self.page > 1:
            self.page -= 1
        
        for child in self.children:
            child.disabled = False

        if self.page == 1:
            for child in self.children[:2]:
                child.disabled = True
        
        await self.display_page()
        await interaction.response.defer()

    @ui.button(label = '>', style = ButtonStyle.blurple)
    async def right(self, interaction: Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("This isn't your interaction. Get your own.", ephemeral = True)
            return

        if self.page < self.page_count:
            self.page += 1

            for child in self.children[:2]:
                child.disabled = False

        for child in self.children:
            child.disabled = False
        
        if self.page == self.page_count:
            for child in self.children[2:-1]:
                child.disabled = True

        await self.display_page()
        await interaction.response.defer()
    
    @ui.button(label = '>>', style = ButtonStyle.grey)
    async def fastfwdright(self, interaction: Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("This isn't your interaction. Get your own.", ephemeral = True)
            return
        
        self.page = self.page_count

        for i, child in enumerate(self.children):
            if i > 1 and i < 4:
                child.disabled = True
            else:
                child.disabled = False

        await self.display_page()
        await interaction.response.defer()

def calc_page_num(items: int, page_size: int):
    """
    Calculate the number of pages that are needed to fit N items with K items per page.

    Paramters:
    - items: int (The number of items to be paginated)
    - page_size: int (The amount of items to be listed on each page)
    """

    from math import ceil

    pages = ceil(items / page_size)

    return pages