import discord
from discord.ext import commands
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-5s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('bot')

# Intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class LFGBot(commands.Bot):
    async def setup_hook(self):
        # Load all cogs in the cogs directory
        cog_dir = os.path.join(os.path.dirname(__file__), 'cogs')
        for filename in os.listdir(cog_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'lfg_bot.cogs.{filename[:-3]}')
                    logger.info(f'Loaded cog: {filename}')
                except Exception as e:
                    logger.error(f'Failed to load {filename}: {e}')

    async def on_ready(self):
        logger.info(f'Logged in as {self.user.name}')
        logger.info(f'Bot ID: {self.user.id}')
        logger.info('------')


def create_bot():
    """Create and return the bot instance"""
    return LFGBot(command_prefix='!', intents=intents)


# Error handling
def add_error_handlers(bot):
    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            logger.warning(f"Command not found: {ctx.message.content}")
            await ctx.send(f"Command not found. Try !help to see available commands.")
        else:
            logger.error(f"An error occurred: {error}")

    # Ping command for testing
    @bot.command()
    async def ping(ctx):
        await ctx.send('Pong!')


def run_bot():
    import os
    bot = create_bot()
    add_error_handlers(bot)

    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("No Discord token found. Set DISCORD_TOKEN environment variable.")
        raise ValueError("No Discord token found")

    bot.run(token)