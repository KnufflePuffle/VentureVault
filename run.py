import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path
from commands import register_commands
import db
from views import PlotpointButtons

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up Discord bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    """Event triggered when bot is ready"""
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

    # Initialize the database
    if db.init_db():
        print("Database initialized successfully")
    else:
        print("WARNING: Failed to initialize database")

    # Set up category and overview channel for each guild
    for guild in bot.guilds:
        await setup_guild(guild)

    print("Bot is ready!")


async def setup_guild(guild):
    """Set up the necessary category and overview channel for a guild"""
    # Look for "Plot Point LFG" category
    lfg_category = discord.utils.get(guild.categories, name="Plot Point LFG")

    # Create the category if it doesn't exist
    if not lfg_category:
        lfg_category = await guild.create_category("Plot Point LFG")
        print(f"Created 'Plot Point LFG' category in {guild.name}")

    # Look for "Plot-Point-Overview" channel in the category
    overview_channel = discord.utils.get(
        guild.text_channels,
        name="plot-point-overview",
        category=lfg_category
    )

    # Create the overview channel if it doesn't exist
    if not overview_channel:
        overview_channel = await guild.create_text_channel(
            "plot-point-overview",
            category=lfg_category
        )
        print(f"Created 'Plot-Point-Overview' channel in {guild.name}")

    # Update the overview message
    await update_overview_message(guild, overview_channel)


async def update_overview_message(guild, overview_channel=None):
    """Update the overview message with all plotpoints"""
    if not overview_channel:
        lfg_category = discord.utils.get(guild.categories, name="Plot Point LFG")
        if not lfg_category:
            return

        overview_channel = discord.utils.get(
            guild.text_channels,
            name="plot-point-overview",
            category=lfg_category
        )

        if not overview_channel:
            return

    # Clear existing messages in the channel
    try:
        await overview_channel.purge(limit=100)
    except Exception as e:
        print(f"Error clearing messages: {e}")

    # Send a header message with instructions
    await overview_channel.send(
        "# Plot Point Overview\nBelow are all registered plot points with their current status:")
    await overview_channel.send(
        "Use `!add_plotpoint <ID> <TITLE> <Description>` to create a new plot point.\nExample: `!add_plotpoint 01 THE BEGINNING This is where our adventure begins...`")

    # Fetch all plotpoints from database
    rows = db.get_plotpoints()

    if not rows:
        await overview_channel.send("No plot points have been added yet.")
        return

    # Group rows by status
    status_groups = {
        'Active': [],
        'Inactive': [],
        'Finished': []
    }

    for plotpoint in rows:
        status = plotpoint['status']
        if status not in status_groups:
            status = 'Inactive'  # Default if status is invalid

        status_groups[status].append(plotpoint)

    # Send messages for each status group
    for status, plotpoints in status_groups.items():
        if plotpoints:
            await overview_channel.send(f"## {status} Plot Points:")

            for plotpoint in plotpoints:
                view = PlotpointButtons(plotpoint['id'], plotpoint['status'])

                await overview_channel.send(
                    f"**{plotpoint['id']}: {plotpoint['title']}**\n{plotpoint['description']}",
                    view=view
                )


@bot.event
async def on_interaction(interaction):
    """Handle button interactions"""
    if not interaction.data or not interaction.data.get('custom_id'):
        return

    custom_id = interaction.data['custom_id']
    if not (custom_id.startswith('activate_') or
            custom_id.startswith('deactivate_') or
            custom_id.startswith('finish_')):
        return

    action, plotpoint_id = custom_id.split('_', 1)

    # Fetch the plotpoint from the database
    plotpoint = db.get_plotpoint_by_id(plotpoint_id)

    if not plotpoint:
        await interaction.response.send_message(
            content='Plot point not found or database error occurred.',
            ephemeral=True
        )
        return

    guild = interaction.guild
    category = discord.utils.get(guild.categories, name="Plot Point LFG")

    if not category:
        await interaction.response.send_message(
            content='Plot Point LFG category not found. Please contact an administrator.',
            ephemeral=True
        )
        return

    # Handle activation
    if action == 'activate':
        # Create a new channel for this plotpoint if it doesn't exist
        channel = None
        if plotpoint['channel_id']:
            channel = guild.get_channel(int(plotpoint['channel_id']))

        if not channel:
            channel = await guild.create_text_channel(
                f"plot-point-{plotpoint['id']}",
                category=category,
                topic=f"{plotpoint['title']} - {plotpoint['description'][:100]}..."
            )

            # Send initial message to the new channel
            await channel.send(
                f"# Plot Point {plotpoint['id']}: {plotpoint['title']}\n"
                f"{plotpoint['description']}\n\n"
                f"This channel is for discussion and coordination related to this plot point."
            )

        # Update plotpoint status in database
        if db.update_plotpoint_status(plotpoint_id, 'Active', str(channel.id)):
            await interaction.response.send_message(
                content=f"Plot Point {plotpoint_id} has been activated!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                content=f"Failed to update plot point status. Check database connection.",
                ephemeral=True
            )

    # Handle deactivation
    elif action == 'deactivate':
        # Delete the channel if it exists
        if plotpoint['channel_id']:
            channel = guild.get_channel(int(plotpoint['channel_id']))
            if channel:
                await channel.delete(reason="Plot point deactivated")

        # Update plotpoint status in database
        if db.update_plotpoint_status(plotpoint_id, 'Inactive'):
            await interaction.response.send_message(
                content=f"Plot Point {plotpoint_id} has been deactivated!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                content=f"Failed to update plot point status. Check database connection.",
                ephemeral=True
            )

    # Handle finishing
    elif action == 'finish':
        # Delete the channel if it exists
        if plotpoint['channel_id']:
            channel = guild.get_channel(int(plotpoint['channel_id']))
            if channel:
                await channel.delete(reason="Plot point finished")

        # Update plotpoint status in database
        if db.update_plotpoint_status(plotpoint_id, 'Finished'):
            await interaction.response.send_message(
                content=f"Plot Point {plotpoint_id} has been marked as finished!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                content=f"Failed to update plot point status. Check database connection.",
                ephemeral=True
            )

    # Update the overview message
    await update_overview_message(guild)


# Register commands from commands.py
register_commands(bot, update_overview_message)

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)