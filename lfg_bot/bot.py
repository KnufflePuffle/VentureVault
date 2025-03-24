import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()


class LFGBot(commands.Bot):
    def __init__(self):
        # Configure intents with all privileged intents
        intents = discord.Intents.all()

        super().__init__(
            command_prefix='!',
            intents=intents
        )

    async def setup_hook(self):
        # Use async setup for cogs
        await self.load_extension('lfg_bot.cogs.lfg')

        # Optional: Sync application commands
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged in as {self.user.name}')
        print(f'Bot ID: {self.user.id}')