import os
import sys
from dotenv import load_dotenv
from lfg_bot.bot import LFGBot

# Load environment variables
load_dotenv()

def main():
    # Get token and validate
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("Error: No Discord bot token found. Check your .env file.")
        print("Make sure you have created a bot at https://discord.com/developers/applications")
        print("and added the token to the .env file as DISCORD_BOT_TOKEN=your_token_here")
        sys.exit(1)

    bot = LFGBot()
    bot.run(token)

if __name__ == '__main__':
    main()