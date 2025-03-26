import discord
from discord.ext import commands
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class VentureVaultBot(commands.Bot):
    async def setup_hook(self):
        # Load all cogs in the cogs directory
        for filename in os.listdir('./lfg_bot/cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    # Use this to prevent multiple loads
                    if f'lfg_bot.cogs.{filename[:-3]}' not in self.extensions:
                        await self.load_extension(f'lfg_bot.cogs.{filename[:-3]}')
                        print(f'Loaded {filename}')
                except Exception as e:
                    print(f'Failed to load {filename}: {e}')
# Create bot instance
bot = VentureVaultBot(command_prefix='!', intents=intents)

# Error handling for command not found
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Command not found. Try !help to see available commands.")
    else:
        # Log other types of errors
        print(f"An error occurred: {error}")

# Optional: Add a ping command to test bot connectivity
@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

# Run the bot (get token from environment variable or config file)
def run_bot():
    import os
    token = os.getenv('DISCORD_TOKEN')  # Make sure to set this environment variable
    if not token:
        raise ValueError("No Discord token found. Set DISCORD_TOKEN environment variable.")
    bot.run(token)

if __name__ == '__main__':
    run_bot()