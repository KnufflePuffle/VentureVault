import os
import sys
from dotenv import load_dotenv
import discord
from discord.ext import commands
import logging
from lfg_bot.bot import VentureVaultBot  # Import the bot class from the correct location

# Load environment variables from .env file
load_dotenv()

# Configure logging
#logging.basicConfig(level=logging.INFO)

# Intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


def main():
    # Print current working directory
   # print(f"Current working directory: {os.getcwd()}")

    # Print all environment variables (be careful with sensitive info in production)
   # print("Environment variables:")
    for key, value in os.environ.items():
        if 'TOKEN' in key or 'SECRET' in key:
            print(f"{key}: ***REDACTED***")
        else:
            print(f"{key}: {value}")

    # Try to get token
    token = os.getenv('DISCORD_TOKEN')

    # Additional debugging
    #print(f"Token from os.getenv(): {token}")
    #print(f"Token is None: {token is None}")
    #print(f"Token length: {len(token) if token else 'N/A'}")

    # Create bot instance
    bot = VentureVaultBot(command_prefix='!', intents=intents)

    if not token:
        print("ERROR: No Discord token found!")
        raise ValueError("No Discord token found. Set DISCORD_TOKEN in .env file.")

    bot.run(token)


if __name__ == '__main__':
    main()