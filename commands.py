import re
import sqlite3
from discord.ext import commands
from db import DB_PATH


def register_commands(bot, update_overview_message):
    """Register all bot commands"""

    @bot.command(name='add_plot_point')
    async def add_plot_point(ctx, plotpoint_id: str, *, rest_of_command: str):
        """
        Add a new plot point to the system
        Format: !add_plot_point <plotpoint_id> <PLOTTITLE> <Description>
        """
        # Validate plotpoint_id format (e.g., 01, 02, 03a, 03b, 04, 13, 99)
        if not re.match(r'^(0?[1-9]|[1-9][0-9])[a-z]?$', plotpoint_id):
            await ctx.reply('Invalid plot point ID format. It should be like 01, 02, 03a, 13, 27b, up to 99.')
            return

        # Split the rest into title (all caps) and description
        parts = rest_of_command.split(' ')
        if len(parts) < 2:
            await ctx.reply('Invalid format. Use `!add_plot_point <plotpoint_id> <PLOTTITLE> <Description>`')
            return

        title_part = parts[0]
        description_start_idx = 1

        # Keep adding words to the title as long as they're all uppercase
        while (description_start_idx < len(parts) and
               parts[description_start_idx].isupper() and
               parts[description_start_idx].strip()):
            title_part += f" {parts[description_start_idx]}"
            description_start_idx += 1

        if description_start_idx >= len(parts):
            # No description provided or all words are uppercase
            await ctx.reply('Please provide a description after your all-caps title.')
            return

        title = title_part
        description = ' '.join(parts[description_start_idx:])

        # Ensure title is all uppercase
        if not title.isupper():
            await ctx.reply('The plot title must be in ALL CAPS.')
            return

        # Check if this ID already exists in the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM plotpoints WHERE id = ?", (plotpoint_id,))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            await ctx.reply(f'A plot point with ID {plotpoint_id} already exists.')
            return

        # Insert new plot_point
        try:
            cursor.execute(
                "INSERT INTO plotpoints (id, title, description) VALUES (?, ?, ?)",
                (plotpoint_id, title, description)
            )
            conn.commit()
            conn.close()

            await ctx.reply(f'Plot Point {plotpoint_id}: {title} has been added successfully!')

            # Update the overview message
            await update_overview_message(ctx.guild)
        except Exception as e:
            conn.close()
            print(f"Database error: {e}")
            await ctx.reply('An error occurred while adding the plot point.')

    @bot.command(name='help_lfg')
    async def help_lfg(ctx):
        """Display help information for the LFG bot commands"""
        help_text = """
# Plot Point LFG Bot Commands

**!add_plot_point <ID> <TITLE> <Description>**
Add a new plot point to the system.
- ID: Must be in format like 01, 02, 03a, 13, 27b, etc. (1-99 with optional letter)
- TITLE: Must be ALL CAPS
- Description: Regular text describing the plot point

**!help_lfg**
Show this help message.

# Examples:
`!add_plot_point 01 THE BEGINNING This is where our adventure begins...`
`!add_plot_point 13a SIDE QUEST This optional quest involves finding the lost artifact.`

# Status Management:
Use the buttons in the Plot-Point-Overview channel to:
- Activate a plot point (creates a dedicated channel)
- Deactivate a plot point (removes the channel)
- Mark a plot point as finished (removes the channel)
        """
        await ctx.send(help_text)