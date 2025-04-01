import os
import sys
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
# Configure logging to be cleaner
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Don't print environment variables
if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)


    @bot.event
    async def on_ready():
        print(f"Bot is ready! Connected as {bot.user}")
        print(f"Connected to {len(bot.guilds)} servers")


    # Load extensions
    async def load_extensions():
        # Update the path to where your cogs are located
        cogs_path = './lfg_bot/cogs'
        if not os.path.exists(cogs_path):
            print(f"Warning: Path {cogs_path} does not exist.")
            return

        for filename in os.listdir(cogs_path):
            if filename.endswith('.py'):
                try:
                    # Update the import path to include lfg_bot
                    await bot.load_extension(f'lfg_bot.cogs.{filename[:-3]}')
                    print(f"Loaded {filename}")
                except commands.ExtensionAlreadyLoaded:
                    print(f"Extension {filename} is already loaded. Skipping.")
                except Exception as e:
                    print(f"Failed to load {filename}: {e}")


    # Run the bot
    async def main():
        async with bot:
            await load_extensions()
            await bot.start(os.getenv('DISCORD_TOKEN'))


    # Start the bot
    asyncio.run(main())